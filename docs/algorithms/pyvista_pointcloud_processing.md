---
title: "PyVista Point Cloud Processing (pyvista_pointcloud_processing): 5 methods in Python"
description: "Point cloud and mesh filtering operations via PyVista: thresholding, clipping by plane/box, random sampling, and scalar-based point extraction"
---

# PyVista Point Cloud Processing

`pyvista_pointcloud_processing`: Point cloud and mesh filtering operations via PyVista: thresholding, clipping by plane/box, random sampling, and scalar-based point extraction.

| | |
|---|---|
| Methods | [`pv_threshold`](#pv_threshold), [`pv_clip_plane`](#pv_clip_plane), [`pv_clip_box`](#pv_clip_box), [`pv_random_sample`](#pv_random_sample), [`pv_extract_points`](#pv_extract_points) |
| Input files | `.ply`, `.pcd`, `.vtk`, `.vtu`, `.obj`, `.stl` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run pyvista_pointcloud_processing.<method> input.ext [--param value]` |

## How it works

PyVista provides spatial and scalar filtering for point data:

**Threshold** keeps points/cells within a scalar range.
**Clip** removes geometry on one side of a plane.
**Clip Box** crops to a bounding box.
**Random Sampling** reduces data by random selection.
**Extract Points** selects points matching scalar criteria.

## Methods

### pv_threshold

Keeps cells whose scalar values satisfy $l \leq s_i \leq u$ for lower bound $l$ and upper bound $u$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_pointcloud_processing.pv_threshold")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_pointcloud_processing.threshold --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `lower` | float | `0.0` | -10000000000.0 to 10000000000.0 | Lower scalar bound. | 0 and upper 1 select a normalised scalar range; set them to your field's units (HU, reflectance). |
| `upper` | float | `1.0` | -10000000000.0 to 10000000000.0 | Upper scalar bound. | 1, see lower. |
| `scalars` | string | `""` |  | Scalar array name (empty = active scalars). | Empty uses the active scalar array, which is what a freshly loaded file has. |
| `invert` *(advanced)* | bool | `false` |  | Invert the threshold (keep values OUTSIDE the range). | Off: keep what is inside the range. |
| `continuous` *(advanced)* | bool | `false` |  | Use continuous cell range: include cells whose scalar range overlaps [lower, upper]. | Off: a cell is kept on its own scalar, not on the range it spans. |
| `preference` *(advanced)* | enum | `cell` | `cell`, `point` | Whether to threshold on cell or point scalars when both exist. | cell: VTK's default when both point and cell scalars exist. |
| `all_scalars` *(advanced)* | bool | `false` |  | Require all points of a cell to satisfy the criterion (else any point). | Off: a cell is kept if any of its points pass, which keeps boundaries intact. |
| `component_mode` *(advanced)* | enum | `all` | `all`, `any`, `component` | For multi-component scalars: test all components, any component, or a single one. | all: every component of a vector scalar must pass. |
| `component` *(advanced)* | int | `0` | 0 to 100 | Component index to threshold when component_mode='component'. | 0: the first component when component_mode is component. |

### pv_clip_plane

Removes all geometry on the negative side of the plane $\mathbf{n} \cdot (\mathbf{x} - \mathbf{o}) = 0$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_pointcloud_processing.pv_clip_plane")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_pointcloud_processing.clip_plane --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `origin_x` | float | `0.0` | -10000000000.0 to 10000000000.0 | Plane origin X. | 0: the plane passes through the origin by default; set it to a point on the cut you want. |
| `origin_y` | float | `0.0` | -10000000000.0 to 10000000000.0 | Plane origin Y. | 0, see origin_x. |
| `origin_z` | float | `0.0` | -10000000000.0 to 10000000000.0 | Plane origin Z. | 0, see origin_x. |
| `normal_x` | float | `1.0` | -1.0 to 1.0 | Plane normal X. | 1: cut perpendicular to x by default. |
| `normal_y` | float | `0.0` | -1.0 to 1.0 | Plane normal Y. | 0, see normal_x. |
| `normal_z` | float | `0.0` | -1.0 to 1.0 | Plane normal Z. | 0, see normal_x. |
| `invert` *(advanced)* | bool | `true` |  | Which side to keep. True (default) keeps the side the normal points away from. | On keeps the side the normal points away from, VTK's convention for clip. |
| `value` *(advanced)* | float | `0.0` | -10000000000.0 to 10000000000.0 | Scalar offset of the clip plane along the normal. | 0: no offset along the normal. |
| `crinkle` *(advanced)* | bool | `false` |  | Keep whole cells crossed by the plane instead of cutting them (crinkle clip). | Off: cells crossed by the plane are cut, giving a flat face; on keeps them whole, which preserves the original cells. |

### pv_clip_box

Keeps geometry inside the axis-aligned box $[x_{min}, x_{max}] \times [y_{min}, y_{max}] \times [z_{min}, z_{max}]$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_pointcloud_processing.pv_clip_box")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_pointcloud_processing.clip_box --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `x_min` | float | `-0.5` | -10000000000.0 to 10000000000.0 | Box X minimum. | -0.5 to 0.5 is a unit box around the origin, the placeholder for normalised data; set the box in file units. |
| `x_max` | float | `0.5` | -10000000000.0 to 10000000000.0 | Box X maximum. | 0.5, see x_min. |
| `y_min` | float | `-0.5` | -10000000000.0 to 10000000000.0 | Box Y minimum. | -0.5, see x_min. |
| `y_max` | float | `0.5` | -10000000000.0 to 10000000000.0 | Box Y maximum. | 0.5, see x_min. |
| `z_min` | float | `-0.5` | -10000000000.0 to 10000000000.0 | Box Z minimum. | -0.5, see x_min. |
| `z_max` | float | `0.5` | -10000000000.0 to 10000000000.0 | Box Z maximum. | 0.5, see x_min. |
| `invert` *(advanced)* | bool | `false` |  | Invert the box selection (keep geometry OUTSIDE the box). | Off: keep the inside of the box. |
| `merge_points` *(advanced)* | bool | `true` |  | Merge coincident points in the clipped output. | On: coincident points created by the clip are merged. |
| `crinkle` *(advanced)* | bool | `false` |  | Keep whole cells crossed by the box instead of cutting them (crinkle clip). | Off: cut the crossed cells. |

### pv_random_sample

Uniformly samples a fraction $f$ of the input points without replacement.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_pointcloud_processing.pv_random_sample")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_pointcloud_processing.random_sample --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `fraction` | float | `0.5` | 0.01 to 1.0 | Fraction of points to keep (0-1). | 0.5 halves a cloud, the usual first step before an interactive look at a multi-million-point scan. |
| `replace` *(advanced)* | bool | `false` |  | Sample with replacement (allows duplicate picks). | Off: no duplicate picks. |
| `seed` *(advanced)* | int | `-1` | -1 to 2147483647 | RNG seed for reproducibility; -1 = no seeding (non-deterministic, original behavior). | -1 is non-deterministic, matching the original script; set a seed for reproducible figures. |
| `adjacent_cells` *(advanced)* | bool | `true` |  | Include cells that contain at least one selected point (else only fully-selected cells). | On: cells touching a selected point are kept so meshes stay connected. |
| `include_cells` *(advanced)* | bool | `true` |  | Carry cells through to the output (else points only). | On: carry cells through. |

### pv_extract_points

Selects points whose scalar values lie within a specified range, producing a filtered point cloud.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_pointcloud_processing.pv_extract_points")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_pointcloud_processing.extract_points --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `scalars` | string | `""` |  | Scalar array name (empty = active scalars). | Empty uses the active scalars. |
| `lower` | float | `0.0` | -10000000000.0 to 10000000000.0 | Lower bound for extraction. | 0 with upper 1 is a normalised range placeholder. |
| `upper` | float | `1.0` | -10000000000.0 to 10000000000.0 | Upper bound for extraction. | 1, see lower. |
| `adjacent_cells` *(advanced)* | bool | `true` |  | Include cells that contain at least one selected point (else only fully-selected cells). | On keeps connectivity. |
| `include_cells` *(advanced)* | bool | `true` |  | Carry cells through to the output (else points only). | On carries cells through. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("pyvista_pointcloud_processing")` prints this module from the installed package; `pl.describe("pyvista_pointcloud_processing.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/pyvista_pointcloud_processing.json` and `_defaults.json` on 2026-10-17.</sub>
