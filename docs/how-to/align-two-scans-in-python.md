---
title: How to align two scans in Python (meshes, point clouds, CT and MRI volumes)
description: Align two meshes, two point clouds or two volumes in Python with one call that picks the right method for the object type: RANSAC + ICP for geometry, mutual-information rigid registration for volumes, Coherent Point Drift for non-rigid cases; the transform and how to apply it.
---

# How to align two scans in Python

`align(moving)` is defined on every object type and picks the method that fits it:

| You have | Call | Method underneath |
|---|---|---|
| two point clouds | `target.align(moving)` | FPFH + RANSAC, then point-to-plane ICP (`registration.ransac_icp_pipeline`) |
| two meshes | `target.to_points().align(moving.to_points())` | same, on sampled points |
| two volumes (CT, MR, any modality) | `fixed.align(moving)` | SimpleITK rigid, Mattes mutual information (`simpleitk_registration.rigid`) |
| a scan and an atlas with labels | `scan.align(atlas)` then transfer labels | see [Label a scan from an atlas](label-a-scan-from-an-atlas-in-python.md) |
| organ motion, breathing | rigid first, then `deformable_registration.cpd_deformable` (points) or `simpleitk_registration.bspline` (volumes) | non-rigid |

```python
import pardesline as pl

a = pl.load("scan_a.stl")  # Mesh
b = pl.load("scan_b.stl")
pa, pb = a.to_points(num_points=50000, seed=1), b.to_points(num_points=50000, seed=1)
moved = pa.align(pb)  # pb moved onto pa
T = moved.transform["transformation_matrix"]  # 4x4, apply it to b's vertices to move the mesh
```

## Applying the transform to the original mesh

```python
import numpy as np

T = np.asarray(T)
verts = b.to_numpy()
moved_verts = (T[:3, :3] @ verts.T).T + T[:3, 3]
```

Or let PyVista do it: `b.to_pyvista().transform(T, inplace=False)`.

## Units first

Both inputs must be in the same units and the frame must be known: `a.frame`, `a.units`; `with_frame("sensor", "mm")` to declare them. A millimetre scan against a metre scan "aligns" to nonsense with a plausible-looking fitness.

## Verify

Fitness caps at the overlap and lies when the threshold is wide; inlier RMSE should approach the noise level; landmarks not used by the algorithm are the real test. [Why our defaults work](../algorithms/why-our-defaults-work.md) has the numbers for each method.

Related: [Register two point clouds with ICP](register-two-point-clouds-with-icp-in-python.md) · [Register CT and MRI](register-ct-and-mri-of-the-same-patient-in-python.md) · [Fix ICP](fix-icp-that-does-not-converge.md)
