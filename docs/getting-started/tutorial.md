---
title: 5-minute tutorial — a medical imaging dataset to a registered volume and a mesh in Python
description: Load a Decathlon dataset, inspect its roles and licence, turn a label map into a mesh, register CT and MR, hand the result to PyVista and SimpleITK, export standard files.
---

# 5-minute tutorial

Everything below ran on 2026-10-16 with `pip install "pardesline[all]"`. The first run downloads 19 MB (RIRE) and 28 MB (hippocampus).

## 1. A dataset, and what it knows about itself

```python
import pardesline as pl

ds = pl.load("msd_task04_hippocampus")  # nothing is downloaded yet
print(ds.describe())
```

```
msd_task04_hippocampus  -  Medical Segmentation Decathlon, Task04 Hippocampus
  ...
  licence: CC-BY-SA-4.0 (CC-BY-SA 4.0 as stated in the archive's dataset.json ...)
  cite:    Antonelli M., Reinke A., Bakas S., et al. The Medical Segmentation Decathlon. Nat Commun 13:4128, 2022. ...
  samples: pattern-derived, paired by id
  roles:
    mri          volume     MR image (NIfTI, LPS mm from the header); split Tr = labelled, Ts = test
    mask         labels     Label map (training cases only)  [labels 1=anterior, 2=posterior]
```

The roles come from the manifest, so you know before downloading anything that `mask` is a label map with two named labels, in the frame and units of the NIfTI header, under CC-BY-SA 4.0.

## 2. One sample, one object

```python
case = ds.filter(split="Tr")[0]  # the first labelled case
mri, mask = case.mri, case.mask  # fetched now: two files out of the 28 MB tar
print(mask.info())  # {'size': (35, 51, 35), 'spacing': (1.0, 1.0, 1.0), ...}
print(mask.labels)  # {1: 'anterior', 2: 'posterior'}
```

`mri` is a `Volume`, `mask` a `LabelMap`. Both know their frame (LPS millimetres), their licence and where they came from (`obj.provenance`).

## 3. A label becomes a surface

```python
anterior = mask.to_mesh(label=1)  # exact boundary of label 1, world coordinates
anterior = anterior.smooth()  # Taubin smoothing, catalog defaults (20 iterations, pass band 0.1)
anterior.save("anterior.stl")  # + anterior.stl.pardesline.json: frame, licence, both steps
```

Open the sidecar: it records `to_mesh(label=1)` then `pyvista_mesh_processing.pv_smooth_taubin` with every parameter, the duration and the package version. Hand the surface to the library you prefer:

```python
anterior.to_pyvista().plot()  # PyVista
o3d_mesh = anterior.to_open3d()  # Open3D TriangleMesh
```

## 4. Registration, across modalities

```python
s = pl.load("rire_brain")[0]  # CT + MR T1 of one head; the licence line is printed
moved = s.ct.align(s.mr_t1)  # simpleitk_registration.rigid, Mattes mutual information
print(moved.transform["sub_transforms"][0]["rotation_deg"])  # [0.34, -0.35, -4.38]
print(moved.provenance[-1]["params"])  # {} = every catalog default was used
```

`moved` is the MR resampled on the CT grid. `print(pl.describe("simpleitk_registration.rigid"))` lists the fourteen parameters with their ranges and the reason for each default; pass any of them to `align`.

## 5. Your own files and folders

```python
ct = pl.load("scan.nii.gz")  # a Volume; frame from the header
pts = pl.load("sweep.bin", layout=dict(dtype="float32", shape="(N,4)", columns=["x", "y", "z", "i"]))
ds = pl.scan("/data/my_study")  # drafts a manifest, asks what it cannot know
```

`pl.scan` raises `NeedsConfirmation` with the questions (units? label names? licence?) and the draft path; answer them once (`pl.load(draft, units="mm", ...)`) and the manifest is saved for next time. See [Standardize a folder of medical images](../how-to/standardize-a-folder-of-medical-images-in-python.md).

## 6. Export standard files

```python
ds.take(5).export("./hippocampus_std")  # MetaImage volumes + sidecars + manifest.json, one folder per sample
```

## Next

- [Concepts](concepts.md): the four ideas behind this (dataset, manifest, object, catalog).
- [Why our defaults work](../algorithms/why-our-defaults-work.md): what `align()` set and why.
- [Examples](../examples.md): twelve scripts with their images and numbers.
