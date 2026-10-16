---
title: How to segment organs in a CT scan in Python
description: Segment structures in a CT volume in Python: Hounsfield windows with volume.segment(lower, upper), Otsu, connected components and watershed in one call each, the honest limits of thresholds against an expert label, and where learned organ segmentation models come in.
---

# How to segment organs in a CT scan in Python

Thresholds segment tissue classes, not organs: bone (300+ HU), soft tissue (30–200 HU), lung (−900 to −500 HU) separate well; the spleen from the liver does not. Start with the threshold, measure it against an expert label, then decide whether a model is needed.

```python
import pardesline as pl

case = pl.load("msd_task09_spleen").filter(split="Tr")[0]
ct = case.ct  # CT in Hounsfield units, LPS mm
soft = ct.segment(lower=30, upper=200)  # LabelMap, label 1 = inside the window
blobs = soft.run("simpleitk_segmentation.connected_components", threshold=0.5, min_size=1000)
surface = blobs.as_labels().to_mesh(isovalue=0.5).smooth()
reference = case.mask.to_mesh(label=1).smooth()  # the expert spleen label
```

`ct.segment()` without bounds is Otsu (128 bins). Bone: `ct.segment(lower=300, upper=3000)`. Lungs: `ct.segment(lower=-950, upper=-500)` then the two largest components.

## Measure before believing

```python
import numpy as np

pred = blobs.to_numpy() > 0
truth = case.mask.to_numpy() == 1
dice = 2 * (pred & truth).sum() / (pred.sum() + truth.sum())
print(round(float(dice), 3))
```

The [spleen example](../examples.md#spleen_ct_threshold_segmentation) draws both surfaces: the threshold finds every soft-tissue organ, and the Dice against the spleen label is low. That is the baseline a learned model has to beat, and the number to put in a report before any model is trained. For Dice, HD95 and surface Dice with spacing, use [`metrics3d.py`](../models/evaluation-metrics.md).

## Watershed when structures touch

```python
parts = ct.run(
    "simpleitk_segmentation.watershed",
    threshold=30,
    upper_threshold=200,
    seed_radius=15,
    min_object_size=1000,
)
```

Markers are placed where the distance map exceeds `seed_radius` mm, so only objects at least twice that size become basins; dam lines are drawn between touching structures.

## MR, PET, 8-bit images

MR has no absolute intensity scale: take bounds from percentiles of the volume (`np.percentile(mr.to_numpy(), [60, 99])`). PET SUV windows are per study. 8-bit windowed exports (the SimpleITK liver excerpt) need bounds in 0–255.

## Organs: use a model

Organ-level segmentation on CT is a solved problem for nnU-Net and TotalSegmentator-class models (117 structures). pardesline does not ship weights yet; [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes any dataset in the nnU-Net layout, the model's output loads back as a `LabelMap`, and one-line model access is the top [roadmap](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22) item.

Related: [simpleitk_segmentation](../algorithms/simpleitk_segmentation.md) · [Run a pretrained 3D segmentation model](run-a-pretrained-3d-segmentation-model-on-your-ct-scans.md) · [Why our defaults work](../algorithms/why-our-defaults-work.md#threshold-segmentation-of-volumes-simpleitk_segmentation)
