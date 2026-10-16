---
title: 3D and medical imaging datasets for Python, one line each
description: 43 public 3D and medical imaging datasets (Medical Segmentation Decathlon, TCIA, TotalSegmentator, AMOS, LUNA16, KITTI, Objaverse) loadable in one line with licence, citation and standardized roles.
---

# Datasets catalog

Every dataset below loads with one call and comes back as typed objects (volumes, label maps, meshes, point clouds, splats, images) that know their frame, units, labels, licence and citation. Files are fetched on access, verified, cached; archives are read by HTTP Range so one sample costs one sample. `pl.datasets()` lists the names, `pl.describe(name)` prints a manifest.

```python
import pardesline as pl

print(pl.datasets())                      # 43 names
print(pl.datasets(tag="ct"))             # by tag
ds = pl.load("msd_task09_spleen")        # lazy: nothing downloaded yet
ct = ds.filter(split="Tr")[0].ct          # one 30 MB volume out of a 1.6 GB tar
```

Not bundled, and why: BraTS (Synapse data-use agreement), ModelNet, ShapeNet and ScanNet (registration-gated downloads). They are tracked on the [Datasets wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Adataset) issue; a manifest that fetches with the user's own credentials is welcome.

## Any source, not only the bundled ones

| URI | What happens |
|---|---|
| `pl.load("hf://org/repo")` | the Hub tree is listed, a manifest is drafted, you confirm units / labels / licence once, it is saved |
| `pl.load("tcia://Collection")` | a public TCIA collection through the NBIA API, DICOM series as folders |
| `pl.load("s3://openneuro.org/ds000228")` | an OpenNeuro dataset from the public bucket |
| `pl.load("https://.../archive.zip")` | a remote zip or tar read by HTTP Range |
| `pl.scan("/data/study")` | your folder: a draft manifest and the questions the files cannot answer |

