---
title: "OpenNeuro ds000228: T1-weighted MRI of 155 children and adults (Richardson et al.)"
description: "Anatomical T1w volumes of 122 children (3-12 years) and 33 adults from the OpenNeuro dataset ds000228, read straight from the public OpenNeuro S3 bucket (a"
---

# OpenNeuro ds000228: T1-weighted MRI of 155 children and adults (Richardson et al.)

`pl.load("openneuro_ds000228")` loads this dataset. Anatomical T1w volumes of 122 children (3-12 years) and 33 adults from the OpenNeuro dataset ds000228, read straight from the public OpenNeuro S3 bucket (anonymous listing and download). The functional runs and fMRIPrep derivatives of the same dataset are in the bucket too; any other OpenNeuro dataset is one line away: pl.load('s3://openneuro.org/ds000001').

```python
import pardesline as pl

ds = pl.load("openneuro_ds000228")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.t1w  # fetched now, cached under ~/.cache/pardesline/datasets/openneuro_ds000228
```

## Provenance and licence

| | |
|---|---|
| Source | public S3 bucket `openneuro.org`, prefix `ds000228` |
| Scheme | `s3` |
| Size of the whole source | 2.4 GB |
| Licence | PDDL-1.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | dataset_description.json states License: PDDL (checked 2026-10-14); OpenNeuro datasets published since 2018 are CC0. |
| Terms | <https://openneuro.org/datasets/ds000228> |
| Homepage | <https://openneuro.org/datasets/ds000228> |
| Cite | Richardson H., Lisandrelli G., Riobueno-Naylor A., Saxe R. Development of the social brain from age three to twelve years. Nat Commun 9:1027, 2018. OpenNeuro ds000228. doi:10.18112/openneuro.ds000228.v1.1.1 |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `t1w` | volume (MR) | from the file header | from the file header |  | `{id}/anat/{id}_T1w.nii.gz`<br>T1-weighted anatomical MRI (BIDS anat/) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("openneuro_ds000228").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mri`, `brain`, `pediatric`, `nifti`, `openneuro`, `bids`

<sub>Generated from `src/pardesline/data/manifests/openneuro_ds000228.json` on 2026-10-14.</sub>
