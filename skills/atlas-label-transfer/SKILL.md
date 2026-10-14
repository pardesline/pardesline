---
name: atlas-label-transfer
description: >-
  Expert recipe for labelling an unlabelled 3D reconstruction (ultrasound, CBCT,
  surface scan, LiDAR object) from a labelled atlas: rigid RANSAC + ICP registration
  of the atlas onto the scan (the scan stays fixed), nearest-structure label transfer
  with a KD-tree (per-structure distances, not a single nearest point), per-label
  Poisson surfaces with closed-surface volumes in mL, and the evaluation that makes
  the result credible (pose error, label agreement against the true transform,
  per-structure Dice on surfaces, volume versus atlas), plus when to add a
  non-rigid CPD step, how to build an atlas from TotalSegmentator or MSD label maps
  with pardesline, and the pitfalls (units, point order, nested chambers, outliers,
  partial scans). Use for atlas-based segmentation of point clouds, label
  propagation between scans, or turning a registered atlas into surfaces and
  volumes.
---

# Atlas label transfer: from a labelled atlas to a segmented scan

The pipeline of PardesLine use case 01 (3-D ultrasound heart, 60 lines), made
general and runnable locally with `scripts/atlas_label_transfer.py`.

```
atlas (points + per-point label)   scan (points, no labels, unknown pose)
          |                                   |
          +---- RANSAC + ICP (atlas -> scan) --+      registration.ransac_icp_pipeline
                         |
            aligned atlas, SAME point order  ->  labels still valid
                         |
          per-structure KD-tree distances; each scan point takes the closest structure
                         |
          per-label Poisson surface (density_quantile=0 -> closed) -> volume in mL
                         |
          evaluation: pose error, label agreement, per-structure Dice, volume vs atlas
```

## Step 1: registration (the scan is the fixed reference)

The atlas moves onto the scan so that the scan's coordinates (and its frame,
units, provenance) stay untouched. `fixed.align(moving)` keeps the moving
cloud's point order in the output, so the atlas labels index the aligned
points directly. Settings: `voxel_size` 2-5x the point spacing (auto when the
units are right), point-to-plane ICP, `ransac_with_scaling=False` unless the
atlas is in different units (then fix the units instead). See
`point-cloud-registration` for every parameter and failure mode. Expect
fitness 0.6-0.95 on partial, noisy ultrasound; inlier RMSE near the noise
floor (0.5-1 mm).

## Step 2: nearest-structure label transfer

For each structure `k`, compute the distance from every scan point to the
aligned atlas points of structure `k` (one KD-tree per structure); assign
`argmin_k`. This differs from "label of the single nearest atlas point":
per-structure minima are robust to a few mislabelled atlas points and to
density differences. Reject scan points whose minimum distance exceeds a
tolerance (2-3x the noise, or the atlas point spacing) as *unlabelled* rather
than forcing a label; report their fraction.

Refinements when needed: majority vote in a k-neighbourhood of the scan
(smooths salt-and-pepper labels at boundaries); a non-rigid CPD step
(`deformable_registration.cpd_deformable`) after the rigid alignment when the
patient's anatomy differs in shape, with the folding check from
`evaluation-metrics-3d`.

## Step 3: surfaces and volumes

Poisson reconstruction expects **one closed surface**: reconstruct each
structure separately (`PointCloud.to_mesh(depth=8, density_quantile=0.0,
normal_radius=...)`), never the nested chambers together (that produces a
tangle). `density_quantile=0` keeps every vertex so the mesh stays closed and
its volume is meaningful; `normal_radius` must be in the data's units (mm:
3-6; the catalog default 0.1 is for metre-scale scenes). Volume = PyVista
`mass_properties` on a mesh with `n_open_edges == 0`; mm^3 / 1000 = mL.

## Step 4: evaluation (what to report)

| Quantity | How | Meaning |
|---|---|---|
| Pose error | rotation (deg) and translation at the object centre against the true transform (synthetic or phantom) | the registration itself |
| Label agreement | fraction of scan points whose transferred label equals the label obtained with the true transform | the transfer, independent of the registration quality |
| Per-structure surface Dice / HD95 | between transferred and reference structures | where it fails (small chambers) |
| Volume | per structure, vs the atlas or a reference measurement | the clinically read number |
| Unlabelled fraction | points beyond the tolerance | honesty about partial scans |

"100 % label accuracy" on a scan generated from the atlas itself is a
pipeline sanity check; on a real patient, expect 85-95 % at chamber
boundaries and report where the 5-15 % sits.

## Building an atlas with pardesline

A labelled atlas is a point cloud with a label per point. From a label map:

```python
import pardesline as pl, numpy as np

s = pl.load("totalsegmentator_ct")[0]  # 117 organ masks
atlas_points, atlas_labels = [], []
for k, organ in enumerate(["heart", "aorta", "lung_upper_lobe_left", "lung_upper_lobe_right"], start=1):
    pts = s.get(organ).to_mesh(label=1).to_points(num_points=4000).to_numpy()  # LPS mm
    atlas_points.append(pts)
    atlas_labels.append(np.full(len(pts), k))
atlas = np.vstack(atlas_points)
labels = np.concatenate(atlas_labels)
```

Or from `msd_task02_heart` (left atrium), `amos22` (15 organs), MedShapeNet
STL meshes (`medshapenet`, one structure per file). Keep the atlas frame and
units with the arrays (write a `.pardesline.json` sidecar or a manifest role
with `labels`).

## Pitfalls

- Units: an atlas in mm and a scan in m never register (fitness ~0). Check
  `frame.describe()` on both.
- Point order: any operation that reorders the aligned atlas (voxel
  downsampling, outlier removal) breaks the label mapping; transfer labels from
  the aligned output of the registration, which keeps the order, or carry
  labels as a colour attribute.
- Partial scans: fitness caps at the overlap; the unlabelled fraction tells
  the truth.
- Symmetric structures (two ventricles, paired kidneys) can swap: verify with a
  landmark or the volume ordering.
- Noise: outlier removal on the scan *before* registration
  (`point_cloud_processing.statistical_outlier_removal`) improves both stages.

## Datasets to practise on

`open3d_bunny` (synthetic atlas, the script), `medshapenet` (pairs of the same
organ from different patients, `ds.filter(structure="liver")`),
`totalsegmentator_ct` / `amos22` (build atlases), `c3vd_endoscopy_splats`
(`points` role: scene-to-scene transfer).
