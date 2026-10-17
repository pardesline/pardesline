---
title: "KITTI raw, drive 2011_09_26_0001: 108 Velodyne sweeps with the four camera streams"
description: "One synced+rectified KITTI raw drive read frame by frame out of the official 459 MB zip on S3 (HTTP Range: the central directory costs 157 KB, one sweep 2 "
---

# KITTI raw, drive 2011_09_26_0001: 108 Velodyne sweeps with the four camera streams

`pl.load("kitti_raw_2011_09_26_drive_0001")` loads this dataset. One synced+rectified KITTI raw drive read frame by frame out of the official 459 MB zip on S3 (HTTP Range: the central directory costs 157 KB, one sweep 2 MB). Velodyne sweeps are headerless float32 (N,4) x, y, z, reflectance in the sensor frame (x forward, y left, z up, metres) - the layout below is what makes them readable. Calibration files are their own samples.

```python
import pardesline as pl

ds = pl.load("kitti_raw_2011_09_26_drive_0001")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.lidar  # fetched now, cached under ~/.cache/pardesline/datasets/kitti_raw_2011_09_26_drive_0001
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://s3.eu-central-1.amazonaws.com/avg-kitti/raw_data/2011_09_26_drive_0001/2011_09_26_drive_0001_sync.zip` |
| Scheme | `archive` |
| Size of the whole source | 459 MB |
| Licence | CC-BY-NC-SA-3.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | forbidden |
| Licence note | KITTI terms: Creative Commons Attribution-NonCommercial-ShareAlike 3.0; the loader fetches from the authors' server, nothing is mirrored. |
| Terms | <https://www.cvlibs.net/datasets/kitti/> |
| Homepage | <https://www.cvlibs.net/datasets/kitti/raw_data.php> |
| Cite | Geiger A., Lenz P., Stiller C., Urtasun R. Vision meets Robotics: The KITTI Dataset. IJRR 2013. |
| Samples grouped by | frame |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `lidar` | points | sensor | m | layout: float32 (N,4) x, y, z, reflectance | `2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/{frame}.bin`<br>Velodyne HDL-64E sweep, sensor frame (x forward, y left, z up) |
| `image_left` | image | from the file header | from the file header |  | `2011_09_26/2011_09_26_drive_0001_sync/image_02/data/{frame}.png`<br>Colour left camera (image_02), rectified |
| `image_right` | image | from the file header | from the file header |  | `2011_09_26/2011_09_26_drive_0001_sync/image_03/data/{frame}.png`<br>Colour right camera (image_03), rectified |
| `calibration` | calibration | from the file header | from the file header |  | `2011_09_26/calib_*.txt`<br>KITTI calibration text files (velo_to_cam, cam_to_cam, imu_to_velo) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("kitti_raw_2011_09_26_drive_0001").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **image** roles: `dinov3_features.py` (DINOv2 / DINOv3 patch features)
- **points** roles: `points.align(moving)`, `points.clean()`, `points.to_mesh()`, `points.segment(eps, min_points)` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)
- Dense features: [DINOv2 / DINOv3](../models/dinov3.md) on the image roles.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `lidar`, `points`, `driving`, `kitti`, `stereo`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/kitti_raw_2011_09_26_drive_0001.json` on 2026-10-14.</sub>
