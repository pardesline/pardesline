---
title: "Collision Detection & Measurement (collision_detection): 2 methods in Python"
description: "Detect and measure collisions between 3D geometries using SDF-based penetration analysis"
---

# Collision Detection & Measurement

`collision_detection`: Detect and measure collisions between 3D geometries using SDF-based penetration analysis. Computes penetration depth, collision region, and bounding box intersection.

| | |
|---|---|
| Methods | [`sdf_collision`](#sdf_collision), [`penetration_depth`](#penetration_depth) |
| Input files | `.ply`, `.obj`, `.stl`, `.off` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run collision_detection.<method> input.ext [--param value]` |

## How it works

Collision detection between 3D objects can be performed using Signed Distance Fields (SDF). Given a static mesh $S$ and a moving mesh $M$, we sample points on $M$ and compute their signed distance to $S$:


$$
d(p) = \text{SDF}_S(p), \quad p \in M
$$


Points where $d(p) < 0$ lie inside the static mesh, indicating collision. The penetration depth is:


$$
\delta = \max_{p \in M} |\min(d(p), 0)|
$$


This approach is robust for arbitrary mesh geometries and provides continuous penetration measurements.

## Methods

### sdf_collision

Samples points uniformly on the input mesh surface, then creates a synthetic obstacle (sphere) and computes the SDF of the input points against the obstacle.

Penetrating points satisfy $\text{SDF}(p) < 0$. The collision region is visualized by coloring points by their signed distance: red (deep penetration) to blue (no contact).

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("collision_detection.sdf_collision")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.collision_detection.sdf_collision --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `obstacle_radius` | float | `0.5` | 0.1 to 5.0 | Radius of the synthetic obstacle sphere. | 0.5 in file units: a sphere half the size of a unit object, the demo obstacle. |
| `penetration_ratio` | float | `0.3` | 0.05 to 0.8 | Fraction of obstacle radius for penetration overlap. | 0.3: the obstacle is placed so that 30 % of its radius overlaps the part, enough to show a clear collision patch. |
| `num_samples` | int | `50000` | 5000 to 200000 | Number of surface sample points for SDF evaluation. | 50 000 surface samples give a dense signed-distance map on the part in under a second. |
| `obstacle_resolution` *(advanced)* | int | `50` | 4 to 200 | Sphere tessellation resolution for the synthetic obstacle mesh. | 50 tessellation steps make the sphere smooth enough that its SDF has no facet artefacts. |
| `obstacle_viz_points` *(advanced)* | int | `5000` | 100 to 100000 | Points sampled on the obstacle for visualization. | 5 000 points draw the obstacle without hiding the part. |
| `colormap` *(advanced)* | string | `coolwarm` |  | Matplotlib colormap used to color points by signed distance. | coolwarm is diverging around zero distance: red inside the obstacle, blue outside. |

### penetration_depth

Computes the maximum penetration depth between the input geometry and a synthetic obstacle:

$$\delta = |\min_i \text{SDF}(p_i)|$$

Also computes the bounding box of the collision region and outputs a combined point cloud showing the penetration zone with color-coded depth.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("collision_detection.penetration_depth")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.collision_detection.penetration_depth --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `obstacle_radius` | float | `0.5` | 0.1 to 5.0 | Radius of the synthetic obstacle sphere. | 0.5 in file units, the demo obstacle. |
| `overlap_distance` | float | `0.15` | 0.01 to 2.0 | Distance the obstacle overlaps with the input geometry. | 0.15 in file units: the obstacle overlaps the part by 15 % of a unit object. |
| `num_samples` *(advanced)* | int | `50000` | 5000 to 200000 | Number of surface sample points for SDF evaluation. | 50 000 surface samples. |
| `obstacle_resolution` *(advanced)* | int | `50` | 4 to 200 | Sphere tessellation resolution for the synthetic obstacle mesh. | 50 tessellation steps make the sphere smooth enough that its SDF has no facet artefacts. |
| `colormap` *(advanced)* | string | `hot` |  | Matplotlib colormap used to color penetrating points by depth. | hot maps zero depth to black and the deepest penetration to white. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("collision_detection")` prints this module from the installed package; `pl.describe("collision_detection.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/collision_detection.json` and `_defaults.json` on 2026-10-17.</sub>
