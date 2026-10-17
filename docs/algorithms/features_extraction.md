---
title: "Features Extraction (features_extraction): 3 methods in Python"
description: "Extract geometric features from point clouds: normals, curvature, and FPFH descriptors for registration and analysis"
---

# Features Extraction

`features_extraction`: Extract geometric features from point clouds: normals, curvature, and FPFH descriptors for registration and analysis.

| | |
|---|---|
| Methods | [`normal_estimation`](#normal_estimation), [`fpfh_features`](#fpfh_features), [`curvature_estimation`](#curvature_estimation) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| CLI | `pardesline run features_extraction.<method> input.ext [--param value]` |

## How it works

Geometric feature extraction computes descriptors that characterize the local or global shape of a point cloud.

Normal estimation fits a local tangent plane to neighbors. Curvature is estimated from eigenvalues of the local covariance matrix. FPFH descriptors encode angular relationships between normals.

## Methods

### normal_estimation

The normal $\vec{n}_i$ is the eigenvector corresponding to the smallest eigenvalue of $\mathbf{C}_i$. Normals are oriented consistently using tangent plane propagation.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("features_extraction.normal_estimation")  # catalog defaults
# same thing, domain vocabulary: `points.normals()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.features_extraction.normal_estimation --input ... --output ...`.

**Defaults validated on:** Stanford bunny through the registration pipeline; generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `radius` | float | `0.05` | 0.005 to 0.5 | Search radius for normal estimation. | 0.05 in file units: about 5x the spacing of a centimetre-resolution scan; the covariance needs 10-30 points inside the radius. |
| `max_nn` | int | `30` | 10 to 100 | Maximum nearest neighbors. | 30 neighbours cap the cost and keep normals local at edges. |
| `fast_normal_computation` *(advanced)* | bool | `true` |  | Use the faster (less accurate) covariance eigen solver in estimate_normals. | On: Open3D's closed-form eigen solver is accurate to visual precision and several times faster than the iterative one. |
| `orient_k` *(advanced)* | int | `0` | 0 to 100 | k neighbors for consistent tangent-plane orientation (0 = auto min(max_nn,15)). | 0 lets the script choose min(max_nn, 15) for the orientation propagation: small enough to stay consistent across thin parts. |

### fpfh_features

Fast Point Feature Histograms encode angular relationships between normals into a 33-dimensional descriptor using three angular features $(\alpha, \phi, \theta)$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("features_extraction.fpfh_features")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.features_extraction.fpfh_features --input ... --output ...`.

**Defaults validated on:** Stanford bunny and Open3D fragments through registration.ransac_global; generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.005` | 0.001 to 0.05 | Voxel size for downsampling before feature computation. | 0.005 in file units (5 mm on a metre object) keeps enough points for descriptive histograms; the registration pipeline derives it from the bounding box instead. |
| `normal_radius_factor` *(advanced)* | float | `2.0` | 1.0 to 10.0 | Normal search radius as a multiple of voxel_size. | 2x the voxel for normals. |
| `normal_max_nn` *(advanced)* | int | `30` | 10 to 200 | Maximum nearest neighbors for normal estimation. | 30 neighbours cap the normal-estimation cost on dense clouds while keeping the covariance stable. |
| `feature_radius_factor` *(advanced)* | float | `5.0` | 1.0 to 20.0 | FPFH search radius as a multiple of voxel_size. | 5x the voxel: the Open3D-recommended FPFH support. |
| `feature_max_nn` *(advanced)* | int | `100` | 10 to 500 | Maximum nearest neighbors for FPFH feature computation. | 100 neighbours bound the histogram cost. |

### curvature_estimation

Curvature $\kappa_i = \frac{\lambda_0}{\lambda_0 + \lambda_1 + \lambda_2}$. Near 0 = flat, near $1/3$ = high curvature.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("features_extraction.curvature_estimation")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.features_extraction.curvature_estimation --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `radius` | float | `0.05` | 0.005 to 0.5 | Search radius for curvature computation. | 0.05 in file units for the covariance neighbourhood, as for normals. |
| `max_nn` | int | `30` | 10 to 100 | Maximum nearest neighbors. | 30 neighbours cap the cost and keep the estimate local at edges. |
| `normalize_percentile` *(advanced)* | float | `99` | 50 to 100 | Percentile of curvature used as the color-normalization ceiling. | Colour scale capped at the 99th percentile so a few extreme points (edges, noise) do not flatten the map. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("features_extraction")` prints this module from the installed package; `pl.describe("features_extraction.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/features_extraction.json` and `_defaults.json` on 2026-10-17.</sub>
