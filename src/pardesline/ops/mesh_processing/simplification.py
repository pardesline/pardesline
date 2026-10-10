"""
Mesh Simplification (Quadric Decimation) — adapted from PardesLine 02_mesh_processing.

CONTRACT:
  python simplification.py --input <mesh_file> --output <mesh_file> [--target_triangles N]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Mesh Quadric Simplification")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--target_triangles", type=int, default=5000, help="Target number of triangles")
    parser.add_argument("--maximum_error", type=float, default=1e30, help="Advisory max quadric error per collapse (very large = unbounded)")
    parser.add_argument("--boundary_weight", type=float, default=1.0, help="Weight applied to boundary edges")
    args = parser.parse_args()

    logger.info(f"Loading mesh: {args.input}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    logger.info(f"Input: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
    logger.info(f"Parameters: target_triangles={args.target_triangles}, maximum_error={args.maximum_error}, boundary_weight={args.boundary_weight}")

    logger.info("Running quadric decimation")
    mesh_simplified = mesh.simplify_quadric_decimation(
        target_number_of_triangles=args.target_triangles,
        maximum_error=args.maximum_error,
        boundary_weight=args.boundary_weight,
    )

    logger.info("Computing vertex normals")
    mesh_simplified.compute_vertex_normals()

    reduction_pct = (1 - len(mesh_simplified.triangles) / len(mesh.triangles)) * 100 if len(mesh.triangles) > 0 else 0
    logger.info(f"Output: {len(mesh_simplified.vertices)} vertices, {len(mesh_simplified.triangles)} triangles (reduction: {reduction_pct:.1f}%)")

    o3d.io.write_triangle_mesh(args.output, mesh_simplified)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
