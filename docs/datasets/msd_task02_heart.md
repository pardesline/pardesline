---
title: "Medical Segmentation Decathlon, Task02 Heart: left-atrium segmentation on 30 cardiac MRIs"
description: "Twenty training MRIs with the left atrium labelled (King's College London) and ten unlabelled test MRIs, read member by member out of the official 456 MB t"
---

# Medical Segmentation Decathlon, Task02 Heart: left-atrium segmentation on 30 cardiac MRIs

`pl.load("msd_task02_heart")` loads this dataset. Twenty training MRIs with the left atrium labelled (King's College London) and ten unlabelled test MRIs, read member by member out of the official 456 MB tar on S3 (HTTP Range; the 61 headers cost 32 KB, each volume its own size). The reference cardiac-segmentation exercise: mask.to_mesh(label=1) gives the atrium surface in LPS millimetres. ds.filter(split='Tr') keeps the labelled cases.

```python
import pardesline as pl

ds = pl.load("msd_task02_heart")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mri  # fetched now, cached under ~/.cache/pardesline/datasets/msd_task02_heart
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://msd-for-monai.s3-us-west-2.amazonaws.com/Task02_Heart.tar` |
| Scheme | `archive` |
| Size of the whole source | 456 MB |
| Licence | CC-BY-SA-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC-BY-SA 4.0 as stated in the archive's dataset.json (checked 2026-10-13); share-alike applies to derived data. |
| Terms | <http://medicaldecathlon.com/> |
| Homepage | <http://medicaldecathlon.com/> |
| Cite | Antonelli M., Reinke A., Bakas S., et al. The Medical Segmentation Decathlon. Nat Commun 13:4128, 2022. Simpson A.L. et al. A large annotated medical image dataset for the development and evaluation of segmentation algorithms. arXiv:1902.09063, 2019. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mri` | volume (MR) | from the file header | from the file header |  | `Task02_Heart/images{split}/{id}.nii.gz`<br>Cardiac MRI (NIfTI, LPS mm from the header); split Tr = labelled, Ts = test |
| `mask` | labels | from the file header | from the file header | 1=left_atrium | `Task02_Heart/labelsTr/{id}.nii.gz`<br>Left-atrium label map (training cases only) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("msd_task02_heart").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mri`, `heart`, `cardiac`, `left-atrium`, `segmentation`, `nifti`, `msd`

<sub>Generated from `src/pardesline/data/manifests/msd_task02_heart.json` on 2026-10-16.</sub>
