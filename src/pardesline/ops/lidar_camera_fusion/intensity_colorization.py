"""
Intensity Colorization — adapted from PardesLine 11_lidar_cam_aligned_viewer.

Colors point cloud by intensity/reflectance (if available) or by distance from sensor.

CONTRACT:
  python intensity_colorization.py --input <pcd_file> --output <pcd_file> [--colormap N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Intensity Colorization")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--colormap", type=int, default=0, help="Colormap: 0=distance, 1=viridis, 2=plasma")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Loaded {} points", len(points))
    logger.info("Colormap selection: {}", args.colormap)

    # Compute distance from origin (sensor)
    distances = np.linalg.norm(points, axis=1)
    d_norm = (distances - distances.min()) / (distances.max() - distances.min() + 1e-12)

    import matplotlib
    if args.colormap == 0:
        # Distance-based: close=warm, far=cool
        logger.info("Applying custom distance-based colormap (close=warm, far=cool)")
        colors = np.zeros((len(points), 3))
        colors[:, 0] = 1.0 - d_norm
        colors[:, 1] = 0.3
        colors[:, 2] = d_norm
    else:
        cmap_names = {1: 'viridis', 2: 'plasma'}
        cmap_name = cmap_names.get(args.colormap, 'viridis')
        logger.info("Applying matplotlib colormap: {}", cmap_name)
        cmap = matplotlib.colormaps[cmap_name]
        colors = cmap(d_norm)[:, :3]

    logger.info("Distance range: [{:.4f}, {:.4f}]", distances.min(), distances.max())

    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved colorized point cloud to {}", args.output)


if __name__ == "__main__":
    main()
