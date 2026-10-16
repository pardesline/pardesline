"""RANSAC + ICP registration on the Stanford bunny: textbook ICP vs pardesline defaults.

    pip install "pardesline[local]"
    python examples/icp_registration_bunny/run.py        # writes two PNGs and a JSON next to this file

The bunny mesh (Open3D data) is sampled into a point cloud. A "moving" copy is
rotated by 35 degrees, translated, trimmed to 70 % overlap and jittered with
0.5 % noise, the way a second scan of a part looks. Both approaches get the
same two clouds:

* textbook: Open3D ``registration_icp`` from the identity with the tutorial's
  constant threshold, point-to-point, 30 iterations (Open3D's defaults);
* pardesline: ``target.align(moving)`` = ``registration.ransac_icp_pipeline``
  with the catalog defaults (voxel size from the bounding box, FPFH + RANSAC,
  then point-to-plane ICP at a distance tied to the voxel size).

The rotation error against the known transform is printed for both.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import open3d as o3d

import pardesline as pl
from pardesline.object.arrays import write_ply

HERE = Path(__file__).parent
RNG = np.random.default_rng(7)


def rigid(deg: float, axis=(0.3, 1.0, 0.2), t=(0.05, -0.02, 0.03)) -> np.ndarray:
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    T = np.eye(4)
    T[:3, :3] = o3d.geometry.get_rotation_matrix_from_axis_angle(axis * np.deg2rad(deg))
    T[:3, 3] = t
    return T


def rotation_error_deg(T_est: np.ndarray, T_true: np.ndarray) -> float:
    R = T_est[:3, :3] @ T_true[:3, :3].T
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))


def render(target: np.ndarray, moved: np.ndarray, title: str, out: Path) -> None:
    import pyvista as pv

    p = pv.Plotter(off_screen=True, window_size=(640, 520))
    p.add_points(pv.PolyData(target), color="#8fa3bf", point_size=3)
    p.add_points(pv.PolyData(moved), color="#f0a05a", point_size=3)
    p.add_text(title, font_size=11)
    p.camera_position = "xy"
    p.camera.azimuth = 30
    p.camera.elevation = 15
    p.screenshot(out)


def main() -> None:
    bunny = pl.load("open3d_bunny")[0].mesh
    target_obj = bunny.to_points(num_points=20000, seed=1)  # Poisson-disk sampling of the surface
    target = target_obj.to_numpy()

    # Make the "second scan": partial overlap, noise, unknown pose.
    T_true = rigid(35.0)
    keep = target[:, 0] > np.quantile(target[:, 0], 0.30)  # 70 % of the extent along x
    moving = target[keep]
    moving = (T_true[:3, :3] @ moving.T).T + T_true[:3, 3]
    diag = np.linalg.norm(target.max(0) - target.min(0))
    moving += RNG.normal(scale=0.005 * diag, size=moving.shape)
    moving_path = HERE / "bunny_moving.ply"
    write_ply(moving_path, moving)

    # --- textbook: Open3D ICP from the identity, tutorial threshold -----------
    src = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(moving))
    dst = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(target))
    textbook = o3d.pipelines.registration.registration_icp(
        src, dst, 0.02, np.eye(4), o3d.pipelines.registration.TransformationEstimationPointToPoint()
    )
    T_tb = textbook.transformation
    moved_tb = (T_tb[:3, :3] @ moving.T).T + T_tb[:3, 3]
    err_tb = rotation_error_deg(T_tb, np.linalg.inv(T_true))

    # --- pardesline: one call, catalog defaults -------------------------------
    aligned = target_obj.align(moving_path)
    T_pl = np.asarray(aligned.transform["transformation_matrix"])
    moved_pl = aligned.to_numpy()
    err_pl = rotation_error_deg(T_pl, np.linalg.inv(T_true))

    # nearest-neighbour RMSE of the moved clouds against the target, same metric for both
    tree = o3d.geometry.KDTreeFlann(dst)

    def rmse(pts: np.ndarray) -> float:
        d = [tree.search_knn_vector_3d(p, 1)[2][0] for p in pts[:: max(1, len(pts) // 4000)]]
        return float(np.sqrt(np.mean(d)))

    res = {
        "diag": diag,
        "textbook": {"rotation_error_deg": err_tb, "fitness": textbook.fitness, "rmse": rmse(moved_tb)},
        "pardesline": {"rotation_error_deg": err_pl, "rmse": rmse(moved_pl), "transform": aligned.transform},
    }
    print(json.dumps(res, indent=1, default=str))
    (HERE / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    render(
        target,
        moved_tb,
        f"Open3D ICP, textbook defaults: {err_tb:.1f} deg off",
        HERE / "textbook_defaults.png",
    )
    render(
        target,
        moved_pl,
        f"pardesline target.align(moving): {err_pl:.2f} deg off",
        HERE / "pardesline_defaults.png",
    )


if __name__ == "__main__":
    main()
