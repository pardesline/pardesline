"""
Convex Hull — template script.

CONTRACT:
  python convex_hull.py --input <point_cloud_file> --output <mesh_file>

Replace this with your own implementation.
"""

import argparse
import sys

import open3d as o3d
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Convex Hull Reconstruction")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--joggle_inputs", type=_b, default=False, help="Joggle input to avoid degenerate/coplanar QHull errors")
    args = parser.parse_args()

    logger.info(f"Loading point cloud: {args.input}")
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info(f"Points: {len(pcd.points)}")

    # Compute convex hull
    logger.info(f"Computing convex hull (joggle_inputs={args.joggle_inputs})")
    hull, _ = pcd.compute_convex_hull(joggle_inputs=args.joggle_inputs)

    logger.info(f"Hull: {len(hull.vertices)} vertices, {len(hull.triangles)} faces")

    # Save
    o3d.io.write_triangle_mesh(args.output, hull)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
