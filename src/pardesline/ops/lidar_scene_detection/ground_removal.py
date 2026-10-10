"""
Ground Plane Removal — adapted from PardesLine 10_scene_Lidar_car_detection.

Uses RANSAC to fit a ground plane and removes ground points.

CONTRACT:
  python ground_removal.py --input <pcd_file> --output <pcd_file> [--distance_threshold F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Ground Plane Removal")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--distance_threshold", type=float, default=0.3, help="Distance threshold for ground plane")
    parser.add_argument("--ransac_n", type=int, default=3, help="Points sampled per RANSAC iteration")
    parser.add_argument("--num_iterations", type=int, default=1000, help="RANSAC iterations")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Input points: {}", len(pcd.points))
    logger.info("RANSAC distance threshold: {}", args.distance_threshold)

    # RANSAC plane segmentation
    logger.info("Running RANSAC plane segmentation (ransac_n=3, iterations=1000)")
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=args.distance_threshold,
        ransac_n=args.ransac_n,
        num_iterations=args.num_iterations
    )

    a, b, c, d = plane_model
    logger.info("Fitted plane: {:.4f}x + {:.4f}y + {:.4f}z + {:.4f} = 0", a, b, c, d)
    logger.info("Ground inlier points: {}", len(inliers))

    # Remove ground (keep outliers)
    non_ground = pcd.select_by_index(inliers, invert=True)

    # Color by height
    pts = np.asarray(non_ground.points)
    if len(pts) > 0:
        z = pts[:, 2]
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-12)
        colors = np.zeros((len(pts), 3))
        colors[:, 0] = z_norm
        colors[:, 1] = 0.5
        colors[:, 2] = 1.0 - z_norm
        non_ground.colors = o3d.utility.Vector3dVector(colors)
        logger.info("Applied height-based coloring to non-ground points")

    logger.info("Remaining points after ground removal: {}", len(non_ground.points))

    o3d.io.write_point_cloud(args.output, non_ground)
    logger.info("Saved to {}", args.output)


if __name__ == "__main__":
    main()
