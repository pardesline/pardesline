---
title: "OpenMind: head-and-neck 3D MRI pooled from OpenNeuro, one study at a time"
description: "114k MRI volumes from 800 OpenNeuro studies, pooled by the nnU-Net group (MIC-DKFZ) for self-supervised pre-training, each with a deface mask and an anatom"
---

# OpenMind: head-and-neck 3D MRI pooled from OpenNeuro, one study at a time

`pl.load("hf_openmind")` loads this dataset. 114k MRI volumes from 800 OpenNeuro studies, pooled by the nnU-Net group (MIC-DKFZ) for self-supervised pre-training, each with a deface mask and an anatomy mask. The repo holds 266 721 files: listing it whole takes 15 minutes and is rate-limited for anonymous clients, so this manifest scopes the listing to one study (source.paths). pl.load('hf://MIC-DKFZ/OpenMind/OpenMind/ds000003') picks another study; openneuro_metadata.csv at the repo root indexes them all.

```python
import pardesline as pl

ds = pl.load("hf_openmind")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.t1w  # fetched now, cached under ~/.cache/pardesline/datasets/hf_openmind
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `MIC-DKFZ/OpenMind`, paths `OpenMind/ds000001` |
| Scheme | `hf` |
| Licence | CC-BY-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 4.0 on the Hub card (checked 2026-10-13); each OpenNeuro study keeps its own CC0 / CC BY terms upstream, TO CONFIRM per study before redistribution. |
| Terms | <https://huggingface.co/datasets/MIC-DKFZ/OpenMind> |
| Homepage | <https://huggingface.co/datasets/MIC-DKFZ/OpenMind> |
| Cite | Wald T., Ulrich C., Suprijadi J., et al. An OpenMind for 3D medical vision self-supervised learning. arXiv:2412.17041, 2024. |
| Samples grouped by | subject |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `t1w` | volume (MR) | from the file header | from the file header |  | `OpenMind/{study}/{subject}/anat/*_T1w.nii.gz`<br>T1-weighted MRI (NIfTI; LPS mm come from the header once loaded) |
| `t2w` | volume (MR) | from the file header | from the file header |  | `OpenMind/{study}/{subject}/anat/*T2*.nii.gz`<br>T2-weighted MRI when the study has one (inplane T2 in ds000001) |
| `deface_mask` | labels | from the file header | from the file header | 1=defaced | `OpenMind/{study}/{subject}/anat/*_T1w__Data/deface_mask.nii.gz`<br>Voxels removed by defacing on the T1w image |
| `anatomy_mask` | labels | from the file header | from the file header | 1=anatomy | `OpenMind/{study}/{subject}/anat/*_T1w__Data/fb_mask.nii.gz`<br>Voxels that hold anatomy on the T1w image (fb_mask) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_openmind").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mri`, `head`, `brain`, `nifti`, `hf`, `self-supervised`

<sub>Generated from `src/pardesline/data/manifests/hf_openmind.json` on 2026-10-14.</sub>
