---
title: "TCIA LIDC-IDRI: 1 018 thoracic CTs for lung nodule analysis (DICOM)"
description: "The Lung Image Database Consortium collection: 1 018 CT scans of 1 010 patients with nodule annotations by four radiologists (the XML annotations are on th"
---

# TCIA LIDC-IDRI: 1 018 thoracic CTs for lung nodule analysis (DICOM)

`pl.load("tcia_lidc_idri")` loads this dataset. The Lung Image Database Consortium collection: 1 018 CT scans of 1 010 patients with nodule annotations by four radiologists (the XML annotations are on the collection page; DICOM SEG and SR objects derived from them are in NBIA as separate series). This manifest exposes the CT series; patients with several CT series keep the first. Series are listed through the public NBIA API (no account) and each one is downloaded as a zip of DICOM files on first access; the folder is then a DICOM volume (LPS mm from the headers).

```python
import pardesline as pl

ds = pl.load("tcia_lidc_idri")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/tcia_lidc_idri
```

## Provenance and licence

| | |
|---|---|
| Source | The Cancer Imaging Archive, collection `LIDC-IDRI` through the NBIA REST API |
| Scheme | `tcia` |
| Size of the whole source | 122.1 GB |
| Licence | CC-BY-3.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 3.0 on the TCIA collection page (checked 2026-10-14). |
| Terms | <https://www.cancerimagingarchive.net/collection/lidc-idri/> |
| Homepage | <https://www.cancerimagingarchive.net/collection/lidc-idri/> |
| Cite | Armato S.G. III, McLennan G., Bidaut L., et al. Data From LIDC-IDRI. The Cancer Imaging Archive, 2015. doi:10.7937/K9/TCIA.2015.LO9QL9SX. Clark K., Vendt B., Smith K., et al. The Cancer Imaging Archive (TCIA): Maintaining and Operating a Public Information Repository. J Digit Imaging 26(6):1045-1057, 2013. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `{id}/CT/{series}`<br>Thorax CT, DICOM series |
| `seg` | file | from the file header | from the file header |  | `{id}/SEG/{series}`<br>DICOM SEG object derived from the annotations (one of several per patient) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("tcia_lidc_idri").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `dicom`, `tcia`, `ct`, `lung`, `nodules`

<sub>Generated from `src/pardesline/data/manifests/tcia_lidc_idri.json` on 2026-10-16.</sub>
