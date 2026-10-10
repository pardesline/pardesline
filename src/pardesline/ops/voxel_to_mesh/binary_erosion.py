"""
Binary Erosion + Marching Cubes Reconstruction — adapted from PardesLine 03_mesh_pcd_to_volume / functions_for_sdf.

CONTRACT:
  python binary_erosion.py --input <mesh_file> --output <mesh_file> [--voxel_size F] [--erosion_iterations N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Binary Erosion + Reconstruction")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--voxel_size", type=float, default=0.01, help="Voxel size")
    parser.add_argument("--erosion_iterations", type=int, default=1, help="Erosion iterations")
    parser.add_argument("--erosion_connectivity", type=int, default=1, choices=[1, 2, 3], help="Connectivity of the 3D structuring element (1=faces, 2=+edges, 3=+corners)")
    parser.add_argument("--iso_level", type=float, default=0.5, help="Marching-cubes iso-surface level")
    parser.add_argument("--padding_voxels", type=int, default=5, help="Padding around the bounding box, in voxels")
    args = parser.parse_args()

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: voxel_size={args.voxel_size}, erosion_iterations={args.erosion_iterations}, erosion_connectivity={args.erosion_connectivity}, iso_level={args.iso_level}, padding_voxels={args.padding_voxels}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    if len(mesh.triangles) == 0:
        logger.info("No triangles -- building convex hull mesh")
        pcd_tmp = o3d.geometry.PointCloud(mesh.vertices)
        mesh, _ = pcd_tmp.compute_convex_hull()
        logger.info(f"Hull: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    logger.info("Computing vertex normals")
    mesh.compute_vertex_normals()

    # Create raycasting scene for occupancy
    logger.info("Building raycasting scene")
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh_t)

    # Create grid
    bbox = mesh.get_axis_aligned_bounding_box()
    padding = args.padding_voxels * args.voxel_size
    min_bound = np.asarray(bbox.min_bound) - padding
    max_bound = np.asarray(bbox.max_bound) + padding

    xs = np.arange(min_bound[0], max_bound[0], args.voxel_size)
    ys = np.arange(min_bound[1], max_bound[1], args.voxel_size)
    zs = np.arange(min_bound[2], max_bound[2], args.voxel_size)
    grid_shape = (len(xs), len(ys), len(zs))

    logger.info(f"Grid: {grid_shape}, total voxels: {np.prod(grid_shape)}")

    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing='ij')
    points = np.vstack((gx.ravel(), gy.ravel(), gz.ravel())).T

    # Compute occupancy
    logger.info("Computing occupancy field")
    query = o3d.core.Tensor(points.astype(np.float32), dtype=o3d.core.Dtype.Float32)
    occupancy = scene.compute_occupancy(query).numpy().astype(bool)
    volume = occupancy.reshape(grid_shape)

    logger.info(f"Occupied voxels: {np.sum(volume)}")

    # Apply binary erosion
    logger.info(f"Applying binary erosion with {args.erosion_iterations} iteration(s)")
    from scipy.ndimage import generate_binary_structure, binary_erosion
    struct = generate_binary_structure(3, args.erosion_connectivity)
    eroded = binary_erosion(volume, structure=struct, iterations=args.erosion_iterations)

    logger.info(f"After erosion: {np.sum(eroded)} voxels ({100*(1-np.sum(eroded)/(np.sum(volume)+1e-12)):.1f}% reduction)")

    # Marching cubes reconstruction
    logger.info("Running marching cubes reconstruction")
    from skimage import measure
    volume_mc = np.transpose(eroded.astype(np.float32), (2, 1, 0))
    verts, faces, normals, values = measure.marching_cubes(
        volume_mc, level=args.iso_level, spacing=(args.voxel_size, args.voxel_size, args.voxel_size)
    )
    verts = verts[:, ::-1] + min_bound

    mesh_out = o3d.geometry.TriangleMesh()
    mesh_out.vertices = o3d.utility.Vector3dVector(verts)
    mesh_out.triangles = o3d.utility.Vector3iVector(faces.astype(np.int32))
    mesh_out.compute_vertex_normals()

    logger.info(f"Reconstructed: {len(mesh_out.vertices)} vertices, {len(mesh_out.triangles)} triangles")

    o3d.io.write_triangle_mesh(args.output, mesh_out)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
