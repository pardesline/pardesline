---
title: "C3VD colonoscopy scenes as Gaussian splats and point clouds (EndoGSLAM fits from PR-ENDO)"
description: "Ten colonoscopy sequences of the C3VD phantom dataset reconstructed with EndoGSLAM and released with PR-ENDO (relightable Gaussian splatting for endoscopy)"
---

# C3VD colonoscopy scenes as Gaussian splats and point clouds (EndoGSLAM fits from PR-ENDO)

`pl.load("c3vd_endoscopy_splats")` loads this dataset. Ten colonoscopy sequences of the C3VD phantom dataset reconstructed with EndoGSLAM and released with PR-ENDO (relightable Gaussian splatting for endoscopy): per scene the optimised Gaussian splat (point_cloud.ply with the 3DGS attributes), the Gaussian centres (means3D.ply) and the per-step parameter dumps (.npz / .pt). Read out of the 7.8 GB zip on Zenodo by HTTP Range. The frame is the scene's own camera frame; the scale follows the C3VD phantom (millimetres, TO CONFIRM).

```python
import pardesline as pl

ds = pl.load("c3vd_endoscopy_splats")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.splat  # fetched now, cached under ~/.cache/pardesline/datasets/c3vd_endoscopy_splats
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/15732143/files/C3VD_endogslam_optimized.zip` |
| Scheme | `archive` |
| Size of the whole source | 7.7 GB |
| Licence | CC-BY-4.0 |
| Redistribution | unknown |
| Licence note | CC BY 4.0 on the PR-ENDO Zenodo record (checked 2026-10-14); the underlying C3VD dataset is CC BY-NC-SA 4.0, so commercial use is TO CONFIRM. |
| Terms | <https://zenodo.org/records/15732143> |
| Homepage | <https://github.com/SanoScience/PR-ENDO> |
| Cite | Kaleta J., Dall'Alba D., Plotka S., Korzeniowski P. PR-ENDO: Physically Based Relightable Gaussian Splatting for Endoscopy. arXiv:2411.12510, 2024. Bobrow T.L., Golhar M., Vijayan R., et al. Colonoscopy 3D Video Dataset with Paired Depth from 2D-3D Registration. Med Image Anal 90:102956, 2023. |
| Samples grouped by | scene |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `splat` | splat | sensor | mm |  | `C3VD_endogslam_optimized/{scene}/point_cloud/iteration_*/point_cloud.ply`<br>Optimised 3-D Gaussian splat (PLY with position, scale, rotation, opacity, SH colour) |
| `points` | points | sensor | mm |  | `C3VD_endogslam_optimized/{scene}/means3D.ply`<br>Gaussian centres as a plain point cloud |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("c3vd_endoscopy_splats").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **points** roles: `points.align(moving)`, `points.clean()`, `points.to_mesh()`, `points.segment(eps, min_points)` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)
- **splat** roles: `splat.to_numpy()` (means), the `gaussian-splatting` guide ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](https://github.com/pardesline/pardesline/blob/main/CONTRIBUTING.md#adding-a-dataset)
- Tags: `medical`, `endoscopy`, `colonoscopy`, `splat`, `points`, `gaussian-splatting`

<sub>Generated from `src/pardesline/data/manifests/c3vd_endoscopy_splats.json` on 2026-10-14.</sub>
