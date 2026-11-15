"""
ICP Registration — Open3D point-to-plane / point-to-point ICP.

Conforms to the Open3D ICP tutorial pattern:
  http://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html

Steps: down-sample both clouds (voxel v) and estimate normals (2v); initial pose
from a seeded FPFH + RANSAC pre-pass, or, when its fitness is not above
--ransac_seed_fitness, a translation that aligns the centroids (the JSON says which);
ICP on the down-sampled clouds at --icp_threshold_factor x v; normals re-estimated at
full resolution; ICP on the full-resolution clouds at --refine_threshold_factor x v.
Each ICP pass falls back to point-to-point (same criteria) when point-to-plane fails.

ICP is a *local* optimizer — for large initial rotations (>~30 deg) use the
RANSAC + ICP pipeline instead, which seeds ICP with a global FPFH match.

CONTRACT:
  python icp_refinement.py --input <fixed.ply> --output <registered.ply> \
      --moving <moving.ply> [--voxel_size F] [--max_iterations N] [--seed N]

The output is the moving cloud as read (colours, normals) transformed by T;
the JSON sidecar holds T (p_fixed = T @ [p_moving, 1]) and the parameters used.
"""

import os

# Open3D draws RANSAC samples from one global generator in parallel threads: a seeded run
# is reproducible only on one thread (audit 2026-11, X7). Must precede "import open3d".
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import open3d as o3d
from loguru import logger

from pardesline.ops.registration import _common as C


def _b(v):
    """Parse a CLI boolean (the runner passes every param as a string)."""
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def _estimation(name):
    """Map an estimation-method name to the Open3D estimator."""
    if name == "point_to_point":
        return o3d.pipelines.registration.TransformationEstimationPointToPoint()
    return o3d.pipelines.registration.TransformationEstimationPointToPlane()


def bbox_diag(pcd: o3d.geometry.PointCloud) -> float:
    return float(np.linalg.norm(pcd.get_max_bound() - pcd.get_min_bound()))


def preprocess(pcd: o3d.geometry.PointCloud, voxel_size: float,
               normal_radius_factor: float = 2.0, normal_max_nn: int = 30) -> o3d.geometry.PointCloud:
    """Downsample and estimate normals — matches the Open3D tutorial."""
    down = pcd.voxel_down_sample(voxel_size)
    normal_radius = voxel_size * normal_radius_factor
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=normal_max_nn)
    )
    return down


