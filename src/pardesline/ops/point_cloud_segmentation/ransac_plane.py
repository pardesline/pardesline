"""
RANSAC Plane Segmentation — adapted from PardesLine 08_point_cloud_segmentation.

CONTRACT:
  python ransac_plane.py --input <pcd_file> --output <pcd_file> [--distance_threshold F] [--num_iterations N]
"""

import os

# Open3D draws RANSAC samples from one global generator in parallel threads: a seeded run
# is reproducible only on one thread (audit 2026-11, X7). Must precede "import open3d".
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import json
from pathlib import Path
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="RANSAC Plane Segmentation")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--distance_threshold", type=float, default=None,
                        help="Inlier distance threshold in file units (required: about 2-3x the noise)")
    parser.add_argument("--num_iterations", type=int, default=1000, help="RANSAC iterations")
    parser.add_argument("--ransac_n", type=int, default=3,
                        help="Number of points sampled to estimate each plane candidate.")
    parser.add_argument("--probability", type=float, default=0.99999999,
                        help="Expected probability of finding the best plane (early-stop confidence).")
    parser.add_argument("--seed", type=int, default=0, help="Seed of Open3D's RANSAC")
    args = parser.parse_args()
    if args.distance_threshold is None:
        parser.error("--distance_threshold is required (file units; about 2-3x the noise of the plane)")

    logger.info("Loading point cloud: {}", args.input)
    logger.info("Parameters: distance_threshold={}, num_iterations={}", args.distance_threshold, args.num_iterations)
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info("Loaded {} points", len(pcd.points))

    # RANSAC plane segmentation
    logger.info("Running RANSAC plane segmentation (ransac_n={}, num_iterations={})", args.ransac_n, args.num_iterations)
    o3d.utility.random.seed(args.seed)
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=args.distance_threshold,
        ransac_n=args.ransac_n,
        num_iterations=args.num_iterations,
        probability=args.probability
    )

    a, b, c, d = plane_model
    logger.info("Plane equation: {:.4f}x + {:.4f}y + {:.4f}z + {:.4f} = 0", a, b, c, d)
    logger.info("Plane normal: ({:.4f}, {:.4f}, {:.4f})", a, b, c)
    logger.info("Inliers: {}, Outliers: {}", len(inliers), len(pcd.points) - len(inliers))
    logger.info("Inlier ratio: {:.2f}%", 100.0 * len(inliers) / len(pcd.points))

    # Colour inliers (red) and outliers (blue), keeping the input point order so that
    # point i of the output is point i of the input.
    logger.info("Coloring inliers red, outliers blue (point order kept)")
    is_inlier = np.zeros(len(pcd.points), bool)
    is_inlier[np.asarray(inliers, dtype=int)] = True
    colors = np.where(is_inlier[:, None], [1.0, 0.0, 0.0], [0.0, 0.4, 1.0])
    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(args.output, pcd)
    logger.info("Saved to: {}", args.output)

    json_path = Path(args.output).with_suffix(".json")
    json_path.write_text(json.dumps({
        "plane_abcd": [float(v) for v in plane_model],
        "equation": "a x + b y + c z + d = 0",
        "inliers": int(is_inlier.sum()),
        "points": int(len(is_inlier)),
        "inlier_indices": np.flatnonzero(is_inlier).tolist(),
        "distance_threshold": args.distance_threshold,
        "seed": args.seed,
    }, indent=2))
    logger.info("Plane and inliers saved: {}", json_path)


if __name__ == "__main__":
    main()
