---
title: "AbdomenAtlas 1.0 Mini: abdominal CTs with nine organ masks (first 100 of 5 195 cases)"
description: "AbdomenAtlas 1.0 Mini (Johns Hopkins): 5 195 CT volumes with nine abdominal organs annotated, per case a CT, a combined label map and one mask per organ"
---

# AbdomenAtlas 1.0 Mini: abdominal CTs with nine organ masks (first 100 of 5 195 cases)

`pl.load("hf_abdomenatlas_mini")` loads this dataset. AbdomenAtlas 1.0 Mini (Johns Hopkins): 5 195 CT volumes with nine abdominal organs annotated, per case a CT, a combined label map and one mask per organ. The repo is gated: accept its terms on huggingface.co and log in (HF_TOKEN); the package then fetches files on access. This manifest lists the first 100 cases explicitly (no repo listing needed); edit the sample list or use pl.load('hf://AbdomenAtlas/AbdomenAtlas1.0Mini/BDMAP_00001234') for others.

```python
import pardesline as pl

ds = pl.load("hf_abdomenatlas_mini")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/hf_abdomenatlas_mini
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `AbdomenAtlas/AbdomenAtlas1.0Mini`, paths `BDMAP_00000001` |
| Scheme | `hf` |
| Size of the whole source | 7.8 GB |
| Licence | CC-BY-NC-SA-4.0 (gated: accept the terms at the source first) |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 4.0, gated repository (checked 2026-10-14): non-commercial, share-alike, your own Hub token after accepting the terms. |
| Terms | <https://huggingface.co/datasets/AbdomenAtlas/AbdomenAtlas1.0Mini> |
| Homepage | <https://github.com/MrGiovanni/AbdomenAtlas> |
| Cite | Qu C., Zhang T., Qiao H., et al. AbdomenAtlas-8K: Annotating 8,000 CT Volumes for Multi-Organ Segmentation in Three Weeks. NeurIPS 2023. Li W., et al. AbdomenAtlas: A large-scale, detailed-annotated, & multi-center dataset for efficient transfer learning and open algorithmic benchmarking. Med Image Anal 97:103285, 2024. |
| Samples grouped by | id |
| Samples listed in the manifest | 100 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `BDMAP_00000001/ct.nii.gz, BDMAP_00000002/ct.nii.gz, BDMAP_00000003/ct.nii.gz`<br>Abdominal CT (NIfTI) |
| `combined_labels` | labels | from the file header | from the file header | 1=aorta, 2=gall_bladder, 3=kidney_left, 4=kidney_right, 5=liver, 6=pancreas, 7=postcava, 8=spleen … (9 labels) | `BDMAP_00000001/combined_labels.nii.gz, BDMAP_00000002/combined_labels.nii.gz, BDMAP_00000003/combined_labels.nii.gz`<br>Nine organs in one label map |
| `aorta` | labels | from the file header | from the file header | 1=aorta | `BDMAP_00000001/segmentations/aorta.nii.gz, BDMAP_00000002/segmentations/aorta.nii.gz, BDMAP_00000003/segmentations/aorta.nii.gz`<br> |
| `gall_bladder` | labels | from the file header | from the file header | 1=gall_bladder | `BDMAP_00000001/segmentations/gall_bladder.nii.gz, BDMAP_00000002/segmentations/gall_bladder.nii.gz, BDMAP_00000003/segmentations/gall_bladder.nii.gz`<br> |
| `kidney_left` | labels | from the file header | from the file header | 1=kidney_left | `BDMAP_00000001/segmentations/kidney_left.nii.gz, BDMAP_00000002/segmentations/kidney_left.nii.gz, BDMAP_00000003/segmentations/kidney_left.nii.gz`<br> |
| `kidney_right` | labels | from the file header | from the file header | 1=kidney_right | `BDMAP_00000001/segmentations/kidney_right.nii.gz, BDMAP_00000002/segmentations/kidney_right.nii.gz, BDMAP_00000003/segmentations/kidney_right.nii.gz`<br> |
| `liver` | labels | from the file header | from the file header | 1=liver | `BDMAP_00000001/segmentations/liver.nii.gz, BDMAP_00000002/segmentations/liver.nii.gz, BDMAP_00000003/segmentations/liver.nii.gz`<br> |
| `pancreas` | labels | from the file header | from the file header | 1=pancreas | `BDMAP_00000001/segmentations/pancreas.nii.gz, BDMAP_00000002/segmentations/pancreas.nii.gz, BDMAP_00000003/segmentations/pancreas.nii.gz`<br> |
| `postcava` | labels | from the file header | from the file header | 1=postcava | `BDMAP_00000001/segmentations/postcava.nii.gz, BDMAP_00000002/segmentations/postcava.nii.gz, BDMAP_00000003/segmentations/postcava.nii.gz`<br> |
| `spleen` | labels | from the file header | from the file header | 1=spleen | `BDMAP_00000001/segmentations/spleen.nii.gz, BDMAP_00000002/segmentations/spleen.nii.gz, BDMAP_00000003/segmentations/spleen.nii.gz`<br> |
| `stomach` | labels | from the file header | from the file header | 1=stomach | `BDMAP_00000001/segmentations/stomach.nii.gz, BDMAP_00000002/segmentations/stomach.nii.gz, BDMAP_00000003/segmentations/stomach.nii.gz`<br> |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_abdomenatlas_mini").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `abdomen`, `multi-organ`, `segmentation`, `nifti`, `hf`, `gated`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/hf_abdomenatlas_mini.json` on 2026-10-17.</sub>
