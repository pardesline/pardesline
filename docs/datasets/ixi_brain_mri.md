---
title: "IXI: ~600 healthy-subject brain MRIs (T1, T2, PD, MRA) from three London hospitals"
description: "The Information eXtraction from Images dataset: T1, T2, PD-weighted and MR angiography volumes of nearly 600 healthy subjects acquired at Guy's, Hammersmit"
---

# IXI: ~600 healthy-subject brain MRIs (T1, T2, PD, MRA) from three London hospitals

`pl.load("ixi_brain_mri")` loads this dataset. The Information eXtraction from Images dataset: T1, T2, PD-weighted and MR angiography volumes of nearly 600 healthy subjects acquired at Guy's, Hammersmith and the Institute of Psychiatry (1.5 T and 3 T). One tar per modality on the Imperial College server, read subject by subject with HTTP Range (indexing a tar walks its ~580 headers once, a few minutes). Subject ids such as IXI002-Guys-0828 join the modalities into one sample. Demographics are in IXI.xls on the website.

```python
import pardesline as pl

ds = pl.load("ixi_brain_mri")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.t1  # fetched now, cached under ~/.cache/pardesline/datasets/ixi_brain_mri
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-T1.tar`, `http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-T2.tar`, `http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-PD.tar`, `http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-MRA.tar` |
| Scheme | `archive` |
| Size of the whole source | 24.6 GB |
| Licence | CC-BY-SA-3.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | Creative Commons CC BY-SA 3.0 as stated on the IXI website (checked 2026-10-14). |
| Terms | <https://brain-development.org/ixi-dataset/> |
| Homepage | <https://brain-development.org/ixi-dataset/> |
| Cite | IXI dataset, brain-development.org (Imperial College London, Biomedical Image Analysis Group), EPSRC GR/S21533/02. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `t1` | volume (MR) | from the file header | from the file header |  | `{id}-T1.nii.gz`<br>T1-weighted |
| `t2` | volume (MR) | from the file header | from the file header |  | `{id}-T2.nii.gz`<br>T2-weighted |
| `pd` | volume (MR) | from the file header | from the file header |  | `{id}-PD.nii.gz`<br>Proton density |
| `mra` | volume (MR) | from the file header | from the file header |  | `{id}-MRA.nii.gz`<br>MR angiography |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("ixi_brain_mri").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mri`, `brain`, `healthy`, `nifti`, `multimodal`

<sub>Generated from `src/pardesline/data/manifests/ixi_brain_mri.json` on 2026-10-14.</sub>
