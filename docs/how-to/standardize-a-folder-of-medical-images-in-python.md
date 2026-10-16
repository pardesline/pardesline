---
title: How to standardize a folder of medical images in Python
description: Turn a folder of NIfTI, DICOM, MetaImage, PLY or STL files into a dataset with typed roles, frames, units, label names and a licence in Python: pl.scan drafts a manifest, you confirm what the files cannot say, export writes standard files with sidecars.
---

# How to standardize a folder of medical images in Python

"Standardize" means: every file typed (volume, label map, mesh, points), its frame and units known, label values named, the licence written down, samples grouped by patient, and standard files on disk with that information next to them. pardesline does it with a manifest that you confirm once.

## 1. Scan

```python
import pardesline as pl

draft = pl.scan("/data/my_study")  # reads headers, groups files by sub-folder and name prefix
print(draft.describe())
for q in draft.questions:
    print(q.field, "->", q.message, "| suggestion:", q.suggestion)
```

Typical questions: `license` (none found), `roles.seg.labels` (a label map with values 1, 2, 3 and no names), `roles.scan.units` (a mesh without units), `pairing` (what groups files into a sample: a patient folder, a name prefix). Suggestions come from what was found (a `LICENSE` file, the distinct label values, the folder layout) and are never applied silently.

## 2. Confirm, once

```python
ds = pl.load(
    "/data/my_study",
    license="CC-BY-4.0",
    pairing="folder",
    labels={"seg": {1: "liver", 2: "tumor"}},
    units={"scan": "mm"},
)
```

The confirmed manifest is saved as `/data/my_study/.pardesline-manifest.json` (or `manifest=` to put it elsewhere) and `pl.load("/data/my_study")` uses it from now on. Alternatives: `interactive=True` asks in the terminal; `assume=True` loads with unknowns left unknown and warns; `pardesline describe /data/my_study` prints the draft.

## 3. Use it like any dataset

```python
s = ds[0]
print(s.roles, s.ct.frame, s.seg.labels)
tumor = s.seg.to_mesh(label=2).smooth()
train, test = ds.split(by="patient", fractions=(0.8, 0.2), seed=0)
```

## 4. Export standard files

```python
ds.export("/data/my_study_std")
```

One folder per sample; volumes and label maps as MetaImage (`.mha`), points and meshes as PLY, each with a `.pardesline.json` sidecar (frame, units, labels, licence, provenance) and a `manifest.json` for the folder. DICOM series become one volume each; `.npz` / `.bin` arrays are decoded through their layout.

## What standardization does not do by itself

Resampling to a common spacing, reorienting to a canonical axis order and intensity normalisation change the data; they are explicit steps (`pyvista_volume_processing`, `simpleitk_registration`, your training transforms) and the sidecar records them when you run them.

## When it fails

| Situation | Do |
|---|---|
| files with identifiers (DICOM names, dates) | de-identify before scanning (DICOM PS3.15); pardesline does not de-identify |
| two volumes per patient with the same pattern | refine the pattern in the manifest (`{patient}/{phase}/ct.nii.gz`) or set `pairing` |
| a `.bin` or `.npy` without meaning | answer `layout={"lidar": {"dtype": "float32", "shape": "(N,4)", "columns": ["x","y","z","i"]}}` |

Related: [Concepts: manifest](../getting-started/concepts.md#manifest) · [Guide: scanning a private folder](../guides/scanning-private-folders.md) · [DICOM to NIfTI](convert-a-dicom-series-to-nifti-in-python.md)
