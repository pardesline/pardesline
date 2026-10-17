---
title: "TCIA Pancreas-CT: 82 abdominal contrast-enhanced CTs (NIH)"
description: "82 portal-venous CT scans of the pancreas from the NIH Clinical Center, one DICOM series per patient (the pancreas label maps of the original release are N"
---

# TCIA Pancreas-CT: 82 abdominal contrast-enhanced CTs (NIH)

`pl.load("tcia_pancreas_ct")` loads this dataset. 82 portal-venous CT scans of the pancreas from the NIH Clinical Center, one DICOM series per patient (the pancreas label maps of the original release are NIfTI files on the collection page, not in NBIA). Series are listed through the public NBIA API (no account) and each one is downloaded as a zip of DICOM files on first access; the folder is then a DICOM volume (LPS mm from the headers).

```python
import pardesline as pl

ds = pl.load("tcia_pancreas_ct")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/tcia_pancreas_ct
```

## Provenance and licence

| | |
|---|---|
| Source | The Cancer Imaging Archive, collection `Pancreas-CT` through the NBIA REST API |
| Scheme | `tcia` |
| Size of the whole source | 8.8 GB |
| Licence | CC-BY-3.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 3.0 on the TCIA collection page (checked 2026-10-14). |
| Terms | <https://www.cancerimagingarchive.net/collection/pancreas-ct/> |
| Homepage | <https://www.cancerimagingarchive.net/collection/pancreas-ct/> |
| Cite | Roth H.R., Farag A., Turkbey E.B., et al. Data From Pancreas-CT. The Cancer Imaging Archive, 2016. doi:10.7937/K9/TCIA.2016.tNB1kqBU. Clark K., Vendt B., Smith K., et al. The Cancer Imaging Archive (TCIA): Maintaining and Operating a Public Information Repository. J Digit Imaging 26(6):1045-1057, 2013. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `{id}/CT/{series}`<br>Abdominal CT, DICOM series |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("tcia_pancreas_ct").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `dicom`, `tcia`, `ct`, `pancreas`, `abdomen`

<sub>Generated from `src/pardesline/data/manifests/tcia_pancreas_ct.json` on 2026-10-14.</sub>
