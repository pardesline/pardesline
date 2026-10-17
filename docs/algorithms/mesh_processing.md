---
title: "Mesh Processing (mesh_processing): 4 methods in Python"
description: "Triangle mesh operations: subdivision, simplification, and conversion to point clouds via uniform or Poisson-disk sampling"
---

# Mesh Processing

`mesh_processing`: Triangle mesh operations: subdivision, simplification, and conversion to point clouds via uniform or Poisson-disk sampling.

| | |
|---|---|
| Methods | [`subdivision`](#subdivision), [`simplification`](#simplification), [`mesh_to_pcd_uniform`](#mesh_to_pcd_uniform), [`mesh_to_pcd_poisson_disk`](#mesh_to_pcd_poisson_disk) |
| Input files | `.ply`, `.obj`, `.stl`, `.off` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| Example | [Gaussian splats on the Stanford bunny](../examples.md#points_to_gaussians_bunny) |
| CLI | `pardesline run mesh_processing.<method> input.ext [--param value]` |

## How it works

Mesh processing operates on triangle meshes $\mathcal{M} = (V, F)$. Key operations include:

**Subdivision** increases mesh resolution by splitting triangles. Midpoint subdivision inserts new vertices at edge midpoints, quadrupling the face count per iteration.

**Simplification** reduces complexity using Quadric Error Metrics (QEM) which iteratively collapses edges minimizing $\Delta(v) = v^T Q v$.

**Mesh-to-Point-Cloud sampling** converts surfaces to point sets via uniform or Poisson-disk sampling.

## Methods

### subdivision

Midpoint subdivision splits each edge at its midpoint creating 4 new triangles from each original. After $k$ iterations: $|F| \cdot 4^k$ faces.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("mesh_processing.subdivision")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.mesh_processing.subdivision --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `iterations` | int | `1` | 1 to 4 | Number of subdivision iterations. | 1 iteration quadruples the triangle count; two or more are rarely needed before smoothing and make files large quickly. |

### simplification

Quadric Error Metrics decimation collapses edges in order of increasing cost $v^T (Q_a + Q_b) v$ until the target triangle count is reached.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("mesh_processing.simplification")  # catalog defaults
# same thing, domain vocabulary: `mesh.decimate()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.mesh_processing.simplification --input ... --output ...`.

**Defaults validated on:** Stanford bunny (examples/hippocampus_mask_to_mesh uses the PyVista decimation instead); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `target_triangles` | int | `5000` | 100 to 100000 | Target number of triangles. | 5 000 triangles is the size at which an organ or part surface still looks right on screen and loads instantly in a viewer; raise it for metrology. |
| `maximum_error` *(advanced)* | float | `1e+30` | 0.0 to 1e+30 | Advisory maximum quadric error allowed per edge collapse (very large = unbounded, matches default behavior). | Unbounded (1e30) matches Open3D's behaviour: the decimation stops at the triangle budget, not at an error threshold, so the result is predictable in size. |
| `boundary_weight` *(advanced)* | float | `1.0` | 0.0 to 100.0 | Weight applied to boundary edges during decimation. | 1.0 treats boundary edges like interior ones; raise it on open meshes (scans with holes) so the boundary does not shrink. |

### mesh_to_pcd_uniform

Points are sampled uniformly, each triangle receiving samples proportional to its area $A_i$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("mesh_processing.mesh_to_pcd_uniform")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.mesh_processing.mesh_to_pcd_uniform --input ... --output ...`.

**Defaults validated on:** Stanford bunny (examples/points_to_gaussians_bunny); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `num_points` | int | `5000` | 100 to 100000 | Number of points to sample. | 5 000 points keep registration and clustering fast while covering a surface; the examples use 20 000-50 000 for visual density. |
| `use_triangle_normal` *(advanced)* | bool | `false` |  | Assign each sampled point the normal of its source triangle instead of an interpolated vertex normal. | Off: interpolated vertex normals are smoother on organic surfaces; turn on for CAD meshes with flat faces. |
| `seed` *(advanced)* | int | `-1` | -1 to 2147483647 | Random seed for sampling (-1 = nondeterministic). | -1 (non-deterministic) is Open3D's default; set a seed when a result must be reproducible, as the examples do. |

### mesh_to_pcd_poisson_disk

Blue-noise sampling where no two samples are closer than minimum distance $r$, producing more uniform coverage.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("mesh_processing.mesh_to_pcd_poisson_disk")  # catalog defaults
# same thing, domain vocabulary: `mesh.to_points(num_points=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.mesh_processing.mesh_to_pcd_poisson_disk --input ... --output ...`.

**Defaults validated on:** Stanford bunny (examples/poisson_reconstruction_bunny, examples/icp_registration_bunny); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `num_points` | int | `5000` | 100 to 100000 | Approximate number of points. | 5 000 is the approximate count after elimination: Poisson-disk sampling gives evenly spaced points, which is what registration features and PointNet training want. |
| `init_factor` *(advanced)* | int | `5` | 1 to 20 | Initial uniform-sample oversampling factor before elimination. | 5x oversampling before elimination is Open3D's recommendation: enough candidates for an even blue-noise distribution without a long elimination pass. |
| `use_triangle_normal` *(advanced)* | bool | `false` |  | Assign each sampled point the normal of its source triangle instead of an interpolated vertex normal. | Off: interpolated normals; on for flat-faced CAD meshes. |
| `seed` *(advanced)* | int | `-1` | -1 to 2147483647 | Random seed for sampling (-1 = nondeterministic). | -1 is non-deterministic; the examples pass seed=1 for reproducible figures. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("mesh_processing")` prints this module from the installed package; `pl.describe("mesh_processing.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/mesh_processing.json` and `_defaults.json` on 2026-10-17.</sub>
