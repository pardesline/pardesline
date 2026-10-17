---
title: "NSCLC-Radiomics (TCIA) as NIfTI: 422 lung-cancer CTs with organ and tumour segmentations"
description: "The Lung1 cohort of NSCLC-Radiomics (Aerts et al.), converted from TCIA DICOM + DICOM-SEG to NIfTI by farrell236"
---

# NSCLC-Radiomics (TCIA) as NIfTI: 422 lung-cancer CTs with organ and tumour segmentations

`pl.load("hf_nsclc_radiomics")` loads this dataset. The Lung1 cohort of NSCLC-Radiomics (Aerts et al.), converted from TCIA DICOM + DICOM-SEG to NIfTI by farrell236. Per patient one CT and the available structures: primary tumour (GTV-1), left and right lung, heart, oesophagus, spinal cord, plus a combined label map built by the repo's combine_segmentations.py (label values below come from that script).

```python
import pardesline as pl

ds = pl.load("hf_nsclc_radiomics")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/hf_nsclc_radiomics
```

## Provenance and licence

| | |
|---|---|
| Source | Hugging Face Hub repo `farrell236/NSCLC-Radiomics-NIFTI`, paths `NSCLC-Radiomics-NIFTI` |
| Scheme | `hf` |
| Size of the whole source | 11.7 GB |
| Licence | CC-BY-3.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 3.0 on the Hub card and on the TCIA collection page; cite the data, the publication and TCIA (checked 2026-10-13). |
| Terms | <https://www.cancerimagingarchive.net/collection/nsclc-radiomics/> |
| Homepage | <https://huggingface.co/datasets/farrell236/NSCLC-Radiomics-NIFTI> |
| Cite | Aerts H.J.W.L., Wee L., Rios Velazquez E., et al. Data From NSCLC-Radiomics (version 4). The Cancer Imaging Archive, 2019. doi:10.7937/K9/TCIA.2015.PF0M9REI. Aerts H.J.W.L. et al. Decoding tumour phenotype by noninvasive imaging using a quantitative radiomics approach. Nat Commun 5:4006, 2014. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `NSCLC-Radiomics-NIFTI/{id}/image.nii.gz`<br>Thorax CT (NIfTI, LPS mm from the header) |
| `mask` | labels | from the file header | from the file header | 1=esophagus, 2=gtv, 3=heart, 4=lung_left, 5=lung_right, 6=spinal_cord | `NSCLC-Radiomics-NIFTI/{id}/segmentation.nii.gz`<br>Combined label map (values from combine_segmentations.py in the repo) |
| `gtv` | labels | from the file header | from the file header | 1=gtv | `NSCLC-Radiomics-NIFTI/{id}/seg-GTV-1.nii.gz`<br>Primary gross tumour volume |
| `lung_left` | labels | from the file header | from the file header | 1=lung_left | `NSCLC-Radiomics-NIFTI/{id}/seg-Lung-Left.nii.gz`<br> |
| `lung_right` | labels | from the file header | from the file header | 1=lung_right | `NSCLC-Radiomics-NIFTI/{id}/seg-Lung-Right.nii.gz`<br> |
| `heart` | labels | from the file header | from the file header | 1=heart | `NSCLC-Radiomics-NIFTI/{id}/seg-Heart.nii.gz`<br> |
| `esophagus` | labels | from the file header | from the file header | 1=esophagus | `NSCLC-Radiomics-NIFTI/{id}/seg-Esophagus.nii.gz`<br> |
| `spinal_cord` | labels | from the file header | from the file header | 1=spinal_cord | `NSCLC-Radiomics-NIFTI/{id}/seg-Spinal-Cord.nii.gz`<br> |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("hf_nsclc_radiomics").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `lung`, `thorax`, `segmentation`, `oncology`, `nifti`, `hf`, `tcia`

<sub>Generated from `src/pardesline/data/manifests/hf_nsclc_radiomics.json` on 2026-10-14.</sub>
