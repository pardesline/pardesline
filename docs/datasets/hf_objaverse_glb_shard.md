---
title: "Objaverse 1.0, one shard of glTF meshes (5 000 objects)"
description: "Objaverse hosts 800k+ Sketchfab objects as .glb under glbs/<shard>/<uid>.glb (160 shards of 5 000)"
---

# Objaverse 1.0, one shard of glTF meshes (5 000 objects)

`pl.load("hf_objaverse_glb_shard")` loads this dataset. Objaverse hosts 800k+ Sketchfab objects as .glb under glbs/<shard>/<uid>.glb (160 shards of 5 000). This manifest lists one shard; pl.load('hf://allenai/objaverse/glbs/000-017') picks another. glTF fixes the frame: Y-up, metres. Object metadata (names, categories, per-object licences) is in metadata/ and object-paths.json.gz at the repo root.

```python
import pardesline as pl

ds = pl.load("hf_objaverse_glb_shard")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mesh  # fetched now, cached under ~/.cache/pardesline/datasets/hf_objaverse_glb_shard
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `allenai/objaverse`, paths `glbs/000-000` |
| Scheme | `hf` |
| Size of the whole source | 14.6 GB |
| Licence | ODC-By-1.0 |
| Redistribution | unknown |
| Licence note | ODC-By 1.0 for the collection (Hub card, checked 2026-10-13); every object keeps its own Creative Commons licence from Sketchfab (CC BY, CC BY-NC, CC BY-ND...), recorded in the metadata. Commercial use and redistribution are TO CONFIRM per object from that metadata. |
| Terms | <https://huggingface.co/datasets/allenai/objaverse> |
| Homepage | <https://objaverse.allenai.org/> |
| Cite | Deitke M., Schwenk D., Salvador J., et al. Objaverse: A Universe of Annotated 3D Objects. CVPR 2023. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mesh` | mesh | Y-up | m |  | `glbs/{shard}/{id}.glb`<br>Textured glTF binary mesh (Y-up, metres by the glTF specification) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_objaverse_glb_shard").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **mesh** roles: `mesh.to_points(num_points)`, `mesh.decimate()`, `mesh.smooth()`, `mesh.clean()`, `mesh.to_open3d()` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `mesh`, `gltf`, `objects`, `hf`, `objaverse`

<sub>Generated from `src/pardesline/data/manifests/hf_objaverse_glb_shard.json` on 2026-10-16.</sub>
