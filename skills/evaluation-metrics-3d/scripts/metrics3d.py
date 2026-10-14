"""3D evaluation metrics on NumPy arrays (label maps with spacing, point sets).

    from metrics3d import dice, iou, hd95, assd, surface_dice, volume_error, chamfer, f_score, pose_error
    python metrics3d.py            # self-test on synthetic data
    python metrics3d.py --dataset liver_tumor_patient01   # inter-observer Dice / HD95 of three radiologists

Label-map metrics take (z, y, x) integer arrays and a spacing (sx, sy, sz) in
mm (SimpleITK order); surface distances are computed between the boundary
voxels' physical centres. Point-set metrics take (N, 3) arrays in any unit.
"""

from __future__ import annotations

import argparse
import json
import math

import numpy as np


# ---- label maps -----------------------------------------------------------------
def _binary(mask, label=None):
    m = np.asarray(mask)
    return (m == label) if label is not None else (m > 0)


def dice(pred, ref, label=None) -> float:
    a, b = _binary(pred, label), _binary(ref, label)
    s = a.sum() + b.sum()
    return 1.0 if s == 0 else float(2 * np.logical_and(a, b).sum() / s)


def iou(pred, ref, label=None) -> float:
    a, b = _binary(pred, label), _binary(ref, label)
    u = np.logical_or(a, b).sum()
    return 1.0 if u == 0 else float(np.logical_and(a, b).sum() / u)


def _surface_points(mask: np.ndarray, spacing) -> np.ndarray:
    """Physical coordinates (mm) of boundary voxels of a (z, y, x) mask; spacing is (sx, sy, sz)."""
    from scipy import ndimage

    m = mask.astype(bool)
    if not m.any():
        return np.zeros((0, 3))
    eroded = ndimage.binary_erosion(m, structure=np.ones((3, 3, 3)), border_value=0)
    boundary = m & ~eroded
    zyx = np.argwhere(boundary).astype(float)
    sx, sy, sz = spacing
    return zyx[:, ::-1] * np.array([sx, sy, sz])  # -> (x, y, z) mm


def _directed(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    from scipy.spatial import cKDTree

    if len(a) == 0 or len(b) == 0:
        return np.array([np.inf])
    return cKDTree(b).query(a)[0]


def surface_distances(pred, ref, spacing, label=None):
    a = _surface_points(_binary(pred, label), spacing)
    b = _surface_points(_binary(ref, label), spacing)
    return _directed(a, b), _directed(b, a)


def hausdorff(pred, ref, spacing, label=None, percentile: float = 100.0) -> float:
    d_ab, d_ba = surface_distances(pred, ref, spacing, label)
    return float(max(np.percentile(d_ab, percentile), np.percentile(d_ba, percentile)))


def hd95(pred, ref, spacing, label=None) -> float:
    return hausdorff(pred, ref, spacing, label, percentile=95.0)


def assd(pred, ref, spacing, label=None) -> float:
    d_ab, d_ba = surface_distances(pred, ref, spacing, label)
    return float((d_ab.sum() + d_ba.sum()) / (len(d_ab) + len(d_ba)))


def surface_dice(pred, ref, spacing, tolerance_mm: float, label=None) -> float:
    """Normalised surface Dice: fraction of surface points within the tolerance of the other surface."""
    d_ab, d_ba = surface_distances(pred, ref, spacing, label)
    return float(((d_ab <= tolerance_mm).sum() + (d_ba <= tolerance_mm).sum()) / (len(d_ab) + len(d_ba)))


def volume_error(pred, ref, spacing, label=None) -> dict:
    vox = float(np.prod(spacing))
    vp = _binary(pred, label).sum() * vox
    vr = _binary(ref, label).sum() * vox
    return {"pred_mm3": vp, "ref_mm3": vr, "relative": (vp - vr) / vr if vr else math.nan}


# ---- point sets ---------------------------------------------------------------------
def chamfer(a: np.ndarray, b: np.ndarray, squared: bool = False) -> float:
    d_ab, d_ba = _directed(a, b), _directed(b, a)
    if squared:
        d_ab, d_ba = d_ab**2, d_ba**2
    return float(d_ab.mean() + d_ba.mean())


def f_score(pred: np.ndarray, ref: np.ndarray, threshold: float) -> dict:
    d_pr, d_rp = _directed(pred, ref), _directed(ref, pred)
    precision = float((d_pr <= threshold).mean())
    recall = float((d_rp <= threshold).mean())
    f = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f_score": f, "threshold": threshold}


def hausdorff_points(a: np.ndarray, b: np.ndarray, percentile: float = 95.0) -> float:
    return float(max(np.percentile(_directed(a, b), percentile), np.percentile(_directed(b, a), percentile)))


# ---- registration ---------------------------------------------------------------------
def pose_error(t_est: np.ndarray, t_true: np.ndarray, centre) -> dict:
    r = t_est[:3, :3] @ t_true[:3, :3].T
    rot = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2))))
    c = np.append(np.asarray(centre, dtype=float), 1.0)
    trans = float(np.linalg.norm((t_est @ c)[:3] - (t_true @ c)[:3]))
    return {"rotation_deg": rot, "translation_at_centre": trans}


