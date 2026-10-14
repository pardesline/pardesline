"""Evaluate RANSAC + ICP registration against a known transform.

Takes a point cloud (default: the Stanford bunny through pardesline), applies a
random rigid transform with noise and partial overlap to make a "moving" copy,
registers it back with ``registration.ransac_icp_pipeline`` and reports:
fitness, inlier RMSE, rotation error (deg), translation error at the centre,
chamfer distance and Hausdorff-95 between the aligned clouds.

    python registration_eval.py                       # bunny, 35 deg, 0.5 % noise
    python registration_eval.py --input scan.ply --degrees 60 --noise 0.002 --overlap 0.7
    python registration_eval.py --voxel 0.01          # force the feature scale (file units)

Needs ``pip install "pardesline[local]"`` (Open3D).
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path

import numpy as np

import pardesline as pl


def random_rigid(degrees: float, translation: float, rng: np.random.Generator) -> np.ndarray:
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    a = math.radians(degrees)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rot = np.eye(3) + math.sin(a) * k + (1 - math.cos(a)) * k @ k
    t = np.eye(4)
    t[:3, :3] = rot
    t[:3, 3] = rng.normal(size=3) * translation
    return t


def pose_error(t_est: np.ndarray, t_true: np.ndarray, centre: np.ndarray) -> tuple[float, float]:
    r = t_est[:3, :3] @ t_true[:3, :3].T
    rot_deg = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2))))
    c = np.append(centre, 1.0)
    trans = float(np.linalg.norm((t_est @ c)[:3] - (t_true @ c)[:3]))
    return rot_deg, trans


def chamfer_and_hausdorff(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    from scipy.spatial import cKDTree

    d_ab = cKDTree(b).query(a)[0]
    d_ba = cKDTree(a).query(b)[0]
    chamfer = float(d_ab.mean() + d_ba.mean())
    h95 = float(max(np.percentile(d_ab, 95), np.percentile(d_ba, 95)))
    return chamfer, h95


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", help="point cloud or mesh file (default: open3d_bunny sampled to points)")
    ap.add_argument("--degrees", type=float, default=35.0, help="synthetic rotation")
    ap.add_argument(
        "--noise", type=float, default=0.005, help="Gaussian noise as a fraction of the bbox diagonal"
    )
    ap.add_argument(
        "--overlap", type=float, default=1.0, help="fraction of the moving cloud kept (partial overlap)"
    )
    ap.add_argument(
        "--voxel", type=float, default=0.0, help="voxel size in file units (0 = auto 1.3%% of diagonal)"
    )
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    if args.input:
        fixed = pl.load(args.input)
        if fixed.kind == "mesh":
            fixed = fixed.to_points(num_points=20000)
    else:
        fixed = pl.load("open3d_bunny")[0].mesh.to_points(num_points=20000)
    xyz = fixed.to_numpy()
    diag = float(np.linalg.norm(xyz.max(0) - xyz.min(0)))
    centre = xyz.mean(0)

    t_true = random_rigid(args.degrees, 0.3 * diag, rng)
    moving_xyz = (t_true[:3, :3] @ xyz.T).T + t_true[:3, 3]
    moving_xyz += rng.normal(size=moving_xyz.shape) * args.noise * diag
    if args.overlap < 1.0:  # keep one side along a random direction
        d = rng.normal(size=3)
        proj = moving_xyz @ d
        keep = proj <= np.quantile(proj, args.overlap)
        moving_xyz = moving_xyz[keep]

    tmp = Path(tempfile.mkdtemp(prefix="pl-regeval-"))
    from pardesline.object.arrays import write_ply

    moving = pl.load(write_ply(tmp / "moving.ply", moving_xyz))
    fixed_file = pl.load(write_ply(tmp / "fixed.ply", xyz))

    # the moving cloud must come back onto the fixed one: T_est ~ inverse(T_true)
    aligned = fixed_file.run("registration.ransac_icp_pipeline", moving=moving, voxel_size=args.voxel)
    info = aligned.transform or {}
    t_est = np.array(info.get("transformation_matrix") or info.get("matrix_4x4") or np.eye(4), dtype=float)
    rot_err, trans_err = pose_error(t_est, np.linalg.inv(t_true), moving_xyz.mean(0))
    chamfer, h95 = chamfer_and_hausdorff(aligned.to_numpy(), xyz)

    report = {
        "points": len(xyz),
        "bbox_diagonal": diag,
        "synthetic_rotation_deg": args.degrees,
        "noise_fraction": args.noise,
        "overlap": args.overlap,
        "voxel_size_used": info.get("voxel_size", args.voxel),
        "ransac_fitness": info.get("ransac_fitness"),
        "fitness": info.get("fitness"),
        "inlier_rmse": info.get("inlier_rmse"),
        "rotation_error_deg": rot_err,
        "translation_error_at_centre": trans_err,
        "chamfer": chamfer,
        "hausdorff_95": h95,
        "noise_floor": args.noise * diag,
        "output": str(aligned.path),
    }
    print(json.dumps(report, indent=2, default=float))
    verdict = "OK" if rot_err < 1.0 and trans_err < 0.02 * diag else "CHECK"
    print(
        f"\n{verdict}: rotation error {rot_err:.2f} deg, centre error {trans_err:.4f} (diagonal {diag:.3f})"
    )


if __name__ == "__main__":
    main()
