---
title: "Deformable Registration (deformable_registration): 2 methods in Python"
description: "Non-rigid point cloud alignment using Coherent Point Drift (CPD) and Gaussian deformation fields"
---

# Deformable Registration

`deformable_registration`: Non-rigid point cloud alignment using Coherent Point Drift (CPD) and Gaussian deformation fields. Handles elastic deformations between shapes.

| | |
|---|---|
| Methods | [`cpd_deformable`](#cpd_deformable), [`gaussian_deformation`](#gaussian_deformation) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| CLI | `pardesline run deformable_registration.<method> input.ext [--param value]` |

## How it works

Deformable registration finds a non-rigid transformation that aligns a source shape to a target. CPD models source points as GMM centroids and fits them via EM optimization.

The displacement function is:

$$
\mathbf{v}(\mathbf{x}) = \sum_{m=1}^{M} w_m \phi(\|\mathbf{x} - \mathbf{y}_m\|)
$$

where $\phi$ is a Gaussian kernel and $w_m$ are optimized coefficients.

## Methods

### cpd_deformable

CPD treats alignment as probability density estimation. The E-step computes correspondence probabilities, the M-step updates the transformation with regularization:
$$E(W) = \frac{1}{2\sigma^2} \sum_n \|T(y_n) - x_n\|^2 + \frac{\lambda}{2} \text{tr}(W^T G W)$$

```python
import pardesline as pl

fixed, moving = pl.load("fixed.ply"), pl.load("moving.ply")
result = fixed.run("deformable_registration.cpd_deformable", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.deformable_registration.cpd_deformable --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py; the point-cloud-registration skill documents its use after a rigid stage

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `max_iterations` | int | `100` | 10 to 500 | Maximum EM iterations. | 100 EM iterations: CPD converges in 30-80 on organ-sized clouds; the tolerance below usually stops it first. |
| `tolerance` | float | `0.001` | 0.0001 to 0.01 | Convergence tolerance. | 1e-3 relative change of the objective: tighter costs iterations without visible change in the displacement field. |
| `beta` *(advanced)* | float | `100.0` | 0.1 to 200.0 | CPD Gaussian-kernel width (smoothness). | 100 is pycpd's default Gaussian kernel width in file units, i.e. a very smooth, almost global deformation for unit-scale clouds; lower it to about the size of the structures you expect to move independently (10-20 mm for organs). |
| `lambda_val` *(advanced)* | float | `2.0` | 0.1 to 20.0 | CPD regularization weight. | 2.0 regularisation weight: the pycpd default, balancing fit against smoothness; raise it when the field folds. |
| `w` *(advanced)* | float | `0.0` | 0.0 to 0.99 | Outlier/noise weight. | 0 assumes no outliers; set 0.1-0.3 when the fixed cloud has clutter the moving cloud should not reach. |
| `low_rank` *(advanced)* | bool | `false` |  | Use low-rank Gaussian-kernel acceleration. | Off below about 10k points; on above, where the full kernel matrix no longer fits in memory. |
| `num_eig` *(advanced)* | int | `100` | 10 to 500 | Eigenvectors when low_rank=True. | 100 eigenvectors keep the low-rank approximation close to the full kernel at a fraction of the cost. |

### gaussian_deformation

A localized Gaussian deformation:
$$\mathbf{d}(\mathbf{p}) = d_{\max} \cdot \exp\left(-\frac{\|\mathbf{p} - \mathbf{c}\|^2}{2\sigma^2}\right) \cdot \hat{\mathbf{n}}$$

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("deformable_registration.gaussian_deformation")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.deformable_registration.gaussian_deformation --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `displacement` | float | `0.02` | 0.001 to 0.1 | Maximum displacement at pressure center. | 0.02 in file units: a visible but plausible dent on a unit-scale object, used to synthesise test cases for non-rigid registration. |
| `radius` | float | `0.1` | 0.01 to 0.5 | Radius of influence. | 0.1 in file units: the dent spans 10 % of a unit object. |
| `sigma_factor` *(advanced)* | float | `0.5` | 0.05 to 1.0 | Gaussian falloff sigma as a fraction of radius. | 0.5: the Gaussian falls to about 13 % at the radius, so the dent fades smoothly instead of leaving a crease. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("deformable_registration")` prints this module from the installed package; `pl.describe("deformable_registration.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/deformable_registration.json` and `_defaults.json` on 2026-10-10.</sub>
