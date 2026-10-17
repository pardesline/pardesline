---
title: "Point cloud registration with RANSAC, FPFH and ICP"
description: "Expert guide to rigid and non-rigid point-cloud registration as used in robotics, SLAM, LiDAR mapping and medical 3D (atlas-to-scan, scan-to-scan): the RAN"
---

# Point cloud registration with RANSAC, FPFH and ICP

**Reference scripts:** [`registration_eval.py`](https://github.com/pardesline/pardesline/blob/main/skills/point-cloud-registration/scripts/registration_eval.py).

# Point-cloud registration: RANSAC + FPFH + ICP, done properly

## The pipeline and why two stages

A single ICP converges only from a nearby pose (typically < 30 deg, < one
object radius). The global stage finds that pose from *features*; the local
stage polishes it.

```
downsample (voxel v)  ->  normals (r_n = 2v)  ->  FPFH (r_f = 5v)
      ->  RANSAC on feature correspondences (d_max = 1.5v)   [global, coarse]
      ->  ICP point-to-plane on the full-resolution clouds (d_max = 0.4v)   [local, fine]
      ->  metrics: fitness, inlier RMSE, transform T (4x4)
```

Everything scales with **one number, the voxel size `v`**, which should be
2-5 times the point spacing and about 1 % of the object's bounding-box
diagonal (pardesline's `voxel_size=0` picks 1.3 % of the diagonal, the Open3D
tutorial setting). If the units are wrong (mm vs m) every radius is wrong:
check `cloud.frame.describe()` first.

### FPFH in two sentences
For each point, the Simplified Point Feature Histogram encodes the angles
(alpha, phi, theta of the Darboux frame) between its normal and the normals of
neighbours within `r_f`; FPFH re-weights each point's SPFH with its
neighbours' SPFHs (`1/d` weights), giving a 33-bin histogram that is
rotation-invariant and cheap (O(N k)). It needs normals that are *consistently
oriented*; estimate them on the downsampled cloud with `r_n = 2v`, `max_nn=30`.

### RANSAC on correspondences
Sample `n = 3` correspondences by feature matching (mutual filter on: both
directions must agree), estimate a rigid transform (Umeyama / SVD), prune with
the edge-length checker (`edge_length_threshold = 0.9`: the three pairwise
distances must agree within 10 %) and the distance checker (`d_max = 1.5v`),
count inliers. Stop after `max_iteration` (100 000) or when the confidence
(0.999) is reached. Output: `T_ransac`, fitness (inlier fraction of the
source), inlier RMSE.

### ICP refinement
Point-to-plane minimises `sum ((R p_i + t - q_i) · n_qi)^2` - it converges in
far fewer iterations than point-to-point and slides along surfaces instead of
fighting them; it needs target normals. Point-to-point is the fallback when
normals are unreliable (sparse, noisy LiDAR). Correspondence distance
`0.4v` on the full-resolution clouds; stop on `relative_fitness` and
`relative_rmse` below 1e-6 or at `max_iteration`. Generalised ICP
(plane-to-plane, covariance-weighted) and robust kernels (Tukey, Cauchy on the
residual) help with outliers; multi-scale ICP (v, v/2, v/4) helps with large
residual error after RANSAC.

## Parameters, by name, in pardesline

```python
import pardesline as pl

fixed = pl.load("scan.ply").with_frame("sensor", "mm")
moving = pl.load("atlas.ply").with_frame("sensor", "mm")

aligned = fixed.align(moving)  # registration.ransac_icp_pipeline, voxel_size auto
aligned = fixed.run(
    "registration.ransac_icp_pipeline",
    moving=moving,
    voxel_size=2.0,  # mm; 2-5x the point spacing
    normal_radius_factor=2.0,
    fpfh_radius_factor=5.0,
    distance_threshold_factor=1.5,
    mutual_filter=True,
    ransac_n=3,
    edge_length_threshold=0.9,
    ransac_max_iteration=100000,
    ransac_confidence=0.999,
    icp_threshold_factor=0.4,
    icp_estimation_method="point_to_plane",
    icp_max_iteration=30,
    icp_relative_fitness=1e-6,
    icp_relative_rmse=1e-6,
)
aligned.transform  # {'fitness', 'inlier_rmse', 'transformation_matrix', ...} from <output>.json
```

Two-stage control: `registration.ransac_global` alone (coarse pose, to inspect
before refining) and `registration.icp_refinement` (which runs its own RANSAC
pre-pass unless the clouds already overlap: `ransac_seed_fitness` is the
fitness below which it falls back to a centre-of-mass initialisation). Set
`ransac_with_scaling=True` only when the two clouds come from different
devices with unknown scale (photogrammetry vs scanner); never for LiDAR.

Parameter effects, from experience:

| Symptom | Likely cause | Change |
|---|---|---|
| RANSAC fitness < 0.3, ICP does nothing | features meaningless: `v` too small (noise) or too large (no detail) | scan `v` over 0.5x-4x; check units |
| Converges to a mirrored / rotated pose | symmetric object (sphere, cylinder, vertebra body) | add landmarks or a prior pose; use `ransac_n=4`; verify with TRE, not fitness |
| Fitness high, RMSE high | correspondence distance too generous | lower `icp_threshold_factor` to 0.2-0.3 |
| Fitness drops when overlap is partial | fitness counts source points; partial overlap caps it | judge by inlier RMSE and pose error on the overlapping region; crop first |
| Drift on flat scenes (floors, walls) | point-to-plane slides along planes | point-to-point, or add walls/edges, or constrain DoF |
| Different scale | mm vs m, or photogrammetry | `ransac_with_scaling=True`, then fix the scale and re-run rigid |

## Metrics: which ones mean something

- **Fitness** = inliers / source points at distance `d_max`. Depends on
  `d_max`; compare runs only at the same threshold. Caps at the overlap ratio.
- **Inlier RMSE** = RMS distance of inliers. Lower bound is the noise level of
  the scanner (0.5 mm for the ultrasound use case): below that you are
  measuring noise, not alignment.
- **Pose error against a known transform** (synthetic tests, phantoms): rotation
  error `arccos((tr(R_est R_true^T) - 1) / 2)` in degrees, translation error at
  the object centre `||T_est c - T_true c||` (not the raw translation vector,
  which mixes with rotation about the origin).
- **Target registration error (TRE)**: distance between corresponding landmarks
  *not* used by the algorithm. The only metric a clinician accepts.
- **Chamfer / Hausdorff** between the aligned surfaces: see the
  `evaluation-metrics-3d` skill. Hausdorff is dominated by one outlier;
  report the 95th percentile.

[`scripts/registration_eval.py`](https://github.com/pardesline/pardesline/blob/main/skills/point-cloud-registration/scripts/registration_eval.py) runs the full pipeline on a bundled cloud with a
known synthetic transform and prints all of these.

## Non-rigid: Coherent Point Drift

CPD treats the moving cloud as Gaussian mixture centroids and the fixed cloud
as samples; EM alternates responsibilities and a displacement field that is
regularised to be smooth (`beta` = kernel width, `lambda_val` = regularisation
weight, `w` = outlier fraction). `deformable_registration.cpd_deformable`
exposes them; `low_rank=True` with `num_eig` makes it tractable above ~10 k
points. Use it after a rigid alignment, for organ motion, breathing, or
atlas-to-patient shape adaptation; never as a first stage. Validate with
Jacobian-determinant positivity of the displacement (no folding) and TRE.

## Medical specifics

- Atlas to patient (see `atlas-label-transfer`): the **scan is the fixed
  reference**, the atlas moves. Labels travel with point order, so keep the
  atlas point order (pardesline's output keeps it).
- Ultrasound reconstructions are noisy and partial: `v` 2-3 mm, point-to-plane,
  expect fitness 0.6-0.9, RMSE near the noise floor.
- CBCT / intra-oral scans: 0.1-0.2 mm spacing, `v` 0.5 mm; symmetric teeth
  need the arch as context, never a single tooth.
- Multimodal volumes (CT vs MR) are **not** a point-cloud problem: use
  intensity-based registration (`multimodal-rigid-registration` skill).

## Datasets to practise on

`open3d_icp_demo` (indoor fragments, sensor frame, m), `open3d_bunny`
(synthetic transforms), `kitti_raw_2011_09_26_drive_0001` (consecutive sweeps,
sensor frame, m; odometry-style), `medshapenet` (two instances of the same
organ for shape registration), `c3vd_endoscopy_splats` (`points` role).

```python
ds = pl.load("open3d_icp_demo")
pair = ds["pair_0_1"]
moved = pair.target.align(pair.source, voxel_size=0.05)  # metres
print(moved.transform["fitness"], moved.transform["inlier_rmse"])
```

<sub>Source: `skills/point-cloud-registration/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-14.</sub>
