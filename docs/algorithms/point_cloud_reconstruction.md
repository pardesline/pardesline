---
title: "Surface Reconstruction (point_cloud_reconstruction): 4 methods in Python"
description: "Convert a point cloud into a surface mesh using various reconstruction algorithms: Convex Hull, Alpha Shape, Ball Pivoting, Poisson"
---

# Surface Reconstruction

`point_cloud_reconstruction`: Convert a point cloud into a surface mesh using various reconstruction algorithms: Convex Hull, Alpha Shape, Ball Pivoting, Poisson.

| | |
|---|---|
| Methods | [`poisson`](#poisson), [`convex_hull`](#convex_hull), [`alpha_shape`](#alpha_shape), [`ball_pivoting`](#ball_pivoting) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| Example | [Poisson reconstruction on the Stanford bunny](../examples.md#poisson_reconstruction_bunny) |
| CLI | `pardesline run point_cloud_reconstruction.<method> input.ext [--param value]` |

## How it works

Surface reconstruction converts a discrete set of 3D points $P = \{p_1, p_2, \ldots, p_n\} \subset \mathbb{R}^3$ into a continuous surface $S$, typically represented as a triangle mesh $\mathcal{M} = (V, F)$.

The reconstruction problem is inherently ill-posed: infinitely many surfaces can interpolate a finite point set. Each algorithm introduces different priors:
- Convexity (Convex Hull)
- Scale-dependent connectivity ($\alpha$-shapes, Ball Pivoting)
- Smoothness (Poisson reconstruction)

The quality of reconstruction depends on point density, noise level, and the presence of oriented normals $\{\vec{n}_i\}$ at each sample point.

## Methods

### poisson

**1. Indicator Function**
Given oriented point samples $(p_i, \vec{n}_i)$, the Poisson approach defines a vector field $\vec{V}$ from the normals and seeks an indicator function $\chi: \mathbb{R}^3 \to \mathbb{R}$ whose gradient approximates $\vec{V}$:
$$\nabla \chi \approx \vec{V}$$

**2. Poisson Equation**
Applying divergence to both sides yields the Poisson equation:
$$\Delta \chi = \nabla \cdot \vec{V}$$
This is solved using an adaptive octree of depth $d$ (the `depth` parameter), where higher depth captures finer geometric detail.

**3. Surface Extraction**
The iso-surface is extracted at an appropriate level of $\chi$ using marching cubes. The `scale` parameter controls the extent of the reconstruction volume relative to the bounding box of the input samples.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_reconstruction.poisson")  # catalog defaults
# same thing, domain vocabulary: `points.to_mesh()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_reconstruction.poisson --input ... --output ...`.

**Defaults validated on:** Stanford bunny sampled to 20 000 points (examples/poisson_reconstruction_bunny); ultrasound and CBCT reconstructions in the atlas-label-transfer and pointnet-segmentation skills; generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `depth` | int | `9` | 4 to 13 | Octree depth. Higher = more detail but slower. | 9 gives 512 cells across the bounding cube: on 20k-200k point scans it recovers organ- and part-level detail without fitting the noise; 8 is Open3D's default and blurs small features, 10-11 need hundreds of thousands of points. |
| `scale` | float | `1.1` | 0.5 to 2.0 | Ratio between reconstruction cube and samples bounding cube. | 1.1 is the Kazhdan reference setting: the reconstruction cube is 10 % larger than the samples' bounding cube so the surface can close outside the data. |
| `width` *(advanced)* | float | `0.0` | 0.0 to 1.0 | Target finest octree cell width; 0 uses depth instead. | 0 means depth drives the resolution; set a width in file units when you know the target cell size (e.g. 1 mm). |
| `linear_fit` *(advanced)* | bool | `false` |  | Use linear interpolation to estimate iso-vertex positions. | Off: the default iso-vertex placement is smoother; linear fit is faster and slightly blockier. |
| `n_threads` *(advanced)* | int | `-1` | -1 to 64 | Number of threads (-1 = all available). | -1 uses every core. |
| `density_quantile` *(advanced)* | float | `0.01` | 0.0 to 1.0 | Density quantile below which low-support vertices are removed as noise. | 0.01 removes the 1 % of vertices with the least sample support: that is where Poisson balloons over holes and partial views, so the output is a clean, density-trimmed surface rather than a bubble; raise to 0.05-0.1 on very partial scans. |
| `normal_radius` *(advanced)* | float | `0.1` | 0.001 to 10.0 | Search radius for normal estimation when the cloud has no normals. | 0.1 in file units for normal estimation when the cloud has none; about 5-10x the point spacing on metre-scale data, scale it for millimetre scans. |
| `normal_max_nn` *(advanced)* | int | `30` | 1 to 200 | Max neighbours for normal estimation when the cloud has no normals. | 30 neighbours is enough for a stable covariance; more smooths sharp edges. |
| `normal_orient_k` *(advanced)* | int | `15` | 1 to 200 | k for consistent tangent-plane normal orientation. | 15 neighbours for consistent orientation: Poisson needs normals pointing the same way, and a small k keeps the propagation local on thin parts. |

### convex_hull

**1. Definition**
The convex hull $\text{CH}(P)$ is the smallest convex polytope containing all points:
$$\text{CH}(P) = \left\{ \sum_{i=1}^{n} \lambda_i p_i : \lambda_i \geq 0, \sum_i \lambda_i = 1 \right\}$$

**2. Complexity**
Computed in $O(n \log n)$ using the Quickhull algorithm. The output mesh has at most $2n - 4$ triangular faces.

**3. Limitations**
Cannot represent concavities — the result is always a convex polytope. Best suited for convex objects or as a bounding approximation.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_reconstruction.convex_hull")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_reconstruction.convex_hull --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `joggle_inputs` *(advanced)* | bool | `false` |  | Randomly perturb inputs to avoid QHull errors on coplanar/degenerate points. | Off: exact hull; turn on only when QHull fails on coplanar or duplicated points. |

### alpha_shape

**1. Generalized Hull**
Alpha shapes generalize convex hulls by introducing a scale parameter $\alpha > 0$. A Delaunay simplex (triangle) is included in the alpha shape if it can be circumscribed by a sphere of radius $r \leq 1/\alpha$.

**2. Scale Behavior**
- $\alpha \to 0$: the alpha shape approaches the point set itself
- $\alpha \to \infty$: the alpha shape approaches the convex hull
- Intermediate $\alpha$: captures concavities at scale $\sim 1/\alpha$

**3. Topological Properties**
Alpha shapes can produce surfaces with holes, disconnected components, and non-manifold edges depending on point density and $\alpha$ value.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_reconstruction.alpha_shape")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_reconstruction.alpha_shape --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `alpha` | float | `0.03` | 0.005 to 0.5 | Alpha parameter. Smaller = tighter fit (more detail). Larger = smoother. | 0.03 in file units is a tight fit on metre-scale objects with centimetre point spacing; alpha must be larger than the largest gap you want bridged and smaller than the smallest concavity you want kept. |

### ball_pivoting

**1. Algorithm**
Ball Pivoting (Bernardini et al., 1999) rolls a ball of radius $\rho$ over the point cloud. Starting from a seed triangle formed by three mutually tangent points, the ball pivots around each edge, adding triangles when it contacts a new point.

**2. Multi-Scale Reconstruction**
Using multiple radii $\{\rho, 2\rho, 4\rho\}$ captures geometry at different scales. The `radius_factor` parameter sets $\rho$ as a multiple of the average nearest-neighbor distance:
$$\rho = f \cdot \bar{d}_{\text{nn}}$$

**3. Requirements**
Requires oriented normals $\vec{n}_i$ to determine the inside/outside of the surface. Works best with uniformly sampled, noise-free point clouds.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_reconstruction.ball_pivoting")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_reconstruction.ball_pivoting --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `radius_factor` | float | `2.0` | 0.5 to 10.0 | Ball radius as factor of average point spacing. Uses multiple radii (1x, 2x, 4x). | 2x the average point spacing is the smallest ball that rolls over a sampled surface without falling through; the multi-scale set (1x, 2x, 4x) then fills the larger gaps. |
| `radii_multipliers` *(advanced)* | list | `1,2,4` |  | CSV of base-radius multipliers defining the multi-scale ball set. | 1,2,4 is the classic multi-scale schedule: small balls first for detail, larger ones to bridge sparse regions. |
| `normal_radius` *(advanced)* | float | `0.1` | 0.001 to 10.0 | Search radius for normal estimation when the cloud has no normals. | 0.1 in file units for normal estimation when the cloud has none. |
| `normal_max_nn` *(advanced)* | int | `30` | 1 to 200 | Max neighbours for normal estimation when the cloud has no normals. | 30 neighbours for a stable covariance. |
| `normal_orient_k` *(advanced)* | int | `15` | 1 to 200 | k for consistent tangent-plane normal orientation. | 15 for consistent orientation; ball pivoting needs oriented normals. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("point_cloud_reconstruction")` prints this module from the installed package; `pl.describe("point_cloud_reconstruction.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/point_cloud_reconstruction.json` and `_defaults.json` on 2026-10-16.</sub>
