"""
RANSAC Plane Segmentation — adapted from PardesLine 08_point_cloud_segmentation.

CONTRACT:
  python ransac_plane.py --input <pcd_file> --output <pcd_file> [--distance_threshold F] [--num_iterations N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="RANSAC Plane Segmentation")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--distance_threshold", type=float, default=0.01, help="Inlier distance threshold")
    parser.add_argument("--num_iterations", type=int, default=1000, help="RANSAC iterations")
    parser.add_argument("--ransac_n", type=int, default=3,
                        help="Number of points sampled to estimate each plane candidate.")
    parser.add_argument("--probability", type=float, default=0.99999999,
                        help="Expected probability of finding the best plane (early-stop confidence).")
    args = parser.parse_args()

    logger.info("Loading point cloud: {}", args.input)
    logger.info("Parameters: distance_threshold={}, num_iterations={}", args.distance_threshold, args.num_iterations)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Loaded {} points", len(pcd.points))

    # RANSAC plane segmentation
    logger.info("Running RANSAC plane segmentation (ransac_n={}, num_iterations={})", args.ransac_n, args.num_iterations)
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=args.distance_threshold,
        ransac_n=args.ransac_n,
        num_iterations=args.num_iterations,
        probability=args.probability
    )

    a, b, c, d = plane_model
    logger.info("Plane equation: {:.4f}x + {:.4f}y + {:.4f}z + {:.4f} = 0", a, b, c, d)
    logger.info("Plane normal: ({:.4f}, {:.4f}, {:.4f})", a, b, c)
    logger.info("Inliers: {}, Outliers: {}", len(inliers), len(pcd.points) - len(inliers))
    logger.info("Inlier ratio: {:.2f}%", 100.0 * len(inliers) / len(pcd.points))

    # Color inliers (red) and outliers (blue)
    logger.info("Coloring inliers red, outliers blue")
    inlier_cloud = pcd.select_by_index(inliers)
    outlier_cloud = pcd.select_by_index(inliers, invert=True)

    inlier_cloud.paint_uniform_color([1.0, 0.0, 0.0])
    outlier_cloud.paint_uniform_color([0.0, 0.4, 1.0])

    combined = inlier_cloud + outlier_cloud
    o3d.io.write_point_cloud(args.output, combined)
    logger.info("Saved to: {}", args.output)


if __name__ == "__main__":
    main()
