---
title: How to fix ICP that does not converge (Open3D ICP parameters, max correspondence distance, noisy partial scans)
description: Why ICP stops at a wrong pose with a good-looking fitness, the Open3D parameters behind it (max_correspondence_distance, init, estimation method), what to set for noisy partial industrial scans, and the one-liner that already does it.
---

# How to fix ICP that does not converge

## The symptom

`registration_icp` returns a fitness of 0.9 and the clouds are visibly misaligned; or the fitness is 0.05 and nothing moved; or it converges to a mirrored pose. On the Stanford bunny against a copy rotated 35° with 70 % overlap and 0.5 % noise, the tutorial call ends 32.0° off with a fitness of 0.98 ([the experiment](../examples.md#icp_registration_bunny)).

## The parameters behind it

| Parameter (Open3D) | What goes wrong | What to set |
|---|---|---|
| `init` (initial transform) | ICP is a local optimiser; its basin is a few degrees and a fraction of the object size. From the identity, a 35° offset converges to the nearest wrong minimum. | A global stage first: FPFH features + RANSAC. That is what `align()` does. |
| `max_correspondence_distance` | Too wide (0.02 m on a 0.15 m bunny): every point finds a partner, fitness looks excellent, the pose is wrong. Too tight: no correspondences, nothing moves. | Tie it to the data: 1.5× a voxel of 1.3 % of the bounding-box diagonal for the coarse pass, 0.4× for the fine pass. |
| `estimation_method` | Point-to-point zigzags and stalls on smooth surfaces. | Point-to-plane with target normals; point-to-point only when normals are unreliable (sparse LiDAR). |
| units | Millimetres read as metres make every distance 1000× too small. | `obj.frame.units`; `with_frame("sensor", "mm")`. |
| overlap | The 30 % of points without a counterpart pull the solution. | A tight fine-pass threshold; judge by inlier RMSE on the overlap, not by fitness. |
| symmetry | Cylinders, spheres, vertebral bodies have several equally good poses. | `ransac_n=4`, a prior pose, more context in the scan. |

## The one-liner that already handles it

```python
import pardesline as pl

target, moving = pl.load("scan_a.ply"), pl.load("scan_b.ply")
aligned = target.align(moving)
print(aligned.transform["ransac_fitness"], aligned.transform["inlier_rmse"])
```

`align` = `registration.ransac_icp_pipeline`: voxel from the bounding box, FPFH at 5× the voxel, RANSAC with the mutual filter at 1.5× the voxel, then point-to-plane ICP at 0.4× the voxel. Every value and its reason: `pl.describe("registration.ransac_icp_pipeline")`.

## Still off? Walk the diagnostics

1. **`ransac_fitness` below 0.3**: the features are meaningless. The voxel is wrong for the data: pass `voxel_size` = 2–5× the point spacing. Check the units first.
2. **Good RANSAC, bad ICP**: the fine threshold is too wide for the noise or the overlap: `icp_threshold_factor=0.2–0.3`.
3. **Flat scene**: point-to-plane slides along planes: `icp_estimation_method="point_to_point"`.
4. **Converges to a mirror**: symmetric object; verify with a target registration error on landmarks the algorithm did not see.
5. **Different scale**: `ransac_with_scaling=True` once (photogrammetry vs scanner), then fix the scale and run rigid again.

## Measuring instead of guessing

The [`registration_eval.py`](https://github.com/pardesline/pardesline/blob/main/skills/point-cloud-registration/scripts/registration_eval.py) script applies a known transform with noise and partial overlap to any cloud and prints fitness, inlier RMSE, rotation and translation error, Chamfer and HD95: the way to tune on your data before trusting a number.

Related: [Register two point clouds](register-two-point-clouds-with-icp-in-python.md) · [Why our defaults work](../algorithms/why-our-defaults-work.md) · [Benchmarks](../benchmarks.md)
