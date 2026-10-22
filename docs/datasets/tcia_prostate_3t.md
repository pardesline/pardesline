---
title: "TCIA Prostate-3T: 64 T2-weighted prostate MRIs (DICOM)"
description: "Axial T2-weighted 3 T prostate MRIs of 64 patients (Radboud), the images behind the MSD prostate task"
---

# TCIA Prostate-3T: 64 T2-weighted prostate MRIs (DICOM)

`pl.load("tcia_prostate_3t")` loads this dataset. Axial T2-weighted 3 T prostate MRIs of 64 patients (Radboud), the images behind the MSD prostate task. Series are listed through the public NBIA API (no account) and each one is downloaded as a zip of DICOM files on first access; the folder is then a DICOM volume (LPS mm from the headers).

```python
import pardesline as pl

ds = pl.load("tcia_prostate_3t")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.t2  # fetched now, cached under ~/.cache/pardesline/datasets/tcia_prostate_3t
```

## Provenance and licence

| | |
|---|---|
| Source | The Cancer Imaging Archive, collection `Prostate-3T` through the NBIA REST API |
| Scheme | `tcia` |
| Size of the whole source | 200 MB |
| Licence | CC-BY-3.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 3.0 on the TCIA collection page (checked 2026-10-14). |
| Terms | <https://www.cancerimagingarchive.net/collection/prostate-3t/> |
| Homepage | <https://www.cancerimagingarchive.net/collection/prostate-3t/> |
| Cite | Litjens G., Futterer J., Huisman H. Data From Prostate-3T. The Cancer Imaging Archive, 2015. doi:10.7937/K9/TCIA.2015.QJTV5IL5. Clark K., Vendt B., Smith K., et al. The Cancer Imaging Archive (TCIA): Maintaining and Operating a Public Information Repository. J Digit Imaging 26(6):1045-1057, 2013. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `t2` | volume (MR) | from the file header | from the file header |  | `{id}/MR/{series}`<br>Axial T2 TSE, DICOM series |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("tcia_prostate_3t").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](https://github.com/pardesline/pardesline/blob/main/CONTRIBUTING.md#adding-a-dataset)
- Tags: `medical`, `dicom`, `tcia`, `mri`, `prostate`, `pelvis`

<sub>Generated from `src/pardesline/data/manifests/tcia_prostate_3t.json` on 2026-10-14.</sub>
