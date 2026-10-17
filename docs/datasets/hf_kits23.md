---
title: "KiTS23: 489 kidney-tumour CTs with kidney, tumour and cyst labels"
description: "The 2023 Kidney and Kidney Tumor Segmentation challenge imaging as published by the organisers on the Hub: contrast-enhanced abdominal CT per case (100-280"
---

# KiTS23: 489 kidney-tumour CTs with kidney, tumour and cyst labels

`pl.load("hf_kits23")` loads this dataset. The 2023 Kidney and Kidney Tumor Segmentation challenge imaging as published by the organisers on the Hub: contrast-enhanced abdominal CT per case (100-280 MB) with a three-class label map. Two scoped folders of the repo are listed (images, segmentations).

```python
import pardesline as pl

ds = pl.load("hf_kits23")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/hf_kits23
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `neheller/KiTS-Challenge-Imaging`, paths `images, segmentations` |
| Scheme | `hf` |
| Size of the whole source | 87.9 GB |
| Licence | CC-BY-NC-SA-4.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 4.0 on the Hub card (checked 2026-10-14): non-commercial, share-alike. |
| Terms | <https://kits-challenge.org/kits23/> |
| Homepage | <https://kits-challenge.org/kits23/> |
| Cite | Heller N., Isensee F., Trofimova D., et al. The KiTS21 Challenge: Automatic segmentation of kidneys, renal tumors, and renal cysts in corticomedullary-phase CT. arXiv:2307.01984, 2023. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `images/{id}.nii.gz`<br>Abdominal CT (NIfTI) |
| `mask` | labels | from the file header | from the file header | 1=kidney, 2=tumor, 3=cyst | `segmentations/{id}.nii.gz`<br>Kidney / tumour / cyst label map |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_kits23").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `kidney`, `tumor`, `segmentation`, `nifti`, `hf`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/hf_kits23.json` on 2026-10-17.</sub>
