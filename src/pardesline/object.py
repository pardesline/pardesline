"""``pl.Object``: a local 3D file with its kind, metadata and provenance.

This is the local counterpart of the cloud ``RemoteObject``. It wraps a path,
knows whether it is a point cloud, a mesh, a volume, a transform or an image,
can run any applicable algorithm on itself, and remembers every run that
produced it.

    >>> import pardesline as pl
    >>> scan = pl.load("scan.ply")
    >>> clean = scan.downsample(voxel_size=0.01).remove_outliers()
    >>> surface = clean.poisson(depth=9)
    >>> surface.save("surface.ply")
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .catalog import Method, load_catalog
from .errors import MissingDependency
from .runner import run as _run

__all__ = ["KIND_BY_EXT", "Object", "load"]

KIND_BY_EXT: dict[str, str] = {
    ".ply": "pointcloud",
    ".pcd": "pointcloud",
    ".xyz": "pointcloud",
    ".txt": "pointcloud",
    ".pts": "pointcloud",
    ".las": "pointcloud",
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
    ".gz": "volume",  # .nii.gz
    ".dcm": "volume",
    ".tfm": "transform",
    ".hdf5": "transform",
    ".h5": "transform",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".zip": "archive",
}

# Friendly names → (module, method). Kept small and obvious; everything else is
# reachable through obj.run("module.method", ...).
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


def kind_of(path: str | os.PathLike) -> str:
    p = Path(path)
    suffixes = [s.lower() for s in p.suffixes[-2:]]
    if suffixes[-2:] == [".nii", ".gz"]:
        return "volume"
    return KIND_BY_EXT.get(p.suffix.lower(), "file")


class Object:
    """A local file on disk, typed by its extension."""

    def __init__(self, path: str | os.PathLike, *, provenance: list[dict[str, Any]] | None = None):
        self.path = Path(path).expanduser()
        if not self.path.is_file():
            raise FileNotFoundError(f"No such file: {self.path}")
        self.kind = kind_of(self.path)
        self.provenance: list[dict[str, Any]] = list(provenance or [])
        self._sidecar: dict[str, Any] | bool | None = False  # False = not read yet

    # ---- identity -------------------------------------------------------
    def __fspath__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        mb = self.size_bytes / 1e6
        steps = (
            f", {len(self.provenance)} step{'s' if len(self.provenance) != 1 else ''}"
            if self.provenance
            else ""
        )
        return f"<Object {self.kind} {self.path.name!r} ({mb:.2f} MB){steps}>"

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size

    # ---- metadata -------------------------------------------------------
    @property
    def sidecar(self) -> dict[str, Any] | None:
        """The ``<name>.json`` written next to the file by registration
        methods (transform, statistics), or None."""
        if self._sidecar is False:
            p = self.path.with_suffix(".json")
            if p.is_file() and p != self.path:
                try:
                    self._sidecar = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    self._sidecar = None
            else:
                self._sidecar = None
        return self._sidecar  # type: ignore[return-value]

    @property
    def transform(self) -> dict[str, Any] | None:
        """The estimated transform of a registration output, when present."""
        sc = self.sidecar
        if not sc:
            return None
        for key in ("transform", "transformation", "matrix_4x4", "matrix_3x3"):
            if key in sc:
                return sc[key] if isinstance(sc[key], dict) else {key: sc[key]}
        return sc

    # ---- compute --------------------------------------------------------
    def methods(self) -> list[str]:
        """Qualified names of every method that accepts this file type."""
        return [m.qualname for m in load_catalog().methods_for(self.extension)]

    def describe(self, method: str) -> str:
        return self._resolve(method).describe()

    def _resolve(self, method: str) -> Method:
        if method in ALIASES:
            return load_catalog().method(*ALIASES[method])
        return load_catalog().find(method, self.extension)

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
        """Run ``method`` on this object and return the result as a new
        Object. ``method`` is ``"module.method"``, a bare method id that is
        unique for this file type, or one of the friendly aliases."""
        spec = self._resolve(method)
        kwargs: dict[str, Any] = {"moving": moving, "output": output, "params": params}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if on_log is not None:
            kwargs["on_log"] = on_log
        if on_progress is not None:
            kwargs["on_progress"] = on_progress
        res = _run(spec.module_id, spec.id, self.path, **kwargs)
        prov = res.provenance()
        prov["input_provenance"] = list(self.provenance)
        if isinstance(moving, Object) and moving.provenance:
            prov["moving_provenance"] = list(moving.provenance)
        return Object(res.output, provenance=[*self.provenance, prov])

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
        """Poisson surface reconstruction (``depth``, density trimming)."""
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
        """Sample a mesh into a point cloud (Poisson-disk)."""
        return self.run("to_points", **params)

    def register(self, moving: Object | str | os.PathLike, **params: Any) -> Object:
        """Rigid volume registration (SimpleITK): align ``moving`` onto this volume."""
        return self.run("register", moving=moving, **params)

    def segment(self, **params: Any) -> Object:
        """Otsu threshold segmentation of a volume."""
        return self.run("segment", **params)

    # ---- I/O ------------------------------------------------------------
    def save(self, dest: str | os.PathLike) -> Path:
        """Copy the file (and its sidecar, if any) to ``dest``; a directory
        keeps the current name. Returns the new path."""
        wants_dir = str(dest).endswith(("/", os.sep))
        dest = Path(dest).expanduser()
        if wants_dir or dest.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            dest = dest / self.path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.path, dest)
        sc = self.path.with_suffix(".json")
        if sc.is_file() and sc != self.path:
            shutil.copyfile(sc, dest.with_suffix(".json"))
        return dest

    def to_open3d(self):
        """Load as an Open3D geometry (``PointCloud`` or ``TriangleMesh``)."""
        try:
            import open3d as o3d
        except ImportError:
            raise MissingDependency("Open3D", "local") from None
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
        return pv.read(str(self.path))

    def to_sitk(self):
        """Load a volume as a ``SimpleITK.Image`` (DICOM folders accepted)."""
        try:
            from .medical import load_volume
        except ImportError:
            raise MissingDependency("SimpleITK", "medical") from None
        return load_volume(self.path)


def load(path: str | os.PathLike) -> Object:
    """Open a local 3D file as an :class:`Object`.

    Datasets (folders, ``hf://``, ``sample://``) are the next milestone of
    the package and raise a clear error for now.
    """
    text = str(path)
    if "://" in text:
        raise NotImplementedError(
            f"pl.load({text!r}): dataset URIs (hf://, sample://, msd://) are not available yet. "
            "Pass a local file path. See the roadmap in README.md."
        )
    p = Path(path).expanduser()
    if p.is_dir():
        raise NotImplementedError(
            f"pl.load({text!r}) is a folder. Dataset scanning is the next milestone; "
            "pass one file for now (a DICOM folder can be read with pardesline.medical.load_dicom)."
        )
    return Object(p)
