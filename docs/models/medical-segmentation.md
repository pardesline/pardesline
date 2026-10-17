---
title: "Pretrained 3D medical image segmentation models: nnU-Net and friends in Python"
description: "Expert guide to learned 3D medical image segmentation on CT, MRI and PET volumes: the model families that actually win (nnU-Net and its self-configuring ru"
---

# Pretrained 3D medical image segmentation models: nnU-Net and friends in Python

!!! info "What ships today, and what is coming"
    **Today:** `prepare_nnunet_dataset.py`: any pardesline dataset written in the nnU-Net v2 raw layout, plus the guide to the model families that win the public benchmarks. No weights are shipped and there is no inference API: the scripts are reference implementations that read any pardesline dataset.

    **Coming: one-line model access.** The same registry pattern as datasets, a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`. This page keeps its URL. Follow and vote on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be contributed now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model).

**Reference scripts:** [`prepare_nnunet_dataset.py`](https://github.com/pardesline/pardesline/blob/main/skills/medical-segmentation-models/scripts/prepare_nnunet_dataset.py) (shipped in the wheel under `pardesline/skills/medical-segmentation-models/scripts/`, served by the MCP tool `get_skill`).

# Learned segmentation of medical volumes

## Which model (2026)

| Need | Choose | Why |
|---|---|---|
| A new organ / lesion task with 20-500 labelled volumes | **nnU-Net v2** (3d_fullres, + 3d_lowres cascade for large FOV) | self-configures spacing, patch size, batch size, normalisation from the dataset fingerprint; still the strongest baseline on MSD, AMOS, KiTS |
| 117 body structures on CT without training | **TotalSegmentator** (its dataset `totalsegmentator_ct` is CC BY 4.0; the *weights* carry their own non-commercial terms, check before shipping) | one command, nnU-Net inside |
| Transformer backbone, large data | Swin-UNETR / UNETR (MONAI), SegResNet | gains appear above ~1 000 volumes or with self-supervised pretraining |
| Interactive / few labels | MedSAM, SAM-Med3D, nnInteractive | prompt with boxes or clicks; validate per case |
| Many sources, foundation-model style | BiomedSegFM-type challenge models, STU-Net | pretrain on pooled datasets (`hf_biomedsegfm_3d_val` shows the pooled format) |

Every one of them is a voxel network: the label lives in the voxel grid (see
`3d-representations`).

## Data: from a pardesline dataset to a training set

```python
import pardesline as pl

ds = pl.load("msd_task09_spleen").filter(split="Tr")  # 41 labelled CTs, licence attached
train, val = ds.split(by="id", fractions=(0.8, 0.2), seed=0)  # patient-level split, no leakage
ds.export("./spleen_std")  # NIfTI + sidecars + manifest if you want local files
```

[`scripts/prepare_nnunet_dataset.py`](https://github.com/pardesline/pardesline/blob/main/skills/medical-segmentation-models/scripts/prepare_nnunet_dataset.py) writes the nnU-Net raw layout
(`imagesTr/CASE_0000.nii.gz`, `labelsTr/CASE.nii.gz`, `dataset.json`) from any
pardesline dataset with an image role and a labels role, including multi-channel
inputs (MSD brain tumour: 4 modalities = `_0000..._0003`), DICOM series
(materialised to NIfTI) and TotalSegmentator's one-mask-per-organ layout
(merged into one label map with a class table).

Rules:
- **Split by patient** (`pairing` key); never by slice.
- Keep the licence: nnU-Net models trained on NC data (KiTS23, TotalSegmentator
  MRI, BiomedSegFM) inherit the restriction; say so in the model card.
- Record spacing and orientation per case; nnU-Net resamples to the median
  spacing (or the 10th percentile along the low-res axis) and crops to the
  foreground.

## Preprocessing that matters

| Step | CT | MRI | PET |
|---|---|---|---|
| Resampling | isotropic or dataset-median spacing, image linear / labels nearest | same | same |
| Intensity | clip to the 0.5-99.5 percentile of foreground HU, z-score with global mean/std (nnU-Net "CT" scheme) | per-volume z-score (scanner-dependent intensities), optional N4 bias correction | SUV normalisation |
| Orientation | reorient to a canonical frame (RAS or LPS) consistently; pardesline volumes are LPS | same | same |
| Cropping | to the non-zero / body region | brain extraction optional | |
| Patches | 128^3 (fullres) or anisotropic (e.g. 40 x 224 x 224) when spacing is anisotropic; oversample patches containing foreground (33 %) | | |

## Training recipe (nnU-Net defaults, the ones worth knowing)

- Loss: Dice + cross-entropy, deep supervision at 3-4 decoder scales
  (weights 1, 1/2, 1/4...).
- Optimizer: SGD momentum 0.99, Nesterov, lr 1e-2 with poly decay, 1 000
  epochs x 250 iterations, batch 2; mixed precision.
- Augmentation on the fly: rotation, scaling, elastic (light), Gaussian noise
  and blur, brightness / contrast, gamma, mirroring along anatomically valid
  axes only (never left-right if laterality matters: kidneys, lungs).
- 5-fold cross-validation; ensemble folds at inference.
- Budget: 1 fold of 3d_fullres ~ 1-2 GPU-days on a 24 GB card at 128^3; a
  "quick look" at 100 epochs tells whether the task is learnable.

## Inference

Sliding window with 50 % overlap and a Gaussian importance map (centre of the
patch trusted more), test-time augmentation by flips, argmax, then
post-processing: keep the largest connected component per class when the
anatomy is a single object (spleen, liver), not for lesions or vessels.
Resample the prediction back to the original grid with nearest-neighbour and
write it with the original header. In pardesline:

```python
pred = pl.load("pred_case07.nii.gz").as_labels({1: "spleen"})  # LabelMap in LPS mm
surf = pred.to_mesh(label=1)  # exact surface for review
pred.save("case07_pred.nii.gz")  # + sidecar with labels and provenance
```

## Evaluation

Per class and per case: Dice, HD95 (mm), NSD at 1-3 mm, volume error; median
and IQR; worst cases shown. `evaluation-metrics-3d/scripts/metrics3d.py`
implements them; `metrics3d.py --dataset liver_tumor_patient01` prints the
inter-observer agreement of three radiologists, the ceiling any model should
be compared with.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| Dice fine, HD95 huge | isolated false positives far away | largest-component post-processing, lower-res cascade for context |
| Collapses on small structures | class imbalance | foreground oversampling, Dice loss already helps, patch size covering the structure |
| Works on one scanner only | intensity shift | per-volume normalisation (MRI), intensity augmentation, more centres |
| Laterality swap | mirroring augmentation on left/right classes | disable left-right flips |
| Looks good in 2D, striped in 3D | 2D model on anisotropic data | 3D model or 2.5D with neighbouring slices |
| Train/val gap | leakage by slice or by patient with several scans | split by patient id |

## Datasets to practise on

MSD tasks (`msd_task01_braintumour` ... `msd_task10_colon`), `amos22` (15
organs CT/MRI), `totalsegmentator_ct` / `totalsegmentator_mri`, `hf_kits23`,
`verse19_spine`, `spider_lumbar_mri`, `hf_nsclc_radiomics`, `hf_biomedsegfm_3d_val`
(pooled npz), `luna16` (detection), `tcia_lidc_idri` (DICOM + SEG).

<sub>Source: `skills/medical-segmentation-models/SKILL.md`, published on 2026-10-17.</sub>
