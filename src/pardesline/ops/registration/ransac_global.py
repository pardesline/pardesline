"""
RANSAC Global Registration — adapted from PardesLine functions_for_registration.

Registers a moving point cloud onto a fixed point cloud using RANSAC global
feature matching (FPFH), without an initial guess. The result is coarse: refine it
with icp_refinement or use ransac_icp_pipeline.

RANSAC is random: it runs --restarts times with the seeds seed, seed+1, ... and the
pose with the best threshold-free score wins (mean of the 0.1 ... 0.9 quantiles of the
distances of every transformed moving point to the nearest fixed point).

CONTRACT:
  python ransac_global.py --input <fixed.ply> --output <registered.ply>       --moving <moving.ply> [--voxel_size F] [--seed N] [--restarts N]

The output is the moving cloud as read (colours, normals) transformed by T; the JSON
sidecar holds T (p_fixed = T @ [p_moving, 1]), the voxel size used, the seeds and
every candidate.
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


def preprocess_point_cloud(pcd, voxel_size, normal_radius_factor=2.0, normal_max_nn=30,
                           fpfh_radius_factor=5.0, fpfh_max_nn=100):
    return C.preprocess(pcd, voxel_size, normal_radius_factor, normal_max_nn, fpfh_radius_factor, fpfh_max_nn)


def main():
    parser = argparse.ArgumentParser(description="RANSAC Global Registration")
    parser.add_argument("--input", required=True, help="Fixed (target) point cloud file")
    parser.add_argument("--output", required=True, help="Output point cloud file")
    parser.add_argument("--moving", required=True, help="Moving (source) point cloud to register to fixed")
    parser.add_argument("--voxel_size", type=float, default=0.0,
                        help="Voxel size in file units, used as given. 0 = auto (1.3 percent of the fixed bbox diagonal).")
    parser.add_argument("--seed", type=int, default=0, help="First RANSAC seed (restart k uses seed + k)")
    parser.add_argument("--restarts", type=int, default=8, help="Number of RANSAC runs; the best-scoring pose wins")
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
    parser.add_argument("--min_fitness", type=float, default=C.DEFAULT_MIN_FITNESS,
                        help="Fail (exit 4) when fewer than this fraction of moving points lie within 1.5 x voxel of the fixed cloud after registration")
    args = parser.parse_args()
    if args.restarts < 1:
        parser.error("--restarts must be at least 1")

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
    _pp = dict(normal_radius_factor=args.normal_radius_factor, normal_max_nn=args.normal_max_nn,
               fpfh_radius_factor=args.fpfh_radius_factor, fpfh_max_nn=args.fpfh_max_nn)
    source_down, source_fpfh = preprocess_point_cloud(source, v, **_pp)
    target_down, target_fpfh = preprocess_point_cloud(target, v, **_pp)

    distance = v * args.distance_threshold_factor
    candidates = []
    for s in range(args.seed, args.seed + args.restarts):
        r = C.ransac(source_down, target_down, source_fpfh, target_fpfh, seed=s, distance=distance,
                     mutual_filter=args.mutual_filter, with_scaling=args.ransac_with_scaling,
                     ransac_n=args.ransac_n, edge_length=args.edge_length_threshold,
                     max_iteration=args.ransac_max_iteration, confidence=args.ransac_confidence)
        t = np.asarray(r.transformation)
        sc = C.score_pose(source, target, t)
        candidates.append({"seed": s, "fitness": float(r.fitness), "inlier_rmse": float(r.inlier_rmse),
                           "correspondence_count": len(r.correspondence_set), **sc,
                           "transformation_matrix": t.tolist()})
        logger.info("seed {}: fitness {:.4f}, RMSE {:.6g}, score {:.4g}", s, r.fitness, r.inlier_rmse, sc["score"])
    best = min(candidates, key=lambda c: c["score"])
    centre = np.asarray(source.get_center())
    for c in candidates:
        c["rotation_from_winner_deg"], c["centre_shift_from_winner"] = C.pose_distance(
            c["transformation_matrix"], best["transformation_matrix"], centre)
    T = np.asarray(best["transformation_matrix"])
    logger.info("Winner: seed {} (score {:.4g}, fitness {:.4f})", best["seed"], best["score"], best["fitness"])

    n = C.write_moving(args.moving, T, args.output)
    logger.info("Saved the moving cloud ({} points, attributes as read) transformed to: {}", n, args.output)

    json_path = Path(args.output).with_suffix('.json')
    quality = C.quality_block(
        source, target, T, C.QUALITY_THRESHOLD_FACTOR * v, min_fitness=args.min_fitness,
        stop_condition=f"best of {args.restarts} RANSAC runs ({args.ransac_max_iteration} iterations, "
                       f"confidence {args.ransac_confidence}, each)",
        iterations=None, final_metric=best["score"],
        metric_name="threshold-free score: mean of the 0.1..0.9 distance quantiles (lower is better)")
    matrix_dict = {
        "quality": quality,
        "transformation_matrix": T.tolist(),
        "convention": "p_fixed = T @ [p_moving, 1]",
        "fitness": best["fitness"],
        "inlier_rmse": best["inlier_rmse"],
        "threshold": distance,
        "correspondence_count": best["correspondence_count"],
        "score": best["score"],
        "seed": best["seed"],
        "first_seed": args.seed,
        "restarts": args.restarts,
        "voxel_size": v,
        "voxel_size_auto": auto,
        "candidates": candidates,
        "open3d_version": o3d.__version__,
    }
    json_path.write_text(json.dumps(matrix_dict, indent=2))
    logger.info("Transformation matrix saved: {}", json_path)
    C.exit_if_below_floor(quality, json_path)


if __name__ == "__main__":
    main()
