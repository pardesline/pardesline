"""
SDF Voxel Visualization — Colored point cloud showing signed distance field.

Each voxel center is colored using a coolwarm diverging colormap:
  - Blue (interior, SDF < 0)
  - White (surface, SDF ~ 0)
  - Red (exterior, SDF > 0)

CONTRACT:
  python sdf_voxel_visualization.py --input <mesh> --output <output.ply> \
      [--resolution 32] [--min_clamp -0.1] [--max_clamp 0.1]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
import matplotlib
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="SDF Voxel Visualization")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output point cloud (PLY)")
    parser.add_argument("--resolution", type=int, default=32,
                        help="Grid resolution per axis (8-128)")
    parser.add_argument("--min_clamp", type=float, default=-0.1,
                        help="Min SDF clamp value")
    parser.add_argument("--max_clamp", type=float, default=0.1,
                        help="Max SDF clamp value")
    # Advanced knobs (SDK/API).
    parser.add_argument("--padding_factor", type=float, default=0.15,
                        help="Bbox padding as a fraction of the max extent")
    parser.add_argument("--colormap", type=str, default="coolwarm",
                        help="Matplotlib diverging colormap (e.g. coolwarm, bwr, seismic, RdBu)")
    args = parser.parse_args()

    logger.info(f"Loading: {args.input}")
    logger.info(f"Parameters: resolution={args.resolution}, min_clamp={args.min_clamp}, max_clamp={args.max_clamp}")
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Mesh is empty")
        sys.exit(1)

    logger.info(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    # Build convex hull if no triangles (e.g. point cloud input)
    if len(mesh.triangles) == 0:
        logger.info("No triangles - building convex hull")
        pcd_tmp = o3d.geometry.PointCloud(mesh.vertices)
        mesh, _ = pcd_tmp.compute_convex_hull()
        logger.info(f"Hull: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    logger.info("Computing vertex normals")
    mesh.compute_vertex_normals()

    # Raycasting scene for SDF computation
    logger.info("Building raycasting scene")
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh_t)

    # Compute bounding box with padding
    bbox = mesh.get_axis_aligned_bounding_box()
    min_bound = np.asarray(bbox.min_bound).copy()
    max_bound = np.asarray(bbox.max_bound).copy()
    extent = max_bound - min_bound
    pad = extent.max() * args.padding_factor
    min_bound -= pad
    max_bound += pad
    logger.info(f"Bounding box extent: {extent}, padding: {pad:.4f}")

    # Generate regular 3D grid
    res = max(8, min(128, args.resolution))
    xs = np.linspace(min_bound[0], max_bound[0], res)
    ys = np.linspace(min_bound[1], max_bound[1], res)
    zs = np.linspace(min_bound[2], max_bound[2], res)

    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing='ij')
    points = np.vstack((gx.ravel(), gy.ravel(), gz.ravel())).T

    total_voxels = len(points)
    logger.info(f"Grid: {res}x{res}x{res} = {total_voxels} voxels")

    # Compute signed distances
    logger.info("Computing signed distance field")
    query = o3d.core.Tensor(points.astype(np.float32), dtype=o3d.core.Dtype.Float32)
    sdf_values = scene.compute_signed_distance(query).numpy()

    logger.info(f"SDF range: [{sdf_values.min():.6f}, {sdf_values.max():.6f}]")

    # Clamp SDF values
    min_clamp = args.min_clamp
    max_clamp = args.max_clamp

    # Filter: keep only voxels within the SDF range [min_clamp, max_clamp].
    # This removes the far-exterior shell (all red) and deep-interior bulk (all blue),
    # revealing the near-surface band where both interior (blue) and exterior (red) are visible.
    mask = (sdf_values >= min_clamp) & (sdf_values <= max_clamp)
    filtered_points = points[mask]
    filtered_sdf = sdf_values[mask]

    logger.info(f"Near-surface band: {filtered_points.shape[0]} / {total_voxels} voxels kept")

    # Normalize to [0, 1] for colormap (blue=interior, white=surface, red=exterior)
    denom = max_clamp - min_clamp
    if denom < 1e-12:
        denom = 1.0
    normalized = (filtered_sdf - min_clamp) / denom

    # Apply coolwarm colormap
    logger.info("Applying coolwarm colormap")
    cmap = matplotlib.colormaps[args.colormap]
    colors = cmap(normalized)[:, :3]  # RGB only

    # Create colored point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(filtered_points)
    pcd.colors = o3d.utility.Vector3dVector(colors)

    logger.info(f"Output: {filtered_points.shape[0]} colored voxel points")

    o3d.io.write_point_cloud(args.output, pcd)
    logger.info(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
