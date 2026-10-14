"""Atlas label transfer, end to end and locally: register a labelled atlas onto an
unlabelled scan, transfer labels by nearest structure, reconstruct per-label
surfaces, measure volumes and evaluate against the known truth.

Default demo: the Stanford bunny is the "atlas", labelled into four regions
(head, ears, body, base) by position; the "scan" is a noisy, rotated,
sub-sampled copy with a known transform, so the evaluation is exact.

    python atlas_label_transfer.py                              # bunny demo
    python atlas_label_transfer.py --atlas atlas.ply --atlas-labels labels.npy --scan scan.ply
    python atlas_label_transfer.py --tolerance 2.0 --voxel 0.005 --out ./transfer

Needs ``pip install "pardesline[local]"`` (Open3D, PyVista).
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path

import numpy as np

import pardesline as pl
from pardesline.object.arrays import write_ply


def transfer_labels(
    scan_xyz: np.ndarray, atlas_xyz: np.ndarray, atlas_labels: np.ndarray, tolerance: float | None
):
    """Each scan point takes the label of the closest atlas *structure* (one KD-tree per label)."""
    from scipy.spatial import cKDTree

    labels = np.unique(atlas_labels)
    dists = np.full((len(labels), len(scan_xyz)), np.inf)
    for i, k in enumerate(labels):
        pts = atlas_xyz[atlas_labels == k]
        if len(pts):
            dists[i] = cKDTree(pts).query(scan_xyz)[0]
    best = dists.argmin(axis=0)
    out = labels[best].astype(int)
    dmin = dists[best, np.arange(len(scan_xyz))]
    if tolerance is not None:
        out[dmin > tolerance] = -1  # unlabelled: too far from every structure
    return out, dmin


def random_rigid(degrees: float, rng: np.random.Generator, translation: float) -> np.ndarray:
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    a = math.radians(degrees)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    t = np.eye(4)
    t[:3, :3] = np.eye(3) + math.sin(a) * k + (1 - math.cos(a)) * k @ k
    t[:3, 3] = rng.normal(size=3) * translation
    return t


def bunny_atlas(num_points: int, rng: np.random.Generator):
    """A labelled atlas from the bunny: regions by height and position (demo only)."""
    pts = pl.load("open3d_bunny")[0].mesh.to_points(num_points=num_points, seed=0).to_numpy()
    y = pts[:, 1]
    x = pts[:, 0]
    labels = np.full(len(pts), 3)  # body
    labels[y > np.quantile(y, 0.80)] = 1  # ears (top)
    labels[(y > np.quantile(y, 0.55)) & (y <= np.quantile(y, 0.80)) & (x < np.quantile(x, 0.45))] = 2  # head
    labels[y < np.quantile(y, 0.12)] = 4  # base
    return pts, labels, {1: "ears", 2: "head", 3: "body", 4: "base"}


def closed_volume(mesh_obj) -> tuple[bool, float | None]:
    surface = mesh_obj.to_pyvista()
    closed = int(surface.n_open_edges) == 0
    return closed, float(surface.volume) if closed else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", help="labelled atlas point cloud (.ply)")
    ap.add_argument("--atlas-labels", help=".npy with one integer label per atlas point")
    ap.add_argument("--scan", help="unlabelled scan point cloud")
    ap.add_argument("--out", default=None)
    ap.add_argument("--voxel", type=float, default=0.0, help="registration voxel size (0 = auto)")
    ap.add_argument(
        "--tolerance", type=float, default=None, help="max distance to a structure, else unlabelled"
    )
    ap.add_argument("--degrees", type=float, default=35.0, help="demo: synthetic rotation of the scan")
    ap.add_argument("--noise", type=float, default=0.003, help="demo: noise fraction of the bbox diagonal")
    ap.add_argument("--poisson-depth", type=int, default=7)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    out = Path(args.out or tempfile.mkdtemp(prefix="pl-atlas-"))
    out.mkdir(parents=True, exist_ok=True)

    if args.atlas and args.atlas_labels and args.scan:
        atlas_xyz = pl.load(args.atlas).to_numpy()
        atlas_labels = np.load(args.atlas_labels).astype(int)
        names = {int(k): str(k) for k in np.unique(atlas_labels)}
        scan_xyz = pl.load(args.scan).to_numpy()
        t_true = None
    else:
        atlas_xyz, atlas_labels, names = bunny_atlas(20000, rng)
        diag = float(np.linalg.norm(atlas_xyz.max(0) - atlas_xyz.min(0)))
        t_true = random_rigid(args.degrees, rng, 0.3 * diag)
        keep = rng.random(len(atlas_xyz)) < 0.6  # the scan is coarser than the atlas
        scan_xyz = (t_true[:3, :3] @ atlas_xyz[keep].T).T + t_true[:3, 3]
        scan_xyz += rng.normal(size=scan_xyz.shape) * args.noise * diag
        truth_labels = atlas_labels[keep]

    atlas = pl.load(write_ply(out / "atlas.ply", atlas_xyz))
    scan = pl.load(write_ply(out / "scan.ply", scan_xyz))

    # 1. registration: the scan is fixed, the atlas moves; output keeps the atlas point order
    aligned = scan.run("registration.ransac_icp_pipeline", moving=atlas, voxel_size=args.voxel)
    aligned_xyz = aligned.to_numpy()
    assert len(aligned_xyz) == len(atlas_xyz), "the registration output must keep the atlas point order"
    info = aligned.transform or {}

    # 2. label transfer
    scan_labels, dmin = transfer_labels(scan_xyz, aligned_xyz, atlas_labels, args.tolerance)
    counts = {names.get(int(k), str(k)): int((scan_labels == k).sum()) for k in np.unique(atlas_labels)}
    unlabelled = float((scan_labels < 0).mean())

    # 3. per-label surfaces and volumes
    volumes = {}
    for k, name in names.items():
        pts = scan_xyz[scan_labels == k]
        if len(pts) < 200:
            continue
        part = pl.load(write_ply(out / f"scan_{name}.ply", pts))
        diag = float(np.linalg.norm(scan_xyz.max(0) - scan_xyz.min(0)))
        try:
            mesh = part.to_mesh(depth=args.poisson_depth, density_quantile=0.0, normal_radius=0.03 * diag)
            closed, vol = closed_volume(mesh)
            mesh.save(out / f"surface_{name}.ply")
            volumes[name] = {"closed": closed, "volume": vol, "points": len(pts)}
        except Exception as exc:  # a structure too thin for Poisson is reported, not hidden
            volumes[name] = {"error": str(exc)[:120], "points": len(pts)}

    report = {
        "registration": {k: info.get(k) for k in ("fitness", "inlier_rmse", "ransac_fitness")},
        "label_counts": counts,
        "unlabelled_fraction": unlabelled,
        "volumes": volumes,
        "out": str(out),
    }
    if t_true is not None:
        t_est = np.array(info.get("transformation_matrix") or np.eye(4), dtype=float)
        r = t_est[:3, :3] @ t_true[:3, :3].T
        report["pose_error_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2))))
        c = np.append(atlas_xyz.mean(0), 1.0)
        report["pose_error_at_centre"] = float(np.linalg.norm((t_est @ c)[:3] - (t_true @ c)[:3]))
        valid = scan_labels >= 0
        report["label_agreement"] = float((scan_labels[valid] == truth_labels[valid]).mean())
        per = {}
        for k, name in names.items():
            a, b = scan_labels == k, truth_labels == k
            per[name] = float(2 * (a & b).sum() / max(1, a.sum() + b.sum()))
        report["per_structure_dice"] = per
    print(json.dumps(report, indent=2, default=float))
    (out / "report.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
