---
name: evaluation-metrics-3d
description: >-
  The metrics that decide whether a 3D or medical-imaging result is good, with their
  definitions, units, pitfalls and a NumPy / SimpleITK implementation: segmentation
  (Dice, IoU, Hausdorff and HD95, average surface distance, normalised surface
  Dice at a tolerance, volume error), surfaces and point clouds (chamfer distance,
  F-score at a threshold, point-to-mesh distance, Hausdorff), registration (rotation
  and translation error, target registration error on held-out landmarks, Jacobian
  determinant folding for deformable fields), detection (IoU, AP at IoU 0.5 and
  0.5:0.95), anomaly detection (image and pixel AUROC, AUPRC, threshold by FPR),
  reconstruction / rendering (PSNR, SSIM, LPIPS), and the statistics that make a
  number credible (per-case distributions, confidence intervals, paired tests, split by
  patient). Use when reporting results, choosing a metric for a task, writing an
  evaluation script, or reviewing a claim such as "100 % accuracy".
---

# Evaluation metrics for 3D vision and medical imaging

`scripts/metrics3d.py` implements every metric below on NumPy arrays (label
maps as (z, y, x) arrays with spacing, point sets as (N, 3)) and runs on a
bundled dataset as a self-test.

## Segmentation (label maps)

| Metric | Definition | Use / caveat |
|---|---|---|
| Dice | `2|A∩B| / (|A|+|B|)` | overlap of volumes; insensitive to boundary errors on large organs (liver Dice 0.95 can hide a 10 mm boundary error); report per class |
| IoU (Jaccard) | `|A∩B| / |A∪B|` | `IoU = Dice / (2 - Dice)`; stricter |
| Hausdorff | `max(sup_a d(a,B), sup_b d(b,A))` on the *surfaces*, mm | one stray voxel dominates it |
| HD95 | 95th percentile of the two directed surface distances | the robust version; always with the spacing applied |
| ASSD | mean of both directed surface distances | boundary accuracy in mm |
| Normalised surface Dice (NSD) | fraction of surface points within tolerance tau of the other surface | tau = 1-3 mm for organs, what challenges (TotalSegmentator, KiTS) use |
| Volume error | `(V_pred - V_true) / V_true` | clinically meaningful (ejection fraction, tumour volume); sign matters |

Rules: compute on the **original spacing**, never on resampled isotropic
labels only; report the **per-case distribution** (median, IQR, worst case),
not just the mean; an empty prediction on an empty reference is Dice 1 by
convention only if you say so.

## Surfaces and point clouds

- Chamfer distance `CD = mean_a min_b ||a-b|| + mean_b min_a ||a-b||` (some
  papers square the distances; say which). Units of the data.
- F-score at threshold `d`: precision = fraction of predicted points within
  `d` of the reference, recall = the converse, `F = 2PR/(P+R)`. Readable,
  bounded; pick `d` from the scanner noise (0.5-1 mm) or 1 % of the diagonal.
- Point-to-mesh distance when the reference is a mesh: use the true distance
  to triangles, not to vertices (vertex-only overestimates on coarse meshes).
- Hausdorff / HD95 as above; for partial overlap, restrict to the overlapping
  region or the number is meaningless.

## Registration

- Rigid: rotation error `arccos((tr(R_est R_trueᵀ) - 1) / 2)`, translation error
  at the object centre `||T_est c - T_true c||`.
- Target registration error (TRE): mean distance between landmark pairs not
  used by the algorithm; fiducial registration error (FRE) on the ones used is
  optimistic and should not be reported alone.
- Fitness / inlier RMSE (ICP): threshold-dependent, see
  `point-cloud-registration`.
- Deformable: Jacobian determinant of the displacement field, `det(J) <= 0`
  fraction = folding (must be ~0), its log standard deviation = smoothness;
  Dice of propagated labels; TRE.
- Multimodal intensity registration (CT/MR): mutual information value is not
  comparable across pairs; use TRE on anatomical landmarks or Dice of
  propagated masks.

## Detection

IoU between boxes (2D or 3D), AP = area under the precision-recall curve at
IoU 0.5 (`AP50`) and averaged over 0.5:0.05:0.95 (COCO `mAP`). For medical
lesions: sensitivity at a fixed false positives per scan (FROC, LUNA16 uses
0.125 to 8 FP/scan), because one missed nodule matters more than a loose box.

## Anomaly detection (reconstruction-based, VAE)

Image-level AUROC on the anomaly score (reconstruction error or its
percentile); pixel-level AUROC / AUPRC when masks exist (AUPRC is the honest
one when anomalies cover 1 % of pixels); choose the operating threshold on a
validation set by a target false-positive rate, never on the test set.

## Reconstruction and rendering

PSNR `10 log10(MAX^2 / MSE)` (dB), SSIM (structure, 0-1), LPIPS (learned
perceptual, lower better) on **held-out views**; training views say nothing.

## Making a number credible

1. Split by patient / scene (`ds.split(by="patient")`), never by slice or
   frame.
2. Report n, median and IQR (or mean and 95 % CI from bootstrap over cases).
3. Paired comparison between methods on the same cases (Wilcoxon signed-rank).
4. State the units, the spacing, the threshold `d` or tau, and whether the
   metric is on voxels or surfaces.
5. Show the worst case, not only the best.
6. "100 % label accuracy" on a scan generated from the atlas itself is a
   sanity check, not a result: say so.

```python
from metrics3d import dice, hd95, surface_dice, chamfer, f_score, pose_error
```
