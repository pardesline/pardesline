---
title: "RIRE training_001: CT and MR-T1 of one brain"
description: "Multimodal brain pair from the Retrospective Image Registration Evaluation project, as distributed with the SimpleITK notebooks"
---

# RIRE training_001: CT and MR-T1 of one brain

`pl.load("rire_brain")` loads this dataset. Multimodal brain pair from the Retrospective Image Registration Evaluation project, as distributed with the SimpleITK notebooks. The classic rigid CT/MR registration exercise.

```python
import pardesline as pl

ds = pl.load("rire_brain")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/rire_brain
```

## Provenance and licence

| | |
|---|---|
| Source | direct HTTPS downloads with checksums: `training_001_ct.mha`, `training_001_mr_T1.mha` |
| Scheme | `https` |
| Size of the whole source | 19 MB |
| Licence | not a standard licence: see the note |
| Redistribution | unknown |
| Licence note | RIRE data are distributed for research evaluation of registration methods. Terms of use TO CONFIRM with the data owner before any redistribution. |
| Terms | <https://rire.insight-journal.org/> |
| Homepage | <https://rire.insight-journal.org/> |
| Cite | West J. et al. Comparison and evaluation of retrospective intermodality brain image registration techniques. J Comput Assist Tomogr 21(4), 1997. |
| Samples grouped by | patient |
| Samples listed in the manifest | 1 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `training_001_ct.mha`<br>CT, the fixed reference |
| `mr_t1` | volume (MR) | from the file header | from the file header |  | `training_001_mr_T1.mha`<br>MR T1-weighted, the moving volume |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("rire_brain").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `brain`, `ct`, `mr`, `registration`, `multimodal`

<sub>Generated from `src/pardesline/data/manifests/rire_brain.json` on 2026-10-10.</sub>
