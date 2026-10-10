"""
Voxel Downsampling — adapted from PardesLine 01_pointcloud_processing.

CONTRACT:
  python voxel_downsample.py --input <file> --output <file> [--voxel_size F]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Voxel Downsampling")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--voxel_size", type=float, default=0.02, help="Voxel size")
    args = parser.parse_args()

    logger.info(f"Loading point cloud: {args.input}")
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info(f"Input points: {len(pcd.points)}")
    logger.info(f"Voxel size parameter: {args.voxel_size}")

    logger.info("Running voxel downsampling")
    pcd_down = pcd.voxel_down_sample(voxel_size=args.voxel_size)

    reduction_pct = (1 - len(pcd_down.points) / len(pcd.points)) * 100
    logger.info(f"Output points: {len(pcd_down.points)} (reduction: {reduction_pct:.1f}%)")

    o3d.io.write_point_cloud(args.output, pcd_down)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
