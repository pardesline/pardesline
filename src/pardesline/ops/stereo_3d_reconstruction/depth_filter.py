"""
Depth Filter — adapted from PardesLine 09_stereo_disparity_3D.

Filters a point cloud to keep only points within a depth range.

CONTRACT:
  python depth_filter.py --input <pcd_file> --output <pcd_file> [--min_depth F] [--max_depth F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Depth Range Filter")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--min_depth", type=float, default=0.1, help="Min depth percentile (0-1)")
    parser.add_argument("--max_depth", type=float, default=0.9, help="Max depth percentile (0-1)")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Input points: {}", len(points))
    logger.info("Filter parameters: min_depth={}, max_depth={}", args.min_depth, args.max_depth)

    # Compute depth range from percentiles
    z = points[:, 2]
    z_min = np.percentile(z, args.min_depth * 100)
    z_max = np.percentile(z, args.max_depth * 100)

    # Filter
    mask = (z >= z_min) & (z <= z_max)
    indices = np.where(mask)[0].tolist()

    pcd_filtered = pcd.select_by_index(indices)

    logger.info("Depth range: [{:.4f}, {:.4f}]", z_min, z_max)
    logger.info("Kept {} / {} points ({:.1f}%)", len(pcd_filtered.points), len(points),
                100.0 * len(pcd_filtered.points) / len(points))

    # Color by depth
    if len(pcd_filtered.points) > 0:
        pts = np.asarray(pcd_filtered.points)
        z_f = pts[:, 2]
        z_norm = (z_f - z_f.min()) / (z_f.max() - z_f.min() + 1e-12)
        import matplotlib
        colors = matplotlib.colormaps['viridis'](z_norm)[:, :3]
        pcd_filtered.colors = o3d.utility.Vector3dVector(colors)
        logger.info("Applied viridis depth colormap to filtered points")

    o3d.io.write_point_cloud(args.output, pcd_filtered)
    logger.info("Saved filtered point cloud to {}", args.output)


if __name__ == "__main__":
    main()
