"""Well-posed conversions done in-process (no catalog op needed).

Each function writes a file and returns a provenance step. Lossy or
parametric conversions (points -> surface) go through the catalog ops instead,
so their parameters stay visible.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import MissingDependency

__all__ = [
    "SAVE_WRITERS",
    "content_kind",
    "dicom_to_mha",
    "read_volume",
    "read_volume_header",
    "save_as",
    "volume_to_mesh",
]

# What ``Object.save`` can write, by the CONTENT of the source (a .ply with triangles is a mesh).
# Same extension: the file is copied. Another extension listed here: converted by a reader and a
# writer. Anything else: refused with an error, never a file whose content does not match its
# extension.
SAVE_WRITERS: dict[str, frozenset[str]] = {
    "pointcloud": frozenset({".ply", ".pcd", ".xyz", ".pts"}),
    # .glb is not offered: Open3D 0.19 writes GLB files that Assimp and VTK reject (bad buffer view).
    "mesh": frozenset({".ply", ".stl", ".obj", ".off", ".gltf", ".vtp", ".vtk"}),
    "volume": frozenset({".mha", ".mhd", ".nrrd", ".nii", ".nii.gz", ".vti"}),
    "transform": frozenset({".tfm", ".h5", ".hdf5", ".mat", ".txt"}),
}


def _ext(path: str | os.PathLike) -> str:
    name = Path(path).name.lower()
    return ".nii.gz" if name.endswith(".nii.gz") else Path(path).suffix.lower()


def content_kind(path: str | os.PathLike, kind: str) -> str:
    """The kind of what a file holds, for saving: ``labels`` is a volume, and a ``.ply``
    typed as a point cloud is a mesh when it has triangles."""
    if kind == "labels":
        return "volume"
    if kind in ("pointcloud", "mesh") and _ext(path) == ".ply":
        try:
            import open3d as o3d
        except ImportError:
            raise MissingDependency("Open3D", "local") from None
        return "mesh" if len(o3d.io.read_triangle_mesh(str(path)).triangles) > 0 else "pointcloud"
    return kind


def save_as(src: str | os.PathLike, kind: str, dest: str | os.PathLike) -> str:
    """Write ``src`` (content ``kind``) to ``dest``: ``"copied"`` when the extensions match,
    ``"converted"`` when a writer exists for the target, ``ValueError`` otherwise."""
    import shutil

    src, dest = Path(src), Path(dest)
    s_ext, d_ext = _ext(src), _ext(dest)
    if s_ext == d_ext and s_ext != ".mhd":  # an .mhd header names its .raw file: always rewritten
        shutil.copyfile(src, dest)
        return "copied"
    ckind = content_kind(src, kind)
    allowed = SAVE_WRITERS.get(ckind, frozenset())
    if d_ext not in allowed:
        hint = f"; it can be saved as {', '.join(sorted(allowed))}" if allowed else ""
        if ckind == "mesh" and d_ext in SAVE_WRITERS["pointcloud"]:
            hint += " (sample it into points first: to_points())"
        raise ValueError(f"cannot save a {ckind} ({src.name}) as {d_ext}{hint}")
    if ckind == "pointcloud":
        import open3d as o3d

        pcd = o3d.io.read_point_cloud(str(src))
        if pcd.is_empty() or not o3d.io.write_point_cloud(str(dest), pcd):
            raise ValueError(f"could not convert {src.name} to {d_ext}")
    elif ckind == "mesh":
        vtk_side = {".vtp", ".vtk"}
        if s_ext in vtk_side or d_ext in vtk_side:
            try:
                import pyvista as pv
            except ImportError:
                raise MissingDependency("PyVista", "local") from None
        if s_ext in vtk_side:  # VTK reader, triangles kept
            poly = pv.read(str(src))
            if not isinstance(poly, pv.PolyData):
                poly = poly.extract_surface()
            poly = poly.triangulate()
            verts = np.asarray(poly.points, dtype=float)
            tris = np.asarray(poly.faces).reshape(-1, 4)[:, 1:] if poly.n_cells else np.zeros((0, 3), int)
        else:  # Open3D reader
            import open3d as o3d

            m = o3d.io.read_triangle_mesh(str(src))
            verts, tris = np.asarray(m.vertices, dtype=float), np.asarray(m.triangles)
        if len(tris) == 0:
            raise ValueError(f"{src.name} has no triangles: not a mesh")
        if d_ext in vtk_side:
            faces = np.column_stack([np.full(len(tris), 3), tris]).ravel()
            pv.PolyData(verts, faces).save(str(dest))
        else:
            import open3d as o3d

            m = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(verts), o3d.utility.Vector3iVector(tris))
            m.compute_triangle_normals()
            m.compute_vertex_normals()
            if not o3d.io.write_triangle_mesh(str(dest), m):
                raise ValueError(f"could not convert {src.name} to {d_ext}")
    elif ckind == "volume":
        sitk = _sitk()
        from ..medical._service import load_volume, volume_to_vti

        img = load_volume(src, pixel_type=None)  # stored pixel type: label ids stay exact
        if d_ext == ".vti":
            volume_to_vti(img, dest)
        else:
            sitk.WriteImage(img, str(dest))
    elif ckind == "transform":
        sitk = _sitk()
        from ..medical._service import save_transform

        save_transform(sitk.ReadTransform(str(src)), dest)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise ValueError(f"writing {dest.name} produced no file")
    return "converted"


_VTK_EXTS = (".vti", ".vtu", ".vtk")


def _sitk():
    try:
        import SimpleITK as sitk
    except ImportError:
        raise MissingDependency("SimpleITK", "medical") from None
    return sitk


def read_volume(path: str | os.PathLike):
    """Load any supported volume (file, VTK grid, DICOM folder) as a SimpleITK image."""
    _sitk()
    from ..medical._service import load_dicom, load_volume

    p = Path(path)
    return load_dicom(p) if p.is_dir() else load_volume(p)


def _geometry(img) -> dict[str, Any]:
    size, spacing, origin, direction = img.GetSize(), img.GetSpacing(), img.GetOrigin(), img.GetDirection()
    dim = len(size)
    d = np.array(direction, dtype=float).reshape(dim, dim)
    affine = np.eye(4)
    affine[:dim, :dim] = d * np.array(spacing)[None, :]
    affine[:dim, 3] = origin
    return {
        "size": tuple(int(s) for s in size),
        "spacing": tuple(float(s) for s in spacing),
        "origin": tuple(float(o) for o in origin),
        "direction": tuple(float(x) for x in direction),
        "affine": tuple(tuple(float(x) for x in row) for row in affine),
    }


def read_volume_header(path: str | os.PathLike) -> dict[str, Any]:
    """Size, spacing, origin, direction, pixel type and the 4x4 affine of a
    volume. ITK formats are read header-only (fast); VTK grids and DICOM
    folders need a full read."""
    sitk = _sitk()
    p = Path(path)
    if p.is_dir() or p.suffix.lower() in _VTK_EXTS:
        img = read_volume(p)
        out = _geometry(img)
        pixel = img.GetPixelIDTypeAsString()
        components = img.GetNumberOfComponentsPerPixel()
    else:
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(p))
        reader.ReadImageInformation()
        out = _geometry(reader)
        pixel = sitk.GetPixelIDValueAsString(reader.GetPixelID())
        components = reader.GetNumberOfComponents()
    out["pixel_type"] = pixel
    out["components"] = int(components)
    out["integer"] = "float" not in pixel.lower() and "complex" not in pixel.lower()
    return out


def dicom_to_mha(folder: str | os.PathLike, out_path: str | os.PathLike) -> Path:
    """Materialise a DICOM series as one .mha file (what the ops consume)."""
    sitk = _sitk()
    from ..medical._service import load_dicom

    img = load_dicom(folder)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(out))
    return out


def volume_to_mesh(
    volume_path: str | os.PathLike,
    out_path: str | os.PathLike,
    *,
    isovalue: float | None = None,
    label: int | None = None,
    method: str = "flying_edges",
) -> dict[str, Any]:
    """Extract an isosurface from a volume, in physical (world) coordinates.

    ``label=k`` extracts the boundary of voxels equal to ``k`` (exact for a
    label map); ``isovalue=v`` extracts the level set of a grey-level volume.
    Exactly one of them is required: the package never picks a level for you.
    """
    if (isovalue is None) == (label is None):
        raise ValueError("volume_to_mesh: pass exactly one of isovalue=<float> or label=<int>.")
    sitk = _sitk()
    try:
        import pyvista as pv
    except ImportError:
        raise MissingDependency("PyVista", "local") from None

    p = Path(volume_path)
    img = read_volume(p)
    if img.GetNumberOfComponentsPerPixel() != 1:
        img = sitk.VectorIndexSelectionCast(img, 0)
    arr = sitk.GetArrayFromImage(img)  # (z, y, x)
    if label is not None:
        arr = (np.rint(arr) == label).astype(np.float32)
        if not arr.any():
            raise ValueError(f"volume_to_mesh: no voxel has label {label}.")
        level = 0.5
    else:
        arr = arr.astype(np.float32)
        assert isovalue is not None
        level = float(isovalue)

    grid = pv.ImageData(dimensions=img.GetSize(), spacing=img.GetSpacing(), origin=img.GetOrigin())
    grid.direction_matrix = np.array(img.GetDirection(), dtype=float).reshape(3, 3)
    grid.point_data["values"] = arr.ravel(order="C")  # (z,y,x) C-order == VTK x-fastest order
    surface = grid.contour([level], scalars="values", method=method)  # type: ignore[arg-type]
    if surface.n_points == 0:
        raise ValueError(f"volume_to_mesh: the level {level} produces an empty surface.")
    surface = surface.extract_surface().triangulate()
    surface.clear_data()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    surface.save(str(out))
    return {
        "step": "convert",
        "op": "volume_to_mesh",
        "method": method,
        "isovalue": None if label is not None else level,
        "label": label,
        "n_points": int(surface.n_points),
        "n_faces": int(surface.n_cells),
        "input": str(p),
        "output": str(out),
        "exact": label is not None,
    }