See [How to standardize a folder of medical images](../how-to/standardize-a-folder-of-medical-images-in-python.md) and the [manifest schema](../getting-started/concepts.md#manifest).

## The bundled manifests

**Medical (35)**

| Dataset | Modality / type | Size | Licence | Source | One-line loader |
|---|---|---|---|---|---|
| [AMOS 22: abdominal multi-organ segmentation, 600 CT and MRI with 15 organ labels](amos22.md) | CT / MRI / NIfTI (labels, volume) | 23.7 GB | CC-BY-SA-4.0 | zenodo.org | `pl.load("amos22")` |
| [C3VD colonoscopy scenes as Gaussian splats and point clouds (EndoGSLAM fits from PR-ENDO)](c3vd_endoscopy_splats.md) | endoscopy / Gaussian splats / points (points, splat) | 7.7 GB | CC-BY-4.0 | zenodo.org | `pl.load("c3vd_endoscopy_splats")` |
| [CHAOS: abdominal CT and MR (T1 in/out-phase, T2 SPIR) as DICOM series, 40 patients](chaos_abdomen.md) | CT / MRI / DICOM (volume) | 891 MB | CC-BY-NC-SA-4.0 | zenodo.org | `pl.load("chaos_abdomen")` |
| [AbdomenAtlas 1.0 Mini: abdominal CTs with nine organ masks (first 100 of 5 195 cases)](hf_abdomenatlas_mini.md) | CT / NIfTI (labels, volume) | 7.8 GB | CC-BY-NC-SA-4.0 (gated) | Hugging Face `AbdomenAtlas/AbdomenAtlas1.0Mini` | `pl.load("hf_abdomenatlas_mini")` |
| [CVPR 2025 BiomedSegFM, 3-D validation set: 2 144 CT / MRI / PET / 3-D ultrasound / microscopy volumes as npz](hf_biomedsegfm_3d_val.md) | CT / MRI / PET (labels, volume) | 19.5 GB | CC-BY-NC-SA-4.0 | Hugging Face `junma/CVPR-BiomedSegFM` | `pl.load("hf_biomedsegfm_3d_val")` |
| [CT-RATE: non-contrast chest CTs paired with radiology reports (first 20 validation cases)](hf_ct_rate_valid.md) | CT / NIfTI (volume) | 6.8 GB | CC-BY-NC-SA-4.0 (gated) | Hugging Face `ibrahimhamamci/CT-RATE` | `pl.load("hf_ct_rate_valid")` |
| [KiTS23: 489 kidney-tumour CTs with kidney, tumour and cyst labels](hf_kits23.md) | CT / NIfTI (labels, volume) | 87.9 GB | CC-BY-NC-SA-4.0 | Hugging Face `neheller/KiTS-Challenge-Imaging` | `pl.load("hf_kits23")` |
| [NSCLC-Radiomics (TCIA) as NIfTI: 422 lung-cancer CTs with organ and tumour segmentations](hf_nsclc_radiomics.md) | CT / NIfTI (labels, volume) | 11.7 GB | CC-BY-3.0 | Hugging Face `farrell236/NSCLC-Radiomics-NIFTI` | `pl.load("hf_nsclc_radiomics")` |
| [OpenMind: head-and-neck 3D MRI pooled from OpenNeuro, one study at a time](hf_openmind.md) | MRI / NIfTI (labels, volume) |  | CC-BY-4.0 | Hugging Face `MIC-DKFZ/OpenMind` | `pl.load("hf_openmind")` |
| [IXI: ~600 healthy-subject brain MRIs (T1, T2, PD, MRA) from three London hospitals](ixi_brain_mri.md) | MRI / NIfTI (volume) | 24.6 GB | CC-BY-SA-3.0 | biomedic.doc.ic.ac.uk | `pl.load("ixi_brain_mri")` |
| [Liver tumour CT with three radiologists segmentations](liver_tumor_patient01.md) | CT (labels, volume) | 2 MB | see source | https | `pl.load("liver_tumor_patient01")` |
| [LUNA16: 888 thoracic CTs (LIDC-IDRI subset) for lung nodule detection](luna16.md) | CT / MetaImage (volume) | 64.8 GB | CC-BY-4.0 | zenodo.org | `pl.load("luna16")` |
| [MedShapeNet: 106 101 anatomical and surgical-instrument shapes as STL meshes](medshapenet.md) | mesh / STL (mesh) | 1953.1 GB | CC-BY-4.0 | mml.ikim.nrw | `pl.load("medshapenet")` |
| [Medical Segmentation Decathlon, Task01 BrainTumour](msd_task01_braintumour.md) | MRI / NIfTI (labels, volume) | 7.4 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task01_braintumour")` |
| [Medical Segmentation Decathlon, Task02 Heart: left-atrium segmentation on 30 cardiac MRIs](msd_task02_heart.md) | MRI / NIfTI (labels, volume) | 456 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task02_heart")` |
| [Medical Segmentation Decathlon, Task03 Liver](msd_task03_liver.md) | CT / NIfTI (labels, volume) | 28.2 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task03_liver")` |
| [Medical Segmentation Decathlon, Task04 Hippocampus](msd_task04_hippocampus.md) | MRI / NIfTI (labels, volume) | 28 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task04_hippocampus")` |
| [Medical Segmentation Decathlon, Task05 Prostate](msd_task05_prostate.md) | MRI / NIfTI (labels, volume) | 240 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task05_prostate")` |
| [Medical Segmentation Decathlon, Task06 Lung](msd_task06_lung.md) | CT / NIfTI (labels, volume) | 8.9 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task06_lung")` |
| [Medical Segmentation Decathlon, Task07 Pancreas](msd_task07_pancreas.md) | CT / NIfTI (labels, volume) | 12.0 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task07_pancreas")` |
| [Medical Segmentation Decathlon, Task08 HepaticVessel](msd_task08_hepaticvessel.md) | CT / NIfTI (labels, volume) | 9.1 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task08_hepaticvessel")` |
| [Medical Segmentation Decathlon, Task09 Spleen](msd_task09_spleen.md) | CT / NIfTI (labels, volume) | 1.6 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task09_spleen")` |
| [Medical Segmentation Decathlon, Task10 Colon](msd_task10_colon.md) | CT / NIfTI (labels, volume) | 6.1 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task10_colon")` |
| [OpenNeuro ds000228: T1-weighted MRI of 155 children and adults (Richardson et al.)](openneuro_ds000228.md) | MRI / NIfTI (volume) | 2.4 GB | PDDL-1.0 | S3 `openneuro.org` | `pl.load("openneuro_ds000228")` |
| [POPI-model: 4D-CT of one thorax, six breathing phases](popi_lung_4dct.md) | CT / 4D (labels, volume) | 500 MB | see source | creatis.insa-lyon.fr | `pl.load("popi_lung_4dct")` |
| [RIRE training_001: CT and MR-T1 of one brain](rire_brain.md) | CT / MRI (volume) | 19 MB | see source | rire.insight-journal.org | `pl.load("rire_brain")` |
| [SPIDER: lumbar spine MRI (T1, T2, T2 SPACE) of 218 patients with vertebra, disc and canal masks](spider_lumbar_mri.md) | MRI / MetaImage (labels, volume) | 3.7 GB | CC-BY-4.0 | zenodo.org | `pl.load("spider_lumbar_mri")` |
| [TCIA LIDC-IDRI: 1 018 thoracic CTs for lung nodule analysis (DICOM)](tcia_lidc_idri.md) | DICOM / CT (volume) | 122.1 GB | CC-BY-3.0 | TCIA `LIDC-IDRI` | `pl.load("tcia_lidc_idri")` |
| [TCIA NSCLC-Radiomics: 422 lung-cancer CTs with RTSTRUCT and SEG contours (DICOM)](tcia_nsclc_radiomics_dicom.md) | DICOM / CT (volume) | 32.2 GB | CC-BY-3.0 | TCIA `NSCLC-Radiomics` | `pl.load("tcia_nsclc_radiomics_dicom")` |
| [TCIA Pancreas-CT: 82 abdominal contrast-enhanced CTs (NIH)](tcia_pancreas_ct.md) | DICOM / CT (volume) | 8.8 GB | CC-BY-3.0 | TCIA `Pancreas-CT` | `pl.load("tcia_pancreas_ct")` |
| [TCIA Prostate-3T: 64 T2-weighted prostate MRIs (DICOM)](tcia_prostate_3t.md) | DICOM / MRI (volume) | 200 MB | CC-BY-3.0 | TCIA `Prostate-3T` | `pl.load("tcia_prostate_3t")` |
| [TotalSegmentator CT dataset v2.0.1: 1 228 CT volumes with 117 anatomical structures](totalsegmentator_ct.md) | CT / NIfTI (labels, volume) | 23.0 GB | CC-BY-4.0 | zenodo.org | `pl.load("totalsegmentator_ct")` |
| [TotalSegmentator MRI dataset v1.0.0: 298 MRI volumes with 56 anatomical structures](totalsegmentator_mri.md) | MRI / NIfTI (labels, volume) | 2.3 GB | CC-BY-NC-SA-2.0 | zenodo.org | `pl.load("totalsegmentator_mri")` |
| [VerSe 2019: 160 spine CTs with vertebra-level label maps and centroids](verse19_spine.md) | CT / NIfTI (labels, volume) | 12.0 GB | CC-BY-SA-4.0 | s3.bonescreen.de | `pl.load("verse19_spine")` |
| [Visible Human Project: MRI of the head](visible_human_head_mri.md) | MRI (volume) | 2 MB | see source | nlm.nih.gov | `pl.load("visible_human_head_mri")` |

**General 3D (8)**

| Dataset | Modality / type | Size | Licence | Source | One-line loader |
|---|---|---|---|---|---|
| [3D Arena: image-to-3D outputs of 29 generators on 100 shared input images](hf_3d_arena.md) | mesh / Gaussian splats (image, mesh, splat) | 19.5 GB | MIT | Hugging Face `3d-arena/3d-arena` | `pl.load("hf_3d_arena")` |
| [KITTI-360 street chunks as point clouds and Gaussian splats (GaussianWorld subset, 16 chunks)](hf_kitti360_gs_subset.md) | LiDAR / points / Gaussian splats (points) | 2.4 GB | CC-BY-NC-SA-3.0 | Hugging Face `GaussianWorld/kitti_360_subset_chunk_gs_preprocessed` | `pl.load("hf_kitti360_gs_subset")` |
| [Objaverse 1.0, one shard of glTF meshes (5 000 objects)](hf_objaverse_glb_shard.md) | mesh (mesh) | 14.6 GB | ODC-By-1.0 | Hugging Face `allenai/objaverse` | `pl.load("hf_objaverse_glb_shard")` |
| [UniOcc, CARLA 10 Hz mini split: LiDAR sweeps, camera views and semantic occupancy grids](hf_uniocc_carla_mini.md) | LiDAR / points (image, labels, points) | 4.9 GB | MIT | Hugging Face `tasl-lab/uniocc` | `pl.load("hf_uniocc_carla_mini")` |
| [KITTI raw, drive 2011_09_26_0001: 108 Velodyne sweeps with the four camera streams](kitti_raw_2011_09_26_drive_0001.md) | LiDAR / points / stereo (image, points) | 459 MB | CC-BY-NC-SA-3.0 | s3.eu-central-1.amazonaws.com | `pl.load("kitti_raw_2011_09_26_drive_0001")` |
| [Stanford armadillo (Open3D demo mesh)](open3d_armadillo.md) | mesh (mesh) | 7 MB | see source | Open3D data | `pl.load("open3d_armadillo")` |
| [Stanford bunny (Open3D demo mesh)](open3d_bunny.md) | mesh (mesh) | 3 MB | see source | Open3D data | `pl.load("open3d_bunny")` |
| [Open3D ICP demo: three indoor point-cloud fragments](open3d_icp_demo.md) | points (points) | 6 MB | see source | Open3D data | `pl.load("open3d_icp_demo")` |

<!-- generated by docs/_gen/datasets_table.py from 43 manifests -->


"Size" is the whole source; one sample costs its own size. "See source" means the owner states terms outside a standard licence: `ds.describe()` prints them and the loader warns.
