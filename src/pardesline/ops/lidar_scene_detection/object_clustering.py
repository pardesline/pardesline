"""
Object Clustering — adapted from PardesLine 10_scene_Lidar_car_detection.

Ground removal + DBSCAN clustering to detect individual objects.

CONTRACT:
  python object_clustering.py --input <pcd_file> --output <pcd_file> [--ground_threshold F] [--cluster_eps F] [--min_cluster_points N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Object Clustering")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--ground_threshold", type=float, default=0.3, help="Ground removal threshold")
    parser.add_argument("--cluster_eps", type=float, default=0.5, help="DBSCAN epsilon")
    parser.add_argument("--min_cluster_points", type=int, default=10, help="Min cluster points")
    parser.add_argument("--ransac_n", type=int, default=3, help="Points sampled per RANSAC iteration")
    parser.add_argument("--num_iterations", type=int, default=1000, help="Ground-plane RANSAC iterations")
    parser.add_argument("--print_progress", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=False, help="Print DBSCAN progress")
    args = parser.parse_args()

    logger.info("Loading point cloud from {}", args.input)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Input points: {}", len(pcd.points))
    logger.info("Parameters: ground_threshold={}, cluster_eps={}, min_cluster_points={}",
                args.ground_threshold, args.cluster_eps, args.min_cluster_points)

    # Step 1: Remove ground
    logger.info("Step 1: RANSAC ground plane segmentation")
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=args.ground_threshold,
        ransac_n=args.ransac_n,
        num_iterations=args.num_iterations
    )
    non_ground = pcd.select_by_index(inliers, invert=True)
    logger.info("Non-ground points: {} (removed {} ground inliers)",
                len(non_ground.points), len(inliers))

    if non_ground.is_empty():
        logger.error("No non-ground points found")
        o3d.io.write_point_cloud(args.output, pcd)
        sys.exit(0)

    # Step 2: DBSCAN clustering
    logger.info("Step 2: DBSCAN clustering (eps={}, min_points={})",
                args.cluster_eps, args.min_cluster_points)
    labels = np.array(non_ground.cluster_dbscan(
        eps=args.cluster_eps,
        min_points=args.min_cluster_points,
        print_progress=args.print_progress
    ))

    n_clusters = labels.max() + 1
    n_noise = np.sum(labels == -1)
    logger.info("Detected {} clusters, {} noise points", n_clusters, n_noise)

    # Color each cluster
    colors = np.zeros((len(labels), 3))
    if n_clusters > 0:
        np.random.seed(42)
        cluster_colors = np.random.rand(n_clusters, 3)
        cluster_colors = cluster_colors * 0.7 + 0.3  # Ensure bright colors
        for i in range(n_clusters):
            mask = labels == i
            colors[mask] = cluster_colors[i]
            logger.info("Cluster {}: {} points", i, np.sum(mask))

    colors[labels == -1] = [0.3, 0.3, 0.3]  # Noise = gray
    non_ground.colors = o3d.utility.Vector3dVector(colors)

    o3d.io.write_point_cloud(args.output, non_ground)
    logger.info("Saved clustered point cloud to {}", args.output)


if __name__ == "__main__":
    main()
