---
title: "MedShapeNet: 106 101 anatomical and surgical-instrument shapes as STL meshes"
description: "The MedShapeNet collection (IKIM, University Hospital Essen): over 100 000 3-D shapes extracted from 23 medical datasets - organs, bones, vessels, tumours,"
---

# MedShapeNet: 106 101 anatomical and surgical-instrument shapes as STL meshes

`pl.load("medshapenet")` loads this dataset. The MedShapeNet collection (IKIM, University Hospital Essen): over 100 000 3-D shapes extracted from 23 medical datasets - organs, bones, vessels, tumours, teeth, instruments - as STL files, one per URL in the public download index (sciebo, HTTP Range supported). Sample ids are case/structure (426 structure names, e.g. liver, vertebrae, skull, tumoredbrain); ds.filter(structure='liver') selects one anatomy. STL carries no unit: shapes derived from medical images are in millimetres (declared here, TO CONFIRM for the instrument sets).

```python
import pardesline as pl

ds = pl.load("medshapenet")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mesh  # fetched now, cached under ~/.cache/pardesline/datasets/medshapenet
```

## Provenance and licence

| | |
|---|---|
| Source | URL index `https://mml.ikim.nrw/ait/projects/medshapenet/MedShapeNetDataset.txt` |
| Scheme | `urllist` |
| Size of the whole source | 1953.1 GB |
| Licence | CC-BY-4.0 |
| Redistribution | unknown |
| Licence note | MedShapeNetCore on Zenodo is CC BY 4.0 (checked 2026-10-14); the full collection inherits the licence of each source dataset, TO CONFIRM per structure before commercial use or redistribution. |
| Terms | <https://medshapenet.ikim.nrw/> |
| Homepage | <https://medshapenet.ikim.nrw/> |
| Cite | Li J., Zhou Z., Yang J., et al. MedShapeNet - A Large-Scale Dataset of 3D Medical Shapes for Computer Vision. Biomedical Engineering / Biomedizinische Technik, 2024. arXiv:2308.16139. |
| Samples grouped by | case |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mesh` | mesh | from the file header | mm |  | `{case}_{structure}.stl`<br>Triangle mesh of one anatomical structure (STL, millimetres) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("medshapenet").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **mesh** roles: `mesh.to_points(num_points)`, `mesh.decimate()`, `mesh.smooth()`, `mesh.clean()`, `mesh.to_open3d()` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mesh`, `stl`, `anatomy`, `shapes`, `instruments`

<sub>Generated from `src/pardesline/data/manifests/medshapenet.json` on 2026-10-17.</sub>
