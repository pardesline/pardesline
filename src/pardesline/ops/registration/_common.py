"""Steps shared by the three registration scripts.

Conventions: the transform T maps the MOVING cloud onto the FIXED cloud,
p_fixed = T @ [p_moving, 1]; lengths are in the unit of the files (Open3D has none).

Fixes of the 2026-11 audit (Part 2): A2 (a voxel size given by the user is used as
given), A3 (RANSAC seeded; restarts scored without a distance threshold), A4 (ICP in
several passes, coarse to fine), A14 (the output is the moving cloud as read, with its
colours and normals, transformed), A19 (the point-to-point fallback uses the same
convergence criteria; a pass that finds nothing keeps the previous pose).
"""

from __future__ import annotations

import math

import numpy as np
import open3d as o3d
from loguru import logger

REG = o3d.pipelines.registration
KD = o3d.geometry.KDTreeSearchParamHybrid

SAME_POSE_DEG = 2.0  # candidates closer than this (and SAME_POSE_VOXELS) are one pose
SAME_POSE_VOXELS = 2.0


def bbox_diag(pcd) -> float:
    return float(np.linalg.norm(pcd.get_max_bound() - pcd.get_min_bound()))


def choose_voxel(target, user_value: float) -> tuple[float, bool]:
    """(voxel size, chosen automatically). 0 or less: 1.3 % of the fixed diagonal;
    a positive value is used as given, with a warning outside 0.5-5 % of the diagonal."""
    diag = bbox_diag(target)
    if user_value is None or user_value <= 0:
        v = diag * 0.013
        logger.info("voxel_size auto: {:.6g} (1.3 % of the fixed bounding-box diagonal {:.6g})", v, diag)
        return v, True
    if not 0.005 * diag <= user_value <= 0.05 * diag:
        logger.warning("voxel_size {} is outside 0.5-5 % of the fixed diagonal {:.6g}; used as given",
                       user_value, diag)
    return float(user_value), False


def estimation(name: str):
    if name == "point_to_point":
        return REG.TransformationEstimationPointToPoint()
    return REG.TransformationEstimationPointToPlane()


def preprocess(pcd, voxel_size, normal_radius_factor=2.0, normal_max_nn=30, fpfh_radius_factor=5.0,
               fpfh_max_nn=100):
    down = pcd.voxel_down_sample(voxel_size)
    down.estimate_normals(KD(radius=voxel_size * normal_radius_factor, max_nn=normal_max_nn))
    fpfh = REG.compute_fpfh_feature(down, KD(radius=voxel_size * fpfh_radius_factor, max_nn=fpfh_max_nn))
    return down, fpfh


def ransac(src_down, tgt_down, f_src, f_tgt, *, seed: int, distance: float, mutual_filter=True,
           with_scaling=False, ransac_n=3, edge_length=0.9, max_iteration=100000, confidence=0.999):
    """One seeded RANSAC run on FPFH matches (Open3D's generator is global: seed it first)."""
    o3d.utility.random.seed(int(seed))
    return REG.registration_ransac_based_on_feature_matching(
        src_down, tgt_down, f_src, f_tgt, mutual_filter=mutual_filter, max_correspondence_distance=distance,
        estimation_method=REG.TransformationEstimationPointToPoint(with_scaling), ransac_n=ransac_n,
        checkers=[REG.CorrespondenceCheckerBasedOnEdgeLength(edge_length),
                  REG.CorrespondenceCheckerBasedOnDistance(distance)],
        criteria=REG.RANSACConvergenceCriteria(max_iteration, confidence))


def icp_passes(source, target, init, thresholds, method, criteria):
    """ICP at each threshold in turn, each pass starting from the previous pose.

    A pass uses ``method`` and falls back to point-to-point (same criteria) when it
    raises or finds no correspondence. Returns (last good result or None, stages).
    """
    t, result, stages = np.asarray(init), None, []
    for thr in thresholds:
        r = None
        for name in dict.fromkeys([method, "point_to_point"]):
            try:
                r = REG.registration_icp(source, target, float(thr), t, estimation(name), criteria)
            except RuntimeError as e:
                logger.warning("ICP {} at threshold {:.6g} raised: {}", name, thr, e)
                r = None
            if r is not None and r.fitness > 0.0:
                stages.append({"threshold": float(thr), "estimation": name, "fitness": float(r.fitness),
                               "inlier_rmse": float(r.inlier_rmse)})
                logger.info("ICP {} at {:.6g}: fitness {:.6f}, RMSE {:.6g}", name, thr, r.fitness, r.inlier_rmse)
                break
            logger.warning("ICP {} at threshold {:.6g} found no correspondence", name, thr)
        if r is None or r.fitness == 0.0:
            break
        t, result = r.transformation, r
    return result, stages


