---
title: "Stereo & Depth Estimation (stereo_3d_reconstruction): 2 methods in Python"
description: "Depth-based point cloud analysis: colorize by depth, filter by depth range"
---

# Stereo & Depth Estimation

`stereo_3d_reconstruction`: Depth-based point cloud analysis: colorize by depth, filter by depth range. Foundation for stereo vision and 3D reconstruction from camera images.

| | |
|---|---|
| Methods | [`depth_colorization`](#depth_colorization), [`depth_filter`](#depth_filter) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| CLI | `pardesline run stereo_3d_reconstruction.<method> input.ext [--param value]` |

## How it works

Stereo vision reconstructs 3D structure from camera views. The fundamental relationship between depth $Z$, disparity $d$, focal length $f$, and baseline $B$ is:

$$
Z = \frac{f \cdot B}{d}
$$


A 3D point $\mathbf{X} = (X, Y, Z)^T$ in world coordinates projects to pixel $(u, v)$ via the camera intrinsic matrix $K$:

$$
\begin{pmatrix} u \\ v \\ 1 \end{pmatrix} = \frac{1}{Z} K \mathbf{X}, \quad K = \begin{pmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{pmatrix}
$$


For point cloud analysis, depth-based operations include colorization by Euclidean distance and depth-range filtering for region-of-interest extraction.

## Methods

### depth_colorization

**1. Distance Computation**
For each point $p_i$ in the cloud, the Euclidean distance from the origin (camera center) is computed:
$$d_i = \|p_i - \mathbf{o}\|_2 = \sqrt{x_i^2 + y_i^2 + z_i^2}$$

**2. Normalization and Colormap**
Distances are normalized to $[0, 1]$ and mapped through a perceptually uniform colormap (jet, viridis, plasma, or turbo):
$$c_i = \text{colormap}\left(\frac{d_i - d_{\min}}{d_{\max} - d_{\min}}\right)$$

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("stereo_3d_reconstruction.depth_colorization")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.stereo_3d_reconstruction.depth_colorization --input ... --output ...`.

**Defaults validated on:** generated depth clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `colormap` | int | `0` | 0 to 3 | Colormap: 0=jet, 1=viridis, 2=plasma, 3=turbo | 0 (jet) is what stereo and depth tooling has used for decades, so the colours are readable at a glance; the others are perceptually uniform alternatives. |

### depth_filter

**1. Percentile-Based Filtering**
Instead of absolute depth thresholds, the filter uses percentiles of the distance distribution for robustness across different scales:
$$P_{\text{keep}} = \{p_i : q_{\min} \leq d_i \leq q_{\max}\}$$
where $q_{\min}, q_{\max}$ are the `min_depth` and `max_depth` percentiles of $\{d_i\}$.

**2. Application**
Useful for removing background points (far range) or ground plane (near range) in LiDAR and depth camera data.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("stereo_3d_reconstruction.depth_filter")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.stereo_3d_reconstruction.depth_filter --input ... --output ...`.

**Defaults validated on:** generated depth clouds in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `min_depth` | float | `0.1` | 0.0 to 1.0 | Lower depth percentile (0-1 fraction). | Dropping the nearest 10 % removes the lens-edge and occlusion artefacts stereo matching produces close to the camera. |
| `max_depth` | float | `0.9` | 0.0 to 1.0 | Upper depth percentile (0-1 fraction). | Dropping the farthest 10 % removes the sky and the far-range noise where disparity is below one pixel. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("stereo_3d_reconstruction")` prints this module from the installed package; `pl.describe("stereo_3d_reconstruction.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/stereo_3d_reconstruction.json` and `_defaults.json` on 2026-10-10.</sub>
