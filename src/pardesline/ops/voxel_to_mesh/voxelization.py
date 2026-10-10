"""
Mesh Voxelization — adapted from PardesLine 03_mesh_pcd_to_volume.

Creates a voxel grid from a mesh and outputs the voxel centers as a point cloud.

CONTRACT:
  python voxelization.py --input <mesh_file> --output <pcd_file> [--voxel_size F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Mesh Voxelization")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--voxel_size", type=float, default=0.01, help="Voxel size")
    args = parser.parse_args()

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: voxel_size={args.voxel_size}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty() or len(mesh.triangles) == 0:
        # Try reading as point cloud
        pcd = o3d.io.read_point_cloud(args.input)
        if pcd.is_empty():
            logger.error("Input is empty")
            sys.exit(1)
        # Create voxel grid from point cloud
        logger.info(f"Input point cloud: {len(pcd.points)} points")
        logger.info("Creating voxel grid from point cloud")
        voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(pcd, voxel_size=args.voxel_size)
    else:
        logger.info(f"Input mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
        logger.info("Creating voxel grid from triangle mesh")
        voxel_grid = o3d.geometry.VoxelGrid.create_from_triangle_mesh(mesh, voxel_size=args.voxel_size)

    # Extract voxel centers as point cloud
    voxels = voxel_grid.get_voxels()
    logger.info(f"Extracting centers from {len(voxels)} voxels")
    centers = np.array([voxel_grid.get_voxel_center_coordinate(v.grid_index) for v in voxels])

    logger.info(f"Voxels created: {len(centers)}")

    # Create output point cloud with colors
    pcd_out = o3d.geometry.PointCloud()
    pcd_out.points = o3d.utility.Vector3dVector(centers)

    # Color by height
    if len(centers) > 0:
        z = centers[:, 2]
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-12)
        colors = np.zeros((len(centers), 3))
        colors[:, 0] = z_norm
        colors[:, 2] = 1.0 - z_norm
        pcd_out.colors = o3d.utility.Vector3dVector(colors)
        logger.info(f"Applied height-based coloring (z range: [{z.min():.4f}, {z.max():.4f}])")

    o3d.io.write_point_cloud(args.output, pcd_out)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
