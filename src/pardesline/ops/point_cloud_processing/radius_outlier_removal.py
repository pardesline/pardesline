"""
Radius Outlier Removal — adapted from PardesLine 01_pointcloud_processing.

CONTRACT:
  python radius_outlier_removal.py --input <file> --output <file> [--radius F] [--min_neighbors N]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Radius Outlier Removal")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--radius", type=float, default=0.05, help="Search radius")
    parser.add_argument("--min_neighbors", type=int, default=5, help="Minimum neighbors within radius")
    parser.add_argument("--print_progress", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=False, help="Print a progress bar")
    args = parser.parse_args()

    logger.info(f"Loading point cloud: {args.input}")
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info(f"Input points: {len(pcd.points)}")
    logger.info(f"Parameters: radius={args.radius}, min_neighbors={args.min_neighbors}")

    logger.info("Running radius outlier removal")
    cl, ind = pcd.remove_radius_outlier(
        nb_points=args.min_neighbors,
        radius=args.radius,
        print_progress=args.print_progress
    )

    inlier_cloud = pcd.select_by_index(ind)
    removed = len(pcd.points) - len(inlier_cloud.points)
    logger.info(f"Inliers: {len(inlier_cloud.points)}, removed: {removed}")

    o3d.io.write_point_cloud(args.output, inlier_cloud)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
