---
title: How to turn a segmentation mask into a mesh in Python (NIfTI label map to STL)
description: Convert a NIfTI or MetaImage label map into an STL or PLY surface in Python with the exact label boundary in world millimetres, Taubin smoothing without shrinkage, decimation, and a sidecar recording every step.
---

# How to turn a segmentation mask into a mesh in Python

A label map's boundary at value `k` is an exact surface in the volume's world coordinates. Marching cubes on a label map at isovalue 0.5 between `k` and not-`k` gives it; the staircase is removed by Taubin smoothing, which keeps the volume; decimation then halves the triangle count without visible change.

```python
import pardesline as pl

case = pl.load("msd_task04_hippocampus").filter(split="Tr")[0]
mask = case.mask  # LabelMap, labels {1: 'anterior', 2: 'posterior'}
anterior = mask.to_mesh(label=1)  # exact boundary, LPS millimetres
anterior = anterior.smooth().decimate()  # Taubin 20 iterations, then 50 % fewer triangles
anterior.save("hippocampus_anterior.stl")  # + .pardesline.json: frame, licence, the three steps
```

Your own mask: `pl.load("seg.nii.gz").as_labels({1: "liver", 2: "tumor"}).to_mesh(label=2)`. A grey-level volume uses `volume.to_mesh(isovalue=300)` (bone on CT in Hounsfield units).

## What the sidecar says

```json
{"step": "to_mesh", "label": 1, "label_name": "anterior", "isovalue": null, ...}
{"module": "pyvista_mesh_processing", "method": "pv_smooth_taubin", "params": {}, ...}
{"module": "pyvista_mesh_processing", "method": "pv_decimate", "params": {}, ...}
```

Empty `params` means every catalog default was used; `pl.describe("pyvista_mesh_processing.pv_smooth_taubin")` says what they are and why.

## Units and frames

The mesh is in the volume's physical frame (LPS millimetres for NIfTI and DICOM through SimpleITK). To compare with a scanner mesh in RAS, flip x and y; `obj.frame` tells you which one you have. Volumes in millimetres from a mesh: `anterior.to_pyvista().volume`.

## Several labels, several meshes

```python
for label, name in mask.labels.items():
    mask.to_mesh(label=label).smooth().save(f"hippocampus_{name}.stl")
```

TotalSegmentator ships one mask role per structure: `s.liver.to_mesh()` works without a label argument because the role has a single named label.

## When it looks wrong

| Symptom | Cause | Do |
|---|---|---|
| staircase surface | no smoothing | `.smooth()`; more iterations (`n_iterations=40`) for coarse slices |
| small structures shrink | Laplacian smoothing | use `.smooth()` (Taubin); avoid `pv_smooth_laplacian` for thin anatomy |
| holes in the surface | the label touches the volume border | pad the volume, or accept an open surface |
| wrong size | voxel indices instead of world coordinates | `to_mesh` always uses world coordinates; check `mask.info()["spacing"]` |

Related: [Hippocampus example](../examples.md#hippocampus_mask_to_mesh) · [Mesh processing](../algorithms/pyvista_mesh_processing.md) · [Guide: medical volumes](../guides/medical-volumes.md)
