"""
Gaussian Deformation — adapted from PardesLine functions_for_deformation.

Applies a localized Gaussian pressure deformation to a point cloud.

CONTRACT:
  python gaussian_deformation.py --input <pcd_file> --output <pcd_file> [--radius F] [--displacement F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Gaussian Deformation")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--radius", type=float, default=0.1, help="Radius of influence")
    parser.add_argument("--displacement", type=float, default=0.02, help="Max displacement at center")
    parser.add_argument("--sigma_factor", type=float, default=0.5,
                        help="Gaussian falloff sigma as a fraction of radius")
    args = parser.parse_args()

    logger.info("Loading point cloud: {}", args.input)
    logger.info("Parameters: radius={}, displacement={}", args.radius, args.displacement)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Loaded {} points", len(points))

    # Find center and create pressure point on left side
    center = np.mean(points, axis=0)
    x_left = np.min(points[:, 0])
    pressure_center = np.array([x_left, center[1], center[2]])
    direction = np.array([1.0, 0.0, 0.0])
    logger.info("Cloud center: {}, pressure point at x_left={:.6f}", center, x_left)
    logger.info("Pressure direction: {}", direction)

    # Apply Gaussian deformation
    from scipy.spatial import cKDTree
    logger.info("Building KD-tree for neighbor search")
    tree = cKDTree(points)
    affected = tree.query_ball_point(pressure_center, r=args.radius)
    deformation = np.zeros_like(points)

    sigma = args.radius * args.sigma_factor
    logger.info("Gaussian sigma={:.6f}, querying neighbors within radius={}", sigma, args.radius)

    if len(affected) > 0:
        affected_pts = points[affected]
        distances = np.linalg.norm(affected_pts - pressure_center, axis=1)
        weights = np.exp(-(distances ** 2) / (2 * sigma ** 2))
        displacements = weights[:, np.newaxis] * args.displacement * direction
        for i, idx in enumerate(affected):
            deformation[idx] = displacements[i]

    deformed = points + deformation

    mean_mag = np.mean(np.linalg.norm(deformation, axis=1))
    max_mag = np.max(np.linalg.norm(deformation, axis=1))
    logger.info("Affected: {} points, mean deformation: {:.6f}, max deformation: {:.6f}", len(affected), mean_mag, max_mag)

    # Color by deformation magnitude
    logger.info("Coloring points by deformation magnitude (red=high, blue=low)")
    magnitudes = np.linalg.norm(deformation, axis=1)
    if magnitudes.max() > 0:
        norm = magnitudes / magnitudes.max()
    else:
        norm = magnitudes

    colors = np.zeros((len(points), 3))
    colors[:, 0] = norm        # Red = high deformation
    colors[:, 2] = 1.0 - norm  # Blue = no deformation

    pcd_out = o3d.geometry.PointCloud()
    pcd_out.points = o3d.utility.Vector3dVector(deformed)
    pcd_out.colors = o3d.utility.Vector3dVector(colors)

    o3d.io.write_point_cloud(args.output, pcd_out)
    logger.info("Saved to: {}", args.output)


if __name__ == "__main__":
    main()