def tre(landmarks_fixed: np.ndarray, landmarks_moving: np.ndarray, t_est: np.ndarray) -> dict:
    moved = (t_est[:3, :3] @ landmarks_moving.T).T + t_est[:3, 3]
    d = np.linalg.norm(moved - landmarks_fixed, axis=1)
    return {"mean": float(d.mean()), "max": float(d.max()), "per_landmark": d.tolist()}


def jacobian_folding(displacement: np.ndarray, spacing) -> dict:
    """displacement: (z, y, x, 3) field in mm (dx, dy, dz). Fraction of voxels with det(J) <= 0."""
    sx, sy, sz = spacing
    u = displacement
    dz = np.gradient(u, sz, axis=0)
    dy = np.gradient(u, sy, axis=1)
    dx = np.gradient(u, sx, axis=2)
    j = np.zeros(u.shape[:3] + (3, 3))
    j[..., 0, :] = dx
    j[..., 1, :] = dy
    j[..., 2, :] = dz
    j += np.eye(3)
    det = np.linalg.det(j)
    return {
        "folding_fraction": float((det <= 0).mean()),
        "log_det_std": float(np.log(np.clip(det, 1e-6, None)).std()),
    }


# ---- detection / anomaly / rendering ---------------------------------------------------
def box_iou(a, b) -> float:
    """Axis-aligned boxes as (min_xyz..., max_xyz...) in 2D or 3D."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = len(a) // 2
    lo, hi = np.maximum(a[:d], b[:d]), np.minimum(a[d:], b[d:])
    inter = float(np.prod(np.clip(hi - lo, 0, None)))
    va, vb = float(np.prod(a[d:] - a[:d])), float(np.prod(b[d:] - b[:d]))
    return inter / (va + vb - inter) if va + vb - inter > 0 else 0.0


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC without sklearn (ties averaged)."""
    from scipy.stats import rankdata

    s, y = np.asarray(scores, float), np.asarray(labels).astype(bool)
    n_pos, n_neg = y.sum(), (~y).sum()
    if n_pos == 0 or n_neg == 0:
        return math.nan
    r = rankdata(s)
    return float((r[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def psnr(img: np.ndarray, ref: np.ndarray, max_value: float = 1.0) -> float:
    mse = float(np.mean((np.asarray(img, float) - np.asarray(ref, float)) ** 2))
    return math.inf if mse == 0 else 10 * math.log10(max_value**2 / mse)


# ---- self test ----------------------------------------------------------------------
def _selftest() -> dict:
    rng = np.random.default_rng(0)
    z, y, x = np.mgrid[0:40, 0:48, 0:48]
    sphere = ((x - 24) ** 2 + (y - 24) ** 2 + ((z - 20) * 2) ** 2) < 14**2
    shifted = np.roll(sphere, 2, axis=2)  # 2 voxels = 1.4 mm shift in x
    spacing = (0.7, 0.7, 1.4)
    out = {
        "dice": dice(shifted, sphere),
        "iou": iou(shifted, sphere),
        "hd95_mm": hd95(shifted, sphere, spacing),
        "assd_mm": assd(shifted, sphere, spacing),
        "surface_dice_1mm": surface_dice(shifted, sphere, spacing, 1.0),
        "surface_dice_2mm": surface_dice(shifted, sphere, spacing, 2.0),
        "volume_error": volume_error(shifted, sphere, spacing)["relative"],
    }
    pts = rng.random((2000, 3))
    noisy = pts + rng.normal(scale=0.005, size=pts.shape)
    out["chamfer"] = chamfer(pts, noisy)
    out["f_score_0.01"] = f_score(noisy, pts, 0.01)["f_score"]
    t = np.eye(4)
    t[:3, 3] = [1, 0, 0]
    out["pose_error"] = pose_error(t, np.eye(4), [0, 0, 0])
    out["auroc"] = auroc(
        np.r_[rng.normal(1, 1, 100), rng.normal(0, 1, 100)], np.r_[np.ones(100), np.zeros(100)]
    )
    return out


def _dataset_demo(name: str) -> dict:
    import SimpleITK as sitk

    import pardesline as pl

    ds = pl.load(name)
    s = ds[0]
    labels = [r for r in s.roles if ds.roles[r].type == "labels"]
    arrays, spacing = {}, None
    for r in labels:
        img = s.get(r).to_sitk()
        arrays[r] = sitk.GetArrayFromImage(img)
        spacing = img.GetSpacing()
    out = {}
    for i, a in enumerate(labels):
        for b in labels[i + 1 :]:
            out[f"{a} vs {b}"] = {
                "dice": dice(arrays[a], arrays[b]),
                "hd95_mm": hd95(arrays[a], arrays[b], spacing),
                "surface_dice_2mm": surface_dice(arrays[a], arrays[b], spacing, 2.0),
            }
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", help="a bundled dataset with several label roles (liver_tumor_patient01)")
    args = ap.parse_args()
    print(json.dumps(_dataset_demo(args.dataset) if args.dataset else _selftest(), indent=2))
