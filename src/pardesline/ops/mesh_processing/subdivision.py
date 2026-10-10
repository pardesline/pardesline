"""
Mesh Subdivision — adapted from PardesLine 02_mesh_processing.

CONTRACT:
  python subdivision.py --input <mesh_file> --output <mesh_file> [--iterations N]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Mesh Loop Subdivision")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--iterations", type=int, default=1, help="Number of subdivision iterations")
    args = parser.parse_args()

    logger.info(f"Loading mesh: {args.input}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    logger.info(f"Input: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
    logger.info(f"Parameters: iterations={args.iterations}")

    logger.info("Running loop subdivision")
    mesh_subdiv = mesh.subdivide_loop(number_of_iterations=args.iterations)

    logger.info("Computing vertex normals")
    mesh_subdiv.compute_vertex_normals()

    logger.info(f"Output: {len(mesh_subdiv.vertices)} vertices, {len(mesh_subdiv.triangles)} triangles")

    o3d.io.write_triangle_mesh(args.output, mesh_subdiv)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
