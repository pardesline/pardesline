"""
Mesh to Point Cloud (Poisson Disk Sampling) — adapted from PardesLine 02_mesh_processing.

CONTRACT:
  python mesh_to_pcd_poisson_disk.py --input <mesh_file> --output <pcd_file> [--num_points N]
"""

import argparse
import sys
import open3d as o3d
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Mesh to PCD Poisson Disk Sampling")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--num_points", type=int, default=10000, help="Number of points to sample")
    parser.add_argument("--init_factor", type=int, default=5, help="Initial uniform-sample oversampling factor before elimination")
    parser.add_argument("--use_triangle_normal", type=_b, default=False, help="Assign the triangle normal to each sampled point")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed (-1 = nondeterministic)")
    args = parser.parse_args()

    logger.info(f"Loading mesh: {args.input}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
    logger.info(f"Parameters: num_points={args.num_points}, init_factor={args.init_factor}, use_triangle_normal={args.use_triangle_normal}, seed={args.seed}")

    # If input has no triangles (point cloud), create mesh via convex hull
    if len(mesh.triangles) == 0:
        logger.info("No triangles found -- building convex hull mesh")
        pcd_tmp = o3d.geometry.PointCloud(mesh.vertices)
        mesh, _ = pcd_tmp.compute_convex_hull()
        logger.info(f"Hull: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    logger.info("Running Poisson disk sampling")
    sample_kwargs = dict(
        number_of_points=args.num_points,
        init_factor=args.init_factor,
        use_triangle_normal=args.use_triangle_normal,
    )
    if args.seed != -1:
        try:
            pcd = mesh.sample_points_poisson_disk(seed=args.seed, **sample_kwargs)
        except TypeError:
            logger.warning("Installed Open3D build does not support 'seed'; ignoring it")
            pcd = mesh.sample_points_poisson_disk(**sample_kwargs)
    else:
        pcd = mesh.sample_points_poisson_disk(**sample_kwargs)

    logger.info(f"Sampled {len(pcd.points)} points")

    o3d.io.write_point_cloud(args.output, pcd)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
