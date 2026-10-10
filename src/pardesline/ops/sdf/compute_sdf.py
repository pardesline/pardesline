"""
SDF Computation + Marching Cubes — adapted from PardesLine 04_SDF / functions_for_sdf.

CONTRACT:
  python compute_sdf.py --input <mesh_file> --output <mesh_file> [--voxel_size F] [--padding N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="SDF Computation + Marching Cubes")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--voxel_size", type=float, default=0.01, help="Voxel size for SDF grid")
    parser.add_argument("--padding", type=int, default=5, help="Padding voxels around bounding box")
    # Advanced marching-cubes knobs (SDK/API) — defaults are the skimage defaults.
    parser.add_argument("--level", type=float, default=0.0, help="Iso-level for surface extraction")
    parser.add_argument("--mc_step_size", type=int, default=1, help="Marching-cubes voxel step (coarser = faster)")
    parser.add_argument("--mc_method", choices=["lewiner", "lorensen"], default="lewiner")
    parser.add_argument("--mc_gradient_direction", choices=["descent", "ascent"], default="descent")
    parser.add_argument("--mc_allow_degenerate", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=True)
    args = parser.parse_args()

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: voxel_size={args.voxel_size}, padding={args.padding}")
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

    # Create raycasting scene
    logger.info("Building raycasting scene")
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh_t)

    # Create grid
    bbox = mesh.get_axis_aligned_bounding_box()
    pad = args.padding * args.voxel_size
    min_bound = np.asarray(bbox.min_bound) - pad
    max_bound = np.asarray(bbox.max_bound) + pad

    xs = np.arange(min_bound[0], max_bound[0] + 1e-12, args.voxel_size)
    ys = np.arange(min_bound[1], max_bound[1] + 1e-12, args.voxel_size)
    zs = np.arange(min_bound[2], max_bound[2] + 1e-12, args.voxel_size)
    grid_shape = (len(xs), len(ys), len(zs))

    logger.info(f"Grid: {grid_shape}, total voxels: {np.prod(grid_shape)}")

    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing='ij')
    points = np.vstack((gx.ravel(), gy.ravel(), gz.ravel())).T

    # Compute SDF
    logger.info("Computing signed distance field")
    query = o3d.core.Tensor(points.astype(np.float32), dtype=o3d.core.Dtype.Float32)
    sdf = scene.compute_signed_distance(query).numpy()
    sdf_grid = sdf.reshape(grid_shape)

    logger.info(f"SDF range: [{sdf.min():.6f}, {sdf.max():.6f}]")

    # Marching cubes at zero level-set
    logger.info("Running marching cubes at zero level-set")
    from skimage import measure
    sdf_transposed = np.transpose(sdf_grid, (2, 1, 0))
    verts, faces, normals, values = measure.marching_cubes(
        sdf_transposed, level=args.level, spacing=(args.voxel_size, args.voxel_size, args.voxel_size),
        step_size=args.mc_step_size, method=args.mc_method,
        gradient_direction=args.mc_gradient_direction, allow_degenerate=args.mc_allow_degenerate
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
