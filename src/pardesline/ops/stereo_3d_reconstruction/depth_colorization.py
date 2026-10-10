"""
Depth Colorization — adapted from PardesLine 09_stereo_disparity_3D.

Colors a point cloud based on depth (Z-coordinate) using a colormap.

CONTRACT:
  python depth_colorization.py --input <pcd_file> --output <pcd_file> [--colormap N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Depth Colorization")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--colormap", type=int, default=0, help="Colormap: 0=jet, 1=viridis, 2=plasma, 3=turbo")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Loaded {} points", len(points))

    # Get depth values (Z coordinate)
    z = points[:, 2]
    z_norm = (z - z.min()) / (z.max() - z.min() + 1e-12)
    logger.info("Normalizing Z values for colormap application")

    # Apply colormap
    import matplotlib
    cmap_names = ['jet', 'viridis', 'plasma', 'turbo']
    cmap_name = cmap_names[min(args.colormap, len(cmap_names) - 1)]
    cmap = matplotlib.colormaps[cmap_name]
    colors = cmap(z_norm)[:, :3]

    logger.info("Z range: [{:.4f}, {:.4f}], colormap: {}", z.min(), z.max(), cmap_name)
    logger.info("Applied colormap to {} points", len(colors))

    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved colorized point cloud to {}", args.output)


if __name__ == "__main__":
    main()
