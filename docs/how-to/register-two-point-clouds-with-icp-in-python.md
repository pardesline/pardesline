---
title: How to register two point clouds with ICP in Python
description: Rigid registration of two point clouds in Python with RANSAC on FPFH features followed by point-to-plane ICP, in one call with defaults that scale to the data: target.align(moving), the transform, fitness and RMSE, and how to verify the result.
---

# How to register two point clouds with ICP in Python

ICP alone only works from a nearby start. The call below runs global registration (FPFH features + RANSAC) first, then ICP, with every distance derived from the data's own scale.

```python
import pardesline as pl

ds = pl.load("open3d_icp_demo")  # three indoor fragments, sensor frame, metres
pair = ds["pair_0_1"]
aligned = pair.target.align(pair.source)  # registration.ransac_icp_pipeline, catalog defaults
print(aligned.transform["fitness"], aligned.transform["inlier_rmse"])
print(aligned.transform["transformation_matrix"])  # 4x4, source -> target
aligned.save("source_on_target.ply")  # the moved cloud + sidecar with every parameter used
```

Your own files: `pl.load("scan_a.ply").align(pl.load("scan_b.ply"))`. The result is the moving cloud in the target's frame; `.transform` holds the matrix, fitness, inlier RMSE and the RANSAC pre-pass numbers.

## Verify, do not trust fitness alone

- **Fitness** is the fraction of source points with a correspondence within the threshold: it caps at the overlap ratio and is high for any pose when the threshold is wide.
- **Inlier RMSE** should approach the scanner's noise floor (1 mm for a structured-light scanner, 2–3 cm for automotive LiDAR).
- With a **known transform** (phantom, synthetic test), the rotation error is `arccos((trace(R_est R_true^T) - 1) / 2)`: the [bunny example](../examples.md#icp_registration_bunny) measures 0.14° against 32.0° for a textbook ICP call.
- Look at it: `aligned.to_pyvista()` next to `pair.target.to_pyvista()` in one plotter.

## The parameters, when you need them

```python
aligned = pair.target.align(
    pair.source, voxel_size=0.05, icp_threshold_factor=0.3, icp_estimation_method="point_to_point"
)
print(pl.describe("registration.ransac_icp_pipeline"))  # every parameter, range, default and why
```

`voxel_size=0` (the default) picks 1.3 % of the bounding-box diagonal; every other distance is a multiple of it. The reasons are on the [registration page](../algorithms/registration.md) and in [Why our defaults work](../algorithms/why-our-defaults-work.md#registration-of-point-clouds-registration).

## Two stages separately

```python
coarse = pair.target.run("registration.ransac_global", moving=pair.source)  # inspect the global pose
fine = pair.target.run("registration.icp_refinement", moving=coarse)  # then refine
```

Related: [Fix ICP that does not converge](fix-icp-that-does-not-converge.md) · [Fix RANSAC that fails](fix-ransac-global-registration-that-fails.md) · [Guide: point-cloud registration](../guides/point-cloud-registration.md)
