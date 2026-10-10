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

__all__ = ["dicom_to_mha", "read_volume", "read_volume_header", "volume_to_mesh"]

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
        level = float(isovalue)

    grid = pv.ImageData(dimensions=img.GetSize(), spacing=img.GetSpacing(), origin=img.GetOrigin())
    grid.direction_matrix = np.array(img.GetDirection(), dtype=float).reshape(3, 3)
    grid.point_data["values"] = arr.ravel(order="C")  # (z,y,x) C-order == VTK x-fastest order
    surface = grid.contour([level], scalars="values", method=method)
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
