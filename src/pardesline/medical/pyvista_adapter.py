"""
PyVista ↔ Standard Format Adapter.

Stateless utility functions for converting between standard 3D file formats
and PyVista objects. Supports: .ply, .obj, .stl (meshes/point clouds),
.vti (volumes/ImageData), .vtk (StructuredGrid), .vtu (UnstructuredGrid).

No global state. No plotting. All functions are testable in isolation.
"""

from pathlib import Path
from typing import Union

import pyvista as pv


# ---------------------------------------------------------------------------
# Load: standard file → PyVista
# ---------------------------------------------------------------------------

def load_pyvista(filepath: str) -> pv.DataSet:
    """Auto-detect format, load any standard file into a PyVista object.

    Supported: .ply, .obj, .stl, .vtk, .vti, .vtu, .pcd
    For .pcd files, reads via meshio fallback or raw parser.
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()

    if ext == ".pcd":
        return _load_pcd(filepath)

    reader = pv.get_reader(filepath)
    return reader.read()


def _load_pcd(filepath: str) -> pv.PolyData:
    """Load an ASCII .pcd file into PyVista PolyData (points only).

    The x, y, z columns are located through the FIELDS and COUNT lines of the header
    (the first three columns are not necessarily x, y, z); binary and
    binary_compressed data are refused with an explicit error.
    """
    import numpy as np
    points = []
    fields: list[str] = []
    counts: list[int] = []
    cols = None
    reading_data = False
    with open(filepath, "r", errors="replace") as f:
        for line in f:
            if not reading_data:
                head = line.strip().split()
                if not head:
                    continue
                if head[0] == "FIELDS":
                    fields = head[1:]
                elif head[0] == "COUNT":
                    counts = [int(c) for c in head[1:]]
                elif head[0] == "DATA":
                    if len(head) < 2 or head[1].lower() != "ascii":
                        raise ValueError(f"{filepath}: PCD 'DATA {head[1] if len(head) > 1 else ''}' is not "
                                         "supported by this reader (ASCII only); read it with Open3D")
                    if not counts:
                        counts = [1] * len(fields)
                    if not {"x", "y", "z"} <= set(fields) or len(counts) != len(fields):
                        raise ValueError(f"{filepath}: PCD header has no x, y, z FIELDS ({fields})")
                    offsets = np.cumsum([0] + counts[:-1])
                    cols = [int(offsets[fields.index(k)]) for k in ("x", "y", "z")]
                    reading_data = True
                continue
            parts = line.strip().split()
            if len(parts) > max(cols):
                try:
                    points.append([float(parts[c]) for c in cols])
                except ValueError:
                    continue
    if not points:
        raise ValueError(f"No points found in PCD file: {filepath}")
    return pv.PolyData(np.array(points, dtype=np.float64))


# ---------------------------------------------------------------------------
# Save: PyVista → standard file
# ---------------------------------------------------------------------------

def save_pyvista(dataset: pv.DataSet, filepath: str) -> None:
    """Save a PyVista object to a standard format file.

    Format is determined by file extension:
      .ply, .obj, .stl → PolyData (extracts surface if needed)
      .vti             → ImageData
      .vtk             → StructuredGrid or legacy VTK
      .vtu             → UnstructuredGrid
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()

    if ext in (".ply", ".obj", ".stl"):
        poly = _ensure_polydata(dataset)
        poly.save(filepath)
    elif ext == ".vti":
        if not isinstance(dataset, pv.ImageData):
            raise TypeError(f"Cannot save {type(dataset).__name__} as .vti; expected ImageData")
        dataset.save(filepath)
    elif ext == ".vtu":
        if isinstance(dataset, pv.UnstructuredGrid):
            dataset.save(filepath)
        else:
            dataset.cast_to_unstructured_grid().save(filepath)
    elif ext == ".vtk":
        dataset.save(filepath)
    else:
        raise ValueError(f"Unsupported output format: {ext}")


def _ensure_polydata(dataset: pv.DataSet) -> pv.PolyData:
    """Convert any PyVista dataset to PolyData (extract surface if needed)."""
    if isinstance(dataset, pv.PolyData):
        return dataset
    if hasattr(dataset, "extract_surface"):
        return dataset.extract_surface()
    raise TypeError(f"Cannot convert {type(dataset).__name__} to PolyData")


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------

def detect_geometry_type(dataset: pv.DataSet) -> str:
    """Classify a PyVista dataset into a geometry type string.

    Returns one of:
      'mesh', 'pointcloud', 'lines', 'volume', 'structured_grid', 'unstructured_grid'

    A PolyData is a point cloud when it has no cells or only vertex cells, 'lines' when
    it has line cells and no faces, a mesh when it has faces (equal numbers of points and
    cells say nothing: a closed tetrahedron has 4 of each).
    """
    if isinstance(dataset, pv.ImageData):
        return "volume"
    if isinstance(dataset, pv.StructuredGrid):
        return "structured_grid"
    if isinstance(dataset, pv.UnstructuredGrid):
        return "unstructured_grid"
    if isinstance(dataset, pv.PolyData):
        if dataset.n_cells == 0 or dataset.n_cells == dataset.n_verts:
            return "pointcloud"
        if len(dataset.faces) == 0 and len(getattr(dataset, "strips", [])) == 0:
            return "lines" if dataset.n_lines else "pointcloud"
        return "mesh"
    return "mesh"


def get_attributes(dataset: pv.DataSet) -> dict:
    """Return a summary of data arrays attached to the dataset.

    Returns:
        {
            "point_data": ["Normals", "scalars", ...],
            "cell_data": [...],
            "field_data": [...],
            "n_points": int,
            "n_cells": int,
        }
    """
    return {
        "point_data": list(dataset.point_data.keys()) if dataset.point_data else [],
        "cell_data": list(dataset.cell_data.keys()) if dataset.cell_data else [],
        "field_data": list(dataset.field_data.keys()) if dataset.field_data else [],
        "n_points": dataset.n_points,
        "n_cells": dataset.n_cells,
    }


def recommended_visualization(dataset: pv.DataSet) -> str:
    """Suggest a visualization mode based on geometry type."""
    gtype = detect_geometry_type(dataset)
    return {
        "mesh": "surface",
        "pointcloud": "points",
        "lines": "wireframe",
        "volume": "volume",
        "structured_grid": "surface",
        "unstructured_grid": "surface",
    }.get(gtype, "surface")


# ---------------------------------------------------------------------------
# Convenience: extract first meaningful block from MultiBlock
# ---------------------------------------------------------------------------

def extract_from_multiblock(mb: pv.MultiBlock) -> pv.DataSet:
    """Extract the first non-empty dataset from a MultiBlock."""
    for i in range(mb.n_blocks):
        block = mb[i]
        if block is not None and block.n_points > 0:
            return block
    raise ValueError("MultiBlock contains no non-empty blocks")
