---
title: "UniOcc, CARLA 10 Hz mini split: LiDAR sweeps, camera views and semantic occupancy grids"
description: "The smallest split of UniOcc (unified occupancy benchmark over nuScenes, Waymo, CARLA, OpenCOOD)"
---

# UniOcc, CARLA 10 Hz mini split: LiDAR sweeps, camera views and semantic occupancy grids

`pl.load("hf_uniocc_carla_mini")` loads this dataset. The smallest split of UniOcc (unified occupancy benchmark over nuScenes, Waymo, CARLA, OpenCOOD). Two CARLA scenes at 10 Hz; per time step a surround LiDAR sweep (.ply), four camera images, a bird's-eye view and an .npz with the 200x200x16 semantic occupancy grid, camera/LiDAR masks, voxel flow and the ego-to-world 4x4 transform. The other splits are folders of the same repo: pl.load('hf://tasl-lab/uniocc/NuScenes-via-Occ3D-2Hz-mini').

```python
import pardesline as pl

ds = pl.load("hf_uniocc_carla_mini")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.lidar  # fetched now, cached under ~/.cache/pardesline/datasets/hf_uniocc_carla_mini
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `tasl-lab/uniocc`, paths `Carla-10Hz-mini` |
| Scheme | `hf` |
| Size of the whole source | 4.9 GB |
| Licence | MIT |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | MIT on the Hub card (checked 2026-10-13). The nuScenes- and Waymo-derived splits of the same repo inherit the upstream terms of those datasets (non-commercial for nuScenes) - this manifest covers the CARLA split only. |
| Terms | <https://huggingface.co/datasets/tasl-lab/uniocc> |
| Homepage | <https://uniocc.github.io/> |
| Cite | Wang Y., Huang X., Sun X., Yan M., Xing S., Tu Z., Li J. UniOcc: A Unified Benchmark for Occupancy Forecasting and Prediction in Autonomous Driving. arXiv:2503.24381, 2025. |
| Samples grouped by | scene |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `lidar` | points | sensor | m |  | `Carla-10Hz-mini/{scene}/{frame}_surround_lidar.ply`<br>Surround LiDAR sweep in the ego-vehicle frame |
| `occupancy` | labels | from the file header | from the file header | layout:  (200,200,16) | `Carla-10Hz-mini/{scene}/{frame}.npz`<br>Semantic occupancy grid 200x200x16 (L, W, H), class ids per the UniOcc repo; voxel size and grid origin are not stated on the card, so the grid is loaded with unit spacing (TO CONFIRM: 0.4 m voxels in the Occ3D convention) |
| `ego_to_world` | attribute | from the file header | from the file header | layout:  (4,4) | `Carla-10Hz-mini/{scene}/{frame}.npz`<br>4x4 transform from the ego vehicle to the world frame (same .npz) |
| `camera_0` | image | from the file header | from the file header |  | `Carla-10Hz-mini/{scene}/{frame}_camera_0.png`<br> |
| `camera_1` | image | from the file header | from the file header |  | `Carla-10Hz-mini/{scene}/{frame}_camera_1.png`<br> |
| `camera_2` | image | from the file header | from the file header |  | `Carla-10Hz-mini/{scene}/{frame}_camera_2.png`<br> |
| `camera_3` | image | from the file header | from the file header |  | `Carla-10Hz-mini/{scene}/{frame}_camera_3.png`<br> |
| `bev` | image | from the file header | from the file header |  | `Carla-10Hz-mini/{scene}/{frame}_bev.png`<br>Bird's-eye-view rendering of the frame |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_uniocc_carla_mini").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **image** roles: `dinov3_features.py` (DINOv2 / DINOv3 patch features)
- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **points** roles: `points.align(moving)`, `points.clean()`, `points.to_mesh()`, `points.segment(eps, min_points)` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)
- Dense features: [DINOv2 / DINOv3](../models/dinov3.md) on the image roles.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `lidar`, `driving`, `occupancy`, `points`, `carla`, `hf`

<sub>Generated from `src/pardesline/data/manifests/hf_uniocc_carla_mini.json` on 2026-10-14.</sub>
