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
    """Load a .pcd file into PyVista PolyData (points only)."""
    import numpy as np
    points = []
    reading_data = False
    with open(filepath, "r", errors="replace") as f:
        for line in f:
            if line.startswith("DATA"):
                reading_data = True
                continue
            if reading_data:
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        points.append([float(parts[0]), float(parts[1]), float(parts[2])])
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
      'mesh', 'pointcloud', 'volume', 'structured_grid', 'unstructured_grid'
    """
    if isinstance(dataset, pv.ImageData):
        return "volume"
    if isinstance(dataset, pv.StructuredGrid):
        return "structured_grid"
    if isinstance(dataset, pv.UnstructuredGrid):
        return "unstructured_grid"
    if isinstance(dataset, pv.PolyData):
        if dataset.n_cells == 0 or dataset.n_cells == dataset.n_points:
            return "pointcloud"
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
