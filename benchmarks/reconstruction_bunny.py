"""Benchmark: package defaults vs upstream defaults for Poisson surface reconstruction.

    python benchmarks/reconstruction_bunny.py --trials 3        # prints a Markdown table, writes results/reconstruction_bunny.json

Input: the Stanford bunny sampled to 20 000 points, jittered with 0.5 % noise,
with a 15 % hole cut out (a partial scan). Ground truth: the original mesh.
Contenders:

* ``open3d_default``: ``create_from_point_cloud_poisson(depth=8)`` as the Open3D
  tutorial calls it (normals estimated with the tutorial radius), no trimming;
* ``pardesline``: ``points.to_mesh()`` = ``point_cloud_reconstruction.poisson``
  at the catalog defaults (depth 9, density quantile 0.01).

Metric: symmetric Chamfer distance (mean nearest-neighbour distance both ways,
in metres) between 50 000 points sampled on the reconstruction and on the
ground-truth surface, plus the fraction of reconstructed surface farther than
2 mm from the truth (the "balloon" over the hole), plus time.
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


def sample(mesh: o3d.geometry.TriangleMesh, n: int, seed: int) -> np.ndarray:
    o3d.utility.random.seed(seed)  # Open3D 0.19 has no seed= argument
    return np.asarray(mesh.sample_points_uniformly(n).points)


def chamfer(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    ta, tb = (
        o3d.geometry.KDTreeFlann(o3d.geometry.PointCloud(o3d.utility.Vector3dVector(a))),
        o3d.geometry.KDTreeFlann(o3d.geometry.PointCloud(o3d.utility.Vector3dVector(b))),
    )
    d_ab = np.array([np.sqrt(tb.search_knn_vector_3d(p, 1)[2][0]) for p in a])
    d_ba = np.array([np.sqrt(ta.search_knn_vector_3d(p, 1)[2][0]) for p in b])
    return float((d_ab.mean() + d_ba.mean()) / 2), float((d_ab > 0.002).mean())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--noise", type=float, default=0.005)
    ap.add_argument("--hole", type=float, default=0.15)
    args = ap.parse_args()

    truth_obj = pl.load("open3d_bunny")[0].mesh
    truth = truth_obj.to_open3d()
    truth_pts = sample(truth, 50000, 0)
    rows: dict[str, list[dict]] = {"open3d_default": [], "pardesline": []}
    OUT.mkdir(exist_ok=True)
    for trial in range(args.trials):
        rng = np.random.default_rng(200 + trial)
        pts = truth_obj.to_points(num_points=20000, seed=10 + trial).to_numpy()
        diag = np.linalg.norm(pts.max(0) - pts.min(0))
        pts = pts + rng.normal(scale=args.noise * diag, size=pts.shape)
        centre = pts[rng.integers(len(pts))]
        keep = np.linalg.norm(pts - centre, axis=1) > args.hole * diag  # a hole around a random point
        pts = pts[keep]

        pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
        t0 = time.perf_counter()
        pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
        pcd.orient_normals_consistent_tangent_plane(15)
        mesh_o3d, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8)
        dt = time.perf_counter() - t0
        cd, far = chamfer(sample(mesh_o3d, 50000, 1), truth_pts)
        rows["open3d_default"].append(
            {"chamfer_m": cd, "far_fraction": far, "seconds": dt, "triangles": len(mesh_o3d.triangles)}
        )

        path = OUT / f"partial_{trial}.ply"
        write_ply(path, pts)
        t0 = time.perf_counter()
        surf = pl.load(path).to_mesh()
        dt = time.perf_counter() - t0
        mesh_pl = surf.to_open3d()
        cd, far = chamfer(sample(mesh_pl, 50000, 1), truth_pts)
        rows["pardesline"].append(
            {"chamfer_m": cd, "far_fraction": far, "seconds": dt, "triangles": len(mesh_pl.triangles)}
        )
        path.unlink(missing_ok=True)

    summary = {
        name: {
            "chamfer_median_m": float(np.median([r["chamfer_m"] for r in rs])),
            "far_fraction_median": float(np.median([r["far_fraction"] for r in rs])),
            "seconds_median": float(np.median([r["seconds"] for r in rs])),
            "trials": rs,
        }
        for name, rs in rows.items()
    }
    (OUT / "reconstruction_bunny.json").write_text(
        json.dumps({"config": vars(args), "summary": summary}, indent=1), encoding="utf-8"
    )
    print(
        "| Contender | Chamfer, median (mm) | Surface farther than 2 mm from truth, median | Time, median (s) |"
    )
    print("|---|---|---|---|")
    for name, s in summary.items():
        print(
            f"| `{name}` | {s['chamfer_median_m'] * 1000:.2f} | {s['far_fraction_median'] * 100:.1f} % | {s['seconds_median']:.1f} |"
        )


if __name__ == "__main__":
    main()
