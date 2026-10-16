---
title: "LiDAR-Camera Fusion (lidar_camera_fusion): 3 methods in Python"
description: "Sensor fusion operations: distance-based colorization, region-of-interest extraction, and multi-resolution analysis for combined LiDAR and camera proc"
---

# LiDAR-Camera Fusion

`lidar_camera_fusion`: Sensor fusion operations: distance-based colorization, region-of-interest extraction, and multi-resolution analysis for combined LiDAR and camera processing.

| | |
|---|---|
| Methods | [`intensity_colorization`](#intensity_colorization), [`roi_extraction`](#roi_extraction), [`multi_resolution`](#multi_resolution) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz`, `.las` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| CLI | `pardesline run lidar_camera_fusion.<method> input.ext [--param value]` |

## How it works

LiDAR-Camera fusion combines 3D point cloud data with 2D imagery. A 3D point $P = (X,Y,Z)$ projects to pixel $(u,v)$ via:

$$
\begin{pmatrix} u \\ v \\ 1 \end{pmatrix} = \frac{1}{Z} K [R|t] \begin{pmatrix} X \\ Y \\ Z \\ 1 \end{pmatrix}
$$


## Methods

### intensity_colorization

Points colored by distance from origin using a selected colormap.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_camera_fusion.intensity_colorization")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_camera_fusion.intensity_colorization --input ... --output ...`.

**Defaults validated on:** KITTI sweeps carry reflectance in the fourth column (manifest layout); generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `colormap` | int | `0` | 0 to 3 | 0=jet, 1=viridis, 2=inferno, 3=coolwarm | 0 (jet) for reflectance: lane paint and plates saturate to red, asphalt stays blue, which is what people look for in an intensity view. |

### roi_extraction

Extract a sub-volume defined by axis-aligned percentage bounds.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_camera_fusion.roi_extraction")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_camera_fusion.roi_extraction --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `x_range` | float | `0.5` | 0.0 to 1.0 | % of X-range to keep (centered). | Keep the central 50 % along x: the near field in front of and behind the sensor, where the camera overlap is. |
| `y_range` | float | `0.5` | 0.0 to 1.0 | % of Y-range to keep (centered). | Keep the central 50 % along y: the lane and its neighbours. |
| `z_range` | float | `0.8` | 0.0 to 1.0 | % of Z-range to keep (centered). | Keep 80 % along z: drops only the extreme returns (tree tops, below-ground reflections). |

### multi_resolution

Near regions use fine voxels, far regions use coarse voxels.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_camera_fusion.multi_resolution")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_camera_fusion.multi_resolution --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `levels` | int | `3` | 1 to 5 | Number of resolution levels. | 3 levels (base, 2x, 4x) are what multi-scale registration and visualisation consume. |
| `base_voxel_size` | float | `0.01` | 0.001 to 0.5 | Finest voxel size (level 0). | 0.01 in file units at the finest level, matching voxel_downsample's default. |
| `voxel_growth_factor` *(advanced)* | float | `2.0` | 1.1 to 10.0 | Per-level voxel-size multiplier base (voxel = base * factor**level). | 2x per level: the standard octave pyramid. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("lidar_camera_fusion")` prints this module from the installed package; `pl.describe("lidar_camera_fusion.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/lidar_camera_fusion.json` and `_defaults.json` on 2026-10-16.</sub>
