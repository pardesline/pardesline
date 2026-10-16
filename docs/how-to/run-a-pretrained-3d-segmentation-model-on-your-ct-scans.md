---
title: How to run a pretrained 3D segmentation model on your CT scans (nnU-Net, TotalSegmentator) with pardesline
description: Run a pretrained 3D medical segmentation model on your CT scans in Python today: prepare the data in the nnU-Net layout from any pardesline dataset, run nnU-Net or TotalSegmentator, load the predictions back as label maps, measure Dice against the reference; and what the coming model registry changes.
---

# How to run a pretrained 3D segmentation model on your CT scans

!!! info "Status"
    pardesline does not ship weights or an inference API yet. This page shows the working path today (prepare → run the model's own tool → load the result back) and what [one-line model access](../models/index.md) will replace it with.

## 1. Prepare the data in the model's layout

```bash
pip install "pardesline[medical]"
python skills/medical-segmentation-models/scripts/prepare_nnunet_dataset.py msd_task09_spleen --out ./nnUNet_raw/Dataset509_Spleen --take 20
python skills/medical-segmentation-models/scripts/prepare_nnunet_dataset.py /data/my_cts --image ct --mask seg --out ./nnUNet_raw/Dataset900_Mine
```

The script writes `imagesTr/<case>_0000.nii.gz`, `labelsTr/<case>.nii.gz` and `dataset.json` (channel names, labels, number of cases) from any pardesline dataset or scanned folder: NIfTI, MetaImage, DICOM series and npz grids are converted with SimpleITK; several binary mask roles are merged into one label map in the order given. Split by patient before exporting (`ds.split(by="patient")`).

## 2. Run the model with its own tool

- **nnU-Net v2**: `nnUNetv2_predict -i imagesTs -o preds -d 509 -c 3d_fullres` with the trained or downloaded weights.
- **TotalSegmentator** (117 structures on CT): `TotalSegmentator -i case_0000.nii.gz -o seg_case --ml` writes one multi-label NIfTI.

Both read NIfTI in physical coordinates, which is what the preparation step wrote.

## 3. Load the predictions back and measure

```python
import pardesline as pl

pred = pl.load("preds/spleen_10.nii.gz").as_labels({1: "spleen"})
case = pl.load("msd_task09_spleen")["spleen_10"]
surface = pred.to_mesh(label=1).smooth()
surface.save("spleen_10_pred.stl")
```

```bash
python skills/evaluation-metrics-3d/scripts/metrics3d.py --help        # dice, hd95, surface_dice with spacing
```

The [metrics guide](../models/evaluation-metrics.md) explains which numbers mean something; the [threshold baseline](segment-organs-in-a-ct-scan-in-python.md) is the comparison a model report should include.

## Why models fail on new scanners

Spacing and field of view outside the training distribution, contrast phase, cropping, and label-definition mismatches (is the splenic vein spleen?) account for most failures. The [medical segmentation models guide](../models/medical-segmentation.md) lists the checks: resample to the model's spacing, compare intensity histograms, run on a few cases with reference labels first.

## What changes with the model registry

A model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model("totalsegmentator")` / `pl.run(model, dataset)` will replace steps 1–3 with one call that returns `LabelMap` objects with the model's label names and provenance. Follow the [tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be written now from `templates/new_model/`.

Related: [Models](../models/index.md) · [Segment organs in a CT scan](segment-organs-in-a-ct-scan-in-python.md) · [MSD spleen dataset](../datasets/msd_task09_spleen.md)
