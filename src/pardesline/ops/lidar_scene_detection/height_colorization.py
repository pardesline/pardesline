"""
Height Colorization — adapted from PardesLine 10_scene_Lidar_car_detection.

Colors a point cloud based on Z-coordinate (height) with a gradient.

CONTRACT:
  python height_colorization.py --input <pcd_file> --output <pcd_file> [--colormap N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Height-Based Colorization")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--colormap", type=int, default=0, help="Colormap: 0=height gradient, 1=viridis, 2=plasma, 3=turbo")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Loaded {} points", len(points))
    logger.info("Colormap selection: {}", args.colormap)

    z = points[:, 2]
    z_norm = (z - z.min()) / (z.max() - z.min() + 1e-12)

    if args.colormap == 0:
        # Custom height gradient: blue -> cyan -> green -> yellow -> red
        logger.info("Applying custom height gradient colormap")
        colors = np.zeros((len(points), 3))
        colors[:, 0] = np.clip(z_norm * 2, 0, 1)
        colors[:, 1] = np.clip(1 - np.abs(z_norm - 0.5) * 2, 0, 1)
        colors[:, 2] = np.clip(1 - z_norm * 2, 0, 1)
    else:
        import matplotlib
        cmap_names = {1: 'viridis', 2: 'plasma', 3: 'turbo'}
        cmap_name = cmap_names.get(args.colormap, 'viridis')
        logger.info("Applying matplotlib colormap: {}", cmap_name)
        cmap = matplotlib.colormaps[cmap_name]
        colors = cmap(z_norm)[:, :3]

    logger.info("Z range: [{:.4f}, {:.4f}]", z.min(), z.max())

    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved colorized point cloud to {}", args.output)


if __name__ == "__main__":
    main()
