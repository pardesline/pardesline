"""
Curvature Estimation — colors point cloud by local surface curvature.

Curvature = lambda_0 / (lambda_0 + lambda_1 + lambda_2) from local covariance eigenvalues.

CONTRACT:
  python curvature_estimation.py --input <pcd_file> --output <pcd_file> [--radius F] [--max_nn N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Curvature Estimation")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--radius", type=float, default=0.05, help="Search radius")
    parser.add_argument("--max_nn", type=int, default=30, help="Maximum nearest neighbors")
    parser.add_argument("--normalize_percentile", type=float, default=99,
                        help="Percentile of curvature used as the color-normalization ceiling.")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    points = np.asarray(pcd.points)
    logger.info("Loaded {} points", len(points))
    logger.info("Parameters: radius={}, max_nn={}", args.radius, args.max_nn)

    # Build KD-tree
    logger.info("Building KD-tree for neighbor search")
    kdtree = o3d.geometry.KDTreeFlann(pcd)
    curvatures = np.zeros(len(points))

    logger.info("Computing per-point curvature via local covariance eigenvalues")
    for i in range(len(points)):
        [k, idx, _] = kdtree.search_hybrid_vector_3d(points[i], args.radius, args.max_nn)
        if k < 3:
            continue

        neighbors = points[idx, :]
        centered = neighbors - neighbors.mean(axis=0)
        cov = np.cov(centered.T)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.sort(eigenvalues)

        denom = eigenvalues.sum()
        if denom > 1e-12:
            curvatures[i] = eigenvalues[0] / denom

    # Normalize and color
    c_max = np.percentile(curvatures, args.normalize_percentile)
    c_norm = np.clip(curvatures / (c_max + 1e-12), 0, 1)

    import matplotlib
    colors = matplotlib.colormaps['hot'](c_norm)[:, :3]

    logger.info("Curvature range: [{:.6f}, {:.6f}]", curvatures.min(), curvatures.max())
    logger.info("Mean curvature: {:.6f}, {}th percentile: {:.6f}", curvatures.mean(), args.normalize_percentile, c_max)

    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved curvature-colored point cloud to {}", args.output)


if __name__ == "__main__":
    main()
