---
title: "LiDAR Scene Analysis (lidar_scene_detection): 3 methods in Python"
description: "Analyze LiDAR-style point clouds: height-based colorization, ground plane removal, and object clustering for autonomous driving and robotics applicati"
---

# LiDAR Scene Analysis

`lidar_scene_detection`: Analyze LiDAR-style point clouds: height-based colorization, ground plane removal, and object clustering for autonomous driving and robotics applications.

| | |
|---|---|
| Methods | [`height_colorization`](#height_colorization), [`ground_removal`](#ground_removal), [`object_clustering`](#object_clustering) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz`, `.las` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| Example | [Ground removal and clustering on KITTI](../examples.md#kitti_lidar_ground_and_objects) |
| CLI | `pardesline run lidar_scene_detection.<method> input.ext [--param value]` |

## How it works

LiDAR (Light Detection and Ranging) sensors produce dense 3D point clouds of the environment. Processing these point clouds is fundamental to autonomous driving, robotics, and mapping.

Key operations include:
- **Height colorization**: Mapping the Z-coordinate to color for visual analysis
- **Ground removal**: Fitting a plane to the ground surface and removing it
- **Object clustering**: Grouping non-ground points into individual objects

Ground removal typically uses RANSAC to fit a plane $ax + by + cz + d = 0$ where the normal is approximately vertical ($c \approx 1$). Non-ground points are then clustered using DBSCAN to identify individual objects.

## Methods

### height_colorization

Points are colored based on their Z-coordinate (height) using a gradient:
$$c_i = \text{colormap}\left(\frac{z_i - z_{\min}}{z_{\max} - z_{\min}}\right)$$

This reveals terrain structure, building heights, and vegetation layers in the scene.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_scene_detection.height_colorization")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_scene_detection.height_colorization --input ... --output ...`.

**Defaults validated on:** KITTI sweeps (examples/kitti_lidar_ground_and_objects); generated clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `colormap` | int | `0` | 0 to 3 | Colormap: 0=height gradient, 1=viridis, 2=plasma, 3=turbo | 0 (height gradient) maps the sensor z axis directly to colour, which is how LiDAR engineers read a sweep. |

### ground_removal

RANSAC fits a ground plane and removes points within a threshold:
1. Fit plane $ax + by + cz + d = 0$ using RANSAC
2. Compute distance $d_i = |ax_i + by_i + cz_i + d| / \sqrt{a^2+b^2+c^2}$
3. Remove points where $d_i < \epsilon$ (ground points)

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_scene_detection.ground_removal")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_scene_detection.ground_removal --input ... --output ...`.

**Defaults validated on:** KITTI Velodyne HDL-64E sweeps, sensor frame, metres (examples/kitti_lidar_ground_and_objects)

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `distance_threshold` | float | `0.3` | 0.01 to 2.0 | Distance threshold for ground plane inliers. | 0.3 m: a road is not flat over a 100 m sweep (camber, slope, curb), so a 30 cm band keeps the whole surface as ground while a car's lowest points (sills at 0.4-0.5 m) stay out; lower to 0.1 m for indoor floors. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 10 | Points sampled per RANSAC iteration. | 3 points define the plane. |
| `num_iterations` *(advanced)* | int | `1000` | 100 to 10000 | RANSAC iterations. | 1 000 iterations are plenty when the ground holds 30-50 % of a sweep's points. |

### object_clustering

After ground removal, non-ground points are clustered using DBSCAN:
1. Remove ground plane
2. Apply DBSCAN with parameters $(\epsilon, n_{\min})$
3. Each cluster represents a potential object
4. Filter clusters by minimum size

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("lidar_scene_detection.object_clustering")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.lidar_scene_detection.object_clustering --input ... --output ...`.

**Defaults validated on:** KITTI sweeps: 35 476 points clustered into cars, poles, walls after ground removal (examples/kitti_lidar_ground_and_objects)

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `ground_threshold` | float | `0.3` | 0.01 to 2.0 | Distance threshold for ground removal before clustering. | 0.3 m, as in ground_removal: the band that follows a real road's camber and slope. |
| `cluster_eps` | float | `0.5` | 0.1 to 5.0 | DBSCAN epsilon for object clustering. | 0.5 m: the HDL-64E spacing between rings reaches 0.3-0.5 m at 30 m, so a smaller epsilon splits one car into ring-stripes; a larger one merges parked cars. |
| `min_cluster_points` | int | `10` | 3 to 100 | Minimum points to form a cluster. | 10 points keep ring fragments and speckle out while a pedestrian at 20 m (about 15-30 points) still clusters. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 10 | Points sampled per RANSAC iteration. | 3 points define the ground plane. |
| `num_iterations` *(advanced)* | int | `1000` | 100 to 10000 | Ground-plane RANSAC iterations. | 1 000 ground-plane iterations. |
| `print_progress` *(advanced)* | bool | `false` |  | Print DBSCAN progress. | Off: terminal output only. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("lidar_scene_detection")` prints this module from the installed package; `pl.describe("lidar_scene_detection.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/lidar_scene_detection.json` and `_defaults.json` on 2026-10-17.</sub>
