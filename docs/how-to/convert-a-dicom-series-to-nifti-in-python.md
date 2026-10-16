---
title: How to convert a DICOM series to NIfTI in Python
description: Convert a folder of DICOM slices into one NIfTI (or MetaImage) volume in Python with the geometry preserved: pl.load(folder).save("scan.nii.gz"), with SimpleITK underneath and a sidecar recording frame, spacing and provenance.
---

# How to convert a DICOM series to NIfTI in Python

A DICOM series is a folder of slices; a NIfTI is one file with the spacing, origin and direction in the header. pardesline reads the series with SimpleITK's series reader (slices ordered by position, geometry from the headers) and writes any volume format you name.

```python
import pardesline as pl

ct = pl.load("/data/patient01/CT")  # a folder of .dcm files -> one Volume
print(ct.info())  # size, spacing, origin, pixel type, modality from the headers
ct.save("patient01_ct.nii.gz")  # NIfTI; .nii, .mha, .nrrd, .vti work the same way
```

The sidecar `patient01_ct.nii.gz.pardesline.json` records the source folder, the frame (LPS millimetres, the DICOM convention), the licence if the object has one and the conversion step.

## From a TCIA collection or a bundled dataset

```python
s = pl.load("tcia_prostate_3t")[0]
s.mr.save(f"{s.id.replace('/', '_')}_t2.nii.gz")
```

For many series: `pl.load("tcia_prostate_3t").take(10).export("./prostate_std")` writes MetaImage volumes with sidecars; MetaImage and NIfTI carry the same geometry, and every reader (SimpleITK, ITK, nibabel, MONAI, TorchIO) opens both.

## Checks worth doing

```python
import SimpleITK as sitk

img = ct.to_sitk()
print(img.GetSpacing(), img.GetDirection())  # anisotropic slices and oblique acquisitions show here
```

- Slices with varying spacing or missing instances make the series reader warn; `ct.info()["size"]` should match the slice count.
- Multi-frame DICOM (one file with all frames) and enhanced CT/MR are read by the same reader.
- Orientation: NIfTI stores RAS, DICOM LPS; SimpleITK converts on write and on read, so the `Volume.frame` stays LPS in pardesline. Do not reorient voxel arrays by hand.

## Identifiers

pardesline reads pixel data and geometry; it does not de-identify. Remove identifiers before the data reaches any tool (DICOM PS3.15 basic profile or your institution's process).

Related: [Download a TCIA collection](download-a-tcia-collection-in-python.md) · [Guide: medical volumes](../guides/medical-volumes.md) · [Standardize a folder](standardize-a-folder-of-medical-images-in-python.md)
