"""
Poisson Surface Reconstruction — template script.

CONTRACT:
  python poisson.py --input <point_cloud_file> --output <mesh_file> [--depth N] [--scale F]

Replace this with your own implementation.
The only hard requirements are:
  1. Accept --input and --output as CLI args
  2. Write the output mesh to --output path
  3. Exit 0 on success, non-zero on failure
"""

import argparse
import sys

import open3d as o3d
import numpy as np
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Poisson Surface Reconstruction")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--depth", type=int, default=9, help="Octree depth")
    parser.add_argument("--scale", type=float, default=1.1, help="Reconstruction scale")
    parser.add_argument("--width", type=float, default=0.0, help="Target octree width (0 = use depth instead)")
    parser.add_argument("--linear_fit", type=_b, default=False, help="Use linear interpolation to estimate iso-surface positions")
    parser.add_argument("--n_threads", type=int, default=-1, help="Number of threads (-1 = all available)")
    parser.add_argument("--density_quantile", type=float, default=0.01, help="Density quantile below which vertices are removed as noise")
    parser.add_argument("--normal_radius", type=float, default=0.1, help="Normal estimation search radius (when normals absent)")
    parser.add_argument("--normal_max_nn", type=int, default=30, help="Normal estimation max neighbours (when normals absent)")
    parser.add_argument("--normal_orient_k", type=int, default=15, help="k for consistent tangent-plane normal orientation")
    args = parser.parse_args()

    logger.info(f"Loading point cloud: {args.input}")
    logger.info(f"Parameters: depth={args.depth}, scale={args.scale}")
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info(f"Points: {len(pcd.points)}")

    # Estimate normals if not present
    if not pcd.has_normals():
        logger.info(f"Estimating normals (radius={args.normal_radius}, max_nn={args.normal_max_nn})")
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=args.normal_radius, max_nn=args.normal_max_nn)
        )
        logger.info(f"Orienting normals with consistent tangent plane (k={args.normal_orient_k})")
        pcd.orient_normals_consistent_tangent_plane(k=args.normal_orient_k)
    else:
        logger.info("Normals already present, skipping estimation")

    # Poisson reconstruction
    logger.info(f"Running Poisson reconstruction (depth={args.depth}, scale={args.scale}, width={args.width}, linear_fit={args.linear_fit}, n_threads={args.n_threads})")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=args.depth, width=args.width, scale=args.scale,
        linear_fit=args.linear_fit, n_threads=args.n_threads
    )

    # Remove low-density vertices (noise cleanup)
    densities = np.asarray(densities)
    density_threshold = np.quantile(densities, args.density_quantile)
    vertices_to_remove = densities < density_threshold
    logger.info(f"Density threshold (quantile={args.density_quantile}): {density_threshold:.6f}, removing {np.sum(vertices_to_remove)} low-density vertices")
    mesh.remove_vertices_by_mask(vertices_to_remove)

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} faces")

    # Save
    o3d.io.write_triangle_mesh(args.output, mesh)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
