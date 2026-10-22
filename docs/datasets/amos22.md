---
title: "AMOS 22: abdominal multi-organ segmentation, 600 CT and MRI with 15 organ labels"
description: "The AMOS benchmark (Ji et al., NeurIPS 2022): 500 CT and 100 MRI scans with 15 abdominal organs annotated; 240 training, 120 validation and 240 test images"
---

# AMOS 22: abdominal multi-organ segmentation, 600 CT and MRI with 15 organ labels

`pl.load("amos22")` loads this dataset. The AMOS benchmark (Ji et al., NeurIPS 2022): 500 CT and 100 MRI scans with 15 abdominal organs annotated; 240 training, 120 validation and 240 test images. Read case by case out of the 24 GB zip64 archive on Zenodo (HTTP Range: the 1 207-entry central directory costs 145 KB, one case its own size). Case ids below 500 are CT, 500 and above are MRI. ds.filter(split='Tr') or 'Va' keeps the labelled cases.

```python
import pardesline as pl

ds = pl.load("amos22")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.image  # fetched now, cached under ~/.cache/pardesline/datasets/amos22
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/7262581/files/amos22.zip` |
| Scheme | `archive` |
| Size of the whole source | 23.7 GB |
| Licence | CC-BY-SA-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC-BY-SA 4.0 as stated in the archive's dataset.json (checked 2026-10-13); the Zenodo record page lists its own licence field, TO CONFIRM that both agree before redistribution. |
| Terms | <https://zenodo.org/records/7262581> |
| Homepage | <https://amos22.grand-challenge.org/> |
| Cite | Ji Y., Bai H., Ge C., et al. AMOS: A Large-Scale Abdominal Multi-Organ Benchmark for Versatile Medical Image Segmentation. NeurIPS 2022 Datasets and Benchmarks. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `image` | volume | from the file header | from the file header |  | `amos22/images{split}/{id}.nii.gz`<br>Abdominal CT (ids < 500) or MRI (ids >= 500), NIfTI, LPS mm from the header |
| `mask` | labels | from the file header | from the file header | 1=spleen, 2=right_kidney, 3=left_kidney, 4=gall_bladder, 5=esophagus, 6=liver, 7=stomach, 8=aorta … (15 labels) | `amos22/labels{split}/{id}.nii.gz`<br>15-organ label map (training and validation cases) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("amos22").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](https://github.com/pardesline/pardesline/blob/main/CONTRIBUTING.md#adding-a-dataset)
- Tags: `medical`, `ct`, `mri`, `abdomen`, `multi-organ`, `segmentation`, `nifti`, `zenodo`

<sub>Generated from `src/pardesline/data/manifests/amos22.json` on 2026-10-14.</sub>
