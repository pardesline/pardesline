"""
DBSCAN Clustering — adapted from PardesLine 08_point_cloud_segmentation.

CONTRACT:
  python dbscan_clustering.py --input <pcd_file> --output <pcd_file> [--eps F] [--min_points N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="DBSCAN Clustering")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--eps", type=float, default=0.02, help="DBSCAN epsilon")
    parser.add_argument("--min_points", type=int, default=10, help="Minimum points per cluster")
    parser.add_argument("--print_progress", type=_b, default=False,
                        help="Print an Open3D progress bar during clustering.")
    args = parser.parse_args()

    logger.info("Loading point cloud: {}", args.input)
    logger.info("Parameters: eps={}, min_points={}", args.eps, args.min_points)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Loaded {} points", len(pcd.points))

    # DBSCAN clustering
    logger.info("Running DBSCAN clustering (eps={}, min_points={})", args.eps, args.min_points)
    labels = np.array(pcd.cluster_dbscan(eps=args.eps, min_points=args.min_points, print_progress=args.print_progress))

    n_clusters = labels.max() + 1
    n_noise = np.sum(labels == -1)
    logger.info("Found {} clusters, {} noise points", n_clusters, n_noise)
    logger.info("Noise ratio: {:.2f}%", 100.0 * n_noise / len(labels) if len(labels) > 0 else 0.0)

    # Color each cluster
    logger.info("Assigning random colors to {} clusters (noise=dark gray)", n_clusters)
    colors = np.zeros((len(labels), 3))
    if n_clusters > 0:
        # Generate distinct colors
        np.random.seed(42)
        cluster_colors = np.random.rand(n_clusters, 3)
        for i in range(n_clusters):
            mask = labels == i
            colors[mask] = cluster_colors[i]
            logger.info("Cluster {}: {} points", i, np.sum(mask))

    # Noise = dark gray
    colors[labels == -1] = [0.3, 0.3, 0.3]

    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved to: {}", args.output)


if __name__ == "__main__":
    main()
