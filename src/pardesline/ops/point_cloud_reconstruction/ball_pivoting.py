"""
Ball Pivoting Reconstruction — adapted from PardesLine functions_for_surfaceR.

CONTRACT:
  python ball_pivoting.py --input <pcd_file> --output <mesh_file> [--radius_factor F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Ball Pivoting Reconstruction")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--radius_factor", type=float, default=2.0, help="Radius factor of average spacing")
    parser.add_argument("--radii_multipliers", type=str, default="1,2,4", help="CSV of base-radius multipliers for the multi-scale ball set")
    parser.add_argument("--normal_radius", type=float, default=0.1, help="Normal estimation search radius (when normals absent)")
    parser.add_argument("--normal_max_nn", type=int, default=30, help="Normal estimation max neighbours (when normals absent)")
    parser.add_argument("--normal_orient_k", type=int, default=15, help="k for consistent tangent-plane normal orientation")
    args = parser.parse_args()

    multipliers = [float(x) for x in args.radii_multipliers.split(",") if x.strip()]

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: radius_factor={args.radius_factor}")
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

    # Compute average nearest neighbor distance for radius estimation
    logger.info("Computing nearest neighbor distances")
    distances = pcd.compute_nearest_neighbor_distance()
    avg_dist = np.mean(distances)
    base_radius = avg_dist * args.radius_factor

    radii = [base_radius * m for m in multipliers]
    logger.info(f"Avg spacing: {avg_dist:.6f}, base radius: {base_radius:.6f}")
    logger.info(f"Ball radii: {[f'{r:.6f}' for r in radii]}")

    logger.info("Running ball pivoting algorithm")
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        pcd, o3d.utility.DoubleVector(radii)
    )
    mesh.compute_vertex_normals()

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    o3d.io.write_triangle_mesh(args.output, mesh)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
