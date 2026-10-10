"""
FPFH Feature Visualization — adapted from PardesLine functions_for_registration.

Computes FPFH features and colors the point cloud by feature similarity (PCA of FPFH).

CONTRACT:
  python fpfh_features.py --input <pcd_file> --output <pcd_file> [--voxel_size F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="FPFH Feature Visualization")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--voxel_size", type=float, default=0.005, help="Voxel size for downsampling")
    parser.add_argument("--normal_radius_factor", type=float, default=2.0,
                        help="Normal search radius as a multiple of voxel_size.")
    parser.add_argument("--normal_max_nn", type=int, default=30,
                        help="Maximum nearest neighbors for normal estimation.")
    parser.add_argument("--feature_radius_factor", type=float, default=5.0,
                        help="FPFH search radius as a multiple of voxel_size.")
    parser.add_argument("--feature_max_nn", type=int, default=100,
                        help="Maximum nearest neighbors for FPFH feature computation.")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    # Downsample
    logger.info("Downsampling with voxel_size={}", args.voxel_size)
    pcd_down = pcd.voxel_down_sample(args.voxel_size)
    logger.info("Downsampled: {} -> {} points", len(pcd.points), len(pcd_down.points))

    # Estimate normals
    radius_normal = args.voxel_size * args.normal_radius_factor
    logger.info("Estimating normals with radius={:.4f}, max_nn={}", radius_normal, args.normal_max_nn)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=args.normal_max_nn)
    )

    # Compute FPFH features
    radius_feature = args.voxel_size * args.feature_radius_factor
    logger.info("Computing FPFH features with radius={:.4f}, max_nn={}", radius_feature, args.feature_max_nn)
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=args.feature_max_nn)
    )

    features = np.asarray(fpfh.data).T  # (N, 33)
    logger.info("Feature shape: {} (N={}, dim={})", features.shape, features.shape[0], features.shape[1])

    # PCA to 3D for visualization
    logger.info("Running PCA projection from {}D to 3D for visualization", features.shape[1])
    features_centered = features - features.mean(axis=0)
    cov = np.cov(features_centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # Take top 3 components
    top3 = eigenvectors[:, -3:][:, ::-1]
    projected = features_centered @ top3

    # Report variance explained
    total_var = eigenvalues.sum()
    top3_var = eigenvalues[-3:][::-1].sum()
    logger.info("PCA variance explained by top 3 components: {:.1f}%", 100.0 * top3_var / (total_var + 1e-12))

    # Normalize to [0, 1] for color
    for i in range(3):
        col = projected[:, i]
        projected[:, i] = (col - col.min()) / (col.max() - col.min() + 1e-12)

    pcd_down.colors = o3d.utility.Vector3dVector(projected)

    o3d.io.write_point_cloud(args.output, pcd_down)
    logger.info("Saved FPFH-colored point cloud to {}", args.output)


if __name__ == "__main__":
    main()
