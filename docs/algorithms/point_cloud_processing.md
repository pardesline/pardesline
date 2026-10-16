---
title: "Point Cloud Processing (point_cloud_processing): 4 methods in Python"
description: "Fundamental point cloud operations: downsampling, filtering, outlier removal"
---

# Point Cloud Processing

`point_cloud_processing`: Fundamental point cloud operations: downsampling, filtering, outlier removal. Essential preprocessing for all 3D computer vision pipelines.

| | |
|---|---|
| Methods | [`voxel_downsample`](#voxel_downsample), [`statistical_outlier_removal`](#statistical_outlier_removal), [`radius_outlier_removal`](#radius_outlier_removal), [`mesh_to_pointcloud`](#mesh_to_pointcloud) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| Example | [Poisson reconstruction on the Stanford bunny](../examples.md#poisson_reconstruction_bunny) |
| CLI | `pardesline run point_cloud_processing.<method> input.ext [--param value]` |

## How it works

Point cloud processing encompasses the fundamental operations needed to prepare raw 3D data for downstream tasks. A point cloud $P = \{p_1, \ldots, p_n\} \subset \mathbb{R}^3$ often contains noise, outliers, and redundant points.

Voxel downsampling divides the space into a regular grid of cubes (voxels) with side length $v$ and replaces all points within each voxel by their centroid:

$$
\bar{p}_k = \frac{1}{|V_k|} \sum_{p_i \in V_k} p_i
$$


Statistical outlier removal computes the mean distance $\mu_i$ from each point to its $k$ nearest neighbors and removes points where $\mu_i > \bar{\mu} + \alpha \cdot \sigma$.

Radius outlier removal removes points that have fewer than $n_{\min}$ neighbors within a sphere of radius $r$.

## Methods

### voxel_downsample

Voxel downsampling partitions $\mathbb{R}^3$ into a regular grid of cubes with side length $v$. For each non-empty voxel $V_k$, a representative point is computed as the centroid:

$$\bar{p}_k = \frac{1}{|V_k|} \sum_{p_i \in V_k} p_i$$

This reduces the point count while providing uniform spatial sampling.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_processing.voxel_downsample")  # catalog defaults
# same thing, domain vocabulary: `points.downsample(voxel_size=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_processing.voxel_downsample --input ... --output ...`.

**Defaults validated on:** Stanford bunny (0.15 m, examples/poisson_reconstruction_bunny), KITTI sweeps (metres, examples/kitti_lidar_ground_and_objects); generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.02` | 0.001 to 0.5 | Size of each voxel cube. Smaller = more detail. | 0.02 in file units: on a metre-scale object or room it keeps one point per 2 cm, enough for registration features and clustering; set it to 2-5x the point spacing of your scanner (0.5 mm for CBCT, 0.1 m for outdoor LiDAR), because the value is absolute, not relative to the object. |

### statistical_outlier_removal

For each point $p_i$, compute the mean distance to its $k$ nearest neighbors:
$$\mu_i = \frac{1}{k} \sum_{j=1}^{k} \|p_i - p_{nn_j}\|$$

A point is classified as an outlier if $\mu_i > \bar{\mu} + \alpha \cdot \sigma$ where $\alpha$ is the standard deviation multiplier.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_processing.statistical_outlier_removal")  # catalog defaults
# same thing, domain vocabulary: `points.clean()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_processing.statistical_outlier_removal --input ... --output ...`.

**Defaults validated on:** Stanford bunny with 0.5 % Gaussian noise (examples/poisson_reconstruction_bunny, examples/icp_registration_bunny); generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `nb_neighbors` | int | `20` | 5 to 100 | Number of nearest neighbors to consider. | 20 neighbours give a stable mean distance per point on scans of 10k-1M points; fewer makes the estimate noisy, more blurs the boundary between surface and stray points. |
| `std_ratio` | float | `2.0` | 0.5 to 5.0 | Standard deviation multiplier threshold. | 2.0 removes points whose mean neighbour distance is beyond two standard deviations: on scanner noise this drops the flying pixels and keeps thin structures; lower to 1.0 on very noisy depth-camera data, raise to 3.0 on clean CAD-derived clouds. |
| `print_progress` *(advanced)* | bool | `false` |  | Print a progress bar during removal. | Off: the progress bar writes to the terminal and is useless in a pipeline or an agent run. |

### radius_outlier_removal

For each point $p_i$, count the number of neighbors within radius $r$. A point is removed if it has fewer than $n_{\min}$ neighbors.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_processing.radius_outlier_removal")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_processing.radius_outlier_removal --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `radius` | float | `0.05` | 0.001 to 1.0 | Search radius for counting neighbors. | 0.05 in file units: a point with fewer than min_neighbors within 5 cm is isolated on a metre-scale scan; scale with the point spacing (about 10x the spacing). |
| `min_neighbors` | int | `5` | 1 to 50 | Minimum neighbors required to keep a point. | 5 is low enough to keep edges and thin parts, where neighbourhoods are naturally sparse, while isolated speckle has 0-2 neighbours. |
| `print_progress` *(advanced)* | bool | `false` |  | Print a progress bar during removal. | Off: terminal output only. |

### mesh_to_pointcloud

**1. Vertex Extraction**
A triangle mesh $\mathcal{M} = (V, F)$ consists of a vertex set $V = \{v_1, \ldots, v_n\} \subset \mathbb{R}^3$ and a face set $F \subset V \times V \times V$. Converting to a point cloud simply discards the connectivity $F$, retaining only the vertex positions:
$$P = \{v_i \in \mathbb{R}^3 : v_i \in V\}$$

**2. Attribute Preservation**
Per-vertex attributes (normals $\vec{n}_i$, colors $c_i$) are preserved during conversion. Normals computed from mesh faces remain valid as point normals.

**3. Use Cases**
Useful as a preprocessing step when algorithms require point cloud input (e.g., registration, segmentation) but the source data is a mesh.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_processing.mesh_to_pointcloud")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_processing.mesh_to_pointcloud --input ... --output ...`.

**Defaults validated on:** Stanford bunny and armadillo (Open3D data); generated meshes in tests/test_ops_smoke.py

No tunable parameters.

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("point_cloud_processing")` prints this module from the installed package; `pl.describe("point_cloud_processing.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/point_cloud_processing.json` and `_defaults.json` on 2026-10-16.</sub>
