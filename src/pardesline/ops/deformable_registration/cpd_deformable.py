"""
CPD Deformable Registration — adapted from PardesLine 07_deformable_registration / functions_for_deformation.

Registers a moving point cloud onto a fixed point cloud using Coherent Point Drift.

CONTRACT:
  python cpd_deformable.py --input <fixed.ply> --output <registered.ply> \
      --moving <moving.ply> [--beta F] [--lambda_val F] [--max_iterations N]

Deforms moving (source) to fit fixed (target). Both clouds are normalised with one
centre and one scale (the root-mean-square distance of all points to the joint
centroid), so beta (kernel width) and lambda_val (pycpd alpha) mean the same for any
unit and point count.
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
    parser.add_argument("--moving", required=True, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--beta", type=float, default=2.0, help="CPD Gaussian kernel width, in normalised units")
    parser.add_argument("--lambda_val", type=float, default=2.0, help="CPD regularization weight")
    parser.add_argument("--max_iterations", type=int, default=100, help="Max CPD iterations")
    parser.add_argument("--tolerance", type=float, default=0.001, help="Convergence tolerance")
    # Advanced knobs (SDK/API) — pycpd DeformableRegistration defaults.
    parser.add_argument("--w", type=float, default=0.0, help="Outlier/noise weight")
    parser.add_argument("--low_rank", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=False,
                        help="Not supported by pycpd 2: true is refused")
    parser.add_argument("--num_eig", type=int, default=100, help="Ignored (only meaningful with low_rank)")
    parser.add_argument("--min_fitness", type=float, default=0.5,
                        help="Fail (exit 4) when fewer than this fraction of deformed moving points lie within 3 x the fixed point spacing of the fixed cloud")
    args = parser.parse_args()
    if args.low_rank:
        logger.error("--low_rank is not supported by the installed pycpd (2.x ignores it silently); "
                     "run without it")
        sys.exit(1)
    if args.num_eig != 100:
        logger.warning("--num_eig is ignored: it only applies to low_rank, which pycpd 2.x does not support")

    logger.info("Loading fixed (target) point cloud: {}", args.input)
    logger.info("Parameters: beta={}, lambda_val={}, max_iterations={}, tolerance={}",
                args.beta, args.lambda_val, args.max_iterations, args.tolerance)
    target_pcd_in = o3d.io.read_point_cloud(args.input)
    if target_pcd_in.is_empty():
        logger.error("Fixed point cloud is empty")
        sys.exit(1)
    target_pts_world = np.asarray(target_pcd_in.points)
    logger.info("Fixed has {} points", len(target_pts_world))

    logger.info("Loading moving (source) point cloud: {}", args.moving)
    source_pcd_in = o3d.io.read_point_cloud(args.moving)
    if source_pcd_in.is_empty():
        logger.error("Moving point cloud is empty")
        sys.exit(1)
    source_pts_world = np.asarray(source_pcd_in.points)
    logger.info("Moving has {} points", len(source_pts_world))

    # Joint normalization: use combined center+scale so source/target share a frame
    combined = np.vstack([source_pts_world, target_pts_world])
    center = np.mean(combined, axis=0)
    # RMS distance to the joint centroid (np.linalg.norm of the whole array grew with sqrt(N))
    scale = float(np.sqrt(((combined - center) ** 2).sum(axis=1).mean()))
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
        tolerance=args.tolerance,  # pycpd 2 name; 'tol', 'low_rank', 'num_eig' were swallowed
        w=args.w,
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

    # Quality: share of deformed moving points close to the fixed cloud (method-independent)
    import json
    from pathlib import Path
    from scipy.spatial import cKDTree

    tree = cKDTree(target_pts_world)
    spacing = float(np.median(tree.query(target_pts_world, k=2)[0][:, 1]))
    threshold = 3.0 * spacing
    dist = tree.query(registered_world)[0]
    inl = dist <= threshold
    fitness = float(inl.mean())
    quality = {
        "fitness": round(fitness, 6),
        "inlier_rmse": round(float(np.sqrt((dist[inl] ** 2).mean())), 6) if inl.any() else None,
        "fitness_threshold": threshold,
        "final_metric": final_sigma2,
        "metric_name": "CPD sigma^2 in the normalised frame (lower is tighter)",
        "stop_condition": f"{getattr(reg, 'iteration', None)} of {args.max_iterations} iterations, tolerance {args.tolerance}",
        "iterations": getattr(reg, "iteration", None),
        "floors": {"min_fitness": args.min_fitness},
        "status": "ok" if fitness >= args.min_fitness else "below_floor",
    }
    json_path = Path(args.output).with_suffix(".json")
    json_path.write_text(json.dumps({"method": "cpd_deformable", "quality": quality, "normalisation": {
        "centre": center.tolist(), "scale": scale}, "beta": args.beta, "lambda_val": args.lambda_val,
        "w": args.w, "output_layout": "fixed points first, then the deformed moving points in input order"},
        indent=2))
    logger.info("Quality: fitness {:.4f} at {:.4g}, status {}", fitness, threshold, quality["status"])
    if quality["status"] != "ok":
        logger.error("Registration quality below the floor: fitness {:.4f} < {} ({} written)", fitness,
                     args.min_fitness, json_path)
        sys.exit(4)


if __name__ == "__main__":
    main()
