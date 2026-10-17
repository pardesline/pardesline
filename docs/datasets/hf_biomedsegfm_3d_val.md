---
title: "CVPR 2025 BiomedSegFM, 3-D validation set: 2 144 CT / MRI / PET / 3-D ultrasound / microscopy volumes as npz"
description: "The validation volumes of the CVPR 2025 Foundation Models for Interactive 3D Biomedical Image Segmentation challenge (Ma et al.), pooled from 30+ public da"
---

# CVPR 2025 BiomedSegFM, 3-D validation set: 2 144 CT / MRI / PET / 3-D ultrasound / microscopy volumes as npz

`pl.load("hf_biomedsegfm_3d_val")` loads this dataset. The validation volumes of the CVPR 2025 Foundation Models for Interactive 3D Biomedical Image Segmentation challenge (Ma et al.), pooled from 30+ public datasets (AMOS, AbdomenAtlas, TotalSegmentator, BraTS, ...). Each case is an .npz with 'imgs' (the volume), 'gts' (the label map) and 'spacing'; the spacing key cannot be carried by the layout, so the grids load with unit spacing (read s.path('image') with numpy for the real spacing). The field modality is CT, MRI, PET, US3D or Microscopy.

```python
import pardesline as pl

ds = pl.load("hf_biomedsegfm_3d_val")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.image  # fetched now, cached under ~/.cache/pardesline/datasets/hf_biomedsegfm_3d_val
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `junma/CVPR-BiomedSegFM`, paths `3D_val_npz` |
| Scheme | `hf` |
| Size of the whole source | 19.5 GB |
| Licence | CC-BY-NC-SA-4.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 4.0 on the Hub card (checked 2026-10-14); each pooled source dataset keeps its own terms, TO CONFIRM per case. |
| Terms | <https://huggingface.co/datasets/junma/CVPR-BiomedSegFM> |
| Homepage | <https://www.codabench.org/competitions/5263/> |
| Cite | Ma J., et al. CVPR 2025 Challenge: Foundation Models for Interactive 3D Biomedical Image Segmentation. 2025. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `image` | volume | from the file header | from the file header | layout:  (Z,Y,X) | `3D_val_npz/{modality}_{id}.npz`<br>The volume ('imgs' array; spacing in the 'spacing' key of the same file) |
| `mask` | labels | from the file header | from the file header | layout:  (Z,Y,X) | `3D_val_npz/{modality}_{id}.npz`<br>Label map ('gts' array); class ids per source dataset |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_biomedsegfm_3d_val").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `mri`, `pet`, `ultrasound`, `microscopy`, `segmentation`, `npz`, `hf`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/hf_biomedsegfm_3d_val.json` on 2026-10-14.</sub>
