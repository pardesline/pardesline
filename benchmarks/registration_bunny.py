"""Benchmark: package defaults vs upstream defaults for rigid point-cloud registration.

    python benchmarks/registration_bunny.py --trials 5          # prints a Markdown table, writes results/registration_bunny.json

Target: the Stanford bunny sampled to 20 000 points. Moving: a copy rotated by
35 degrees about a fixed axis, translated, trimmed to 70 % overlap along x and
jittered with Gaussian noise of 0.5 % of the bounding-box diagonal (a different
noise draw per trial). Three contenders get the same pair:

* ``open3d_icp_tutorial``: Open3D ``registration_icp`` from the identity, point-to-point,
  threshold 0.02 (the tutorial call, Open3D's own defaults for the rest);
* ``open3d_ransac_tutorial``: Open3D global registration as in the tutorial with its
  constant ``voxel_size = 0.05`` then ICP at ``0.4 * voxel``;
* ``pardesline``: ``target.align(moving)`` with the catalog defaults.

Reported per contender: median and worst rotation error (degrees) against the
known transform, median nearest-neighbour RMSE of the moved cloud against the
target, and wall time. Nothing is tuned to the bunny: the pardesline numbers are
the shipped defaults, the Open3D numbers are the tutorial constants.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import open3d as o3d

import pardesline as pl
from pardesline.object.arrays import write_ply

HERE = Path(__file__).parent
OUT = HERE / "results"


def rigid(deg: float, axis=(0.3, 1.0, 0.2), t=(0.05, -0.02, 0.03)) -> np.ndarray:
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    T = np.eye(4)
    T[:3, :3] = o3d.geometry.get_rotation_matrix_from_axis_angle(axis * np.deg2rad(deg))
    T[:3, 3] = t
    return T


def rot_err(T_est: np.ndarray, T_true_inv: np.ndarray) -> float:
    R = T_est[:3, :3] @ T_true_inv[:3, :3].T
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))


def nn_rmse(moved: np.ndarray, tree: o3d.geometry.KDTreeFlann) -> float:
    step = max(1, len(moved) // 4000)
    d = [tree.search_knn_vector_3d(p, 1)[2][0] for p in moved[::step]]
    return float(np.sqrt(np.mean(d)))


def make_pair(target: np.ndarray, rng: np.random.Generator, deg: float, overlap: float, noise: float):
    T_true = rigid(deg)
    keep = target[:, 0] > np.quantile(target[:, 0], 1 - overlap)
    moving = target[keep]
    moving = (T_true[:3, :3] @ moving.T).T + T_true[:3, 3]
    diag = np.linalg.norm(target.max(0) - target.min(0))
    moving = moving + rng.normal(scale=noise * diag, size=moving.shape)
    return moving, T_true


def open3d_icp_tutorial(src, dst):
    reg = o3d.pipelines.registration.registration_icp(
        src, dst, 0.02, np.eye(4), o3d.pipelines.registration.TransformationEstimationPointToPoint()
    )
    return reg.transformation


def open3d_ransac_tutorial(src, dst):
    voxel = 0.05  # the tutorial constant

    def prep(pcd):
        down = pcd.voxel_down_sample(voxel)
        down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 2, max_nn=30))
        fpfh = o3d.pipelines.registration.compute_fpfh_feature(
            down, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 5, max_nn=100)
        )
        return down, fpfh

    s, sf = prep(src)
    d, df = prep(dst)
    if len(s.points) < 4 or len(d.points) < 4:
        return np.eye(4)  # the tutorial voxel is larger than the object: nothing left to match
    ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        s,
        d,
        sf,
        df,
        True,
        voxel * 1.5,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        3,
        [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(voxel * 1.5),
        ],
        o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999),
    )
    dst.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 2, max_nn=30))
    icp = o3d.pipelines.registration.registration_icp(
        src,
        dst,
        voxel * 0.4,
        ransac.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
    )
    return icp.transformation


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--degrees", type=float, default=35.0)
    ap.add_argument("--overlap", type=float, default=0.7)
    ap.add_argument("--noise", type=float, default=0.005)
    args = ap.parse_args()

    bunny = pl.load("open3d_bunny")[0].mesh
    target_obj = bunny.to_points(num_points=20000, seed=1)
    target = target_obj.to_numpy()
    dst = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(target))
    tree = o3d.geometry.KDTreeFlann(dst)
    rows: dict[str, list[dict]] = {"open3d_icp_tutorial": [], "open3d_ransac_tutorial": [], "pardesline": []}
    for trial in range(args.trials):
        rng = np.random.default_rng(100 + trial)
        moving, T_true = make_pair(target, rng, args.degrees, args.overlap, args.noise)
        T_inv = np.linalg.inv(T_true)
        src = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(moving))
        for name, fn in (
            ("open3d_icp_tutorial", open3d_icp_tutorial),
            ("open3d_ransac_tutorial", open3d_ransac_tutorial),
        ):
            t0 = time.perf_counter()
            T = fn(src, dst)
            dt = time.perf_counter() - t0
            moved = (T[:3, :3] @ moving.T).T + T[:3, 3]
            rows[name].append(
                {"rot_err_deg": rot_err(T, T_inv), "nn_rmse": nn_rmse(moved, tree), "seconds": dt}
            )
        path = OUT / f"moving_{trial}.ply"
        OUT.mkdir(exist_ok=True)
        write_ply(path, moving)
        t0 = time.perf_counter()
        aligned = target_obj.align(path)
        dt = time.perf_counter() - t0
        T = np.asarray(aligned.transform["transformation_matrix"])
        rows["pardesline"].append(
            {"rot_err_deg": rot_err(T, T_inv), "nn_rmse": nn_rmse(aligned.to_numpy(), tree), "seconds": dt}
        )
        path.unlink(missing_ok=True)

    summary = {}
    for name, rs in rows.items():
        e = np.array([r["rot_err_deg"] for r in rs])
        summary[name] = {
            "rot_err_median_deg": float(np.median(e)),
            "rot_err_max_deg": float(e.max()),
            "nn_rmse_median": float(np.median([r["nn_rmse"] for r in rs])),
            "seconds_median": float(np.median([r["seconds"] for r in rs])),
            "trials": rs,
        }
    (OUT / "registration_bunny.json").write_text(
        json.dumps({"config": vars(args), "n_points": len(target), "summary": summary}, indent=1),
        encoding="utf-8",
    )
    print(
        "| Contender | Rotation error, median (deg) | Rotation error, worst (deg) | NN RMSE, median (m) | Time, median (s) |"
    )
    print("|---|---|---|---|---|")
    for name, s in summary.items():
        print(
            f"| `{name}` | {s['rot_err_median_deg']:.2f} | {s['rot_err_max_deg']:.2f} | {s['nn_rmse_median']:.4f} | {s['seconds_median']:.1f} |"
        )


if __name__ == "__main__":
    main()
