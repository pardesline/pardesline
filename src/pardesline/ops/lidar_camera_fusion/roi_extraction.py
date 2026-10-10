"""
ROI Extraction — adapted from PardesLine 11_lidar_cam_aligned_viewer.

Extracts a Region of Interest (bounding box) from a point cloud.

CONTRACT:
  python roi_extraction.py --input <pcd_file> --output <pcd_file> [--x_range F] [--y_range F] [--z_range F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="ROI Extraction")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--x_range", type=float, default=0.5, help="X range factor (0-1) centered on median")
    parser.add_argument("--y_range", type=float, default=0.5, help="Y range factor (0-1)")
    parser.add_argument("--z_range", type=float, default=0.8, help="Z range factor (0-1)")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Input points: {}", len(points))
    logger.info("ROI range factors: x={}, y={}, z={}", args.x_range, args.y_range, args.z_range)

    # Compute bounding box with range factors
    center = np.median(points, axis=0)
    extent = np.max(points, axis=0) - np.min(points, axis=0)

    ranges = np.array([args.x_range, args.y_range, args.z_range])
    half_extent = extent * ranges / 2

    min_bound = center - half_extent
    max_bound = center + half_extent

    logger.info("ROI center: [{:.2f}, {:.2f}, {:.2f}]", center[0], center[1], center[2])
    logger.info("ROI extent: [{:.4f}, {:.4f}, {:.4f}]", extent[0], extent[1], extent[2])
    logger.info("ROI min_bound: [{:.4f}, {:.4f}, {:.4f}]", min_bound[0], min_bound[1], min_bound[2])
    logger.info("ROI max_bound: [{:.4f}, {:.4f}, {:.4f}]", max_bound[0], max_bound[1], max_bound[2])

    # Create axis-aligned bounding box
    bbox = o3d.geometry.AxisAlignedBoundingBox(
        min_bound=min_bound,
        max_bound=max_bound
    )

    pcd_cropped = pcd.crop(bbox)

    logger.info("Extracted {} / {} points ({:.1f}%)", len(pcd_cropped.points), len(points),
                100.0 * len(pcd_cropped.points) / len(points))

    # Color by distance from ROI center
    if not pcd_cropped.is_empty():
        pts = np.asarray(pcd_cropped.points)
        dist = np.linalg.norm(pts - center, axis=1)
        d_norm = (dist - dist.min()) / (dist.max() - dist.min() + 1e-12)
        import matplotlib
        colors = matplotlib.colormaps['coolwarm'](d_norm)[:, :3]
        pcd_cropped.colors = o3d.utility.Vector3dVector(colors)
        logger.info("Applied coolwarm distance colormap to cropped points")

    o3d.io.write_point_cloud(args.output, pcd_cropped)
    logger.info("Saved ROI extraction to {}", args.output)


if __name__ == "__main__":
    main()
