---
title: "Stanford bunny (Open3D demo mesh)"
description: "The Stanford bunny as shipped by open3d.data.BunnyMesh"
---

# Stanford bunny (Open3D demo mesh)

`pl.load("open3d_bunny")` loads this dataset. The Stanford bunny as shipped by open3d.data.BunnyMesh. The file carries no unit; the original scan is in metres (the bunny is about 15 cm long).

```python
import pardesline as pl

ds = pl.load("open3d_bunny")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mesh  # fetched now, cached under ~/.cache/pardesline/datasets/open3d_bunny
```

## Provenance and licence

| | |
|---|---|
| Source | `open3d.data` demo download |
| Scheme | `open3d` |
| Size of the whole source | 3 MB |
| Licence | not a standard licence: see the note |
| Redistribution | unknown |
| Licence note | Stanford 3D Scanning Repository: free to use with acknowledgement; commercial use TO CONFIRM with Stanford. |
| Terms | <https://graphics.stanford.edu/data/3Dscanrep/> |
| Cite | Turk G., Levoy M. Zippered polygon meshes from range images. SIGGRAPH 1994. |
| Samples grouped by | file |
| Samples listed in the manifest | 1 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mesh` | mesh | Y-up | m |  | `BunnyMesh.ply`<br>Triangle mesh |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("open3d_bunny").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **mesh** roles: `mesh.to_points(num_points)`, `mesh.decimate()`, `mesh.smooth()`, `mesh.clean()`, `mesh.to_open3d()` ; catalog modules: [`point_cloud_processing`](../algorithms/point_cloud_processing.md), [`mesh_processing`](../algorithms/mesh_processing.md), [`voxel_to_mesh`](../algorithms/voxel_to_mesh.md), [`sdf`](../algorithms/sdf.md), [`point_cloud_reconstruction`](../algorithms/point_cloud_reconstruction.md), [`registration`](../algorithms/registration.md), [`deformable_registration`](../algorithms/deformable_registration.md), [`point_cloud_segmentation`](../algorithms/point_cloud_segmentation.md), [`stereo_3d_reconstruction`](../algorithms/stereo_3d_reconstruction.md), [`lidar_scene_detection`](../algorithms/lidar_scene_detection.md), [`lidar_camera_fusion`](../algorithms/lidar_camera_fusion.md), [`features_extraction`](../algorithms/features_extraction.md), [`collision_detection`](../algorithms/collision_detection.md), [`pyvista_mesh_processing`](../algorithms/pyvista_mesh_processing.md), [`pyvista_pointcloud_processing`](../algorithms/pyvista_pointcloud_processing.md), [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`pyvista_analysis`](../algorithms/pyvista_analysis.md)

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `mesh`, `demo`

<sub>Generated from `src/pardesline/data/manifests/open3d_bunny.json` on 2026-10-10.</sub>
