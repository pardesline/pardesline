---
title: "VerSe 2019: 160 spine CTs with vertebra-level label maps and centroids"
description: "The Large Scale Vertebrae Segmentation Challenge 2019 (training, validation and test splits, 80 + 40 + 40 scans): spine CT in NIfTI with a 28-class vertebr"
---

# VerSe 2019: 160 spine CTs with vertebra-level label maps and centroids

`pl.load("verse19_spine")` loads this dataset. The Large Scale Vertebrae Segmentation Challenge 2019 (training, validation and test splits, 80 + 40 + 40 scans): spine CT in NIfTI with a 28-class vertebra label map and a JSON of vertebra centroids per scan. Three zips on the BoneScreen S3 bucket read scan by scan with HTTP Range. VerSe 2020 is the same layout under dataset-verse20*.zip.

```python
import pardesline as pl

ds = pl.load("verse19_spine")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/verse19_spine
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://s3.bonescreen.de/public/VerSe-complete/dataset-verse19training.zip`, `https://s3.bonescreen.de/public/VerSe-complete/dataset-verse19validation.zip`, `https://s3.bonescreen.de/public/VerSe-complete/dataset-verse19test.zip` |
| Scheme | `archive` |
| Size of the whole source | 12.0 GB |
| Licence | CC-BY-SA-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY-SA 4.0 as stated in the VerSe repository (checked 2026-10-14). |
| Terms | <https://github.com/anjany/verse> |
| Homepage | <https://github.com/anjany/verse> |
| Cite | Sekuboyina A., Husseini M.E., Bayat A., et al. VerSe: A Vertebrae labelling and segmentation benchmark for multi-detector CT images. Med Image Anal 73:102166, 2021. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `dataset-verse19{split}/rawdata/{id}/{id}_ct.nii.gz`<br>Spine CT (NIfTI); field split = training / validation / test |
| `mask` | labels | from the file header | from the file header | 1=C1, 2=C2, 3=C3, 4=C4, 5=C5, 6=C6, 7=C7, 8=T1 … (28 labels) | `dataset-verse19{split}/derivatives/{id}/{id}_seg-vert_msk.nii.gz`<br>Vertebra label map (VerSe convention: 1-7 cervical, 8-19 thoracic, 20-25 lumbar, 26 sacrum, 27 cocygis, 28 T13) |
| `centroids` | file | from the file header | from the file header |  | `dataset-verse19{split}/derivatives/{id}/{id}_seg-subreg_ctd.json`<br>Vertebra centroids and direction (JSON) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("verse19_spine").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `spine`, `vertebrae`, `segmentation`, `nifti`

<sub>Generated from `src/pardesline/data/manifests/verse19_spine.json` on 2026-10-16.</sub>
