---
title: "SimpleITK Registration (simpleitk_registration): 6 methods in Python"
description: "Medical image registration using SimpleITK"
---

# SimpleITK Registration

`simpleitk_registration`: Medical image registration using SimpleITK. Rigid, affine, B-spline FFD, and demons deformable registration for CT/MR and other medical volumes.

| | |
|---|---|
| Methods | [`rigid`](#rigid), [`advanced_rigid`](#advanced_rigid), [`affine`](#affine), [`bspline`](#bspline), [`demons`](#demons), [`difference_analysis`](#difference_analysis) |
| Input files | `.vti`, `.mha`, `.nrrd`, `.nii`, `.dcm` (and `.nii.gz`) |
| Two inputs | `input` is the fixed reference, `moving` (Moving Volume) is transformed |
| Bundled datasets to try | [`rire_brain`](../datasets/rire_brain.md), [`liver_tumor_patient01`](../datasets/liver_tumor_patient01.md), [`visible_human_head_mri`](../datasets/visible_human_head_mri.md), [`spider_lumbar_mri`](../datasets/spider_lumbar_mri.md), [`msd_task04_hippocampus`](../datasets/msd_task04_hippocampus.md), [`msd_task09_spleen`](../datasets/msd_task09_spleen.md) |
| Example | [SimpleITK rigid registration on RIRE](../examples.md#register_ct_mr_rire) |
| CLI | `pardesline run simpleitk_registration.<method> input.ext [--param value]` |

## How it works

Medical image registration seeks a spatial transformation $T: \mathbb{R}^3 \to \mathbb{R}^3$ that aligns a moving image $I_M$ to a fixed image $I_F$. The optimal transformation minimizes a similarity metric:


$$
T^* = \arg\min_{T} \mathcal{S}(I_F, I_M \circ T) + \lambda \mathcal{R}(T)
$$


where $\mathcal{S}$ is the similarity metric (e.g., Mutual Information for multi-modal, Mean Squared Error for mono-modal), $\mathcal{R}(T)$ is a regularization term enforcing transformation smoothness, and $\lambda$ controls the trade-off.

SimpleITK implements a multi-resolution optimization framework with configurable metrics, interpolators, and optimizers for both rigid and deformable registration.

## Methods

### rigid

**1. Rigid Transformation Model**
A rigid transformation has 6 degrees of freedom — 3 rotation angles $(\theta_x, \theta_y, \theta_z)$ and 3 translations $(t_x, t_y, t_z)$:
$$T_{\text{rigid}}(\mathbf{x}) = R \mathbf{x} + \mathbf{t}$$
where $R \in SO(3)$ is the rotation matrix and $\mathbf{t} \in \mathbb{R}^3$ is the translation vector.

**2. Mattes Mutual Information**
For multi-modal registration (CT-MR), Mutual Information measures the statistical dependency between the two images:
$$MI(I_F, I_M) = H(I_F) + H(I_M) - H(I_F, I_M)$$
where $H$ denotes Shannon entropy and $H(I_F, I_M)$ is the joint entropy. Mattes' implementation uses a stochastic sampling strategy with 50 histogram bins.

**3. Multi-Resolution Framework**
The optimization proceeds from coarse to fine resolution, avoiding local minima. At each level, the optimizer refines the parameters from the previous scale.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.rigid", moving=moving)  # catalog defaults
# same thing, domain vocabulary: `fixed.align(moving)` on a `Volume`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.rigid_registration --input ... --output ...`.

**Defaults validated on:** RIRE CT / MR-T1 brain pair: 0.65 x 0.65 x 4 mm CT vs 1.25 x 1.25 x 4 mm MR, 40 mm initial offset, registered in 8.8 s (examples/register_ct_mr_rire, the README demo); the multimodal-rigid-registration skill reports 3.9 deg / 1 mm-class agreement with the RIRE truth

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `learning_rate` | float | `1.0` | 0.1 to 5.0 | Gradient descent learning rate. | 1.0 with optimizer scales from physical shift: each step moves the image by about one unit of the scaled parameters, fast on the coarse levels and still stable because the scales normalise rotations and translations. |
| `num_iterations` | int | `100` | 10 to 500 | Maximum number of optimizer iterations. | 100 per level: Mattes MI on 1 % sampling plateaus within 50-80 iterations on head and abdomen volumes; the convergence window stops it earlier. |
| `sampling_percentage` | float | `0.01` | 0.005 to 0.5 | Metric sampling percentage (0.01 = 1%). | 1 % of the voxels is enough for the MI estimate on 256^3 volumes and makes each iteration cheap; raise to 5-15 % on small fields of view or very noisy images. |
| `initializer` *(advanced)* | enum | `GEOMETRY` | `GEOMETRY`, `MOMENTS` | Centered-initializer mode (geometric center vs center-of-mass). | GEOMETRY aligns the geometric centres of the two volumes, which works when both scans cover the same anatomy; MOMENTS (intensity centre of mass) is better when one field of view is much larger than the other. |
| `metric` *(advanced)* | enum | `mattes_mutual_information` | `mattes_mutual_information`, `mean_squares`, `correlation`, `joint_histogram_mi` | Similarity metric. | Mattes mutual information is the only one of the four that works across modalities (CT vs MR): it assumes a statistical dependence, not a linear intensity relation. |
| `number_of_histogram_bins` *(advanced)* | int | `50` | 10 to 256 | Mattes MI histogram bins. | 50 bins: 32-64 is the sweet spot for the Parzen-window joint histogram, fewer is blurry, more is noisy. |
| `sampling_strategy` *(advanced)* | enum | `RANDOM` | `NONE`, `REGULAR`, `RANDOM` | Metric sampling strategy. | RANDOM adds a little stochasticity that helps the optimizer leave shallow local minima; REGULAR aliases with voxel grids. |
| `interpolator` *(advanced)* | enum | `LINEAR` | `LINEAR`, `NEAREST`, `BSPLINE` | Resampling interpolator during optimization. | LINEAR during optimisation is the standard trade-off; B-spline is slower and only pays off for the final resampling. |
| `convergence_minimum_value` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | Gradient-descent convergence threshold. | 1e-6 on the metric change over the window. |
| `convergence_window_size` *(advanced)* | int | `10` | 3 to 50 | Gradient-descent convergence window. | 10 iterations smooth the stochastic metric before the convergence test. |
| `shrink_factors` *(advanced)* | list | `4,2,1` |  | Multi-resolution shrink factors per level (comma-separated). | 4,2,1: three resolution levels give the capture range to recover a 40 mm offset at the coarse level and sub-voxel precision at the fine one. |
| `smoothing_sigmas` *(advanced)* | list | `2,1,0` |  | Gaussian smoothing sigma per level (comma-separated). | 2,1,0 mm match the shrink factors so each level sees a properly band-limited image. |
| `smoothing_sigmas_in_physical_units` *(advanced)* | bool | `true` |  | Interpret sigmas in mm vs voxels. | On: sigmas in millimetres so anisotropic voxels (4 mm slices) are smoothed consistently. |
| `optimizer_scales_from_physical_shift` *(advanced)* | bool | `true` |  | Auto-estimate per-parameter optimizer scales. | On: rotations in radians and translations in millimetres have different sensitivities; the physical-shift scales equalise them, which is the single setting that makes a fixed learning rate work across datasets. |

### advanced_rigid

**1. Two-Stage Composite Approach**
From the reference implementation (modulesReg.py::registration_advanced), this method uses a two-stage approach: first, a geometry-based initial transform centers the images, then a second optimized Euler3D transform is applied. The final result is a CompositeTransform combining both stages.

**2. Conservative Parameters**
Compared to basic rigid registration:
- Learning rate: 0.2 (vs 1.0) for more stable convergence
- Sampling: 15% (vs 1%) for better metric estimation
- Iterations: 200 (vs 100) for thorough optimization

**3. Advantages**
The two-stage approach prevents the optimizer from getting stuck in local minima near the initial position, and the higher sampling percentage produces smoother metric landscapes.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.advanced_rigid", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.advanced_rigid_registration --input ... --output ...`.

**Defaults validated on:** RIRE CT / MR pair with the exhaustive rotation pre-search (multimodal-rigid-registration skill); generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `learning_rate` | float | `0.2` | 0.05 to 2.0 | Gradient descent learning rate (lower = more stable). | 0.2 is lower than the plain rigid method because the exhaustive phase already lands near the optimum; smaller steps then avoid overshooting. |
| `num_iterations` | int | `200` | 50 to 500 | Maximum optimizer iterations per stage. | 200 per stage: the second stage starts close and the window stops it early. |
| `sampling_percentage` | float | `0.15` | 0.01 to 0.5 | Metric sampling percentage (0.15 = 15%). | 15 % of the voxels: the exhaustive search compares many poses and needs a less noisy metric than gradient descent does. |
| `exhaustive_steps_per_axis` *(advanced)* | int | `12` | 4 to 24 | Rotation-search steps per axis (phase 1). | 12 steps per axis over the rotation range sample every 15 degrees, enough to land inside the capture range of the gradient stage. |
| `metric` *(advanced)* | enum | `mattes_mutual_information` | `mattes_mutual_information`, `mean_squares`, `correlation`, `joint_histogram_mi` | Similarity metric. | Mattes MI for cross-modality. |
| `number_of_histogram_bins` *(advanced)* | int | `50` | 10 to 256 | Mattes MI histogram bins. | 50 bins: 32-64 is the sweet spot for the Parzen-window joint histogram, fewer is blurry, more is noisy. |
| `sampling_strategy` *(advanced)* | enum | `RANDOM` | `NONE`, `REGULAR`, `RANDOM` | Metric sampling strategy. | RANDOM sampling adds a little stochasticity that helps the optimizer leave shallow local minima; REGULAR aliases with voxel grids. |
| `interpolator` *(advanced)* | enum | `LINEAR` | `LINEAR`, `NEAREST`, `BSPLINE` | Resampling interpolator during optimization. | LINEAR interpolation during optimisation is the standard trade-off between speed and smoothness of the metric. |
| `convergence_minimum_value` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | Gradient-descent convergence threshold. | 1e-6 on the metric change over the window stops the optimizer once improvements are below noise. |
| `convergence_window_size` *(advanced)* | int | `10` | 3 to 50 | Gradient-descent convergence window. | 10 iterations smooth the stochastic metric before the convergence test. |
| `shrink_factors` *(advanced)* | list | `4,2,1` |  | Multi-resolution shrink factors per level (comma-separated). | 4,2,1: three resolution levels give the capture range for large offsets at the coarse level and sub-voxel precision at the fine one. |
| `smoothing_sigmas` *(advanced)* | list | `2,1,0` |  | Gaussian smoothing sigma per level (comma-separated). | 2,1,0 mm match the shrink factors so each level sees a properly band-limited image. |
| `smoothing_sigmas_in_physical_units` *(advanced)* | bool | `true` |  | Interpret sigmas in mm vs voxels. | On: sigmas in millimetres so anisotropic voxels (4 mm slices) are smoothed consistently. |
| `optimizer_scales_from_physical_shift` *(advanced)* | bool | `true` |  | Auto-estimate per-parameter optimizer scales. | On: rotations in radians and translations in millimetres have different sensitivities; physical-shift scales equalise them so one learning rate works across datasets. |

### affine

**1. Affine Transformation Model**
An affine transformation has 12 DOF — rotation, translation, scaling, and shearing:
$$T_{\text{affine}}(\mathbf{x}) = A \mathbf{x} + \mathbf{t}$$
where $A \in \mathbb{R}^{3 \times 3}$ is a general invertible matrix (not restricted to $SO(3)$).

**2. Degrees of Freedom**
Compared to rigid (6 DOF), affine adds:
- 3 scaling parameters: $s_x, s_y, s_z$
- 3 shearing parameters: $k_{xy}, k_{xz}, k_{yz}$

This allows compensating for scanner calibration differences, growth between acquisitions, and anisotropic scaling.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.affine", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.affine_registration --input ... --output ...`.

**Defaults validated on:** generated volumes in tests/test_ops_smoke.py; same stack as rigid, which ran on the RIRE pair

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `learning_rate` | float | `1.0` | 0.1 to 5.0 | Gradient descent learning rate. | 1.0 with physical-shift scales, as for rigid. |
| `num_iterations` | int | `100` | 10 to 500 | Maximum number of optimizer iterations. | 100 per level. |
| `sampling_percentage` | float | `0.01` | 0.005 to 0.5 | Metric sampling percentage (0.01 = 1%). | 1 % of the voxels is enough for the mutual-information estimate on 256^3 volumes and keeps each iteration cheap. |
| `initializer` *(advanced)* | enum | `GEOMETRY` | `GEOMETRY`, `MOMENTS` | Centered-initializer mode (geometric center vs center-of-mass). | GEOMETRY aligns the geometric centres before the first iteration; MOMENTS (intensity centre of mass) when one field of view is much larger than the other. |
| `metric` *(advanced)* | enum | `mattes_mutual_information` | `mattes_mutual_information`, `mean_squares`, `correlation`, `joint_histogram_mi` | Similarity metric. | Mattes MI for cross-modality; mean squares is faster for same-modality follow-ups. |
| `number_of_histogram_bins` *(advanced)* | int | `50` | 10 to 256 | Mattes MI histogram bins. | 50 bins: 32-64 is the sweet spot for the Parzen-window joint histogram, fewer is blurry, more is noisy. |
| `sampling_strategy` *(advanced)* | enum | `RANDOM` | `NONE`, `REGULAR`, `RANDOM` | Metric sampling strategy. | RANDOM sampling adds a little stochasticity that helps the optimizer leave shallow local minima; REGULAR aliases with voxel grids. |
| `interpolator` *(advanced)* | enum | `LINEAR` | `LINEAR`, `NEAREST`, `BSPLINE` | Resampling interpolator during optimization. | LINEAR interpolation during optimisation is the standard trade-off between speed and smoothness of the metric. |
| `convergence_minimum_value` *(advanced)* | float | `1e-06` | 1e-08 to 0.001 | Gradient-descent convergence threshold. | 1e-6 on the metric change over the window stops the optimizer once improvements are below noise. |
| `convergence_window_size` *(advanced)* | int | `10` | 3 to 50 | Gradient-descent convergence window. | 10 iterations smooth the stochastic metric before the convergence test. |
| `shrink_factors` *(advanced)* | list | `4,2,1` |  | Multi-resolution shrink factors per level (comma-separated). | 4,2,1: three resolution levels give the capture range for large offsets at the coarse level and sub-voxel precision at the fine one. |
| `smoothing_sigmas` *(advanced)* | list | `2,1,0` |  | Gaussian smoothing sigma per level (comma-separated). | 2,1,0 mm match the shrink factors so each level sees a properly band-limited image. |
| `smoothing_sigmas_in_physical_units` *(advanced)* | bool | `true` |  | Interpret sigmas in mm vs voxels. | On: sigmas in millimetres so anisotropic voxels (4 mm slices) are smoothed consistently. |
| `optimizer_scales_from_physical_shift` *(advanced)* | bool | `true` |  | Auto-estimate per-parameter optimizer scales. | On: the 12 affine parameters mix scale, shear and translation, so scale normalisation matters even more than for rigid. |

### bspline

**1. Free-Form Deformation**
The displacement field is parameterized by a regular grid of $n_x \times n_y \times n_z$ control points $\{\phi_{i,j,k}\}$. The deformation at any point $\mathbf{x}$ is interpolated using cubic B-spline basis functions:
$$T(\mathbf{x}) = \mathbf{x} + \sum_{l=0}^{3} \sum_{m=0}^{3} \sum_{n=0}^{3} B_l(u) B_m(v) B_n(w) \, \phi_{i+l, j+m, k+n}$$
where $(u, v, w)$ are the local coordinates within the control point cell.

**2. Multi-Scale Refinement**
Registration proceeds from coarse grids (large `grid_spacing`) to fine grids, progressively capturing finer deformations. The LBFGSB optimizer handles the large number of parameters efficiently.

**3. Regularization**
The bending energy of the B-spline ensures smooth deformations:
$$\mathcal{R}_{\text{bend}} = \int \left\| \nabla^2 T(\mathbf{x}) \right\|^2 d\mathbf{x}$$

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.bspline", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.bspline_registration --input ... --output ...`.

**Defaults validated on:** POPI 4D-CT breathing phases (medical-volumes skill); generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `grid_spacing` | float | `50.0` | 10.0 to 100.0 | Control point grid spacing in mm. | 50 mm control-point spacing captures organ-scale motion (breathing, bowel) without fitting noise; 20-30 mm for finer local deformation. |
| `num_iterations` | int | `100` | 20 to 300 | LBFGSB optimizer iterations. | 100 LBFGSB iterations: the deformable metric improves quickly then flattens. |
| `bspline_order` *(advanced)* | int | `3` | 1 to 3 | B-spline basis order. | 3 (cubic) is the standard smooth basis. |
| `mesh_coarsening_factor` *(advanced)* | int | `4` | 1 to 8 | Extra coarsening divisor applied to the control-point mesh. | 4 starts the multi-resolution schedule with a coarser control mesh so large motion is recovered first. |
| `sampling_percentage` *(advanced)* | float | `0.01` | 0.005 to 0.5 | Fraction of voxels sampled by the metric. | 1 % of the voxels for the metric. |
| `interpolator` *(advanced)* | enum | `LINEAR` | `LINEAR`, `NEAREST`, `BSPLINE` | Resampling interpolator. | LINEAR interpolation during optimisation is the standard trade-off between speed and smoothness of the metric. |
| `gradient_convergence_tolerance` *(advanced)* | float | `1e-05` | 1e-07 to 0.001 | LBFGSB gradient convergence tolerance. | 1e-5 is the LBFGSB default. |
| `max_number_of_corrections` *(advanced)* | int | `5` | 1 to 20 | LBFGSB stored corrections (memory). | 5 stored corrections is the LBFGSB default memory. |
| `cost_function_convergence_factor` *(advanced)* | float | `10000000.0` | 10.0 to 1000000000000.0 | LBFGSB cost-function convergence factor. | 1e7 is the LBFGSB default (moderate accuracy). |
| `scale_factors` *(advanced)* | list | `1,2,4` |  | B-spline multi-resolution scale factors (comma-separated). | 1,2,4 refine the control mesh across three levels. |

### demons

**1. Optical Flow Formulation**
Demons registration computes a dense displacement field $\mathbf{u}(\mathbf{x})$ by iteratively solving an optical flow equation. The update step for the displacement at each voxel is:
$$\Delta \mathbf{u}(\mathbf{x}) = \frac{(I_M(\mathbf{x} + \mathbf{u}) - I_F(\mathbf{x})) \nabla I_F(\mathbf{x})}{\|\nabla I_F(\mathbf{x})\|^2 + (I_M - I_F)^2}$$

**2. Symmetric Forces**
The symmetric variant uses gradients from both images for improved convergence:
$$\Delta \mathbf{u} = \frac{(I_M - I_F)(\nabla I_F + \nabla I_M)}{\|\nabla I_F + \nabla I_M\|^2 + (I_M - I_F)^2}$$

**3. Gaussian Smoothing**
After each iteration, the displacement field is convolved with a Gaussian kernel of standard deviation $\sigma$ (`standard_deviations` parameter) to enforce diffeomorphic-like smoothness.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.demons", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.demons_registration --input ... --output ...`.

**Defaults validated on:** generated volumes in tests/test_ops_smoke.py; same-modality use only (the metric is intensity difference)

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `num_iterations` | int | `20` | 5 to 100 | Number of demons iterations. | 20 demons iterations are enough for small same-modality deformations; the method is for follow-up scans, not CT-to-MR. |
| `standard_deviations` | float | `2.0` | 0.5 to 5.0 | Displacement field smoothing sigma. | 2.0 voxels of Gaussian smoothing of the displacement field keep it regular (no folding) at the cost of fine detail. |
| `smooth_displacement_field` *(advanced)* | bool | `true` |  | Smooth the total displacement field each iteration. | On: smoothing the total field each iteration is what keeps demons from producing a torn deformation. |

### difference_analysis

**1. Registration Quality Assessment**
After registration, the absolute difference image $D = |I_F - I_M^{\text{reg}}|$ reveals regions of misalignment. Low values indicate good alignment; high values indicate residual error.

**2. Thresholding**
Binary thresholding on the difference image extracts voxels with significant misalignment:
$$M(\mathbf{x}) = \begin{cases} 1 & \text{if } \tau_L \leq D(\mathbf{x}) \leq \tau_U \\ 0 & \text{otherwise} \end{cases}$$

**3. Statistics**
Mean, max, and standard deviation of the difference image quantify overall registration accuracy. The percentage of high-difference voxels provides a single summary metric.

```python
import pardesline as pl

fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")
result = fixed.run("simpleitk_registration.difference_analysis", moving=moving)  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_registration.difference_analysis --input ... --output ...`.

**Defaults validated on:** generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `lower_threshold` | float | `50.0` | 0.0 to 500.0 | Lower threshold for highlighting high-difference regions. | 50 intensity units: below that, differences are noise and interpolation. |
| `upper_threshold` | float | `400.0` | 100.0 to 3000.0 | Upper threshold for difference analysis. | 400: above that, differences are bone or air boundaries that any residual misalignment produces; the band in between highlights soft-tissue change. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("simpleitk_registration")` prints this module from the installed package; `pl.describe("simpleitk_registration.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/simpleitk_registration.json` and `_defaults.json` on 2026-10-10.</sub>
