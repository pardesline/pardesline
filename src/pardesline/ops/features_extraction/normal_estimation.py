"""
Normal Estimation — adapted from PardesLine functions_for_surfaceR.

Estimates normals and colors the point cloud by normal direction.

CONTRACT:
  python normal_estimation.py --input <pcd_file> --output <pcd_file> [--radius F] [--max_nn N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Normal Estimation")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--radius", type=float, default=0.05, help="Search radius")
    parser.add_argument("--max_nn", type=int, default=30, help="Maximum nearest neighbors")
    parser.add_argument("--fast_normal_computation", type=_b, default=True,
                        help="Use the faster (less accurate) covariance eigen solver in estimate_normals.")
    parser.add_argument("--orient_k", type=int, default=0,
                        help="k neighbors for consistent tangent-plane orientation (0 = auto min(max_nn,15)).")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Loaded {} points", len(pcd.points))
    logger.info("Parameters: radius={}, max_nn={}", args.radius, args.max_nn)

    # Estimate normals
    logger.info("Estimating normals using hybrid KDTree search")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=args.radius, max_nn=args.max_nn),
        fast_normal_computation=args.fast_normal_computation
    )

    # Orient normals consistently
    k_orient = args.orient_k if args.orient_k > 0 else min(args.max_nn, 15)
    logger.info("Orienting normals with consistent tangent plane (k={})", k_orient)
    pcd.orient_normals_consistent_tangent_plane(k=k_orient)

    # Color by normal direction (map normal XYZ to RGB)
    normals = np.asarray(pcd.normals)
    colors = np.abs(normals)  # Map absolute normal components to RGB
    pcd.colors = o3d.utility.Vector3dVector(colors)

    logger.info("Normals estimated and colored by direction for {} points", len(normals))

    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved to {}", args.output)


if __name__ == "__main__":
    main()
