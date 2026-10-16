---
title: How to convert a point cloud to Gaussian splats in Python (3DGS PLY)
description: Initialise 3D Gaussians from a point cloud or mesh in Python and write a 3DGS-compatible PLY that opens in gsplat, Nerfstudio and the Hugging Face viewers: scale from k-nearest neighbours, identity rotation, SH degree-0 colour; load the bundled splat datasets.
---

# How to convert a point cloud to Gaussian splats in Python

A Gaussian splat is a point with a covariance (three log-scales and a quaternion), an opacity and spherical-harmonics colour. The reference script initialises one Gaussian per point, which is the standard starting state of a 3DGS optimisation and already renders as a soft surface.

```bash
pip install "pardesline[local]"
python skills/gaussian-splatting/scripts/points_to_gaussians.py cloud.ply splat.ply --k 4
python examples/points_to_gaussians_bunny/run.py           # the bunny: 50 000 Gaussians, 12 MB
```

In Python, with the script's functions:

```python
import pardesline as pl

points = pl.load("open3d_bunny")[0].mesh.to_points(num_points=50000, seed=1)
# the script reads any point cloud or mesh pardesline opens (raw arrays with --layout)
```

Per Gaussian: `scale = log(mean distance to the k nearest neighbours)` on the three axes, rotation = identity quaternion, `opacity = logit(0.1)`, `f_dc = (rgb - 0.5) / 0.2820948` with `f_rest = 0`. The PLY has the 62 floats per vertex the reference implementation expects; `--sh-degree 3` adds the higher-order coefficients as zeros.

![Bunny Gaussian centres coloured by height](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/points_to_gaussians_bunny/bunny_splats.png)

## Reading splats back

```python
splat = pl.load("splat.ply")  # a PointCloud: x, y, z are standard properties
centres = splat.to_numpy()
```

The extra properties (`scale_0..2`, `rot_0..3`, `opacity`, `f_dc_*`) stay in the file; a splat viewer renders them. Two bundled datasets ship fitted splats: [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) (colonoscopy scenes) and [`hf_kitti360_gs_subset`](../datasets/hf_kitti360_gs_subset.md) (street chunks as `.npy` arrays with a layout).

## From here

Optimising the Gaussians against images needs a renderer (gsplat, the reference CUDA code); the [guide](../guides/gaussian-splatting.md) explains the parameters, the densification schedule and how medical volumes map onto the representation. A first-class `Splat` kind (render, convert to points, metrics) is on the [roadmap](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+splats).

Related: [Guide: Gaussian splatting](../guides/gaussian-splatting.md) · [3D representations](../guides/3d-representations.md)
