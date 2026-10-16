---
title: How to reconstruct a surface from a point cloud in Python (Poisson, ball pivoting, alpha shapes)
description: Point cloud to mesh in Python: clean the cloud, estimate oriented normals, Poisson reconstruction with density trimming so holes do not balloon, ball pivoting for thin structures, alpha shapes for convex-ish objects; what the defaults do and how to check the result.
---

# How to reconstruct a surface from a point cloud in Python

```python
import pardesline as pl

mesh = pl.load("open3d_bunny")[0].mesh
points = mesh.to_points(
    num_points=20000, seed=1
).clean()  # Poisson-disk sampling, statistical outlier removal
surface = points.to_mesh()  # Poisson, depth 9, density-trimmed at the 1 % quantile
surface.save("bunny_surface.ply")
print(surface.info(), surface.provenance[-1]["params"])
```

Your own scan: `pl.load("scan.ply").clean().to_mesh()`. The output is a clean, density-trimmed surface: Poisson closes the object, and the trimming removes the vertices with the least sample support, which is where it would balloon over holes and the unseen back side. It is lossy and parametric, and the sidecar records `depth` and `density_quantile`.

![Bunny points and the Poisson surface](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/poisson_reconstruction_bunny/bunny_poisson.png)

## Choosing the method

| Method | Call | Good for | Watch out |
|---|---|---|---|
| Poisson | `points.to_mesh()` | closed organic objects, scans with noise, 10k–1M points | balloons over holes without trimming; needs oriented normals (estimated if missing) |
| Ball pivoting | `points.run("point_cloud_reconstruction.ball_pivoting")` | thin structures, uniform sampling, interpolating the points exactly | holes where the sampling is sparse; `radius_factor` relative to the point spacing |
| Alpha shape | `points.run("point_cloud_reconstruction.alpha_shape", alpha=0.03)` | convex-ish objects, quick hulls with concavities | `alpha` in file units: larger than the gaps, smaller than the concavities |
| Convex hull | `points.run("point_cloud_reconstruction.convex_hull")` | bounding geometry | no concavities |

## Parameters that matter

- `depth` (Poisson): 9 gives 512 cells across the bounding cube; 8 is Open3D's default and blurs small features; 10–11 need hundreds of thousands of points. [Benchmark](../benchmarks.md).
- `density_quantile`: 0.01 by default; 0.05–0.1 on very partial scans.
- Normals: estimated at `normal_radius=0.1` file units with `normal_orient_k=15` when the cloud has none. Scans in millimetres need `normal_radius` scaled (about 5–10× the point spacing).

## Check the result

```python
import numpy as np
import open3d as o3d

tree = o3d.geometry.KDTreeFlann(points.to_open3d())
d = [np.sqrt(tree.search_knn_vector_3d(p, 1)[2][0]) for p in surface.to_numpy()[::50]]
print("median vertex-to-cloud distance", np.median(d))  # should be at the noise level
```

A vertex far from any input point is a balloon: raise `density_quantile`.

Related: [point_cloud_reconstruction](../algorithms/point_cloud_reconstruction.md) · [Why our defaults work](../algorithms/why-our-defaults-work.md#surface-reconstruction-point_cloud_reconstruction) · [Guide: 3D representations](../guides/3d-representations.md)
