---
title: "SPIDER: lumbar spine MRI (T1, T2, T2 SPACE) of 218 patients with vertebra, disc and canal masks"
description: "447 sagittal lumbar MRI series (T1, T2, some T2 SPACE) of 218 patients with low back pain, with masks of vertebrae, intervertebral discs and spinal canal, "
---

# SPIDER: lumbar spine MRI (T1, T2, T2 SPACE) of 218 patients with vertebra, disc and canal masks

`pl.load("spider_lumbar_mri")` loads this dataset. 447 sagittal lumbar MRI series (T1, T2, some T2 SPACE) of 218 patients with low back pain, with masks of vertebrae, intervertebral discs and spinal canal, as MetaImage. Two zips on Zenodo (images, masks) read series by series with HTTP Range. Label values: vertebrae numbered from L5 upward (1 = L5), 100 = spinal canal, discs numbered from L5/S1 upward (201 = L5/S1) - mapping TO CONFIRM against the dataset paper for the upper levels. Radiological gradings are in a CSV on the record.

```python
import pardesline as pl

ds = pl.load("spider_lumbar_mri")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.t1  # fetched now, cached under ~/.cache/pardesline/datasets/spider_lumbar_mri
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/10159290/files/images.zip`, `https://zenodo.org/records/10159290/files/masks.zip` |
| Scheme | `archive` |
| Size of the whole source | 3.7 GB |
| Licence | CC-BY-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 4.0 on the Zenodo record (checked 2026-10-14). |
| Terms | <https://zenodo.org/records/10159290> |
| Homepage | <https://spider.grand-challenge.org/> |
| Cite | van der Graaf J.W., van Hooff M.L., Buckens C.F.M., et al. Lumbar spine segmentation in MR images: a dataset and a public benchmark. Sci Data 11:264, 2024. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `t1` | volume (MR) | from the file header | from the file header |  | `images/{id}_t1.mha`<br>Sagittal T1 |
| `t2` | volume (MR) | from the file header | from the file header |  | `images/{id}_t2.mha`<br>Sagittal T2 |
| `t2_space` | volume (MR) | from the file header | from the file header |  | `images/{id}_t2_SPACE.mha`<br>3-D T2 SPACE when acquired |
| `t1_mask` | labels | from the file header | from the file header | 1=vertebra_L5, 2=vertebra_L4, 3=vertebra_L3, 4=vertebra_L2, 5=vertebra_L1, 6=vertebra_T12, 7=vertebra_T11, 8=vertebra_T10 … (19 labels) | `masks/{id}_t1.mha`<br> |
| `t2_mask` | labels | from the file header | from the file header | 1=vertebra_L5, 2=vertebra_L4, 3=vertebra_L3, 4=vertebra_L2, 5=vertebra_L1, 6=vertebra_T12, 7=vertebra_T11, 8=vertebra_T10 … (19 labels) | `masks/{id}_t2.mha`<br> |
| `t2_space_mask` | labels | from the file header | from the file header | 1=vertebra_L5, 2=vertebra_L4, 3=vertebra_L3, 4=vertebra_L2, 5=vertebra_L1, 6=vertebra_T12, 7=vertebra_T11, 8=vertebra_T10 … (19 labels) | `masks/{id}_t2_SPACE.mha`<br> |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("spider_lumbar_mri").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](https://github.com/pardesline/pardesline/blob/main/CONTRIBUTING.md#adding-a-dataset)
- Tags: `medical`, `mri`, `spine`, `lumbar`, `segmentation`, `metaimage`

<sub>Generated from `src/pardesline/data/manifests/spider_lumbar_mri.json` on 2026-10-14.</sub>
