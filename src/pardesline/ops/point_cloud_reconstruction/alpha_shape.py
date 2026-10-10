"""
Alpha Shape Reconstruction — adapted from PardesLine functions_for_surfaceR.

CONTRACT:
  python alpha_shape.py --input <pcd_file> --output <mesh_file> [--alpha F]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Alpha Shape Reconstruction")
    parser.add_argument("--input", required=True, help="Input point cloud file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--alpha", type=float, default=0.03, help="Alpha parameter")
    args = parser.parse_args()

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: alpha={args.alpha}")
    pcd = o3d.io.read_point_cloud(args.input)

    if pcd.is_empty():
        logger.error("Point cloud is empty")
        sys.exit(1)

    logger.info(f"Points: {len(pcd.points)}")

    # Pre-compute tetrahedra for efficiency
    logger.info("Computing tetra mesh from point cloud")
    tetra_mesh, pt_map = o3d.geometry.TetraMesh.create_from_point_cloud(pcd)
    logger.info(f"Tetra mesh created: {len(tetra_mesh.vertices)} vertices")

    # Create alpha shape
    logger.info(f"Computing alpha shape (alpha={args.alpha})")
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
        pcd, args.alpha, tetra_mesh, pt_map
    )
    mesh.compute_vertex_normals()

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    if len(mesh.vertices) == 0:
        logger.warning("Empty mesh -- trying larger alpha values")
        import numpy as np
        bbox = pcd.get_axis_aligned_bounding_box()
        diag = np.linalg.norm(np.asarray(bbox.max_bound) - np.asarray(bbox.min_bound))
        logger.info(f"Bounding box diagonal: {diag:.4f}")
        for factor in [0.1, 0.25, 0.5, 1.0]:
            auto_alpha = diag * factor
            logger.info(f"Retrying with alpha={auto_alpha:.4f} (factor={factor})")
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
                pcd, auto_alpha, tetra_mesh, pt_map
            )
            if len(mesh.vertices) > 0:
                mesh.compute_vertex_normals()
                logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
                break

    if len(mesh.vertices) == 0:
        logger.error("Could not reconstruct mesh with any alpha value")
        sys.exit(1)

    o3d.io.write_triangle_mesh(args.output, mesh)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
