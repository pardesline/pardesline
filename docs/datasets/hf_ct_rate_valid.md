---
title: "CT-RATE: non-contrast chest CTs paired with radiology reports (first 20 validation cases)"
description: "CT-RATE (Istanbul Medipol / University of Zurich): 50 188 chest CT volumes from 21 304 patients with radiology reports and multi-abnormality labels"
---

# CT-RATE: non-contrast chest CTs paired with radiology reports (first 20 validation cases)

`pl.load("hf_ct_rate_valid")` loads this dataset. CT-RATE (Istanbul Medipol / University of Zurich): 50 188 chest CT volumes from 21 304 patients with radiology reports and multi-abnormality labels. The repo is gated: accept its terms on huggingface.co and log in (HF_TOKEN). This manifest lists the first reconstruction of the first 20 validation patients explicitly (one 200-500 MB NIfTI each); reports and labels are CSV files under dataset/ in the same repo.

```python
import pardesline as pl

ds = pl.load("hf_ct_rate_valid")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/hf_ct_rate_valid
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `ibrahimhamamci/CT-RATE`, paths `dataset/valid/valid_1` |
| Scheme | `hf` |
| Size of the whole source | 6.8 GB |
| Licence | CC-BY-NC-SA-4.0 (gated: accept the terms at the source first) |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 4.0, gated repository (checked 2026-10-14): non-commercial, share-alike, your own Hub token after accepting the terms. |
| Terms | <https://huggingface.co/datasets/ibrahimhamamci/CT-RATE> |
| Homepage | <https://huggingface.co/datasets/ibrahimhamamci/CT-RATE> |
| Cite | Hamamci I.E., Er S., Almas F., et al. Developing Generalist Foundation Models from a Multimodal Dataset for 3D Computed Tomography. arXiv:2403.17834, 2024. |
| Samples grouped by | patient |
| Samples listed in the manifest | 20 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `dataset/valid/valid_1/valid_1_a/valid_1_a_1.nii.gz, dataset/valid/valid_10/valid_10_a/valid_10_a_1.nii.gz, dataset/valid/valid_11/valid_11_a/valid_11_a_1.nii.gz`<br>Non-contrast chest CT (NIfTI), first reconstruction of the study |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_ct_rate_valid").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `chest`, `reports`, `nifti`, `hf`, `gated`, `non-commercial`

<sub>Generated from `src/pardesline/data/manifests/hf_ct_rate_valid.json` on 2026-10-16.</sub>
