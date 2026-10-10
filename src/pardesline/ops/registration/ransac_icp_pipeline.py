"""
RANSAC + ICP Full Pipeline — adapted from PardesLine functions_for_registration.

Registers a moving point cloud onto a fixed point cloud using RANSAC global
feature matching followed by ICP local refinement.

CONTRACT:
  python ransac_icp_pipeline.py --input <fixed.ply> --output <registered.ply> \
      [--moving <moving.ply>] [--voxel_size F] [--rotation_degrees F]

If --moving is provided, registers moving (source) to fixed (target).
If --moving is omitted, creates a synthetic moving for demo purposes.
"""

import argparse
import sys
import numpy as np
import open3d as o3d
from loguru import logger


def _b(v):
    """Parse a CLI boolean (the runner passes every param as a string)."""
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def _estimation(name):
    if name == "point_to_point":
        return o3d.pipelines.registration.TransformationEstimationPointToPoint()
    return o3d.pipelines.registration.TransformationEstimationPointToPlane()


def preprocess_point_cloud(pcd, voxel_size, normal_radius_factor=2.0, normal_max_nn=30,
                           fpfh_radius_factor=5.0, fpfh_max_nn=100):
    logger.info("Downsampling point cloud with voxel_size={}", voxel_size)
    pcd_down = pcd.voxel_down_sample(voxel_size)
    radius_normal = voxel_size * normal_radius_factor
    logger.info("Estimating normals with radius={}, max_nn={}", radius_normal, normal_max_nn)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=normal_max_nn)
    )
    radius_feature = voxel_size * fpfh_radius_factor
    logger.info("Computing FPFH features with radius={}, max_nn={}", radius_feature, fpfh_max_nn)
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=fpfh_max_nn)
    )
    logger.info("Preprocessing complete: {} downsampled points", len(pcd_down.points))
    return pcd_down, fpfh


