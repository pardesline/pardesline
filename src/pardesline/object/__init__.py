"""``pl.Object``: one typed handle for every 3D file.

An Object is a file on disk plus what the file alone cannot tell you: its
coordinate frame and units, the meaning of its labels, its licence and the
provenance of every step that produced it. Subclasses (:class:`PointCloud`,
:class:`Mesh`, :class:`Volume`, :class:`LabelMap`, :class:`Transform`,
:class:`Image`) add the conversions that are well defined for that kind.

    >>> import pardesline as pl
    >>> ct = pl.load("ct.mha")            # Volume, frame LPS/mm read from the header
    >>> ct.frame.describe()
    'LPS, mm (file)'
    >>> mask = ct.segment(lower=200, upper=600)
    >>> surface = mask.to_mesh(label=1)   # exact: boundary of label 1
    >>> surface.save("la.ply")            # file + la.ply.pardesline.json (frame, licence, provenance)
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from .._version import __version__
from ..catalog import Method, load_catalog
from ..errors import ManifestError, MissingDependency, ParameterError
from ..runner import output_dir
from ..runner import run as _run
from . import arrays, convert
from .arrays import ARRAY_EXTS, is_array_file
from .frame import FORMAT_FRAMES, ITK_VOLUME_EXTS, Frame, License

__all__ = [
    "ALIASES",
    "ARRAY_EXTS",
    "KIND_BY_EXT",
    "SIDECAR_SUFFIX",
    "Frame",
    "Image",
    "LabelMap",
    "License",
    "Mesh",
    "Object",
    "PointCloud",
    "RawArray",
    "Transform",
    "Volume",
    "kind_of",
    "load_object",
    "wrap",
]

SIDECAR_SUFFIX = ".pardesline.json"

KIND_BY_EXT: dict[str, str] = {
    ".ply": "pointcloud",
    ".pcd": "pointcloud",
    ".xyz": "pointcloud",
    ".txt": "pointcloud",
    ".pts": "pointcloud",
    ".las": "pointcloud",
    ".laz": "pointcloud",
    ".stl": "mesh",
    ".obj": "mesh",
    ".off": "mesh",
    ".glb": "mesh",
    ".gltf": "mesh",
    ".vtp": "mesh",
    ".vti": "volume",
    ".vtu": "volume",
    ".vtk": "volume",
    ".mha": "volume",
    ".mhd": "volume",
    ".nrrd": "volume",
    ".nii": "volume",
    ".nii.gz": "volume",
    ".dcm": "volume",
    ".ima": "volume",
    ".tfm": "transform",
    ".hdf5": "transform",
    ".h5": "transform",
    ".mat": "transform",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".zip": "archive",
    ".tar": "archive",
    ".gz": "archive",
    # raw arrays: typed only once a layout says what the numbers are
    ".npy": "array",
    ".npz": "array",
    ".bin": "array",
    ".raw": "array",
}

# Friendly names -> (module, method). Kept small and obvious; everything else
# is reachable through obj.run("module.method", ...).
ALIASES: dict[str, tuple[str, str]] = {
    "downsample": ("point_cloud_processing", "voxel_downsample"),
    "remove_outliers": ("point_cloud_processing", "statistical_outlier_removal"),
    "normals": ("features_extraction", "normal_estimation"),
    "poisson": ("point_cloud_reconstruction", "poisson"),
    "ball_pivoting": ("point_cloud_reconstruction", "ball_pivoting"),
    "icp": ("registration", "icp_refinement"),
    "ransac": ("registration", "ransac_global"),
    "decimate": ("pyvista_mesh_processing", "pv_decimate"),
    "smooth": ("pyvista_mesh_processing", "pv_smooth_laplacian"),
    "to_points": ("mesh_processing", "mesh_to_pcd_poisson_disk"),
    "register": ("simpleitk_registration", "rigid"),
    "segment": ("simpleitk_segmentation", "otsu_threshold"),
}

_DICOM_EXTS = {".dcm", ".ima", ".dicom"}


def extension_of(path: str | os.PathLike) -> str:
    """``.nii.gz`` aware suffix, lower-case. A DICOM folder reports ``.dcm``."""
    p = Path(path)
    if p.is_dir():
        return ".dcm"
    name = p.name.lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return p.suffix.lower()


def kind_of(path: str | os.PathLike) -> str:
    """The object kind a path maps to by extension.

    One of ``pointcloud``, ``mesh``, ``volume``, ``labels``, ``array``...; ``file`` when unknown.
    """

    return KIND_BY_EXT.get(extension_of(path), "file")


def _is_dicom_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    for child in p.iterdir():
        if child.is_file() and (child.suffix.lower() in _DICOM_EXTS or child.suffix == ""):
            return True
    return False


class Object:
    """A local file (or DICOM folder), typed by its extension."""

    kind: str = "file"

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        frame: Frame | None = None,
        labels: dict[int, str] | None = None,
        license: License | None = None,
        provenance: list[dict[str, Any]] | None = None,
        role: str | None = None,
        meta: dict[str, Any] | None = None,
        layout: Any = None,
        read_sidecar: bool = True,
    ):
        self.path = Path(path).expanduser()
        if self.path.is_dir():
            if not _is_dicom_dir(self.path):
                raise FileNotFoundError(f"{self.path} is a folder without DICOM files; pass a file.")
        elif not self.path.is_file():
            raise FileNotFoundError(f"No such file: {self.path}")
        self.role = role
        self.meta: dict[str, Any] = dict(meta or {})
        side = self._read_sidecar() if read_sidecar else {}
        if layout is None:
            layout = side.get("layout")
        if layout is not None:
            self.meta["layout"] = layout if isinstance(layout, dict) else layout.model_dump(exclude_none=True)
        self.provenance: list[dict[str, Any]] = list(
            provenance if provenance is not None else side.get("provenance", [])
        )
        file_frame = self._frame_from_file()
        given = frame if frame is not None else Frame.from_dict(side.get("frame"))
        # The file's own header wins on what it states; the manifest/user fills the rest.
        self.frame: Frame = file_frame.merged(given)
        if given.axes and file_frame.axes and given.axes != file_frame.axes:
            logger.warning(
                "{}: the file is {} but {} was declared; keeping the file's frame.",
                self.path.name,
                file_frame.axes,
                given.axes,
            )
        raw_labels = labels if labels is not None else side.get("labels")
        self.labels: dict[int, str] | None = (
            {int(k): str(v) for k, v in raw_labels.items()} if raw_labels else None
        )
        self.license: License = license if license is not None else License.from_dict(side.get("license"))
        self._info: dict[str, Any] | None = None
        self._registration_sidecar: dict[str, Any] | bool | None = False

    # ---- construction helpers -----------------------------------------
    def _read_sidecar(self) -> dict[str, Any]:
        p = self.sidecar_path
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("ignoring unreadable sidecar {}: {}", p, exc)
        return {}

    def _frame_from_file(self) -> Frame:
        ext = self.extension
        if ext in FORMAT_FRAMES:
            return FORMAT_FRAMES[ext]
        if ext in ITK_VOLUME_EXTS:
            try:
                header = convert.read_volume_header(self.path)
            except MissingDependency:
                return Frame(axes="LPS", units="mm", source="format")
            except Exception as exc:  # unreadable header: stay honest, say unknown
                logger.debug("could not read the header of {}: {}", self.path, exc)
                return Frame()
            self.meta.update(
                {k: header[k] for k in ("size", "spacing", "origin", "pixel_type", "components")}
            )
            return Frame(axes="LPS", units="mm", affine=header["affine"], source="file")
        return Frame()

    # ---- identity -------------------------------------------------------
    def __fspath__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        size = f"{self.size_bytes / 1e6:.2f} MB" if not self.path.is_dir() else "DICOM folder"
        steps = (
            f", {len(self.provenance)} step{'s' if len(self.provenance) != 1 else ''}"
            if self.provenance
            else ""
        )
        role = f" role={self.role}" if self.role else ""
        return f"<{type(self).__name__} {self.path.name!r} {self.frame.describe()} ({size}){steps}{role}>"

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return extension_of(self.path)

    @property
    def size_bytes(self) -> int:
        if self.path.is_dir():
            return sum(f.stat().st_size for f in self.path.iterdir() if f.is_file())
        return self.path.stat().st_size

    @property
    def units(self) -> str | None:
        return self.frame.units

    @property
    def axes(self) -> str | None:
        return self.frame.axes

    @property
    def sidecar_path(self) -> Path:
        return self.path.with_name(self.path.name + SIDECAR_SUFFIX)

    @property
    def is_raw_array(self) -> bool:
        """True for ``.npy`` / ``.npz`` / ``.bin`` / ``.raw`` files: data that only a layout can read."""
        return is_array_file(self.path)

    @property
    def layout(self) -> dict[str, Any] | None:
        """How a raw array is to be read (dtype, shape, columns, key...), when declared."""
        lay = self.meta.get("layout")
        return dict(lay) if lay else None

    def with_layout(self, **layout: Any) -> Object:
        """A copy that declares the array layout, e.g.
        ``with_layout(dtype="float32", shape="(N,4)", columns=["x","y","z","reflectance"])``."""
        new = self._copy()
        new.meta["layout"] = {**(self.layout or {}), **layout}
        new.meta.pop("_materialised", None)
        return new

    # ---- metadata -------------------------------------------------------
    def with_frame(self, axes: str | None = None, units: str | None = None, **more: Any) -> Object:
        """A copy that states the frame (``source="user"``). Does not override
        what the file header itself says."""
        declared = Frame(axes=axes, units=units, source="user", **more)
        new = self._copy()
        new.frame = (
            self.frame.merged(declared) if self.frame.source == "file" else declared.merged(self.frame)
        )
        return new

    def with_labels(self, labels: dict[int, str]) -> LabelMap | Object:
        new = self._copy()
        new.labels = {int(k): str(v) for k, v in labels.items()}
        if isinstance(new, Volume) and not isinstance(new, LabelMap):
            return LabelMap._from_object(new)
        return new

    def with_license(self, license: License | str | dict[str, Any]) -> Object:
        new = self._copy()
        new.license = license if isinstance(license, License) else License.from_dict(license)
        return new

    def _copy(self) -> Object:
        new = type(self).__new__(type(self))
        new.__dict__.update(self.__dict__)
        new.meta = dict(self.meta)
        new.provenance = list(self.provenance)
        return new

    def info(self) -> dict[str, Any]:
        """Header-level facts (size, spacing, counts...) read lazily and cached."""
        if self._info is None:
            self._info = {k: v for k, v in self.meta.items() if not k.startswith("_")}
            if self.kind in ("volume", "labels") and "size" not in self._info:
                readable = self.extension in ITK_VOLUME_EXTS or self.extension in (".vti", ".vtu", ".vtk")
                if self.is_raw_array or self.path.is_dir():
                    with contextlib.suppress(MissingDependency, ManifestError):
                        self._info.update(convert.read_volume_header(self._op_input()))
                elif readable:
                    with contextlib.suppress(MissingDependency):
                        self._info.update(convert.read_volume_header(self.path))
        return self._info

    @property
    def registration_sidecar(self) -> dict[str, Any] | None:
        """The ``<name>.json`` written next to the file by registration ops."""
        if self._registration_sidecar is False:
            p = self.path.with_suffix(".json")
            self._registration_sidecar = None
            if p.is_file() and p != self.path:
                with contextlib.suppress(OSError, ValueError):
                    self._registration_sidecar = json.loads(p.read_text(encoding="utf-8"))
        return self._registration_sidecar  # type: ignore[return-value]

    @property
    def transform(self) -> dict[str, Any] | None:
        """The estimated transform of a registration output, when present."""
        sc = self.registration_sidecar
        if not sc:
            return None
        for key in ("transform", "transformation", "matrix_4x4", "matrix_3x3"):
            if key in sc:
                return sc[key] if isinstance(sc[key], dict) else {key: sc[key]}
        return sc

    def describe(self) -> str:
        lines = [repr(self), f"  frame:   {self.frame.describe()}", f"  licence: {self.license.describe()}"]
        if self.labels:
            lines.append("  labels:  " + ", ".join(f"{k}={v}" for k, v in sorted(self.labels.items())))
        info = self.info()
        if info.get("size"):
            lines.append(f"  size:    {info['size']}  spacing: {tuple(round(s, 3) for s in info['spacing'])}")
        if self.provenance:
            lines.append("  provenance:")
            for step in self.provenance:
                lines.append(f"    - {step.get('step', 'run')}: {step.get('op') or step.get('method')}")
        return "\n".join(lines)

    # ---- compute --------------------------------------------------------
    def methods(self) -> list[str]:
        """Qualified names of every catalog method that accepts this file type."""
        return [m.qualname for m in load_catalog().methods_for(self._op_extension())]

    def describe_method(self, method: str) -> str:
        return self._resolve(method).describe()

    def _op_extension(self) -> str:
        if self.path.is_dir():
            return ".mha"
        if self.is_raw_array:
            return ".mha" if self.kind in ("volume", "labels") else ".ply"
        return self.extension

    def _materialise_array(self) -> Path:
        """Decode a raw array through its layout into a standard file, once."""
        cached = self.meta.get("_materialised")
        if cached and Path(cached).is_file():
            return Path(cached)
        key = abs(hash((str(self.path), json.dumps(self.layout, sort_keys=True, default=str)))) % 10**8
        if self.kind in ("volume", "labels"):
            out = output_dir() / f"{self.path.stem}_{key:08d}.mha"
            step = arrays.array_to_volume(self.path, self.layout, out)
            if not step["geometry_known"]:
                logger.warning(
                    "{}: the layout gives no spacing/origin; the grid gets unit spacing at the origin.",
                    self.path.name,
                )
        elif self.kind in ("pointcloud", "splat"):
            out = output_dir() / f"{self.path.stem}_{key:08d}.ply"
            step = arrays.array_to_points(self.path, self.layout, out)
        elif self.kind == "array":
            raise ParameterError(
                f"{self.path.name} is a raw array of unknown kind. Use .as_points(...) or .as_volume(...)"
                " with its layout, or load it through a manifest role."
            )
        else:
            raise ParameterError(f"{self.path.name}: a raw array cannot be read as {self.kind}.")
        self.meta["_materialised"] = str(out)
        self.meta["_materialised_step"] = step
        return out

    def _resolve(self, method: str) -> Method:
        if method in ALIASES:
            return load_catalog().method(*ALIASES[method])
        return load_catalog().find(method, self._op_extension())

    def _op_input(self) -> Path:
        """Ops take standard files: a DICOM folder is materialised as .mha
        once, a raw array as .ply or .mha through its layout."""
        if self.is_raw_array:
            return self._materialise_array()
        if not self.path.is_dir():
            return self.path
        cached = self.meta.get("_materialised")
        if cached and Path(cached).is_file():
            return Path(cached)
        out = output_dir() / f"{self.path.name}_{abs(hash(str(self.path))) % 10**8:08d}.mha"
        convert.dicom_to_mha(self.path, out)
        self.meta["_materialised"] = str(out)
        return out

    def run(
        self,
        method: str,
        /,
        *,
        moving: Object | str | os.PathLike | None = None,
        output: str | os.PathLike | None = None,
        timeout: float | None = None,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[int], None] | None = None,
        **params: Any,
    ) -> Object:
        """Run a catalog method on this object; the result is a new Object
        that inherits the frame and licence and records the step."""
        spec = self._resolve(method)
        moving_path = moving._op_input() if isinstance(moving, Object) else moving
        kwargs: dict[str, Any] = {"moving": moving_path, "output": output, "params": params}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if on_log is not None:
            kwargs["on_log"] = on_log
        if on_progress is not None:
            kwargs["on_progress"] = on_progress
        res = _run(spec.module_id, spec.id, self._op_input(), **kwargs)
        step = res.provenance()
        step["step"] = "run"
        step["input_provenance"] = list(self.provenance)
        if isinstance(moving, Object) and moving.provenance:
            step["moving_provenance"] = list(moving.provenance)
        return wrap(
            res.output,
            frame=self.frame if self.frame.source != "file" else self.frame.override(affine=None),
            license=self.license,
            provenance=[*self.provenance, step],
            read_sidecar=False,
        )

    # Friendly aliases (explicit so editors can complete them).
    def downsample(self, **params: Any) -> Object:
        """Voxel downsampling (``voxel_size``)."""
        return self.run("downsample", **params)

    def remove_outliers(self, **params: Any) -> Object:
        """Statistical outlier removal (``nb_neighbors``, ``std_ratio``)."""
        return self.run("remove_outliers", **params)

    def normals(self, **params: Any) -> Object:
        """Normal estimation."""
        return self.run("normals", **params)

    def poisson(self, **params: Any) -> Object:
        """Poisson surface reconstruction (``depth``, ``density_quantile``)."""
        return self.run("poisson", **params)

    def ball_pivoting(self, **params: Any) -> Object:
        return self.run("ball_pivoting", **params)

    def icp(self, moving: Object | str | os.PathLike, **params: Any) -> Object:
        """ICP refinement: align ``moving`` onto this (fixed) cloud."""
        return self.run("icp", moving=moving, **params)

    def ransac(self, moving: Object | str | os.PathLike, **params: Any) -> Object:
        """RANSAC global registration (FPFH features)."""
        return self.run("ransac", moving=moving, **params)

    def decimate(self, **params: Any) -> Object:
        """Mesh decimation (``target_reduction``)."""
        return self.run("decimate", **params)

    def smooth(self, **params: Any) -> Object:
        """Laplacian smoothing (``n_iterations``)."""
        return self.run("smooth", **params)

    def to_points(self, **params: Any) -> Object:
        """Sample a mesh into a point cloud (Poisson-disk, ``num_points``)."""
        return self.run("to_points", **params)

    def register(self, moving: Object | str | os.PathLike, **params: Any) -> Object:
        """Rigid volume registration (SimpleITK): align ``moving`` onto this volume."""
        return self.run("register", moving=moving, **params)

    def segment(self, **params: Any) -> Object:
        """Otsu threshold segmentation of a volume."""
        return self.run("segment", **params)

    # ---- I/O ------------------------------------------------------------
    def to_manifest_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"pardesline": __version__, "kind": self.kind, "frame": self.frame.to_dict()}
        if self.labels:
            d["labels"] = {str(k): v for k, v in self.labels.items()}
        if self.layout:
            d["layout"] = self.layout
        lic = self.license.to_dict()
        if lic:
            d["license"] = lic
        if self.role:
            d["role"] = self.role
        if self.provenance:
            d["provenance"] = self.provenance
        return d

    def save(self, dest: str | os.PathLike, *, sidecar: bool = True) -> Path:
        """Copy the file (plus its registration sidecar and ``.raw`` sibling
        for ``.mhd``) to ``dest`` - a directory keeps the current name - and
        write ``<dest>.pardesline.json`` with frame, labels, licence and
        provenance. Returns the new path."""
        wants_dir = str(dest).endswith(("/", os.sep))
        dest = Path(dest).expanduser()
        if wants_dir or dest.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            dest = dest / self.path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest_ext = extension_of(dest) if not dest.is_dir() else ""
        if self.is_raw_array and dest_ext and not is_array_file(dest):
            shutil.copyfile(self._materialise_array(), dest)  # standard file from the layout
        elif self.path.is_dir() and dest_ext in ITK_VOLUME_EXTS:
            shutil.copyfile(self._op_input(), dest)  # DICOM series as one volume file
        elif self.path.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(self.path, dest)
        else:
            shutil.copyfile(self.path, dest)
            if self.extension == ".mhd":
                raw = self.path.with_suffix(".raw")
                if raw.is_file():
                    shutil.copyfile(raw, dest.with_suffix(".raw"))
            reg = self.path.with_suffix(".json")
            if reg.is_file() and reg != self.path:
                shutil.copyfile(reg, dest.with_suffix(".json"))
        if sidecar:
            side = dest.with_name(dest.name + SIDECAR_SUFFIX)
            side.write_text(json.dumps(self.to_manifest_dict(), indent=2), encoding="utf-8")
        return dest

    def to_open3d(self):
        """Load as an Open3D geometry (``PointCloud`` or ``TriangleMesh``)."""
        try:
            import open3d as o3d
        except ImportError:
            raise MissingDependency("Open3D", "local") from None
        if self.is_raw_array:
            return o3d.io.read_point_cloud(str(self._op_input()))
        if self.kind == "mesh":
            return o3d.io.read_triangle_mesh(str(self.path))
        if self.kind == "pointcloud":
            if self.extension == ".ply":
                mesh = o3d.io.read_triangle_mesh(str(self.path))
                if len(mesh.triangles) > 0:
                    return mesh
            return o3d.io.read_point_cloud(str(self.path))
        raise TypeError(
            f"Open3D cannot load a {self.kind} ({self.path.name}); use to_pyvista() or to_sitk()."
        )

    def to_pyvista(self):
        """Load with ``pyvista.read``."""
        try:
            import pyvista as pv
        except ImportError:
            raise MissingDependency("PyVista", "local") from None
        if self.path.is_dir() or self.is_raw_array:
            return pv.read(str(self._op_input()))
        return pv.read(str(self.path))

    def to_sitk(self):
        """Load a volume as a ``SimpleITK.Image`` (DICOM folders accepted)."""
        try:
            from ..medical import load_dicom, load_volume
        except ImportError:
            raise MissingDependency("SimpleITK", "medical") from None
        if self.path.is_dir():
            return load_dicom(self.path)
        if self.is_raw_array:
            return load_volume(self._op_input())
        return load_volume(self.path)

    def to_numpy(self):
        """Points (N,3) for clouds, vertices for meshes, voxels (z,y,x) for volumes."""
        import numpy as np

        if self.is_raw_array and self.kind in ("pointcloud", "splat"):
            return arrays.decode_points(self.path, self.layout)[0]
        if self.is_raw_array and self.kind == "array":
            return np.asarray(arrays.load_array(self.path, self.layout))
        if self.kind in ("volume", "labels"):
            import SimpleITK as sitk

            return sitk.GetArrayFromImage(self.to_sitk())
        geo = self.to_open3d()
        if hasattr(geo, "vertices"):
            return np.asarray(geo.vertices)
        return np.asarray(geo.points)


class PointCloud(Object):
    kind = "pointcloud"

    def to_mesh(self, **params: Any) -> Mesh:
        """A surface from the points (Poisson, density-trimmed). Lossy and
        parametric - ``depth``, ``density_quantile`` - the step records them."""
        return self.run("poisson", **params)  # type: ignore[return-value]

    def align(self, moving: Object | str | os.PathLike, **params: Any) -> PointCloud:
        """Coarse-to-fine rigid alignment of ``moving`` onto this cloud
        (RANSAC on FPFH features, then ICP). Returns the moved cloud; the
        transform is in ``.transform``."""
        return self.run("registration.ransac_icp_pipeline", moving=moving, **params)  # type: ignore[return-value]

    def clean(self, **params: Any) -> PointCloud:
        """Statistical outlier removal."""
        return self.run("remove_outliers", **params)  # type: ignore[return-value]

    def segment(self, **params: Any) -> PointCloud:
        """DBSCAN clustering (``eps``, ``min_points``); clusters are colours."""
        return self.run("point_cloud_segmentation.dbscan_clustering", **params)  # type: ignore[return-value]


class Mesh(Object):
    kind = "mesh"

    def to_points(self, **params: Any) -> PointCloud:
        """Sample the surface into points (Poisson-disk, ``num_points``)."""
        return self.run("to_points", **params)  # type: ignore[return-value]

    def clean(self, **params: Any) -> Mesh:
        """Merge duplicate points, drop degenerate cells."""
        return self.run("pyvista_mesh_processing.pv_clean", **params)  # type: ignore[return-value]


class Volume(Object):
    kind = "volume"

    def to_mesh(self, *, isovalue: float | None = None, label: int | None = None, output=None) -> Mesh:
        """Isosurface in world coordinates. ``label=k`` is exact for a label
        map; ``isovalue=v`` is the level set of a grey-level volume. One of
        the two is required."""
        out = (
            Path(output)
            if output
            else output_dir()
            / f"{self.path.stem}_surface_{abs(hash((str(self.path), isovalue, label))) % 10**8:08d}.ply"
        )
        t0 = time.perf_counter()
        step = convert.volume_to_mesh(self._op_input(), out, isovalue=isovalue, label=label)
        step["duration_s"] = round(time.perf_counter() - t0, 3)
        step["pardesline"] = __version__
        if label is not None and self.labels and label in self.labels:
            step["label_name"] = self.labels[label]
        return Mesh(
            out,
            frame=self.frame.override(affine=None),
            license=self.license,
            provenance=[*self.provenance, step],
            read_sidecar=False,
        )

    def align(self, moving: Object | str | os.PathLike, **params: Any) -> Volume:
        """Rigid registration of ``moving`` onto this volume (SimpleITK,
        GEOMETRY initialisation). The transform is in ``.transform``."""
        return self.run("register", moving=moving, **params)  # type: ignore[return-value]

    def segment(self, *, lower: float | None = None, upper: float | None = None, **params: Any) -> LabelMap:
        """Threshold segmentation: Otsu when no bounds are given, otherwise
        ``lower``/``upper`` in intensity units. Returns a LabelMap with label 1."""
        if lower is None and upper is None:
            out = self.run("segment", **params)
        else:
            bounds: dict[str, Any] = {k: v for k, v in (("lower", lower), ("upper", upper)) if v is not None}
            out = self.run("simpleitk_segmentation.manual_threshold", **bounds, **params)
        return LabelMap._from_object(out, labels={1: "foreground"})

    def as_labels(self, labels: dict[int, str] | None = None) -> LabelMap:
        """Declare this volume a label map (voxel value = class id)."""
        return LabelMap._from_object(self, labels=labels)


class LabelMap(Volume):
    """A volume whose voxel values are class ids. ``labels`` names them."""

    kind = "labels"

    @classmethod
    def _from_object(cls, obj: Object, labels: dict[int, str] | None = None) -> LabelMap:
        new = cls.__new__(cls)
        new.__dict__.update(obj.__dict__)
        new.meta = dict(obj.meta)
        new.provenance = list(obj.provenance)
        if labels is not None:
            new.labels = {int(k): str(v) for k, v in labels.items()}
        return new

    def to_mesh(self, label: int | None = None, *, isovalue: float | None = None, output=None) -> Mesh:
        """Exact boundary of one label. With a single named label it is the default."""
        if label is None and isovalue is None:
            if self.labels and len(self.labels) == 1:
                label = next(iter(self.labels))
            else:
                names = ", ".join(f"{k}={v}" for k, v in sorted((self.labels or {}).items())) or "unknown"
                raise ParameterError(f"LabelMap.to_mesh: which label? Available: {names}.")
        return super().to_mesh(isovalue=isovalue, label=label, output=output)

    def label_id(self, name: str) -> int:
        for k, v in (self.labels or {}).items():
            if v == name:
                return k
        raise KeyError(f"No label named {name!r}; labels: {self.labels}")


class Transform(Object):
    kind = "transform"


class RawArray(Object):
    """A ``.npy`` / ``.npz`` / ``.bin`` file: numbers without meaning until a
    layout says what they are. ``as_points(...)`` or ``as_volume(...)`` turn
    it into a typed object; a manifest role does the same for a dataset."""

    kind = "array"

    def as_points(self, **layout: Any) -> PointCloud:
        """Declare the array as points: ``as_points(dtype="float32",
        shape="(N,4)", columns=["x","y","z","reflectance"])``."""
        new = PointCloud.__new__(PointCloud)
        new.__dict__.update(self.with_layout(**layout).__dict__)
        return new

    def as_volume(self, labels: dict[int, str] | None = None, **layout: Any) -> Volume:
        """Declare the array as a dense grid: ``as_volume(key="occ_label",
        shape="(200,200,16)", spacing=[0.4,0.4,0.4])``; with ``labels`` it is a LabelMap."""
        cls: type[Volume] = LabelMap if labels is not None else Volume
        new = cls.__new__(cls)
        new.__dict__.update(self.with_layout(**layout).__dict__)
        if labels is not None:
            new.labels = {int(k): str(v) for k, v in labels.items()}
        return new


class Image(Object):
    kind = "image"


_CLASS_BY_KIND: dict[str, type[Object]] = {
    "pointcloud": PointCloud,
    "mesh": Mesh,
    "volume": Volume,
    "labels": LabelMap,
    "transform": Transform,
    "image": Image,
    "array": RawArray,
}


def wrap(path: str | os.PathLike, *, kind: str | None = None, **kwargs: Any) -> Object:
    """Pick the Object subclass for a path (or force ``kind``)."""
    p = Path(path)
    if kind is None:
        side = p.with_name(p.name + SIDECAR_SUFFIX)
        if kwargs.get("read_sidecar", True) and side.is_file():
            try:
                kind = json.loads(side.read_text(encoding="utf-8")).get("kind")
            except (OSError, ValueError):
                kind = None
        if kind is None and kwargs.get("labels"):
            kind = "labels"
        if kind is None:
            kind = kind_of(p)
    cls = _CLASS_BY_KIND.get(kind, Object)
    return cls(p, **kwargs)


def load_object(path: str | os.PathLike) -> Object:
    """Open a file as the right :class:`Object` subclass, reading its sidecar when present.

    Same as ``pl.load`` for a file.
    """

    return wrap(path)
