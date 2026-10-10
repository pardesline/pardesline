"""
SDF-Based Collision Detection — adapted from PardesLine 12_collision_measure_SDF.

Detects collision between input geometry and a synthetic obstacle using SDF.
Colors penetrating points by depth.

CONTRACT:
  python sdf_collision.py --input <file> --output <pcd_file> [--obstacle_radius F] [--penetration_ratio F] [--num_samples N]
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="SDF-Based Collision Detection")
    parser.add_argument("--input", required=True, help="Input mesh/point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--obstacle_radius", type=float, default=0.5, help="Obstacle sphere radius")
    parser.add_argument("--penetration_ratio", type=float, default=0.3, help="Penetration ratio")
    parser.add_argument("--num_samples", type=int, default=50000, help="Number of surface samples")
    parser.add_argument("--obstacle_resolution", type=int, default=50, help="Sphere tessellation resolution for the obstacle mesh")
    parser.add_argument("--obstacle_viz_points", type=int, default=5000, help="Points sampled on the obstacle for visualization")
    parser.add_argument("--colormap", type=str, default="coolwarm", help="Matplotlib colormap for SDF coloring")
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
    logger.info("Parameters: obstacle_radius={}, penetration_ratio={}, num_samples={}",
                args.obstacle_radius, args.penetration_ratio, args.num_samples)

    # Compute bounding info — use actual max distance from center
    bbox = mesh.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    mesh_radius = np.max(np.linalg.norm(np.asarray(mesh.vertices) - center, axis=1))
    logger.info("Mesh bounding radius: {:.4f}, center: [{:.4f}, {:.4f}, {:.4f}]",
                mesh_radius, center[0], center[1], center[2])

    # Place obstacle sphere overlapping the input
    R_obs = args.obstacle_radius
    penetration = args.penetration_ratio * R_obs
    obstacle_center = center + np.array([mesh_radius + R_obs - penetration, 0, 0])

    logger.info("Obstacle sphere: R={}, center=[{:.4f}, {:.4f}, {:.4f}], penetration={:.4f}",
                R_obs, obstacle_center[0], obstacle_center[1], obstacle_center[2], penetration)

    # Create obstacle mesh for SDF computation
    logger.info(f"Creating obstacle sphere mesh (resolution={args.obstacle_resolution})")
    obstacle = o3d.geometry.TriangleMesh.create_sphere(radius=R_obs, resolution=args.obstacle_resolution)
    obstacle.translate(obstacle_center)

    # Sample points on input mesh
    logger.info("Sampling {} points on input mesh surface", args.num_samples)
    pcd_input = mesh.sample_points_uniformly(number_of_points=args.num_samples)
    input_points = np.asarray(pcd_input.points)

    # Compute SDF of input points against obstacle
    logger.info("Computing signed distance field against obstacle")
    obstacle_t = o3d.t.geometry.TriangleMesh.from_legacy(obstacle)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(obstacle_t)

    query = o3d.core.Tensor(input_points.astype(np.float32), dtype=o3d.core.Dtype.Float32)
    sdf_values = scene.compute_signed_distance(query).numpy()

    # Find penetrating points (inside obstacle = negative SDF)
    penetrating_mask = sdf_values < 0
    n_penetrating = np.sum(penetrating_mask)
    logger.info("Penetrating points: {} / {} ({:.1f}%)", n_penetrating, len(input_points),
                100.0 * n_penetrating / len(input_points))
    logger.info("SDF range: [{:.6f}, {:.6f}]", sdf_values.min(), sdf_values.max())

    # Color all points by SDF: red=inside, blue=outside
    import matplotlib
    sdf_norm = np.clip(sdf_values / (np.abs(sdf_values).max() + 1e-12), -1, 1)
    # Map [-1, 1] to [0, 1] for colormap (red=penetrating, blue=safe)
    color_val = (sdf_norm + 1) / 2
    cmap = matplotlib.colormaps[args.colormap]
    colors = cmap(color_val)[:, :3]

    pcd_input.colors = o3d.utility.Vector3dVector(colors)

    # Also sample obstacle for visualization
    logger.info(f"Sampling {args.obstacle_viz_points} points on obstacle for visualization")
    pcd_obstacle = obstacle.sample_points_uniformly(number_of_points=args.obstacle_viz_points)
    pcd_obstacle.paint_uniform_color([0.8, 0.8, 0.2])

    combined = pcd_input + pcd_obstacle
    o3d.io.write_point_cloud(args.output, combined)
    logger.info("Saved collision result ({} total points) to {}", len(combined.points), args.output)


if __name__ == "__main__":
    main()
