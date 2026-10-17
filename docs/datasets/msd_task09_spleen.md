---
title: "Medical Segmentation Decathlon, Task09 Spleen"
description: "Spleen: 41 + 20 portal-venous CTs (MSKCC)"
---

# Medical Segmentation Decathlon, Task09 Spleen

`pl.load("msd_task09_spleen")` loads this dataset. Spleen: 41 + 20 portal-venous CTs (MSKCC). Read case by case out of the official MSD tar on S3 (HTTP Range: one 512-byte header per member to index, each volume its own size). ds.filter(split='Tr') keeps the labelled cases; the test split has images only.

```python
import pardesline as pl

ds = pl.load("msd_task09_spleen")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/msd_task09_spleen
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://msd-for-monai.s3-us-west-2.amazonaws.com/Task09_Spleen.tar` |
| Scheme | `archive` |
| Size of the whole source | 1.6 GB |
| Licence | CC-BY-SA-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC-BY-SA 4.0 as stated in the archive's dataset.json (checked 2026-10-14); share-alike applies to derived data. |
| Terms | <http://medicaldecathlon.com/> |
| Homepage | <http://medicaldecathlon.com/> |
| Cite | Antonelli M., Reinke A., Bakas S., et al. The Medical Segmentation Decathlon. Nat Commun 13:4128, 2022. Simpson A.L. et al. A large annotated medical image dataset for the development and evaluation of segmentation algorithms. arXiv:1902.09063, 2019. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `Task09_Spleen/images{split}/{id}.nii.gz`<br>CT image (NIfTI, LPS mm from the header); split Tr = labelled, Ts = test |
| `mask` | labels | from the file header | from the file header | 1=spleen | `Task09_Spleen/labelsTr/{id}.nii.gz`<br>Label map (training cases only) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("msd_task09_spleen").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `segmentation`, `nifti`, `msd`, `spleen`, `abdomen`

<sub>Generated from `src/pardesline/data/manifests/msd_task09_spleen.json` on 2026-10-14.</sub>
