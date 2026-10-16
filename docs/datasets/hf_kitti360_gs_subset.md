---
title: "KITTI-360 street chunks as point clouds and Gaussian splats (GaussianWorld subset, 16 chunks)"
description: "Sixteen chunks of KITTI-360 sequence 0000 pre-processed by GaussianWorld: per chunk the accumulated LiDAR point cloud (pc_coord.npy, ~3 M points, with segm"
---

# KITTI-360 street chunks as point clouds and Gaussian splats (GaussianWorld subset, 16 chunks)

`pl.load("hf_kitti360_gs_subset")` loads this dataset. Sixteen chunks of KITTI-360 sequence 0000 pre-processed by GaussianWorld: per chunk the accumulated LiDAR point cloud (pc_coord.npy, ~3 M points, with segment ids) and a fitted Gaussian splat stored as separate arrays (coord, color, opacity, scale, quat). Coordinates are in the KITTI-360 world frame with offsets above 1 000 m - keep float64. This is the dataset the pl.load feasibility test of 2026-10-03 ran on (one chunk of 43 MB fetched in 5.5 s, ground removal unchanged).

```python
import pardesline as pl

ds = pl.load("hf_kitti360_gs_subset")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.points  # fetched now, cached under ~/.cache/pardesline/datasets/hf_kitti360_gs_subset
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `GaussianWorld/kitti_360_subset_chunk_gs_preprocessed`, paths `test` |
| Scheme | `hf` |
| Size of the whole source | 2.4 GB |
| Licence | CC-BY-NC-SA-3.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | forbidden |
| Licence note | The Hub card declares no licence; KITTI-360 upstream is CC BY-NC-SA 3.0 (non-commercial, share-alike), inherited here. TO CONFIRM with the GaussianWorld authors for the splat fits. |
| Terms | <https://www.cvlibs.net/datasets/kitti-360/> |
| Homepage | <https://huggingface.co/datasets/GaussianWorld/kitti_360_subset_chunk_gs_preprocessed> |
| Cite | Liao Y., Xie J., Geiger A. KITTI-360: A Novel Dataset and Benchmarks for Urban Scene Understanding in 2D and 3D. TPAMI 2022. |
| Samples grouped by | chunk |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `points` | points | world | m | layout:  (N,3) x, y, z | `test/{chunk}/pc_coord.npy`<br>Accumulated LiDAR points of the chunk (KITTI-360 world frame, metres) |
| `point_segments` | attribute | from the file header | from the file header | layout:  (N) | `test/{chunk}/pc_segment.npy`<br>One segment id per LiDAR point (meaning of the ids TO CONFIRM) |
| `gaussian_centers` | points | world | m | layout:  (N,3) x, y, z | `test/{chunk}/coord.npy`<br>Centres of the fitted Gaussians (same frame as the points) |
| `gaussian_color` | attribute | from the file header | from the file header | layout:  (N,3) r, g, b | `test/{chunk}/color.npy`<br>RGB per Gaussian (range 0-1 or 0-255 TO CONFIRM) |
| `gaussian_opacity` | attribute | from the file header | from the file header | layout:  (N,1) | `test/{chunk}/opacity.npy`<br> |
| `gaussian_scale` | attribute | from the file header | from the file header | layout:  (N,3) | `test/{chunk}/scale.npy`<br> |
| `gaussian_rotation` | attribute | from the file header | from the file header | layout:  (N,4) | `test/{chunk}/quat.npy`<br>Unit quaternion per Gaussian |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_kitti360_gs_subset").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **points** roles: `points.align(moving)`, `points.clean()`, `points.to_mesh()`, `points.segment(eps, min_points)` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `lidar`, `points`, `splat`, `driving`, `kitti`, `hf`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/hf_kitti360_gs_subset.json` on 2026-10-16.</sub>
