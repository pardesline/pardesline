"""
Multi-Resolution Downsampling — adapted from PardesLine 11_lidar_cam_aligned_viewer.

Creates a multi-resolution view by progressively downsampling and coloring each level.

CONTRACT:
  python multi_resolution.py --input <pcd_file> --output <pcd_file> [--levels N] [--base_voxel_size F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Multi-Resolution Downsampling")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--levels", type=int, default=3, help="Number of resolution levels")
    parser.add_argument("--base_voxel_size", type=float, default=0.01, help="Base voxel size (finest)")
    parser.add_argument("--voxel_growth_factor", type=float, default=2.0,
                        help="Per-level voxel-size multiplier base (voxel = base * factor**level)")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Input points: {}", len(pcd.points))
    logger.info("Parameters: levels={}, base_voxel_size={}", args.levels, args.base_voxel_size)

    # Level colors: finest=blue, medium=green, coarsest=red
    level_colors = [
        [0.2, 0.4, 1.0],
        [0.2, 0.8, 0.2],
        [1.0, 0.3, 0.2],
        [1.0, 0.8, 0.0],
        [0.8, 0.2, 0.8]
    ]

    combined = o3d.geometry.PointCloud()

    for level in range(args.levels):
        voxel_size = args.base_voxel_size * (args.voxel_growth_factor ** level)
        logger.info("Processing level {}/{}: voxel_size={:.4f}", level, args.levels - 1, voxel_size)
        pcd_level = pcd.voxel_down_sample(voxel_size)
        color = level_colors[min(level, len(level_colors) - 1)]
        pcd_level.paint_uniform_color(color)

        # Offset each level slightly in Z for visualization
        pts = np.asarray(pcd_level.points)
        bbox_extent = pts.max(axis=0) - pts.min(axis=0)
        offset = np.array([bbox_extent[0] * 1.2 * level, 0, 0])
        pcd_level.translate(offset)

        combined += pcd_level
        logger.info("Level {}: voxel={:.4f}, points={}", level, voxel_size, len(pcd_level.points))

    o3d.io.write_point_cloud(args.output, combined)
    logger.info("Total combined points: {}", len(combined.points))
    logger.info("Saved multi-resolution point cloud to {}", args.output)


if __name__ == "__main__":
    main()
