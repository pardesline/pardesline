"""
Penetration Depth Measurement — adapted from PardesLine 12_collision_measure_SDF.

Measures penetration depth between input geometry and a synthetic obstacle.
Outputs the collision zone with depth-coded colors and prints metrics.

CONTRACT:
  python penetration_depth.py --input <file> --output <pcd_file> [--obstacle_radius F] [--overlap_distance F]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Penetration Depth Measurement")
    parser.add_argument("--input", required=True, help="Input mesh/point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--obstacle_radius", type=float, default=0.5, help="Obstacle sphere radius")
    parser.add_argument("--overlap_distance", type=float, default=0.15, help="Overlap distance")
    parser.add_argument("--num_samples", type=int, default=50000, help="Number of surface sample points for SDF evaluation")
    parser.add_argument("--obstacle_resolution", type=int, default=50, help="Sphere tessellation resolution for the obstacle mesh")
    parser.add_argument("--colormap", type=str, default="hot", help="Matplotlib colormap for penetration-depth coloring")
    args = parser.parse_args()

    logger.info("Loading mesh from {}", args.input)
    mesh = o3d.io.read_triangle_mesh(args.input)

    if mesh.is_empty():
        logger.error("Input is empty")
        sys.exit(1)

    # If point cloud, build convex hull
    if len(mesh.triangles) == 0:
        logger.info("No triangles found, building convex hull mesh from {} vertices", len(mesh.vertices))
        pcd_tmp = o3d.geometry.PointCloud(mesh.vertices)
        mesh, _ = pcd_tmp.compute_convex_hull()

    mesh.compute_vertex_normals()
    logger.info("Mesh: {} vertices, {} triangles", len(mesh.vertices), len(mesh.triangles))
    logger.info("Parameters: obstacle_radius={}, overlap_distance={}", args.obstacle_radius, args.overlap_distance)

    # Compute bounding info — use actual max distance from center
    bbox = mesh.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    mesh_radius = np.max(np.linalg.norm(np.asarray(mesh.vertices) - center, axis=1))
    logger.info("Mesh bounding radius: {:.4f}", mesh_radius)

    # Place obstacle overlapping the input
    R_obs = args.obstacle_radius
    obstacle_center = center + np.array([mesh_radius + R_obs - args.overlap_distance, 0, 0])

    logger.info("Obstacle: R={}, overlap={}, center=[{:.4f}, {:.4f}, {:.4f}]",
                R_obs, args.overlap_distance, obstacle_center[0], obstacle_center[1], obstacle_center[2])

    # Create obstacle mesh
    logger.info(f"Creating obstacle sphere mesh (resolution={args.obstacle_resolution})")
    obstacle = o3d.geometry.TriangleMesh.create_sphere(radius=R_obs, resolution=args.obstacle_resolution)
    obstacle.translate(obstacle_center)

    # Sample points on input mesh
    logger.info(f"Sampling {args.num_samples} points on input mesh surface")
    pcd_input = mesh.sample_points_uniformly(number_of_points=args.num_samples)
    input_points = np.asarray(pcd_input.points)

    # Compute SDF against obstacle
    logger.info("Computing signed distance field against obstacle")
    obstacle_t = o3d.t.geometry.TriangleMesh.from_legacy(obstacle)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(obstacle_t)

    query = o3d.core.Tensor(input_points.astype(np.float32), dtype=o3d.core.Dtype.Float32)
    sdf_values = scene.compute_signed_distance(query).numpy()

    # Extract penetrating points only
    penetrating_mask = sdf_values < 0
    pen_points = input_points[penetrating_mask]
    pen_sdf = sdf_values[penetrating_mask]

    if len(pen_points) == 0:
        logger.info("No penetration detected -- geometries don't overlap")
        pcd_input.paint_uniform_color([0, 1, 0])
        o3d.io.write_point_cloud(args.output, pcd_input)
        logger.info("Saved (no collision) to {}", args.output)
        return

    # Metrics
    max_depth = abs(pen_sdf.min())
    mean_depth = abs(pen_sdf.mean())
    pen_bbox_min = pen_points.min(axis=0)
    pen_bbox_max = pen_points.max(axis=0)
    pen_bbox_size = pen_bbox_max - pen_bbox_min

    logger.info("Penetrating points: {} / {}", len(pen_points), len(input_points))
    logger.info("Max penetration depth: {:.6f}", max_depth)
    logger.info("Mean penetration depth: {:.6f}", mean_depth)
    logger.info("Collision BBox size: [{:.4f}, {:.4f}, {:.4f}]",
                pen_bbox_size[0], pen_bbox_size[1], pen_bbox_size[2])

    # Color penetrating points by depth (hot colormap)
    logger.info(f"Applying {args.colormap} colormap to penetration depth values")
    import matplotlib
    depth_norm = np.clip(np.abs(pen_sdf) / (max_depth + 1e-12), 0, 1)
    cmap = matplotlib.colormaps[args.colormap]
    pen_colors = cmap(depth_norm)[:, :3]

    pen_pcd = o3d.geometry.PointCloud()
    pen_pcd.points = o3d.utility.Vector3dVector(pen_points)
    pen_pcd.colors = o3d.utility.Vector3dVector(pen_colors)

    # Non-penetrating points in gray
    safe_mask = ~penetrating_mask
    safe_pcd = o3d.geometry.PointCloud()
    safe_pcd.points = o3d.utility.Vector3dVector(input_points[safe_mask])
    safe_pcd.paint_uniform_color([0.7, 0.7, 0.7])

    combined = pen_pcd + safe_pcd
    o3d.io.write_point_cloud(args.output, combined)
    logger.info("Saved penetration depth result ({} total points) to {}",
                len(combined.points), args.output)


if __name__ == "__main__":
    main()