def main():
    parser = argparse.ArgumentParser(description="ICP Registration (Open3D)")
    parser.add_argument("--input", required=True, help="Fixed (target) point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--moving", required=True, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--voxel_size", type=float, default=0.0,
                        help="Voxel size in file units, used as given. 0 = auto (1.3 percent of the fixed bbox diagonal).")
    parser.add_argument("--max_iterations", type=int, default=2000, help="Max ICP iterations")
    # Advanced knobs (SDK/API) — defaults reproduce the tutorial-strict pipeline.
    parser.add_argument("--icp_estimation_method", choices=["point_to_plane", "point_to_point"],
                        default="point_to_plane")
    parser.add_argument("--relative_fitness", type=float, default=1e-6)
    parser.add_argument("--relative_rmse", type=float, default=1e-6)
    parser.add_argument("--icp_threshold_factor", type=float, default=1.5)
    parser.add_argument("--refine_threshold_factor", type=float, default=0.4)
    parser.add_argument("--normal_radius_factor", type=float, default=2.0)
    parser.add_argument("--normal_max_nn", type=int, default=30)
    parser.add_argument("--fpfh_radius_factor", type=float, default=5.0)
    parser.add_argument("--fpfh_max_nn", type=int, default=100)
    parser.add_argument("--ransac_distance_factor", type=float, default=1.5)
    parser.add_argument("--mutual_filter", type=_b, default=True)
    parser.add_argument("--ransac_with_scaling", type=_b, default=False)
    parser.add_argument("--ransac_n", type=int, default=3)
    parser.add_argument("--edge_length_threshold", type=float, default=0.9)
    parser.add_argument("--ransac_max_iteration", type=int, default=100000)
    parser.add_argument("--ransac_confidence", type=float, default=0.999)
    parser.add_argument("--ransac_seed_fitness", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=0, help="Seed of the RANSAC pre-pass")
    parser.add_argument("--min_fitness", type=float, default=C.DEFAULT_MIN_FITNESS,
                        help="Fail (exit 4) when fewer than this fraction of moving points lie within 1.5 x voxel of the fixed cloud after registration")
    args = parser.parse_args()

    logger.info("Loading fixed (target): {}", args.input)
    target = o3d.io.read_point_cloud(args.input)
    if target.is_empty():
        logger.error("Fixed point cloud is empty")
        sys.exit(1)

    logger.info("Loading moving (source): {}", args.moving)
    source = o3d.io.read_point_cloud(args.moving)
    if source.is_empty():
        logger.error("Moving point cloud is empty")
        sys.exit(1)
    logger.info("Source={} pts, target={} pts", len(source.points), len(target.points))

    args.voxel_size, voxel_auto = C.choose_voxel(target, args.voxel_size)

    # Tutorial-style preprocessing — downsample + normals for point-to-plane
    logger.info("Preprocessing source (voxel_size={})", args.voxel_size)
    source_down = preprocess(source, args.voxel_size, args.normal_radius_factor, args.normal_max_nn)
    logger.info("Preprocessing target (voxel_size={})", args.voxel_size)
    target_down = preprocess(target, args.voxel_size, args.normal_radius_factor, args.normal_max_nn)
    logger.info("Downsampled: source={} pts, target={} pts",
                len(source_down.points), len(target_down.points))

    # Initial alignment: the Open3D ICP tutorial uses a hand-picked trans_init
    # close to the answer. We don't have that luxury — so for non-trivial
    # rotations (>~20°) we need a global pre-alignment. Try a quick FPFH-RANSAC
    # pass; if RANSAC gives a usable seed (fitness > 0.3), use it. Otherwise
    # fall back to a translation-only center-of-mass init.
    logger.info("Computing FPFH features for global init (RANSAC pre-pass)")
    src_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        source_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=args.voxel_size * args.fpfh_radius_factor, max_nn=args.fpfh_max_nn))
    tgt_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        target_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=args.voxel_size * args.fpfh_radius_factor, max_nn=args.fpfh_max_nn))
    ransac_thr = args.voxel_size * args.ransac_distance_factor
    o3d.utility.random.seed(args.seed)
    ransac_result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, src_fpfh, tgt_fpfh,
        mutual_filter=args.mutual_filter,
        max_correspondence_distance=ransac_thr,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(args.ransac_with_scaling),
        ransac_n=args.ransac_n,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(args.edge_length_threshold),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(ransac_thr),
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(args.ransac_max_iteration, args.ransac_confidence),
    )
    logger.info("RANSAC pre-pass: fitness={:.6f}, RMSE={:.6f}",
                ransac_result.fitness, ransac_result.inlier_rmse)

    if ransac_result.fitness > args.ransac_seed_fitness:
        trans_init = ransac_result.transformation
        init_stage = "RANSAC pre-pass"
        logger.info("Using RANSAC transform as init (fitness > {})", args.ransac_seed_fitness)
    else:
        src_center = source_down.get_center()
        tgt_center = target_down.get_center()
        trans_init = np.eye(4)
        trans_init[:3, 3] = tgt_center - src_center
        init_stage = "centroid translation (RANSAC pre-pass fitness too low)"
        logger.info("RANSAC fitness too low — falling back to center-of-mass init "
                    "(translation only): {}", trans_init[:3, 3])

    # ICP — Open3D tutorial uses threshold ~= voxel_size * 1.5 to voxel_size * 4
    # depending on init quality. After centering, voxel_size * 1.5 is appropriate.
    threshold = args.voxel_size * args.icp_threshold_factor
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=args.relative_fitness,
        relative_rmse=args.relative_rmse,
        max_iteration=args.max_iterations,
    )
    primary_est = _estimation(args.icp_estimation_method)

    def _icp(src, tgt, thr, init, estimation, label):
        try:
            r = o3d.pipelines.registration.registration_icp(
                src, tgt, thr, init, estimation, criteria)
            logger.info("{}: fitness={:.6f}, RMSE={:.6f}, corr={}",
                        label, r.fitness, r.inlier_rmse, len(r.correspondence_set))
            return r
        except RuntimeError as e:
            logger.warning("{} raised RuntimeError: {}", label, e)
            return None

    logger.info("Running point-to-plane ICP (threshold={}, max_iter={})",
                threshold, args.max_iterations)
    result = _icp(source_down, target_down, threshold, trans_init, primary_est,
                  f"{args.icp_estimation_method} (down)")
    # Detect silent failure (fitness=0, RMSE=0 with empty correspondences)
    if result is None or result.fitness == 0.0:
        logger.warning("Point-to-plane unusable — falling back to point-to-point")
        result = _icp(source_down, target_down, threshold, trans_init,
                      o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                      "Point-to-point (down)")
    if result is None:
        logger.error("ICP failed on downsampled clouds; aborting")
        sys.exit(1)

    # Force re-estimate normals on full-resolution clouds. Files may ship with
    # stale or NaN normals (icp_target.ply from Open3D demo is one such case),
    # which causes point-to-plane to silently return 0 correspondences.
    _nr = args.voxel_size * args.normal_radius_factor
    logger.info("Re-estimating normals on full-res clouds (radius={:.4f})", _nr)
    source.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=_nr, max_nn=args.normal_max_nn))
    target.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=_nr, max_nn=args.normal_max_nn))

    # Tutorial-strict refinement on full-resolution: single pass,
    # threshold = voxel_size * 0.4, point-to-plane (with point-to-point fallback).
    # Multi-scale was tested and over-fits below the data noise floor.
    refine_threshold = args.voxel_size * args.refine_threshold_factor
    logger.info("Refining on full-res ({}, threshold={:.5f})", args.icp_estimation_method, refine_threshold)
    refined = _icp(source, target, refine_threshold, result.transformation, primary_est,
                   f"{args.icp_estimation_method} (full-res)")
    if refined is None or refined.fitness == 0.0:
        logger.warning("Full-res point-to-plane unusable — falling back to point-to-point")
        refined = _icp(source, target, refine_threshold, result.transformation,
                       o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                       "Point-to-point (full-res)")
    if refined is not None and refined.fitness > 0.0:
        result = refined
        result_stage, result_threshold = "full-resolution ICP", refine_threshold
    else:
        logger.warning("Full-res refinement unusable — keeping downsampled result")
        result_stage, result_threshold = "down-sampled ICP (full-resolution pass found nothing)", threshold

    logger.info("Correspondence set size: {}", len(result.correspondence_set))
    logger.info("Final transformation:\n{}", result.transformation)

    n = C.write_moving(args.moving, result.transformation, args.output)
    logger.info("Saved the moving cloud ({} points, attributes as read) transformed to: {}", n, args.output)

    json_path = Path(args.output).with_suffix('.json')
    quality = C.quality_block(
        source, target, result.transformation, C.QUALITY_THRESHOLD_FACTOR * args.voxel_size,
        min_fitness=args.min_fitness,
        stop_condition=f"{result_stage}; max_iterations {args.max_iterations} (Open3D does not report whether "
                       "ICP converged or hit the limit)",
        iterations=None, final_metric=float(result.inlier_rmse),
        metric_name="ICP inlier RMSE at the final threshold")
    json_path.write_text(json.dumps({
        "quality": quality,
        "transformation_matrix": result.transformation.tolist(),
        "fitness": float(result.fitness),
        "inlier_rmse": float(result.inlier_rmse),
        "correspondence_count": len(result.correspondence_set),
        "method": "point-to-plane (with point-to-point fallback)",
        "convention": "p_fixed = T @ [p_moving, 1]",
        "threshold": result_threshold,
        "result_stage": result_stage,
        "init": init_stage,
        "ransac_prepass_fitness": float(ransac_result.fitness),
        "seed": args.seed,
        "voxel_size": args.voxel_size,
        "voxel_size_auto": voxel_auto,
        "open3d_version": o3d.__version__,
    }, indent=2))
    logger.info("Transformation matrix saved: {}", json_path)
    C.exit_if_below_floor(quality, json_path)


if __name__ == "__main__":
    main()
