---
title: "Visible Human Project: MRI of the head"
description: "Head MRI from the NLM Visible Human Project, as distributed with the SimpleITK notebooks"
---

# Visible Human Project: MRI of the head

`pl.load("visible_human_head_mri")` loads this dataset. Head MRI from the NLM Visible Human Project, as distributed with the SimpleITK notebooks. Small (2 MB), ideal for a first segmentation.

```python
import pardesline as pl

ds = pl.load("visible_human_head_mri")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mri  # fetched now, cached under ~/.cache/pardesline/datasets/visible_human_head_mri
```

## Provenance and licence

| | |
|---|---|
| Source | direct HTTPS downloads with checksums: `vm_head_mri.mha` |
| Scheme | `https` |
| Size of the whole source | 2 MB |
| Licence | not a standard licence: see the note |
| Redistribution | unknown |
| Licence note | NLM Visible Human Project data; free since 2019 under NLM terms. Terms of use TO CONFIRM with the data owner before any redistribution. |
| Terms | <https://www.nlm.nih.gov/research/visible/visible_human.html> |
| Homepage | <https://www.nlm.nih.gov/research/visible/visible_human.html> |
| Cite | Ackerman M.J. The Visible Human Project. Proc. IEEE 86(3), 1998. |
| Samples grouped by | file |
| Samples listed in the manifest | 1 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mri` | volume (MR) | from the file header | from the file header |  | `vm_head_mri.mha`<br>Head MRI |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("visible_human_head_mri").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `head`, `mri`

<sub>Generated from `src/pardesline/data/manifests/visible_human_head_mri.json` on 2026-10-16.</sub>
