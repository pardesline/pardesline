---
title: "Point Cloud Registration (registration): 3 methods in Python"
description: "Align point clouds into a common coordinate frame using RANSAC-based global registration and ICP local refinement"
---

# Point Cloud Registration

`registration`: Align point clouds into a common coordinate frame using RANSAC-based global registration and ICP local refinement.

| | |
|---|---|
| Methods | [`ransac_global`](#ransac_global), [`icp_refinement`](#icp_refinement), [`ransac_icp_pipeline`](#ransac_icp_pipeline) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Two inputs | `input` is the fixed reference, `moving` (Moving Cloud) is transformed |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| Example | [RANSAC + ICP on the Stanford bunny](../examples.md#icp_registration_bunny) |
| CLI | `pardesline run registration.<method> input.ext [--param value]` |

## How it works

Point cloud registration finds the optimal rigid transformation $T = (\mathbf{R}, \mathbf{t})$ that aligns a source point cloud $P$ to a target $Q$:


$$
T^* = \arg\min_{\mathbf{R}, \mathbf{t}} \sum_{i=1}^{N} \|\mathbf{R} p_i + \mathbf{t} - q_{c(i)}\|^2
$$


Global registration methods like RANSAC + FPFH features provide initial alignment before ICP refinement.

## Methods

### ransac_global

RANSAC-based registration uses FPFH feature matching to establish correspondences, then estimates the best transformation from random subsets.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.ply"), pl.load("moving.ply")
result = fixed.run("registration.ransac_global", moving=moving)  # catalog defaults
# same thing, domain vocabulary: `points.ransac(moving=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.registration.ransac_global --input ... --output ...`.

**Defaults validated on:** Stanford bunny, 35 deg / 70 % overlap / 0.5 % noise (examples/icp_registration_bunny: 0.14 deg residual after ICP); ultrasound and CBCT reconstructions in the atlas-label-transfer skill (0.06 deg pose error on the bunny atlas); Open3D indoor fragments

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.5` | 0 to 0.9 | Voxel size for downsampling. 0 = auto-detect (1.3% of bbox diagonal, matches Open3D tutorial). | 0.5 is a placeholder for the platform UI; 0 (auto) is what the one-call API passes: 1.3 % of the bounding-box diagonal, so the feature scale follows the object instead of a fixed number that is wrong for both a 15 cm part and a 15 m facade. |
| `normal_radius_factor` *(advanced)* | float | `2.0` | 1.0 to 5.0 | Normal-estimation radius as a multiple of voxel_size. | 2x the voxel: normals need a neighbourhood a little larger than the downsampling cell to be stable but local. |
| `normal_max_nn` *(advanced)* | int | `30` | 10 to 100 | Max neighbors for normal estimation. | 30 neighbours cap the normal estimation cost on dense clouds. |
| `fpfh_radius_factor` *(advanced)* | float | `5.0` | 2.0 to 10.0 | FPFH feature radius as a multiple of voxel_size. | 5x the voxel is the Open3D-recommended FPFH support: large enough for a descriptive 33-bin histogram, small enough to stay local on partial scans. |
| `fpfh_max_nn` *(advanced)* | int | `100` | 30 to 300 | Max neighbors for the FPFH histogram. | 100 neighbours bound the histogram cost. |
| `distance_threshold_factor` *(advanced)* | float | `1.5` | 0.5 to 3.0 | RANSAC max correspondence distance as a multiple of voxel_size. | 1.5x the voxel: a correspondence within one and a half cells counts as an inlier; tighter rejects true matches on noisy scans, looser lets outliers vote. |
| `mutual_filter` *(advanced)* | bool | `true` |  | Use RANSAC mutual nearest-neighbor filtering. | On: both directions of the feature match must agree, which removes most false correspondences before RANSAC and is the single setting that most improves success on symmetric parts. |
| `ransac_with_scaling` *(advanced)* | bool | `false` |  | Estimate a scale factor in the RANSAC transform. | Off: rigid scans share a scale; turn on only for photogrammetry against a scanner. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 6 | Correspondences sampled per RANSAC iteration. | 3 correspondences is the minimum for a rigid transform; 4 helps on symmetric objects at the cost of more iterations. |
| `edge_length_threshold` *(advanced)* | float | `0.9` | 0.0 to 1.0 | Edge-length similarity threshold for RANSAC checker. | 0.9: the pairwise distances of the sampled correspondences must agree within 10 %, which prunes wrong triplets before the expensive inlier count. |
| `ransac_max_iteration` *(advanced)* | int | `100000` | 1000 to 4000000 | Max RANSAC iterations. | 100 000 iterations with the early-stop confidence below converge in seconds on 20k-point clouds. |
| `ransac_confidence` *(advanced)* | float | `0.999` | 0.9 to 0.9999 | RANSAC early-stop confidence. | 0.999 stops once the best model is that likely to be the true one. |

### icp_refinement

Iterative Closest Point alternates between finding correspondences via nearest-neighbor search and solving for $(\mathbf{R}, \mathbf{t})$ using SVD.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.ply"), pl.load("moving.ply")
result = fixed.run("registration.icp_refinement", moving=moving)  # catalog defaults
# same thing, domain vocabulary: `points.icp(moving=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.registration.icp_refinement --input ... --output ...`.

**Defaults validated on:** Stanford bunny (examples/icp_registration_bunny); Open3D indoor fragments; generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.5` | 0 to 0.9 | Voxel size for downsampling. 0 = auto-detect (1.3% of bbox diagonal, matches Open3D tutorial). | 0 (auto) picks 1.3 % of the bounding-box diagonal; the explicit 0.5 is the platform UI placeholder. |
| `max_iterations` | int | `2000` | 100 to 10000 | Maximum ICP iterations. | 2 000 is a ceiling, not a target: point-to-plane ICP stops on the relative thresholds long before. |
| `icp_estimation_method` *(advanced)* | enum | `point_to_plane` | `point_to_plane`, `point_to_point` | ICP estimation method (point-to-point remains the automatic fallback). | point_to_plane converges in far fewer iterations and slides along surfaces instead of fighting them; point-to-point is the automatic fallback when normals cannot be estimated (sparse LiDAR). |
| `relative_fitness` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | ICP stop threshold on fitness change. | 1e-6: stop when the inlier fraction no longer changes. |
| `relative_rmse` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | ICP stop threshold on RMSE change. | 1e-6: stop when the inlier RMSE no longer changes. |
| `icp_threshold_factor` *(advanced)* | float | `1.5` | 0.5 to 4.0 | Downsampled-ICP correspondence distance as a multiple of voxel_size. | 1.5x the voxel on the downsampled pass: generous so the first ICP pass can pull a coarse RANSAC pose in. |
| `refine_threshold_factor` *(advanced)* | float | `0.4` | 0.2 to 2.0 | Full-res refinement correspondence distance as a multiple of voxel_size. | 0.4x the voxel on the full-resolution pass: tight so the last iterations are not pulled by points without a true counterpart (the 30 % non-overlap of a partial scan). |
| `normal_radius_factor` *(advanced)* | float | `2.0` | 1.0 to 5.0 | Normal-estimation radius as a multiple of voxel_size. | 2x the voxel for normal estimation. |
| `normal_max_nn` *(advanced)* | int | `30` | 10 to 100 | Max neighbors for normal estimation. | 30 neighbours cap the normal-estimation cost on dense clouds while keeping the covariance stable. |
| `fpfh_radius_factor` *(advanced)* | float | `5.0` | 2.0 to 10.0 | Pre-pass FPFH radius as a multiple of voxel_size. | 5x the voxel for the RANSAC pre-pass features. |
| `fpfh_max_nn` *(advanced)* | int | `100` | 30 to 300 | Max neighbors for pre-pass FPFH. | 100 neighbours bound the FPFH histogram cost; the radius, not the count, sets the feature scale. |
| `ransac_distance_factor` *(advanced)* | float | `1.5` | 0.5 to 3.0 | Pre-pass RANSAC correspondence distance as a multiple of voxel_size. | 1.5x the voxel for the pre-pass inlier distance. |
| `mutual_filter` *(advanced)* | bool | `true` |  | Use RANSAC mutual filtering in the pre-pass. | On for the pre-pass. |
| `ransac_with_scaling` *(advanced)* | bool | `false` |  | Estimate scale in the pre-pass RANSAC. | Off: two rigid scans share a scale; estimating one only makes sense for photogrammetry against a scanner. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 6 | Correspondences per pre-pass RANSAC iteration. | 3 correspondences is the minimum that determines a rigid transform, which keeps the inlier probability per draw highest. |
| `edge_length_threshold` *(advanced)* | float | `0.9` | 0.0 to 1.0 | Edge-length similarity threshold (pre-pass). | 0.9 edge-length agreement. |
| `ransac_max_iteration` *(advanced)* | int | `100000` | 1000 to 4000000 | Max pre-pass RANSAC iterations. | 100 000 pre-pass iterations. |
| `ransac_confidence` *(advanced)* | float | `0.999` | 0.9 to 0.9999 | Pre-pass RANSAC confidence. | 0.999 early stop. |
| `ransac_seed_fitness` *(advanced)* | float | `0.3` | 0.0 to 1.0 | Min RANSAC fitness to seed ICP (else center-of-mass init). | 0.3: below this pre-pass fitness the features were not informative and ICP starts from the centre-of-mass alignment instead of a wrong pose. |

### ransac_icp_pipeline

Complete pipeline: apply a known transformation, then recover it using RANSAC global alignment followed by ICP local refinement.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.ply"), pl.load("moving.ply")
result = fixed.run("registration.ransac_icp_pipeline", moving=moving)  # catalog defaults
# same thing, domain vocabulary: `target.align(moving)` on a `PointCloud`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.registration.ransac_icp_pipeline --input ... --output ...`.

**Defaults validated on:** Stanford bunny, 35 deg / 70 % overlap / 0.5 % noise: 0.14 deg residual, inlier RMSE 0.9 mm against a 1.4 mm noise floor (examples/icp_registration_bunny); bunny atlas transfer 99.4 % label agreement (examples/atlas_label_transfer_bunny); Open3D indoor fragments

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.5` | 0 to 0.9 | Voxel size for downsampling. 0 = auto-detect (1.3% of bbox diagonal, matches Open3D tutorial). | 0 (auto) = 1.3 % of the bounding-box diagonal: every other distance is a multiple of it, so one number adapts the whole pipeline to a 15 cm part or a 15 m facade; the explicit 0.5 is the platform UI placeholder. |
| `rotation_degrees` | float | `45.0` | 5.0 to 90.0 | Synthetic rotation for DEMO MODE only (when no moving cloud is connected). Ignored in real registration. | 45 degrees is used only in demo mode (no moving cloud): a synthetic rotation large enough to defeat plain ICP so the global stage is visibly needed. |
| `normal_radius_factor` *(advanced)* | float | `2.0` | 1.0 to 5.0 | Normal-estimation radius as a multiple of voxel_size. | 2x the voxel for stable but local normals. |
| `normal_max_nn` *(advanced)* | int | `30` | 10 to 100 | Max neighbors for normal estimation. | 30 neighbours cap the normal-estimation cost on dense clouds while keeping the covariance stable. |
| `fpfh_radius_factor` *(advanced)* | float | `5.0` | 2.0 to 10.0 | FPFH feature radius as a multiple of voxel_size. | 5x the voxel: the Open3D-recommended FPFH support. |
| `fpfh_max_nn` *(advanced)* | int | `100` | 30 to 300 | Max neighbors for the FPFH histogram. | 100 neighbours bound the FPFH histogram cost; the radius, not the count, sets the feature scale. |
| `distance_threshold_factor` *(advanced)* | float | `1.5` | 0.5 to 3.0 | RANSAC max correspondence distance as a multiple of voxel_size. | 1.5x the voxel for RANSAC inliers: tolerant to scanner noise, still rejects outliers. |
| `mutual_filter` *(advanced)* | bool | `true` |  | Use RANSAC mutual nearest-neighbor filtering. | On: mutual nearest-neighbour matching is the setting that most reduces false correspondences on symmetric or repetitive parts. |
| `ransac_with_scaling` *(advanced)* | bool | `false` |  | Estimate a scale factor in the RANSAC transform. | Off: two rigid scans share a scale; estimating one only makes sense for photogrammetry against a scanner. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 6 | Correspondences sampled per RANSAC iteration. | 3 correspondences, the minimum for a rigid transform. |
| `edge_length_threshold` *(advanced)* | float | `0.9` | 0.0 to 1.0 | Edge-length similarity threshold for RANSAC checker. | 0.9: prune triplets whose pairwise distances disagree by more than 10 %. |
| `ransac_max_iteration` *(advanced)* | int | `100000` | 1000 to 4000000 | Max RANSAC iterations. | 100 000 with early stop. |
| `ransac_confidence` *(advanced)* | float | `0.999` | 0.9 to 0.9999 | RANSAC early-stop confidence. | 0.999 early-stop confidence. |
| `icp_threshold_factor` *(advanced)* | float | `0.4` | 0.2 to 2.0 | ICP correspondence distance as a multiple of voxel_size. | 0.4x the voxel for the final ICP: tight, so the refinement is driven by true overlap and not by the partial-view points that have no counterpart. |
| `icp_estimation_method` *(advanced)* | enum | `point_to_plane` | `point_to_plane`, `point_to_point` | ICP estimation method (point-to-point remains the automatic fallback). | point_to_plane: faster convergence and no sliding across flat regions compared with point-to-point; point-to-point is the automatic fallback without normals. |
| `icp_max_iteration` *(advanced)* | int | `30` | 1 to 2000 | Max ICP iterations. | 30 iterations after a good global pose is enough; the relative thresholds usually stop it earlier. |
| `icp_relative_fitness` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | ICP stop threshold on fitness change. | 1e-6 stop on fitness plateau. |
| `icp_relative_rmse` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | ICP stop threshold on RMSE change. | 1e-6 stop on RMSE plateau. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("registration")` prints this module from the installed package; `pl.describe("registration.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/registration.json` and `_defaults.json` on 2026-10-10.</sub>
