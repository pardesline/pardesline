"""Build labelled point clouds for PointNet-style training from a pardesline dataset.

For each sample: every label role (or every value of a multi-label map) becomes a
surface (LabelMap.to_mesh), the surface is sampled with Poisson-disk sampling and
face normals, points get the structure's class id, the structures are merged,
normalised to the unit sphere, and written as one .npz:

    points   (N, 6) float32   xyz + normal, unit sphere
    labels   (N,)   int64     class id per point (0..K-1)
    centroid (3,)   float64   original centroid (file units, frame below)
    scale    float             max radius used for normalisation
    frame    str               e.g. "LPS, mm (file)"
    classes  json              {"0": "anterior", "1": "posterior"}

    python make_point_dataset.py msd_task04_hippocampus --out ./hippo_points --take 4 --points 2048
    python make_point_dataset.py totalsegmentator_ct --roles liver,spleen,kidney_left,kidney_right --take 2
    python make_point_dataset.py verse19_spine --mask mask --take 3 --points 8192

Needs ``pip install "pardesline[all]"`` (SimpleITK + PyVista + Open3D).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


def sample_structure(mask_obj, label: int, n: int):
    mesh = mask_obj.to_mesh(label=label)
    pts = mesh.to_points(num_points=n, use_triangle_normal=True)
    geo = pts.to_open3d()
    xyz = np.asarray(geo.points)
    nrm = np.asarray(geo.normals) if len(geo.normals) == len(geo.points) else np.zeros_like(xyz)
    return xyz, nrm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--roles", help="comma-separated binary mask roles, one class each (TotalSegmentator style)"
    )
    ap.add_argument("--mask", help="a multi-label role (default: the first labels role)")
    ap.add_argument("--points", type=int, default=2048, help="points per structure before merging")
    ap.add_argument("--take", type=int)
    ap.add_argument("--split", default="Tr")
    ap.add_argument("--assume", action="store_true")
    args = ap.parse_args()

    import pardesline as pl

    ds = pl.load(args.dataset, assume=args.assume)
    if args.split and any("split" in s.fields for s in ds._specs):
        ds = ds.filter(split=args.split)
    if args.take:
        ds = ds.take(args.take)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    roles = args.roles.split(",") if args.roles else None
    mask_role = args.mask or (
        None if roles else next(r for r, spec in ds.roles.items() if spec.type == "labels")
    )
    classes: dict[int, str] = {}
    if roles:
        classes = {i: r for i, r in enumerate(roles)}
    else:
        table = ds.roles[mask_role].labels or {}
        classes = {i: name for i, (_k, name) in enumerate(sorted(table.items()))}
    written = 0
    for s in ds:
        xyz_all, nrm_all, lab_all = [], [], []
        try:
            if roles:
                for cid, r in enumerate(roles):
                    if r not in s.roles:
                        continue
                    xyz, nrm = sample_structure(s.get(r), 1, args.points)
                    xyz_all.append(xyz)
                    nrm_all.append(nrm)
                    lab_all.append(np.full(len(xyz), cid))
            else:
                mask = s.get(mask_role)
                table = mask.labels or {}
                for cid, (k, _name) in enumerate(sorted(table.items())):
                    try:
                        xyz, nrm = sample_structure(mask, int(k), args.points)
                    except ValueError:
                        continue  # label absent in this case
                    xyz_all.append(xyz)
                    nrm_all.append(nrm)
                    lab_all.append(np.full(len(xyz), cid))
        except Exception as exc:
            print(f"  {s.id}: skipped ({str(exc)[:100]})")
            continue
        if not xyz_all:
            continue
        xyz = np.vstack(xyz_all)
        nrm = np.vstack(nrm_all)
        labels = np.concatenate(lab_all)
        centroid = xyz.mean(0)
        scale = float(np.abs(xyz - centroid).max())
        pts = np.hstack([(xyz - centroid) / scale, nrm]).astype(np.float32)
        case = re.sub(r"[^A-Za-z0-9]+", "_", s.id).strip("_")
        frame = s.get(roles[0] if roles else mask_role).frame.describe()
        np.savez(
            out / f"{case}.npz",
            points=pts,
            labels=labels.astype(np.int64),
            centroid=centroid,
            scale=scale,
            frame=frame,
            classes=json.dumps({str(k): v for k, v in classes.items()}),
        )
        written += 1
        counts = {classes[int(k)]: int((labels == k).sum()) for k in np.unique(labels)}
        print(f"  {case}: {len(pts)} points, {counts}, scale {scale:.1f} ({frame})")
    (out / "classes.json").write_text(
        json.dumps({str(k): v for k, v in classes.items()}, indent=2), encoding="utf-8"
    )
    print(f"\n{written} cloud(s) in {out}; classes {classes}; licence: {ds.license.describe()}")


if __name__ == "__main__":
    main()
