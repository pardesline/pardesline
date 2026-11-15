"""
RANSAC + ICP Full Pipeline — adapted from PardesLine functions_for_registration.

Registers a moving point cloud onto a fixed point cloud: FPFH + RANSAC global
matching, then ICP refinement, repeated for several RANSAC seeds; the winner is
the pose with the best threshold-free score.

For each of --restarts seeds (seed, seed+1, ...):
  1. RANSAC on FPFH matches of the down-sampled clouds (voxel v; normals 2v; FPFH 5v;
     distance 1.5v; ransac_n 3; edge-length checker 0.9; criteria 100000 / 0.999);
  2. ICP on the full-resolution clouds from that pose, first at
     --icp_coarse_threshold_factor x v (1.5v; 0 skips it) then at --icp_threshold_factor
     x v (0.4v), point-to-plane with a point-to-point fallback (same criteria) when a
     pass finds no correspondence; when every pass fails, the RANSAC pose is kept and
     the JSON says so;
  3. score: mean of the 0.1 ... --score_upper_quantile quantiles of the distances of
     every transformed moving point to the nearest fixed point (no threshold involved).
With --symmetry_probe true, the best pose is also turned by 90, 180 and 270 degrees
about each principal axis of the moving cloud, refined and scored. Candidates with the
same pose (2 deg, 2 voxels) form one cluster. If a DIFFERENT pose scores within
--ambiguity_margin of the winner, the status is "ambiguous": the output and the JSON are
written, and with --on_ambiguous error (default) the script exits with code 3.

Why restarts: a single RANSAC run can stop on a wrong pose with a high fitness (a
180-degree flip of a near-symmetric part); seeding makes runs reproducible, not right.

CONTRACT:
  python ransac_icp_pipeline.py --input <fixed.ply> --output <registered.ply> \
      --moving <moving.ply> [--voxel_size F] [--seed N] [--restarts N]

The output is the moving cloud as read (colours, normals) transformed by T; the JSON
sidecar holds T (p_fixed = T @ [p_moving, 1]), the status, every candidate and the
parameters actually used (voxel size, thresholds, seeds).
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


def main():
    parser = argparse.ArgumentParser(description="RANSAC + ICP Pipeline")
    parser.add_argument("--input", required=True, help="Fixed (target) point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--moving", required=True, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--voxel_size", type=float, default=0.0,
                        help="Voxel size in file units, used as given. 0 = auto (1.3 percent of the fixed bbox diagonal).")
    parser.add_argument("--rotation_degrees", type=float, default=45.0,
                        help="Ignored: it set the rotation of the removed self-registration demo")
    parser.add_argument("--seed", type=int, default=0, help="First RANSAC seed (restart k uses seed + k)")
    parser.add_argument("--restarts", type=int, default=8, help="Number of RANSAC seeds, each refined by ICP")
    parser.add_argument("--symmetry_probe", type=_b, default=True,
                        help="Also refine the winner turned 90/180/270 deg about each principal axis")
    parser.add_argument("--score_upper_quantile", type=float, default=0.9,
                        help="Highest distance quantile in the score; keep it below the overlap fraction")
    parser.add_argument("--ambiguity_margin", type=float, default=0.10,
                        help="A different pose scoring within this relative margin makes the result ambiguous")
    parser.add_argument("--on_ambiguous", choices=["error", "warn"], default="error",
                        help="error: exit code 3 when ambiguous (output still written); warn: exit 0")
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
    parser.add_argument("--icp_coarse_threshold_factor", type=float, default=1.5,
                        help="First ICP pass at this x voxel (0 = single fine pass)")
    parser.add_argument("--icp_threshold_factor", type=float, default=0.4, help="Final ICP pass at this x voxel")
    parser.add_argument("--icp_estimation_method", choices=["point_to_plane", "point_to_point"],
                        default="point_to_plane")
    parser.add_argument("--icp_max_iteration", type=int, default=100)
    parser.add_argument("--icp_relative_fitness", type=float, default=1e-6)
    parser.add_argument("--icp_relative_rmse", type=float, default=1e-6)
    parser.add_argument("--min_fitness", type=float, default=C.DEFAULT_MIN_FITNESS,
                        help="Fail (exit 4) when fewer than this fraction of moving points lie within 1.5 x voxel of the fixed cloud after registration")
    args = parser.parse_args()
    if args.restarts < 1:
        parser.error("--restarts must be at least 1")
    if not 0.1 <= args.score_upper_quantile <= 1.0:
        parser.error("--score_upper_quantile must be in [0.1, 1]")
    if args.rotation_degrees != 45.0:
        logger.warning("--rotation_degrees is ignored: it only drove the removed demo mode")

    target = o3d.io.read_point_cloud(args.input)
    if target.is_empty():
        logger.error("Fixed point cloud is empty")
        sys.exit(1)
    source = o3d.io.read_point_cloud(args.moving)
    if source.is_empty():
        logger.error("Moving point cloud is empty")
        sys.exit(1)
    logger.info("Source has {} points, target has {} points", len(source.points), len(target.points))

    v, auto = C.choose_voxel(target, args.voxel_size)
    source_down, source_fpfh = C.preprocess(source, v, args.normal_radius_factor, args.normal_max_nn,
                                            args.fpfh_radius_factor, args.fpfh_max_nn)
    target_down, target_fpfh = C.preprocess(target, v, args.normal_radius_factor, args.normal_max_nn,
                                            args.fpfh_radius_factor, args.fpfh_max_nn)
    # Full-resolution normals for point-to-plane (files may carry stale or NaN normals).
    nrm = o3d.geometry.KDTreeSearchParamHybrid(radius=v * args.normal_radius_factor, max_nn=args.normal_max_nn)
    source.estimate_normals(nrm)
    target.estimate_normals(nrm)

    distance = v * args.distance_threshold_factor
    thresholds = ([v * args.icp_coarse_threshold_factor] if args.icp_coarse_threshold_factor > 0 else [])
    thresholds.append(v * args.icp_threshold_factor)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=args.icp_relative_fitness, relative_rmse=args.icp_relative_rmse,
        max_iteration=args.icp_max_iteration)
    centre = np.asarray(source.get_center())

    candidates = []
    for s in range(args.seed, args.seed + args.restarts):
        coarse = C.ransac(source_down, target_down, source_fpfh, target_fpfh, seed=s, distance=distance,
                          mutual_filter=args.mutual_filter, with_scaling=args.ransac_with_scaling,
                          ransac_n=args.ransac_n, edge_length=args.edge_length_threshold,
                          max_iteration=args.ransac_max_iteration, confidence=args.ransac_confidence)
        fine, stages = C.icp_passes(source, target, coarse.transformation, thresholds,
                                    args.icp_estimation_method, criteria)
        final = fine if fine is not None else coarse
        t = np.asarray(final.transformation)
        sc = C.score_pose(source, target, t, args.score_upper_quantile)
        candidates.append({
            "id": len(candidates), "origin": f"RANSAC seed {s}", "seed": s,
            "ransac": {"fitness": float(coarse.fitness), "inlier_rmse": float(coarse.inlier_rmse),
                       "threshold": distance},
            "result_stage": "ICP" if fine is not None else "RANSAC only (every ICP pass failed)",
            "fitness": float(final.fitness), "inlier_rmse": float(final.inlier_rmse),
            "threshold": stages[-1]["threshold"] if stages else distance, "icp_stages": stages,
            **sc, "transformation_matrix": t.tolist()})
        logger.info("seed {}: RANSAC fitness {:.3f}, final fitness {:.3f}, score {:.4g}",
                    s, coarse.fitness, final.fitness, sc["score"])

    if args.symmetry_probe:
        best0 = min(candidates, key=lambda c: c["score"])
        for origin, init in C.symmetry_probes(source, best0["transformation_matrix"], centre):
            fine, stages = C.icp_passes(source, target, init, thresholds, args.icp_estimation_method, criteria)
            if fine is None:
                continue
            t = np.asarray(fine.transformation)
            candidates.append({
                "id": len(candidates), "origin": origin, "seed": None, "ransac": None, "result_stage": "ICP",
                "fitness": float(fine.fitness), "inlier_rmse": float(fine.inlier_rmse),
                "threshold": stages[-1]["threshold"], "icp_stages": stages,
                **C.score_pose(source, target, t, args.score_upper_quantile), "transformation_matrix": t.tolist()})

    best, clusters, status = C.cluster(candidates, centre, v, args.ambiguity_margin)
    T = np.asarray(best["transformation_matrix"])
    logger.info("Winner: {} (score {:.4g}); status {}", best["origin"], best["score"], status)
    logger.info("Final transformation:\n{}", T)

    n = C.write_moving(args.moving, T, args.output)
    logger.info("Saved the moving cloud ({} points, attributes as read) transformed to: {}", n, args.output)

    json_path = Path(args.output).with_suffix('.json')
    quality = C.quality_block(
        source, target, T, C.QUALITY_THRESHOLD_FACTOR * v, min_fitness=args.min_fitness,
        stop_condition=f"{args.restarts} RANSAC restarts, ICP passes {[round(x, 6) for x in thresholds]} "
                       "(Open3D does not report whether ICP converged or hit max_iteration)",
        iterations=None, final_metric=best["score"],
        metric_name="threshold-free score: mean of the 0.1..q distance quantiles (lower is better)")
    if quality["status"] == "ok" and status == "ambiguous":
        quality["status"] = "ambiguous"
    matrix_dict = {
        "quality": quality,
        "transformation_matrix": T.tolist(),
        "convention": "p_fixed = T @ [p_moving, 1]",
        "status": status,
        "result_stage": best["result_stage"],
        "winner_origin": best["origin"],
        "seed": args.seed,
        "restarts": args.restarts,
        "voxel_size": v,
        "voxel_size_auto": auto,
        "fitness": best["fitness"],
        "inlier_rmse": best["inlier_rmse"],
        "threshold": best["threshold"],
        "score": best["score"],
        "ransac_fitness": (best["ransac"] or {}).get("fitness"),
        "ransac_inlier_rmse": (best["ransac"] or {}).get("inlier_rmse"),
        "clusters": clusters,
        "candidates": candidates,
        "open3d_version": o3d.__version__,
    }
    json_path.write_text(json.dumps(matrix_dict, indent=2))
    logger.info("Transformation matrix saved: {}", json_path)
    C.exit_if_below_floor(quality, json_path)
    if status == "ambiguous":
        msg = ("AMBIGUOUS: another pose scores within {:.0f} % of the winner (near-symmetric part?); "
               "see 'clusters' in {}").format(100 * args.ambiguity_margin, json_path)
        if args.on_ambiguous == "error":
            logger.error(msg)
            sys.exit(3)
        logger.warning(msg)


if __name__ == "__main__":
    main()
