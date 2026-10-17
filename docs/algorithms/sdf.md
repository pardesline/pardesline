---
title: "Signed Distance Fields (sdf): 3 methods in Python"
description: "Compute and visualize Signed Distance Fields from meshes"
---

# Signed Distance Fields

`sdf`: Compute and visualize Signed Distance Fields from meshes. Foundation for implicit surface representations, marching cubes reconstruction, and neural SDFs.

| | |
|---|---|
| Methods | [`compute_sdf`](#compute_sdf), [`occupancy_reconstruction`](#occupancy_reconstruction), [`sdf_voxel_visualization`](#sdf_voxel_visualization) |
| Input files | `.ply`, `.obj`, `.stl`, `.off` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run sdf.<method> input.ext [--param value]` |

## How it works

A Signed Distance Field (SDF) is a scalar function $f: \mathbb{R}^3 \to \mathbb{R}$ that returns the signed distance from any point $x$ to the closest surface point:


$$
f(x) = \text{sign}(x) \cdot \min_{y \in S} \|x - y\|
$$


where $f(x) < 0$ inside the surface, $f(x) > 0$ outside, and $f(x) = 0$ on the surface $S$ itself. The zero level-set $\{x : f(x) = 0\}$ implicitly defines the surface.

SDFs have several key properties:
- The gradient $\nabla f(x)$ points in the direction of steepest distance increase
- $\|\nabla f(x)\| = 1$ almost everywhere (Eikonal equation)
- Boolean operations become simple min/max on SDF values:

$$
\text{Union:} \min(f_A, f_B), \quad \text{Intersection:} \max(f_A, f_B), \quad \text{Difference:} \max(f_A, -f_B)
$$


## Methods

### compute_sdf

**1. SDF Computation**
The SDF is computed using Open3D's RaycastingScene which casts rays to determine signed distance. Query points are placed on a regular 3D grid covering the mesh bounding box with padding.

For a grid with voxel size $v$ and padding $p$, the query points are:
$$Q = \{(x_0 + iv, y_0 + jv, z_0 + kv) : 0 \leq i,j,k < N\}$$

where $(x_0, y_0, z_0)$ is the padded minimum bound.

**2. Marching Cubes**
The surface is reconstructed at the zero-level set $\{x : f(x) = 0\}$ using the Marching Cubes algorithm (Lorensen & Cline, 1987). Each voxel cube is classified by the signs of its 8 corner SDF values, producing 256 possible configurations mapped to triangle meshes via a lookup table.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("sdf.compute_sdf")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.sdf.compute_sdf --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.01` | 0.002 to 0.05 | Voxel size for the SDF grid. Smaller = more detail but slower. | 0.01 in file units for a 100-voxel grid on a unit object; the SDF cost grows with the cube of the resolution. |
| `padding` | int | `5` | 1 to 20 | Number of padding voxels around the bounding box. | 5 voxels of margin so the zero level set is closed inside the grid. |
| `level` *(advanced)* | float | `0.0` | -0.05 to 0.05 | Iso-level for surface extraction. | 0.0 is the surface itself (zero signed distance); offset it to inflate or shrink the mesh. |
| `mc_step_size` *(advanced)* | int | `1` | 1 to 5 | Marching-cubes voxel step (coarser = faster). | 1 samples every voxel; a larger step is a quick coarse preview. |
| `mc_method` *(advanced)* | enum | `lewiner` | `lewiner`, `lorensen` | Marching-cubes algorithm variant. | Lewiner marching cubes resolves the ambiguous cases that the original Lorensen tables get wrong on thin structures. |
| `mc_gradient_direction` *(advanced)* | enum | `descent` | `descent`, `ascent` | Surface-interior interpretation for normals. | descent orients normals so that the inside is negative distance, which is the convention of the SDF grid. |
| `mc_allow_degenerate` *(advanced)* | bool | `true` |  | Allow degenerate output triangles. | On, matching scikit-image: degenerate triangles are removed later by the mesh cleaning step rather than by rejecting the surface. |

### occupancy_reconstruction

Occupancy testing determines whether query points lie inside or outside a watertight mesh. The occupancy function $o: \mathbb{R}^3 \to \{0, 1\}$ is:
$$o(x) = \begin{cases} 1 & \text{if } x \text{ is inside } S \\ 0 & \text{otherwise} \end{cases}$$

The boundary is extracted using marching cubes at iso-value 0.5.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("sdf.occupancy_reconstruction")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.sdf.occupancy_reconstruction --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.01` | 0.002 to 0.05 | Voxel size for the occupancy grid. | Same grid as compute_sdf for comparable results. |
| `padding` | int | `5` | 1 to 20 | Number of padding voxels around the bounding box. | 5 voxels of margin around the bounding box. |
| `level` *(advanced)* | float | `0.5` | 0.1 to 0.9 | Iso-value for occupancy boundary. | 0.5 is the half-occupancy boundary of a binary occupancy grid. |
| `mc_step_size` *(advanced)* | int | `1` | 1 to 5 | Marching-cubes voxel step (coarser = faster). | 1 samples every voxel. |
| `mc_method` *(advanced)* | enum | `lewiner` | `lewiner`, `lorensen` | Marching-cubes algorithm variant. | Lewiner resolves ambiguous cube cases. |
| `mc_gradient_direction` *(advanced)* | enum | `descent` | `descent`, `ascent` | Surface-interior interpretation for normals. | descent keeps normals pointing outward for occupancy grids. |
| `mc_allow_degenerate` *(advanced)* | bool | `true` |  | Allow degenerate output triangles. | On, matching scikit-image. |

### sdf_voxel_visualization

**1. Signed Distance Function**
The SDF is sampled on a regular 3D grid of resolution $N^3$. For each voxel center $x_i$, the signed distance is computed:
$$d_i = f(x_i) = \text{sign}(x_i) \cdot \min_{y \in S} \|x_i - y\|$$

**2. Distance Clamping**
SDF values are clamped to a user-defined range $[d_{\min}, d_{\max}]$ to focus on the near-surface region:
$$\hat{d}_i = \text{clamp}(d_i, d_{\min}, d_{\max})$$

This truncation is the basis for Truncated SDFs (TSDFs), widely used in real-time 3D reconstruction (KinectFusion, Curless & Levoy 1996).

**3. Colormap Encoding**
The clamped distances are normalized to $[0, 1]$ and mapped to a diverging colormap (coolwarm):
- Blue ($d < 0$): interior of the surface
- White ($d \approx 0$): on or near the surface
- Red ($d > 0$): exterior of the surface

**4. Connection with Collision Detection**
The SDF provides constant-time collision queries: a point $x$ collides with the surface if $f(x) \leq 0$. The penetration depth is $|f(x)|$ and the normal direction is $\nabla f(x)$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("sdf.sdf_voxel_visualization")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.sdf.sdf_voxel_visualization --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `resolution` | int | `32` | 8 to 128 | Grid resolution per axis. Higher = more detail. Total voxels = resolution^3. | 32 voxels per axis (32 768 cells) renders in a second and still shows the shape of the field; it is a visualisation, not the SDF you compute with. |
| `min_clamp` | float | `-0.1` | -1.0 to 0.0 | Minimum SDF clamp value (interior threshold). | -0.1 clamps the interior so colours stay readable near the surface instead of saturating at the object centre. |
| `max_clamp` | float | `0.1` | 0.0 to 1.0 | Maximum SDF clamp value (exterior threshold). | 0.1 clamps the exterior for the same reason. |
| `padding_factor` *(advanced)* | float | `0.15` | 0.0 to 1.0 | Bbox padding as a fraction of the max extent. | 15 % of the extent as margin shows the field decaying outside the object. |
| `colormap` *(advanced)* | string | `coolwarm` |  | Matplotlib diverging colormap (coolwarm, bwr, seismic, RdBu). | coolwarm is diverging around zero, which is what a signed field needs: blue inside, red outside. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("sdf")` prints this module from the installed package; `pl.describe("sdf.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/sdf.json` and `_defaults.json` on 2026-10-17.</sub>
