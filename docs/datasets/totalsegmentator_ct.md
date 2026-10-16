---
title: "TotalSegmentator CT dataset v2.0.1: 1 228 CT volumes with 117 anatomical structures"
description: "1 228 CT examinations from the University Hospital Basel with 117 structures segmented (organs, vessels, bones, muscles) as one binary mask per structure -"
---

# TotalSegmentator CT dataset v2.0.1: 1 228 CT volumes with 117 anatomical structures

`pl.load("totalsegmentator_ct")` loads this dataset. 1 228 CT examinations from the University Hospital Basel with 117 structures segmented (organs, vessels, bones, muscles) as one binary mask per structure - the data behind the TotalSegmentator model. Read subject by subject out of the 23.6 GB zip on Zenodo (HTTP Range: the 144 905-entry central directory costs 14 MB once, a CT a few MB). meta.csv at the archive root gives age, gender, institute and split.

```python
import pardesline as pl

ds = pl.load("totalsegmentator_ct")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/totalsegmentator_ct
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/10047292/files/Totalsegmentator_dataset_v201.zip` |
| Scheme | `archive` |
| Size of the whole source | 23.0 GB |
| Licence | CC-BY-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 4.0 on the Zenodo record (checked 2026-10-14). The TotalSegmentator model weights are a separate work under their own (non-commercial) terms. |
| Terms | <https://zenodo.org/records/10047292> |
| Homepage | <https://github.com/wasserth/TotalSegmentator> |
| Cite | Wasserthal J., Breit H.-C., Meyer M.T., et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. Radiology: AI 5(5), 2023. |
| Samples grouped by | id |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `{id}/ct.nii.gz`<br>CT image (NIfTI, LPS mm from the header) |
| `adrenal_gland_left` | labels | from the file header | from the file header | 1=adrenal_gland_left | `{id}/segmentations/adrenal_gland_left.nii.gz`<br> |
| `adrenal_gland_right` | labels | from the file header | from the file header | 1=adrenal_gland_right | `{id}/segmentations/adrenal_gland_right.nii.gz`<br> |
| `aorta` | labels | from the file header | from the file header | 1=aorta | `{id}/segmentations/aorta.nii.gz`<br> |
| `atrial_appendage_left` | labels | from the file header | from the file header | 1=atrial_appendage_left | `{id}/segmentations/atrial_appendage_left.nii.gz`<br> |
| `autochthon_left` | labels | from the file header | from the file header | 1=autochthon_left | `{id}/segmentations/autochthon_left.nii.gz`<br> |
| `autochthon_right` | labels | from the file header | from the file header | 1=autochthon_right | `{id}/segmentations/autochthon_right.nii.gz`<br> |
| `brachiocephalic_trunk` | labels | from the file header | from the file header | 1=brachiocephalic_trunk | `{id}/segmentations/brachiocephalic_trunk.nii.gz`<br> |
| `brachiocephalic_vein_left` | labels | from the file header | from the file header | 1=brachiocephalic_vein_left | `{id}/segmentations/brachiocephalic_vein_left.nii.gz`<br> |
| `brachiocephalic_vein_right` | labels | from the file header | from the file header | 1=brachiocephalic_vein_right | `{id}/segmentations/brachiocephalic_vein_right.nii.gz`<br> |
| `brain` | labels | from the file header | from the file header | 1=brain | `{id}/segmentations/brain.nii.gz`<br> |
| `clavicula_left` | labels | from the file header | from the file header | 1=clavicula_left | `{id}/segmentations/clavicula_left.nii.gz`<br> |
| `clavicula_right` | labels | from the file header | from the file header | 1=clavicula_right | `{id}/segmentations/clavicula_right.nii.gz`<br> |
| `colon` | labels | from the file header | from the file header | 1=colon | `{id}/segmentations/colon.nii.gz`<br> |
| `common_carotid_artery_left` | labels | from the file header | from the file header | 1=common_carotid_artery_left | `{id}/segmentations/common_carotid_artery_left.nii.gz`<br> |
| `common_carotid_artery_right` | labels | from the file header | from the file header | 1=common_carotid_artery_right | `{id}/segmentations/common_carotid_artery_right.nii.gz`<br> |
| `costal_cartilages` | labels | from the file header | from the file header | 1=costal_cartilages | `{id}/segmentations/costal_cartilages.nii.gz`<br> |
| `duodenum` | labels | from the file header | from the file header | 1=duodenum | `{id}/segmentations/duodenum.nii.gz`<br> |
| `esophagus` | labels | from the file header | from the file header | 1=esophagus | `{id}/segmentations/esophagus.nii.gz`<br> |
| `femur_left` | labels | from the file header | from the file header | 1=femur_left | `{id}/segmentations/femur_left.nii.gz`<br> |
| `femur_right` | labels | from the file header | from the file header | 1=femur_right | `{id}/segmentations/femur_right.nii.gz`<br> |
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
| `kidney_cyst_left` | labels | from the file header | from the file header | 1=kidney_cyst_left | `{id}/segmentations/kidney_cyst_left.nii.gz`<br> |
| `kidney_cyst_right` | labels | from the file header | from the file header | 1=kidney_cyst_right | `{id}/segmentations/kidney_cyst_right.nii.gz`<br> |
| `kidney_left` | labels | from the file header | from the file header | 1=kidney_left | `{id}/segmentations/kidney_left.nii.gz`<br> |
| `kidney_right` | labels | from the file header | from the file header | 1=kidney_right | `{id}/segmentations/kidney_right.nii.gz`<br> |
| `liver` | labels | from the file header | from the file header | 1=liver | `{id}/segmentations/liver.nii.gz`<br> |
| `lung_lower_lobe_left` | labels | from the file header | from the file header | 1=lung_lower_lobe_left | `{id}/segmentations/lung_lower_lobe_left.nii.gz`<br> |
| `lung_lower_lobe_right` | labels | from the file header | from the file header | 1=lung_lower_lobe_right | `{id}/segmentations/lung_lower_lobe_right.nii.gz`<br> |
| `lung_middle_lobe_right` | labels | from the file header | from the file header | 1=lung_middle_lobe_right | `{id}/segmentations/lung_middle_lobe_right.nii.gz`<br> |
| `lung_upper_lobe_left` | labels | from the file header | from the file header | 1=lung_upper_lobe_left | `{id}/segmentations/lung_upper_lobe_left.nii.gz`<br> |
| `lung_upper_lobe_right` | labels | from the file header | from the file header | 1=lung_upper_lobe_right | `{id}/segmentations/lung_upper_lobe_right.nii.gz`<br> |
| `pancreas` | labels | from the file header | from the file header | 1=pancreas | `{id}/segmentations/pancreas.nii.gz`<br> |
| `portal_vein_and_splenic_vein` | labels | from the file header | from the file header | 1=portal_vein_and_splenic_vein | `{id}/segmentations/portal_vein_and_splenic_vein.nii.gz`<br> |
| `prostate` | labels | from the file header | from the file header | 1=prostate | `{id}/segmentations/prostate.nii.gz`<br> |
| `pulmonary_vein` | labels | from the file header | from the file header | 1=pulmonary_vein | `{id}/segmentations/pulmonary_vein.nii.gz`<br> |
| `rib_left_1` | labels | from the file header | from the file header | 1=rib_left_1 | `{id}/segmentations/rib_left_1.nii.gz`<br> |
| `rib_left_10` | labels | from the file header | from the file header | 1=rib_left_10 | `{id}/segmentations/rib_left_10.nii.gz`<br> |
| `rib_left_11` | labels | from the file header | from the file header | 1=rib_left_11 | `{id}/segmentations/rib_left_11.nii.gz`<br> |
| `rib_left_12` | labels | from the file header | from the file header | 1=rib_left_12 | `{id}/segmentations/rib_left_12.nii.gz`<br> |
| `rib_left_2` | labels | from the file header | from the file header | 1=rib_left_2 | `{id}/segmentations/rib_left_2.nii.gz`<br> |
| `rib_left_3` | labels | from the file header | from the file header | 1=rib_left_3 | `{id}/segmentations/rib_left_3.nii.gz`<br> |
| `rib_left_4` | labels | from the file header | from the file header | 1=rib_left_4 | `{id}/segmentations/rib_left_4.nii.gz`<br> |
| `rib_left_5` | labels | from the file header | from the file header | 1=rib_left_5 | `{id}/segmentations/rib_left_5.nii.gz`<br> |
| `rib_left_6` | labels | from the file header | from the file header | 1=rib_left_6 | `{id}/segmentations/rib_left_6.nii.gz`<br> |
| `rib_left_7` | labels | from the file header | from the file header | 1=rib_left_7 | `{id}/segmentations/rib_left_7.nii.gz`<br> |
| `rib_left_8` | labels | from the file header | from the file header | 1=rib_left_8 | `{id}/segmentations/rib_left_8.nii.gz`<br> |
| `rib_left_9` | labels | from the file header | from the file header | 1=rib_left_9 | `{id}/segmentations/rib_left_9.nii.gz`<br> |
| `rib_right_1` | labels | from the file header | from the file header | 1=rib_right_1 | `{id}/segmentations/rib_right_1.nii.gz`<br> |
| `rib_right_10` | labels | from the file header | from the file header | 1=rib_right_10 | `{id}/segmentations/rib_right_10.nii.gz`<br> |
| `rib_right_11` | labels | from the file header | from the file header | 1=rib_right_11 | `{id}/segmentations/rib_right_11.nii.gz`<br> |
| `rib_right_12` | labels | from the file header | from the file header | 1=rib_right_12 | `{id}/segmentations/rib_right_12.nii.gz`<br> |
| `rib_right_2` | labels | from the file header | from the file header | 1=rib_right_2 | `{id}/segmentations/rib_right_2.nii.gz`<br> |
| `rib_right_3` | labels | from the file header | from the file header | 1=rib_right_3 | `{id}/segmentations/rib_right_3.nii.gz`<br> |
| `rib_right_4` | labels | from the file header | from the file header | 1=rib_right_4 | `{id}/segmentations/rib_right_4.nii.gz`<br> |
| `rib_right_5` | labels | from the file header | from the file header | 1=rib_right_5 | `{id}/segmentations/rib_right_5.nii.gz`<br> |
| `rib_right_6` | labels | from the file header | from the file header | 1=rib_right_6 | `{id}/segmentations/rib_right_6.nii.gz`<br> |
| `rib_right_7` | labels | from the file header | from the file header | 1=rib_right_7 | `{id}/segmentations/rib_right_7.nii.gz`<br> |
| `rib_right_8` | labels | from the file header | from the file header | 1=rib_right_8 | `{id}/segmentations/rib_right_8.nii.gz`<br> |
| `rib_right_9` | labels | from the file header | from the file header | 1=rib_right_9 | `{id}/segmentations/rib_right_9.nii.gz`<br> |
| `sacrum` | labels | from the file header | from the file header | 1=sacrum | `{id}/segmentations/sacrum.nii.gz`<br> |
| `scapula_left` | labels | from the file header | from the file header | 1=scapula_left | `{id}/segmentations/scapula_left.nii.gz`<br> |
| `scapula_right` | labels | from the file header | from the file header | 1=scapula_right | `{id}/segmentations/scapula_right.nii.gz`<br> |
| `skull` | labels | from the file header | from the file header | 1=skull | `{id}/segmentations/skull.nii.gz`<br> |
| `small_bowel` | labels | from the file header | from the file header | 1=small_bowel | `{id}/segmentations/small_bowel.nii.gz`<br> |
| `spinal_cord` | labels | from the file header | from the file header | 1=spinal_cord | `{id}/segmentations/spinal_cord.nii.gz`<br> |
| `spleen` | labels | from the file header | from the file header | 1=spleen | `{id}/segmentations/spleen.nii.gz`<br> |
| `sternum` | labels | from the file header | from the file header | 1=sternum | `{id}/segmentations/sternum.nii.gz`<br> |
| `stomach` | labels | from the file header | from the file header | 1=stomach | `{id}/segmentations/stomach.nii.gz`<br> |
| `subclavian_artery_left` | labels | from the file header | from the file header | 1=subclavian_artery_left | `{id}/segmentations/subclavian_artery_left.nii.gz`<br> |
| `subclavian_artery_right` | labels | from the file header | from the file header | 1=subclavian_artery_right | `{id}/segmentations/subclavian_artery_right.nii.gz`<br> |
| `superior_vena_cava` | labels | from the file header | from the file header | 1=superior_vena_cava | `{id}/segmentations/superior_vena_cava.nii.gz`<br> |
| `thyroid_gland` | labels | from the file header | from the file header | 1=thyroid_gland | `{id}/segmentations/thyroid_gland.nii.gz`<br> |
| `trachea` | labels | from the file header | from the file header | 1=trachea | `{id}/segmentations/trachea.nii.gz`<br> |
| `urinary_bladder` | labels | from the file header | from the file header | 1=urinary_bladder | `{id}/segmentations/urinary_bladder.nii.gz`<br> |
| `vertebrae_c1` | labels | from the file header | from the file header | 1=vertebrae_c1 | `{id}/segmentations/vertebrae_C1.nii.gz`<br> |
| `vertebrae_c2` | labels | from the file header | from the file header | 1=vertebrae_c2 | `{id}/segmentations/vertebrae_C2.nii.gz`<br> |
| `vertebrae_c3` | labels | from the file header | from the file header | 1=vertebrae_c3 | `{id}/segmentations/vertebrae_C3.nii.gz`<br> |
| `vertebrae_c4` | labels | from the file header | from the file header | 1=vertebrae_c4 | `{id}/segmentations/vertebrae_C4.nii.gz`<br> |
| `vertebrae_c5` | labels | from the file header | from the file header | 1=vertebrae_c5 | `{id}/segmentations/vertebrae_C5.nii.gz`<br> |
| `vertebrae_c6` | labels | from the file header | from the file header | 1=vertebrae_c6 | `{id}/segmentations/vertebrae_C6.nii.gz`<br> |
| `vertebrae_c7` | labels | from the file header | from the file header | 1=vertebrae_c7 | `{id}/segmentations/vertebrae_C7.nii.gz`<br> |
| `vertebrae_l1` | labels | from the file header | from the file header | 1=vertebrae_l1 | `{id}/segmentations/vertebrae_L1.nii.gz`<br> |
| `vertebrae_l2` | labels | from the file header | from the file header | 1=vertebrae_l2 | `{id}/segmentations/vertebrae_L2.nii.gz`<br> |
| `vertebrae_l3` | labels | from the file header | from the file header | 1=vertebrae_l3 | `{id}/segmentations/vertebrae_L3.nii.gz`<br> |
| `vertebrae_l4` | labels | from the file header | from the file header | 1=vertebrae_l4 | `{id}/segmentations/vertebrae_L4.nii.gz`<br> |
| `vertebrae_l5` | labels | from the file header | from the file header | 1=vertebrae_l5 | `{id}/segmentations/vertebrae_L5.nii.gz`<br> |
| `vertebrae_s1` | labels | from the file header | from the file header | 1=vertebrae_s1 | `{id}/segmentations/vertebrae_S1.nii.gz`<br> |
| `vertebrae_t1` | labels | from the file header | from the file header | 1=vertebrae_t1 | `{id}/segmentations/vertebrae_T1.nii.gz`<br> |
| `vertebrae_t10` | labels | from the file header | from the file header | 1=vertebrae_t10 | `{id}/segmentations/vertebrae_T10.nii.gz`<br> |
| `vertebrae_t11` | labels | from the file header | from the file header | 1=vertebrae_t11 | `{id}/segmentations/vertebrae_T11.nii.gz`<br> |
| `vertebrae_t12` | labels | from the file header | from the file header | 1=vertebrae_t12 | `{id}/segmentations/vertebrae_T12.nii.gz`<br> |
| `vertebrae_t2` | labels | from the file header | from the file header | 1=vertebrae_t2 | `{id}/segmentations/vertebrae_T2.nii.gz`<br> |
| `vertebrae_t3` | labels | from the file header | from the file header | 1=vertebrae_t3 | `{id}/segmentations/vertebrae_T3.nii.gz`<br> |
| `vertebrae_t4` | labels | from the file header | from the file header | 1=vertebrae_t4 | `{id}/segmentations/vertebrae_T4.nii.gz`<br> |
| `vertebrae_t5` | labels | from the file header | from the file header | 1=vertebrae_t5 | `{id}/segmentations/vertebrae_T5.nii.gz`<br> |
| `vertebrae_t6` | labels | from the file header | from the file header | 1=vertebrae_t6 | `{id}/segmentations/vertebrae_T6.nii.gz`<br> |
| `vertebrae_t7` | labels | from the file header | from the file header | 1=vertebrae_t7 | `{id}/segmentations/vertebrae_T7.nii.gz`<br> |
| `vertebrae_t8` | labels | from the file header | from the file header | 1=vertebrae_t8 | `{id}/segmentations/vertebrae_T8.nii.gz`<br> |
| `vertebrae_t9` | labels | from the file header | from the file header | 1=vertebrae_t9 | `{id}/segmentations/vertebrae_T9.nii.gz`<br> |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("totalsegmentator_ct").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `segmentation`, `nifti`, `whole-body`, `totalsegmentator`

<sub>Generated from `src/pardesline/data/manifests/totalsegmentator_ct.json` on 2026-10-16.</sub>
