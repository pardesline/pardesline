---
title: How to fix RANSAC global registration that fails (FPFH features, voxel size, mutual filter)
description: Why FPFH + RANSAC global registration returns a low fitness or a wrong pose on real scans: voxel size, feature radius, units, symmetry, the mutual filter; what pardesline sets and how to diagnose with ransac_fitness.
---

# How to fix RANSAC global registration that fails

## The symptom

`ransac_fitness` is 0.05 and the pose is random; or RANSAC takes a minute and returns a pose that ICP then "refines" into a wrong minimum.

## Causes, in the order to check them

1. **Units.** A millimetre cloud with a voxel chosen for metres has one point per cell. `obj.frame.units`, then `with_frame(units="mm")`.
2. **Voxel size.** Features are computed on the downsampled cloud. Too small: the FPFH histograms describe noise. Too large: there is nothing left to describe. Rule: 2–5× the point spacing, about 1 % of the bounding-box diagonal. `align()` picks 1.3 % of the diagonal when `voxel_size=0`.
3. **Feature radius.** FPFH needs about five voxels of support (`fpfh_radius_factor=5`); normals need two (`normal_radius_factor=2`). Larger radii blur partial views, smaller ones make every point look the same.
4. **Mutual filter off.** Without it, one-directional matches flood RANSAC with false correspondences; `mutual_filter=True` is the single most effective setting on symmetric or repetitive parts.
5. **Overlap below 30 %.** FPFH cannot match what is not there. Crop both clouds to the region that overlaps, or acquire more.
6. **Symmetry.** Cylinders, spheres, planes: several poses score the same. `ransac_n=4`, a prior from the fixture, or landmarks.

## What pardesline sets

```python
import pardesline as pl

coarse = target.run("registration.ransac_global", moving=moving)  # inspect the global stage alone
print(coarse.transform["fitness"], coarse.transform["inlier_rmse"])
print(pl.describe("registration.ransac_global"))  # every parameter with its rationale
```

`voxel_size=0` (auto), `normal_radius_factor=2`, `fpfh_radius_factor=5`, `distance_threshold_factor=1.5`, `mutual_filter=True`, `ransac_n=3`, `edge_length_threshold=0.9`, `ransac_max_iteration=100000`, `ransac_confidence=0.999`. The rationale for each is on the [registration page](../algorithms/registration.md#ransac_global).

## A quick experiment

```python
for v in (0.5, 1, 2, 4):  # multiples of the auto voxel, in file units
    r = target.run("registration.ransac_global", moving=moving, voxel_size=v * 0.013 * diag)
    print(v, r.transform["fitness"], r.transform["inlier_rmse"])
```

Pick the voxel with the highest fitness at a sane RMSE, then run the full pipeline with it.

Related: [Fix ICP that does not converge](fix-icp-that-does-not-converge.md) · [Guide: point-cloud registration](../guides/point-cloud-registration.md)
