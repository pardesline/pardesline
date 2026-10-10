"""
Mesh to Point Cloud — extract vertices from a triangle mesh.

Strips all face/triangle data and keeps only vertex positions
(and optionally normals and colors if present).

CONTRACT:
  python mesh_to_pointcloud.py --input <file> --output <file>
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Mesh to Point Cloud")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    args = parser.parse_args()

    logger.info(f"Loading mesh: {args.input}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    n_vertices = len(mesh.vertices)
    n_triangles = len(mesh.triangles)
    logger.info(f"Input: {n_vertices} vertices, {n_triangles} triangles")

    # Extract vertices into a point cloud
    logger.info("Extracting vertices into point cloud")
    pcd = o3d.geometry.PointCloud()
    pcd.points = mesh.vertices

    # Preserve normals if available
    if mesh.has_vertex_normals():
        pcd.normals = mesh.vertex_normals
        logger.info("Normals preserved")

    # Preserve colors if available
    if mesh.has_vertex_colors():
        pcd.colors = mesh.vertex_colors
        logger.info("Colors preserved")

    logger.info(f"Output: {len(pcd.points)} points")

    o3d.io.write_point_cloud(args.output, pcd)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
