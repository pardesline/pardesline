---
title: "Point Cloud Segmentation (point_cloud_segmentation): 2 methods in Python"
description: "Segment a point cloud into meaningful regions using geometric methods: RANSAC plane fitting and DBSCAN clustering"
---

# Point Cloud Segmentation

`point_cloud_segmentation`: Segment a point cloud into meaningful regions using geometric methods: RANSAC plane fitting and DBSCAN clustering.

| | |
|---|---|
| Methods | [`ransac_plane`](#ransac_plane), [`dbscan_clustering`](#dbscan_clustering) |
| Input files | `.ply`, `.pcd`, `.txt`, `.xyz` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md) |
| CLI | `pardesline run point_cloud_segmentation.<method> input.ext [--param value]` |

## How it works

Point cloud segmentation partitions a set of 3D points $P = \{p_1, \ldots, p_n\}$ into disjoint subsets corresponding to semantic or geometric regions.

RANSAC-based plane fitting iteratively fits a plane model $\vec{n} \cdot \vec{x} + d = 0$ to random point subsets.

DBSCAN groups points based on density: a point is a core point if it has at least $n_{\min}$ neighbors within radius $\epsilon$.

## Methods

### ransac_plane

RANSAC iteratively fits a plane model and identifies inliers within distance threshold $\epsilon$. Plane inliers are colored distinctly from outliers.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_segmentation.ransac_plane")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_segmentation.ransac_plane --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py; the same RANSAC plane model runs on KITTI in lidar_scene_detection

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `distance_threshold` | float | `0.01` | 0.001 to 0.1 | Maximum distance from point to plane for inlier. | 0.01 in file units: one centimetre on metre-scale indoor scans, which is the depth-camera noise level; use 0.2-0.3 m for outdoor LiDAR ground. |
| `num_iterations` | int | `1000` | 100 to 10000 | Number of RANSAC iterations. | 1 000 iterations find the dominant plane with probability above 0.99 when it holds at least 20 % of the points. |
| `ransac_n` *(advanced)* | int | `3` | 3 to 10 | Number of points sampled to estimate each plane candidate. | 3 points define a plane; the minimum keeps the inlier probability per draw highest. |
| `probability` *(advanced)* | float | `0.99999999` | 0 to 1 | Expected probability of finding the best plane (early-stop confidence). | 0.99999999 lets Open3D stop early once the best plane is almost certainly found, so the 1 000 iterations are a ceiling. |

### dbscan_clustering

DBSCAN groups points based on density. Given parameters $(\epsilon, n_{\min})$, connected core points form clusters. Each cluster gets a unique color.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("point_cloud_segmentation.dbscan_clustering")  # catalog defaults
# same thing, domain vocabulary: `points.segment(eps=..., min_points=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.point_cloud_segmentation.dbscan_clustering --input ... --output ...`.

**Defaults validated on:** generated clouds in tests/test_ops_smoke.py; KITTI sweeps through lidar_scene_detection.object_clustering

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `eps` | float | `0.02` | 0.001 to 0.5 | Maximum distance between two points in same cluster. | 0.02 in file units: two centimetres joins points of the same object on indoor depth scans; use 0.5 m outdoors (see object_clustering). |
| `min_points` | int | `10` | 3 to 100 | Minimum points to form a cluster. | 10 points keep speckle out of the cluster list while small objects (a cup, a hand) still form one. |
| `print_progress` *(advanced)* | bool | `false` |  | Print an Open3D progress bar during clustering. | Off: terminal output only. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("point_cloud_segmentation")` prints this module from the installed package; `pl.describe("point_cloud_segmentation.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/point_cloud_segmentation.json` and `_defaults.json` on 2026-10-17.</sub>
