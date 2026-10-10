"""
CPD Deformable Registration — adapted from PardesLine 07_deformable_registration / functions_for_deformation.

Registers a moving point cloud onto a fixed point cloud using Coherent Point Drift.

CONTRACT:
  python cpd_deformable.py --input <fixed.ply> --output <registered.ply> \
      [--moving <moving.ply>] [--beta F] [--lambda_val F] [--max_iterations N]

If --moving is provided, deforms moving (source) to fit fixed (target).
If --moving is omitted, creates a synthetic Gaussian-deformed target for demo purposes.
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="CPD Deformable Registration")
    parser.add_argument("--input", required=True, help="Fixed (target) point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--moving", default=None, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--beta", type=float, default=100.0, help="CPD smoothness parameter")
    parser.add_argument("--lambda_val", type=float, default=2.0, help="CPD regularization weight")
    parser.add_argument("--max_iterations", type=int, default=100, help="Max CPD iterations")
    parser.add_argument("--tolerance", type=float, default=0.001, help="Convergence tolerance")
    # Advanced knobs (SDK/API) — pycpd DeformableRegistration defaults.
    parser.add_argument("--w", type=float, default=0.0, help="Outlier/noise weight")
    parser.add_argument("--low_rank", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=False,
                        help="Use low-rank Gaussian-kernel acceleration")
    parser.add_argument("--num_eig", type=int, default=100, help="Eigenvectors when low_rank=True")
    args = parser.parse_args()

    logger.info("Loading fixed (target) point cloud: {}", args.input)
    logger.info("Parameters: beta={}, lambda_val={}, max_iterations={}, tolerance={}",
                args.beta, args.lambda_val, args.max_iterations, args.tolerance)
    target_pcd_in = o3d.io.read_point_cloud(args.input)
    if target_pcd_in.is_empty():
        logger.error("Fixed point cloud is empty")
        sys.exit(1)
    target_pts_world = np.asarray(target_pcd_in.points)
    logger.info("Fixed has {} points", len(target_pts_world))

    if args.moving:
        logger.info("Loading moving (source) point cloud: {}", args.moving)
        source_pcd_in = o3d.io.read_point_cloud(args.moving)
        if source_pcd_in.is_empty():
            logger.error("Moving point cloud is empty")
            sys.exit(1)
        source_pts_world = np.asarray(source_pcd_in.points)
        logger.info("Moving has {} points (real registration)", len(source_pts_world))
    else:
        logger.info("No --moving provided, creating synthetic deformed target (demo mode)")
        # Synthetic mode: source = original, target = deformed copy
        from scipy.spatial import cKDTree
        source_pts_world = target_pts_world.copy()
        cloud_center = np.mean(target_pts_world, axis=0)
        x_left = np.min(target_pts_world[:, 0])
        bbox_diag = float(np.linalg.norm(target_pts_world.max(axis=0) - target_pts_world.min(axis=0)))
        pressure_center = np.array([x_left, cloud_center[1], cloud_center[2]])
        radius = 0.1 * bbox_diag
        direction = np.array([1.0, 0.0, 0.0])
        max_displacement = 0.003 * bbox_diag

        tree = cKDTree(target_pts_world)
        affected = tree.query_ball_point(pressure_center, r=radius)
        deformation = np.zeros_like(target_pts_world)
        if len(affected) > 0:
            affected_pts = target_pts_world[affected]
            distances = np.linalg.norm(affected_pts - pressure_center, axis=1)
            sigma = radius / 2.0
            weights = np.exp(-(distances ** 2) / (2 * sigma ** 2))
            displacements = weights[:, np.newaxis] * max_displacement * direction
            for i, idx in enumerate(affected):
                deformation[idx] = displacements[i]
        target_pts_world = source_pts_world + deformation
        logger.info("Synthetic deformation applied to {} points (radius={}, max_displacement={})",
                    len(affected), radius, max_displacement)

    # Joint normalization: use combined center+scale so source/target share a frame
    combined = np.vstack([source_pts_world, target_pts_world])
    center = np.mean(combined, axis=0)
    scale = np.linalg.norm(combined - center)
    if scale == 0:
        logger.error("Degenerate point cloud (scale=0)")
        sys.exit(1)
    source_norm = (source_pts_world - center) / scale
    target_norm = (target_pts_world - center) / scale
    logger.info("Joint normalization: center={}, scale={:.6f}", center, scale)

    try:
        from pycpd import DeformableRegistration
    except ImportError:
        logger.error("pycpd not installed. Install with: pip install pycpd")
        sys.exit(1)

    logger.info("Initializing CPD deformable registration (beta={}, alpha={}, max_iter={}, tol={})",
                args.beta, args.lambda_val, args.max_iterations, args.tolerance)
    # pycpd convention: X = target (fixed), Y = source (moving). Y is deformed onto X.
    reg = DeformableRegistration(
        X=target_norm,
        Y=source_norm,
        beta=args.beta,
        alpha=args.lambda_val,
        max_iterations=args.max_iterations,
        tol=args.tolerance,
        w=args.w,
        low_rank=args.low_rank,
        num_eig=args.num_eig,
    )

    logger.info("Running CPD registration...")
    registered_norm, params = reg.register()
    logger.info("Registration complete")

    # CPD's sigma^2 final value is its convergence indicator (lower = better fit).
    # We can't subtract registered (source-shape) - target unless point counts match.
    final_sigma2 = float(getattr(reg, "sigma2", float("nan")))
    logger.info("Final CPD sigma^2 (normalized): {:.6f}", final_sigma2)

    # Un-normalize
    registered_world = registered_norm * scale + center

    # Visualization: fixed (target) in red, registered moving in green
    target_pcd = o3d.geometry.PointCloud()
    target_pcd.points = o3d.utility.Vector3dVector(target_pts_world)
    target_pcd.paint_uniform_color([1, 0, 0])

    result_pcd = o3d.geometry.PointCloud()
    result_pcd.points = o3d.utility.Vector3dVector(registered_world)
    result_pcd.paint_uniform_color([0, 1, 0])

    combined_out = target_pcd + result_pcd

    # Always estimate normals on the output so the viewer shades individual points distinctly
    bbox_diag = float(np.linalg.norm(
        np.asarray(combined_out.points).max(axis=0) -
        np.asarray(combined_out.points).min(axis=0)
    ))
    normal_radius = max(bbox_diag * 0.02, 1e-4)
    combined_out.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))
    logger.info("Estimated output normals (radius={:.6f})", normal_radius)

    logger.info("Combined output has {} points (target=red, registered moving=green)",
                len(combined_out.points))
    o3d.io.write_point_cloud(args.output, combined_out)
    logger.info("Saved to: {}", args.output)


if __name__ == "__main__":
    main()
