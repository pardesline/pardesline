---
title: "TotalSegmentator MRI dataset v1.0.0: 298 MRI volumes with 56 anatomical structures"
description: "298 MRI examinations (various sequences and regions) with 56 structures segmented as one binary mask per structure"
---

# TotalSegmentator MRI dataset v1.0.0: 298 MRI volumes with 56 anatomical structures

`pl.load("totalsegmentator_mri")` loads this dataset. 298 MRI examinations (various sequences and regions) with 56 structures segmented as one binary mask per structure. Read subject by subject out of the 2.4 GB zip on Zenodo by HTTP Range.

```python
import pardesline as pl

ds = pl.load("totalsegmentator_mri")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.mri  # fetched now, cached under ~/.cache/pardesline/datasets/totalsegmentator_mri
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/11367005/files/TotalsegmentatorMRI_dataset_v100.zip` |
| Scheme | `archive` |
| Size of the whole source | 2.3 GB |
| Licence | CC-BY-NC-SA-2.0 |
| Commercial use | not allowed (non-commercial licence) |
| Redistribution | allowed |
| Licence note | CC BY-NC-SA 2.0 on the Zenodo record (checked 2026-10-14): non-commercial, share-alike. |
| Terms | <https://zenodo.org/records/11367005> |
| Homepage | <https://github.com/wasserth/TotalSegmentator> |
| Cite | D'Antonoli T.A., Berger L.K., Indrakanti A.K., et al. TotalSegmentator MRI: Sequence-Independent Segmentation of 59 Anatomical Structures in MR images. Radiology 314(2), 2025. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `mri` | volume (MR) | from the file header | from the file header |  | `{id}/mri.nii.gz`<br>MRI image (NIfTI, LPS mm from the header) |
| `adrenal_gland_left` | labels | from the file header | from the file header | 1=adrenal_gland_left | `{id}/segmentations/adrenal_gland_left.nii.gz`<br> |
| `adrenal_gland_right` | labels | from the file header | from the file header | 1=adrenal_gland_right | `{id}/segmentations/adrenal_gland_right.nii.gz`<br> |
| `aorta` | labels | from the file header | from the file header | 1=aorta | `{id}/segmentations/aorta.nii.gz`<br> |
| `autochthon_left` | labels | from the file header | from the file header | 1=autochthon_left | `{id}/segmentations/autochthon_left.nii.gz`<br> |
| `autochthon_right` | labels | from the file header | from the file header | 1=autochthon_right | `{id}/segmentations/autochthon_right.nii.gz`<br> |
| `brain` | labels | from the file header | from the file header | 1=brain | `{id}/segmentations/brain.nii.gz`<br> |
| `colon` | labels | from the file header | from the file header | 1=colon | `{id}/segmentations/colon.nii.gz`<br> |
| `duodenum` | labels | from the file header | from the file header | 1=duodenum | `{id}/segmentations/duodenum.nii.gz`<br> |
| `esophagus` | labels | from the file header | from the file header | 1=esophagus | `{id}/segmentations/esophagus.nii.gz`<br> |
| `femur_left` | labels | from the file header | from the file header | 1=femur_left | `{id}/segmentations/femur_left.nii.gz`<br> |
| `femur_right` | labels | from the file header | from the file header | 1=femur_right | `{id}/segmentations/femur_right.nii.gz`<br> |
| `fibula` | labels | from the file header | from the file header | 1=fibula | `{id}/segmentations/fibula.nii.gz`<br> |
| `gallbladder` | labels | from the file header | from the file header | 1=gallbladder | `{id}/segmentations/gallbladder.nii.gz`<br> |
| `gluteus_maximus_left` | labels | from the file header | from the file header | 1=gluteus_maximus_left | `{id}/segmentations/gluteus_maximus_left.nii.gz`<br> |
| `gluteus_maximus_right` | labels | from the file header | from the file header | 1=gluteus_maximus_right | `{id}/segmentations/gluteus_maximus_right.nii.gz`<br> |
| `gluteus_medius_left` | labels | from the file header | from the file header | 1=gluteus_medius_left | `{id}/segmentations/gluteus_medius_left.nii.gz`<br> |
| `gluteus_medius_right` | labels | from the file header | from the file header | 1=gluteus_medius_right | `{id}/segmentations/gluteus_medius_right.nii.gz`<br> |
| `gluteus_minimus_left` | labels | from the file header | from the file header | 1=gluteus_minimus_left | `{id}/segmentations/gluteus_minimus_left.nii.gz`<br> |
| `gluteus_minimus_right` | labels | from the file header | from the file header | 1=gluteus_minimus_right | `{id}/segmentations/gluteus_minimus_right.nii.gz`<br> |
| `heart` | labels | from the file header | from the file header | 1=heart | `{id}/segmentations/heart.nii.gz`<br> |
| `hip_left` | labels | from the file header | from the file header | 1=hip_left | `{id}/segmentations/hip_left.nii.gz`<br> |
| `hip_right` | labels | from the file header | from the file header | 1=hip_right | `{id}/segmentations/hip_right.nii.gz`<br> |
| `humerus_left` | labels | from the file header | from the file header | 1=humerus_left | `{id}/segmentations/humerus_left.nii.gz`<br> |
| `humerus_right` | labels | from the file header | from the file header | 1=humerus_right | `{id}/segmentations/humerus_right.nii.gz`<br> |
| `iliac_artery_left` | labels | from the file header | from the file header | 1=iliac_artery_left | `{id}/segmentations/iliac_artery_left.nii.gz`<br> |
| `iliac_artery_right` | labels | from the file header | from the file header | 1=iliac_artery_right | `{id}/segmentations/iliac_artery_right.nii.gz`<br> |
| `iliac_vena_left` | labels | from the file header | from the file header | 1=iliac_vena_left | `{id}/segmentations/iliac_vena_left.nii.gz`<br> |
| `iliac_vena_right` | labels | from the file header | from the file header | 1=iliac_vena_right | `{id}/segmentations/iliac_vena_right.nii.gz`<br> |
| `iliopsoas_left` | labels | from the file header | from the file header | 1=iliopsoas_left | `{id}/segmentations/iliopsoas_left.nii.gz`<br> |
| `iliopsoas_right` | labels | from the file header | from the file header | 1=iliopsoas_right | `{id}/segmentations/iliopsoas_right.nii.gz`<br> |
| `inferior_vena_cava` | labels | from the file header | from the file header | 1=inferior_vena_cava | `{id}/segmentations/inferior_vena_cava.nii.gz`<br> |
| `intervertebral_discs` | labels | from the file header | from the file header | 1=intervertebral_discs | `{id}/segmentations/intervertebral_discs.nii.gz`<br> |
| `kidney_left` | labels | from the file header | from the file header | 1=kidney_left | `{id}/segmentations/kidney_left.nii.gz`<br> |
| `kidney_right` | labels | from the file header | from the file header | 1=kidney_right | `{id}/segmentations/kidney_right.nii.gz`<br> |
| `liver` | labels | from the file header | from the file header | 1=liver | `{id}/segmentations/liver.nii.gz`<br> |
| `lung_left` | labels | from the file header | from the file header | 1=lung_left | `{id}/segmentations/lung_left.nii.gz`<br> |
| `lung_right` | labels | from the file header | from the file header | 1=lung_right | `{id}/segmentations/lung_right.nii.gz`<br> |
| `pancreas` | labels | from the file header | from the file header | 1=pancreas | `{id}/segmentations/pancreas.nii.gz`<br> |
| `portal_vein_and_splenic_vein` | labels | from the file header | from the file header | 1=portal_vein_and_splenic_vein | `{id}/segmentations/portal_vein_and_splenic_vein.nii.gz`<br> |
| `prostate` | labels | from the file header | from the file header | 1=prostate | `{id}/segmentations/prostate.nii.gz`<br> |
| `quadriceps_femoris_left` | labels | from the file header | from the file header | 1=quadriceps_femoris_left | `{id}/segmentations/quadriceps_femoris_left.nii.gz`<br> |
| `quadriceps_femoris_right` | labels | from the file header | from the file header | 1=quadriceps_femoris_right | `{id}/segmentations/quadriceps_femoris_right.nii.gz`<br> |
| `sacrum` | labels | from the file header | from the file header | 1=sacrum | `{id}/segmentations/sacrum.nii.gz`<br> |
| `sartorius_left` | labels | from the file header | from the file header | 1=sartorius_left | `{id}/segmentations/sartorius_left.nii.gz`<br> |
| `sartorius_right` | labels | from the file header | from the file header | 1=sartorius_right | `{id}/segmentations/sartorius_right.nii.gz`<br> |
| `small_bowel` | labels | from the file header | from the file header | 1=small_bowel | `{id}/segmentations/small_bowel.nii.gz`<br> |
| `spinal_cord` | labels | from the file header | from the file header | 1=spinal_cord | `{id}/segmentations/spinal_cord.nii.gz`<br> |
| `spleen` | labels | from the file header | from the file header | 1=spleen | `{id}/segmentations/spleen.nii.gz`<br> |
| `stomach` | labels | from the file header | from the file header | 1=stomach | `{id}/segmentations/stomach.nii.gz`<br> |
| `thigh_medial_compartment_left` | labels | from the file header | from the file header | 1=thigh_medial_compartment_left | `{id}/segmentations/thigh_medial_compartment_left.nii.gz`<br> |
| `thigh_medial_compartment_right` | labels | from the file header | from the file header | 1=thigh_medial_compartment_right | `{id}/segmentations/thigh_medial_compartment_right.nii.gz`<br> |
| `thigh_posterior_compartment_left` | labels | from the file header | from the file header | 1=thigh_posterior_compartment_left | `{id}/segmentations/thigh_posterior_compartment_left.nii.gz`<br> |
| `thigh_posterior_compartment_right` | labels | from the file header | from the file header | 1=thigh_posterior_compartment_right | `{id}/segmentations/thigh_posterior_compartment_right.nii.gz`<br> |
| `tibia` | labels | from the file header | from the file header | 1=tibia | `{id}/segmentations/tibia.nii.gz`<br> |
| `urinary_bladder` | labels | from the file header | from the file header | 1=urinary_bladder | `{id}/segmentations/urinary_bladder.nii.gz`<br> |
| `vertebrae` | labels | from the file header | from the file header | 1=vertebrae | `{id}/segmentations/vertebrae.nii.gz`<br> |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("totalsegmentator_mri").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `mri`, `segmentation`, `nifti`, `whole-body`, `totalsegmentator`

<sub>Generated from `src/pardesline/data/manifests/totalsegmentator_mri.json` on 2026-10-14.</sub>