def score_pose(moving, fixed, t, upper_q: float = 0.9) -> dict:
    """Threshold-free score of a pose: mean of the 0.1, 0.2, ... upper_q quantiles of the
    distances of every transformed moving point to the nearest fixed point. Lower is better."""
    d = np.asarray(o3d.geometry.PointCloud(moving).transform(np.asarray(t)).compute_point_cloud_distance(fixed))
    qs = np.arange(0.1, upper_q + 1e-9, 0.1)
    return {"score": float(np.mean(np.quantile(d, qs))), "median": float(np.median(d)),
            "p90": float(np.quantile(d, 0.9))}


def pose_distance(t1, t2, centre) -> tuple[float, float]:
    """(rotation difference in degrees, displacement of ``centre`` between the two poses)."""
    t1, t2 = np.asarray(t1), np.asarray(t2)
    c = (np.trace(t1[:3, :3] @ t2[:3, :3].T) - 1.0) / 2.0
    p = np.append(centre, 1.0)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))), float(np.linalg.norm((t1 @ p)[:3] - (t2 @ p)[:3]))


def cluster(candidates, centre, voxel, margin: float):
    """Group candidates by pose (best score first) and decide the status.

    Returns (winner, clusters, status). Status "ambiguous" when another, different pose
    scores within ``margin`` (relative) of the winner.
    """
    order = sorted(range(len(candidates)), key=lambda i: candidates[i]["score"])
    clusters: list[dict] = []
    for i in order:
        t = candidates[i]["transformation_matrix"]
        for cl in clusters:
            rot, tr = pose_distance(t, candidates[cl["best"]]["transformation_matrix"], centre)
            if rot < SAME_POSE_DEG and tr < SAME_POSE_VOXELS * voxel:
                cl["members"].append(candidates[i]["id"])
                break
        else:
            clusters.append({"best": i, "members": [candidates[i]["id"]], "score": candidates[i]["score"]})
    winner = candidates[clusters[0]["best"]]
    rivals = 0
    for cl in clusters[1:]:
        rel = (cl["score"] - clusters[0]["score"]) / max(clusters[0]["score"], 1e-12)
        rot, tr = pose_distance(candidates[cl["best"]]["transformation_matrix"],
                                winner["transformation_matrix"], centre)
        cl.update(relative_score_gap=rel, rotation_from_winner_deg=rot, centre_shift_from_winner=tr)
        rivals += rel <= margin
    out = [{"members": cl["members"], "origins": [candidates[m]["origin"] for m in cl["members"]],
            "score": cl["score"], **{k: cl[k] for k in ("relative_score_gap", "rotation_from_winner_deg",
                                                         "centre_shift_from_winner") if k in cl}}
           for cl in clusters]
    return winner, out, ("ambiguous" if rivals else "ok")


def symmetry_probes(moving, transform, centre):
    """The pose ``transform`` turned by 90, 180 and 270 degrees about each principal axis
    of the moving cloud, through its centroid: poses a symmetric part would also accept."""
    _, axes = np.linalg.eigh(np.cov(np.asarray(moving.points).T))
    to_c, from_c = np.eye(4), np.eye(4)
    to_c[:3, 3], from_c[:3, 3] = -centre, centre
    for k in range(3):
        for deg in (90, 180, 270):
            rot = np.eye(4)
            rot[:3, :3] = o3d.geometry.get_rotation_matrix_from_axis_angle(axes[:, k] * math.radians(deg))
            yield f"probe: winner turned {deg} deg about principal axis {k}", np.asarray(transform) @ from_c @ rot @ to_c


def write_moving(moving_path: str, transform, output: str) -> int:
    """Write the moving cloud AS READ (colours, normals) transformed by ``transform``."""
    out = o3d.io.read_point_cloud(moving_path)
    out.transform(np.asarray(transform))  # rotates the normals too
    o3d.io.write_point_cloud(output, out)
    return len(out.points)