def main():
    parser = argparse.ArgumentParser(description="RANSAC + ICP Pipeline")
    parser.add_argument("--input", required=True, help="Fixed (target) point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--moving", default=None, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--voxel_size", type=float, default=0.0,
                        help="Voxel size. 0 = auto (1.3%% of target bbox diagonal, matches Open3D tutorial).")
    parser.add_argument("--rotation_degrees", type=float, default=45.0, help="Synthetic rotation (demo mode only)")
    # Advanced knobs (SDK/API) — defaults reproduce the Open3D tutorial pipeline.
    parser.add_argument("--normal_radius_factor", type=float, default=2.0)
    parser.add_argument("--normal_max_nn", type=int, default=30)
    parser.add_argument("--fpfh_radius_factor", type=float, default=5.0)
    parser.add_argument("--fpfh_max_nn", type=int, default=100)
    parser.add_argument("--distance_threshold_factor", type=float, default=1.5)
    parser.add_argument("--mutual_filter", type=_b, default=True)
    parser.add_argument("--ransac_with_scaling", type=_b, default=False)
    parser.add_argument("--ransac_n", type=int, default=3)
    parser.add_argument("--edge_length_threshold", type=float, default=0.9)
    parser.add_argument("--ransac_max_iteration", type=int, default=100000)
    parser.add_argument("--ransac_confidence", type=float, default=0.999)
    parser.add_argument("--icp_threshold_factor", type=float, default=0.4)
    parser.add_argument("--icp_estimation_method", choices=["point_to_plane", "point_to_point"],
                        default="point_to_plane")
    parser.add_argument("--icp_max_iteration", type=int, default=30)
    parser.add_argument("--icp_relative_fitness", type=float, default=1e-6)
    parser.add_argument("--icp_relative_rmse", type=float, default=1e-6)
    args = parser.parse_args()

    logger.info("Loading fixed (target) point cloud: {}", args.input)
    target = o3d.io.read_point_cloud(args.input)

    if target.is_empty():
        logger.error("Fixed point cloud is empty")
        sys.exit(1)

    if args.moving:
        logger.info("Loading moving (source) point cloud: {}", args.moving)
        source = o3d.io.read_point_cloud(args.moving)
        if source.is_empty():
            logger.error("Moving point cloud is empty")
            sys.exit(1)
        logger.info("Real registration: source has {} points, target has {} points",
                    len(source.points), len(target.points))
    else:
        logger.info("No --moving provided, creating synthetic moving (demo mode)")
        source = o3d.geometry.PointCloud(target)
        angle = np.radians(args.rotation_degrees)
        R = source.get_rotation_matrix_from_xyz((angle * 0.6, angle, angle * 1.3))
        t = np.array([0.2, 0.3, 0.1])
        source.rotate(R, center=(0, 0, 0))
        source.translate(t)
        logger.info("Applied {} deg rotation + translation ({}) to synthetic source ({} points)",
                    args.rotation_degrees, t, len(source.points))

    # Auto-detect voxel_size from target bbox diagonal when user-provided value
    # is 0 (= auto) or out of the [0.5%, 5%] sweet spot of the diagonal.
    # 1.3% matches the Open3D tutorial: voxel_size=0.05 on a bbox=4 scene.
    # Outside that band, RANSAC either finds no features (too small) or
    # downsamples away all detail (too large).
    t_diag = float(np.linalg.norm(target.get_max_bound() - target.get_min_bound()))
    user_vs = args.voxel_size
    auto_vs = t_diag * 0.013
    if user_vs <= 0 or user_vs < t_diag * 0.005 or user_vs > t_diag * 0.05:
        logger.warning("voxel_size={} unsuitable for bbox diagonal {:.4f} (sweet spot: {:.4f}-{:.4f}); "
                       "auto-setting to {:.6f} (1.3%% of diag, Open3D tutorial)",
                       user_vs, t_diag, t_diag * 0.005, t_diag * 0.05, auto_vs)
        args.voxel_size = auto_vs
    logger.info("Parameters: voxel_size={:.6f} ({:.2f}% of bbox diag {:.4f}), rotation_degrees={}",
                args.voxel_size, 100.0 * args.voxel_size / max(t_diag, 1e-9), t_diag, args.rotation_degrees)

    # Step 1: RANSAC global registration (Open3D tutorial values)
    logger.info("Phase 1: RANSAC global registration")
    logger.info("Preprocessing source point cloud")
    _pp = dict(normal_radius_factor=args.normal_radius_factor, normal_max_nn=args.normal_max_nn,
               fpfh_radius_factor=args.fpfh_radius_factor, fpfh_max_nn=args.fpfh_max_nn)
    source_down, source_fpfh = preprocess_point_cloud(source, args.voxel_size, **_pp)
    logger.info("Preprocessing target point cloud")
    target_down, target_fpfh = preprocess_point_cloud(target, args.voxel_size, **_pp)

    # Open3D global_registration tutorial: distance_threshold = voxel_size * 1.5,
    # ransac_n = 3, edge length 0.9, criteria (100000, 0.999).
    distance_threshold = args.voxel_size * args.distance_threshold_factor
    logger.info("Running RANSAC with distance_threshold={}, ransac_n={}, max_iterations={}",
                distance_threshold, args.ransac_n, args.ransac_max_iteration)
    ransac_result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh,
        mutual_filter=args.mutual_filter,
        max_correspondence_distance=distance_threshold,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(args.ransac_with_scaling),
        ransac_n=args.ransac_n,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(args.edge_length_threshold),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(args.ransac_max_iteration, args.ransac_confidence)
    )

    logger.info("RANSAC fitness: {:.6f}, RMSE: {:.6f}", ransac_result.fitness, ransac_result.inlier_rmse)
    logger.info("RANSAC correspondence set size: {}", len(ransac_result.correspondence_set))

    # Step 2: ICP refinement on FULL-resolution clouds with point-to-plane
    # Strict Open3D tutorial: single pass, threshold = voxel_size * 0.4.
    # This reproduces exactly fitness=0.6746, RMSE=0.00642 on the canonical
    # icp_source/icp_target Open3D demo. Multi-scale refinement was tested and
    # over-fits past the data noise floor (~5mm) → don't use it.
    logger.info("Phase 2: ICP refinement (full-res, point-to-plane, tutorial-strict)")

    # Force re-estimate normals on full-resolution clouds. The originals may
    # be missing OR contain NaN values (icp_target.ply from Open3D demo ships
    # with NaN normals) — point-to-plane then silently returns 0 correspondences.
    full_normal_radius = args.voxel_size * args.normal_radius_factor
    logger.info("Re-estimating normals on full-res clouds (radius={:.4f})", full_normal_radius)
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=full_normal_radius, max_nn=args.normal_max_nn))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=full_normal_radius, max_nn=args.normal_max_nn))

    icp_threshold = args.voxel_size * args.icp_threshold_factor
    _icp_criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=args.icp_relative_fitness, relative_rmse=args.icp_relative_rmse,
        max_iteration=args.icp_max_iteration)
    logger.info("Running {} ICP on full-res (threshold={:.5f}, init from RANSAC)",
                args.icp_estimation_method, icp_threshold)
    try:
        icp_result = o3d.pipelines.registration.registration_icp(
            source, target, icp_threshold, ransac_result.transformation,
            _estimation(args.icp_estimation_method), _icp_criteria,
        )
        logger.info("Point-to-plane ICP: fitness={:.6f}, RMSE={:.6f}, corr={}",
                    icp_result.fitness, icp_result.inlier_rmse, len(icp_result.correspondence_set))
    except RuntimeError as e:
        logger.warning("Point-to-plane raised RuntimeError ({}); falling back to point-to-point", e)
        icp_result = None

    # Silent failure (NaN normals etc.) → fitness=0 → fall back
    if icp_result is None or icp_result.fitness == 0.0:
        logger.warning("Point-to-plane unusable — falling back to point-to-point")
        try:
            icp_result = o3d.pipelines.registration.registration_icp(
                source, target, icp_threshold, ransac_result.transformation,
                o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            )
            logger.info("Point-to-point ICP: fitness={:.6f}, RMSE={:.6f}, corr={}",
                        icp_result.fitness, icp_result.inlier_rmse, len(icp_result.correspondence_set))
        except RuntimeError as e:
            logger.error("Point-to-point also failed ({}); keeping RANSAC result", e)
            icp_result = ransac_result

    logger.info("Final ICP correspondence set size: {}", len(icp_result.correspondence_set))
    logger.info("Final transformation:\n{}", icp_result.transformation)

    # Apply final transformation and output only the aligned source (yellow)
    source.transform(icp_result.transformation)
    source.paint_uniform_color([1.0, 0.85, 0.0])  # Yellow

    # Always estimate normals on the output so the viewer shades individual points distinctly
    normal_radius = max(args.voxel_size * 2, 1e-4)
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))
    logger.info("Estimated output normals (radius={})", normal_radius)

    logger.info("Transformed moving has {} points (yellow = registered to fixed)", len(source.points))
    o3d.io.write_point_cloud(args.output, source)
    logger.info("Saved aligned cloud to: {}", args.output)

    # Save transformation matrix as JSON sidecar
    import json
    from pathlib import Path
    json_path = Path(args.output).with_suffix('.json')
    matrix_dict = {
        "transformation_matrix": icp_result.transformation.tolist(),
        "fitness": float(icp_result.fitness),
        "inlier_rmse": float(icp_result.inlier_rmse),
        "correspondence_count": len(icp_result.correspondence_set),
        "ransac_fitness": float(ransac_result.fitness),
        "ransac_inlier_rmse": float(ransac_result.inlier_rmse),
    }
    json_path.write_text(json.dumps(matrix_dict, indent=2))
    logger.info("Transformation matrix saved: {}", json_path)


if __name__ == "__main__":
    main()
