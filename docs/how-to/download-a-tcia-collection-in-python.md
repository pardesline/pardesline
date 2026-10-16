---
title: How to download a TCIA collection in Python
description: Download DICOM series from The Cancer Imaging Archive in Python without the NBIA Data Retriever: tcia://Collection through the public REST API, series as folders, one volume per series, licence attached.
---

# How to download a TCIA collection in Python

The Cancer Imaging Archive serves public collections through the NBIA REST API: `getSeries` lists the series of a collection, `getImage` returns one series as a zip of DICOM files. pardesline wraps both as a dataset source: every series is a sample whose role is a DICOM folder that opens as one `Volume`.

```python
import pardesline as pl

ds = pl.load("tcia_pancreas_ct")  # bundled: Pancreas-CT, 82 CTs, CC-BY-3.0
print(ds.describe())
s = ds[0]
print(s.id, s.fields)  # PatientID / Modality / SeriesInstanceUID, ImageCount, ...
ct = s.ct  # the series zip is fetched and unpacked once (about 100 MB)
print(ct.info())  # one volume, LPS mm from the DICOM headers
ct.save("pancreas_0001.nii.gz")  # NIfTI + sidecar
```

Four collections ship with a manifest: `tcia_pancreas_ct`, `tcia_lidc_idri`, `tcia_nsclc_radiomics_dicom`, `tcia_prostate_3t`.

## Any public collection

```python
ds = pl.load("tcia://Pancreas-CT")  # same as the bundled one
ds = pl.load("tcia://CPTAC-PDA/CT,MR")  # a collection, restricted to the CT and MR modalities
```

The collection name is the one on cancerimagingarchive.net. Restricted collections answer 401: they need the TCIA Data Retriever and your credentials, which pardesline does not handle. Licences are per collection (most CC BY 3.0 or 4.0, some non-commercial): the drafted manifest asks you to confirm it from the collection page, the bundled ones record it.

## Segmentations and RT structures

LIDC-IDRI and NSCLC-Radiomics also carry DICOM SEG and RTSTRUCT series; they appear as their own samples (`Modality` field `SEG` / `RTSTRUCT`). Converting them to label maps on the CT grid is not built in yet: `pydicom-seg` and `rt-utils` do it from the folder `s.path("seg")` returns.

## Size and time

`describe_dataset` and `s.fields["ImageCount"]` tell you the slice count before downloading. LIDC-IDRI is 122 GB in all; `ds.filter(Modality="CT").take(5).fetch_all()` gets five CTs.

Related: [Convert a DICOM series to NIfTI](convert-a-dicom-series-to-nifti-in-python.md) · [Datasets catalog](../datasets/index.md)
