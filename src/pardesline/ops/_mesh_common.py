"""Checks and conversions shared by the mesh, distance-field and collision scripts.

Fixes of the 2026-11 audit (Part 3): A1 (marching-cubes output oriented outward), A5 (a
point cloud is never replaced by its convex hull), A7 (inside / outside decided by a
majority of several rays instead of one).
"""

from __future__ import annotations

import sys

import numpy as np
from loguru import logger

DEFAULT_SIGN_RAYS = 3


def require_triangles(mesh, what: str = "this method") -> None:
    """Exit 1 when the input has no triangles: a point cloud is not a mesh, and its convex
    hull (what the scripts used to substitute) is an invented surface."""
    if len(mesh.triangles) == 0:
        logger.error("Input has no triangles (a point cloud is not a mesh); {} needs a mesh: "
                     "reconstruct a surface first (point_cloud_reconstruction)", what)
        sys.exit(1)


def signed_volume(verts, faces) -> float:
    """Signed volume of a triangle mesh: positive when the faces are oriented outward."""
    v = np.asarray(verts, dtype=float)
    f = np.asarray(faces, dtype=np.int64)
    if len(f) == 0:
        return 0.0
    v0, v1, v2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)


def orient_outward(verts, faces):
    """Reverse the winding of every face when the surface's signed volume is negative
    (reordering marching-cubes vertex axes is a reflection: it inverts every face)."""
    if signed_volume(verts, faces) < 0:
        return np.ascontiguousarray(np.asarray(faces)[:, ::-1])
    return faces


def check_sign_rays(n: int) -> int:
    n = int(n)
    if n < 1 or n % 2 == 0:
        logger.error("sign_rays must be a positive odd number (majority vote), got {}", n)
        sys.exit(2)
    return n


def signed_distance(scene, query, nsamples: int = DEFAULT_SIGN_RAYS):
    """Signed distance (negative inside) with the sign from a majority of ``nsamples`` rays."""
    return scene.compute_signed_distance(query, nsamples=check_sign_rays(nsamples)).numpy()


def occupancy(scene, query, nsamples: int = DEFAULT_SIGN_RAYS):
    """Occupancy (1 inside) decided by a majority of ``nsamples`` rays."""
    return scene.compute_occupancy(query, nsamples=check_sign_rays(nsamples)).numpy()


MAX_GRID_NODES = 50_000_000  # about 0.6 GB for the float32 query points alone


def check_grid_budget(shape, voxel_size: float) -> None:
    """Exit 1 before allocating a grid that would exhaust memory (a unit-scale voxel size on data in
    millimetres asks for billions of nodes)."""
    n = int(np.prod([int(s) for s in shape]))
    if n > MAX_GRID_NODES:
        scale = (n / MAX_GRID_NODES) ** (1 / 3)
        logger.error("A {} grid is {:,} nodes (limit {:,}): voxel_size {} is too small for this object; "
                     "use at least {:.4g} (file units)", tuple(shape), n, MAX_GRID_NODES, voxel_size,
                     voxel_size * scale * 1.01)
        sys.exit(1)


def warn_if_not_watertight(mesh) -> bool:
    """Signs and occupancy assume a closed surface: say so when the input is not one."""
    ok = bool(mesh.is_watertight())
    if not ok:
        logger.warning("The input mesh is not watertight: inside/outside (signs, occupancy) is only "
                       "meaningful for a closed surface; check the result")
    return ok
