---
title: "CHAOS: abdominal CT and MR (T1 in/out-phase, T2 SPIR) as DICOM series, 40 patients"
description: "The Combined Healthy Abdominal Organ Segmentation challenge training set: 20 CT and 20 MR patients as anonymised DICOM series, read series by series out of"
---

# CHAOS: abdominal CT and MR (T1 in/out-phase, T2 SPIR) as DICOM series, 40 patients

`pl.load("chaos_abdomen")` loads this dataset. The Combined Healthy Abdominal Organ Segmentation challenge training set: 20 CT and 20 MR patients as anonymised DICOM series, read series by series out of the 890 MB zip on Zenodo (HTTP Range; a series is fetched as a folder of .dcm files). Ground-truth masks are PNG slice stacks in the same archive (folders Ground/) and are not mapped here. Sample ids are set/case (CT/1, MR/1 are different patients).

```python
import pardesline as pl

ds = pl.load("chaos_abdomen")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/chaos_abdomen
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/3431873/files/CHAOS_Train_Sets.zip` |
| Scheme | `archive` |
| Size of the whole source | 891 MB |
| Licence | CC-BY-NC-SA-4.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 4.0 on the Zenodo record (checked 2026-10-14): non-commercial, share-alike. |
| Terms | <https://zenodo.org/records/3431873> |
| Homepage | <https://chaos.grand-challenge.org/> |
| Cite | Kavur A.E., Gezer N.S., Baris M., et al. CHAOS Challenge - combined (CT-MR) healthy abdominal organ segmentation. Med Image Anal 69:101950, 2021. |
| Samples grouped by | case |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `Train_Sets/{set}/{case}/DICOM_anon/*.dcm`<br>Abdominal CT, DICOM series (set CT) |
| `mr_t1_inphase` | volume (MR) | from the file header | from the file header |  | `Train_Sets/{set}/{case}/T1DUAL/DICOM_anon/InPhase/*.dcm`<br>T1-DUAL in-phase, DICOM series (set MR) |
| `mr_t1_outphase` | volume (MR) | from the file header | from the file header |  | `Train_Sets/{set}/{case}/T1DUAL/DICOM_anon/OutPhase/*.dcm`<br>T1-DUAL out-of-phase, DICOM series (set MR) |
| `mr_t2_spir` | volume (MR) | from the file header | from the file header |  | `Train_Sets/{set}/{case}/T2SPIR/DICOM_anon/*.dcm`<br>T2-SPIR, DICOM series (set MR) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("chaos_abdomen").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](https://github.com/pardesline/pardesline/blob/main/CONTRIBUTING.md#adding-a-dataset)
- Tags: `medical`, `ct`, `mri`, `abdomen`, `dicom`, `segmentation`

<sub>Generated from `src/pardesline/data/manifests/chaos_abdomen.json` on 2026-10-14.</sub>
