---
title: "DINOv3 and DINOv2 features for 3D and medical imaging in Python"
description: "Expert guide to DINOv3 (and DINOv2) frozen vision backbones as the feature primitive for medical and 3D pipelines: why scaling self-supervised ViTs degrade"
---

# DINOv3 and DINOv2 features for 3D and medical imaging in Python

!!! info "What ships today, and what is coming"
    **Today:** `dinov3_features.py` (patch features + PCA colouring, any image, DINOv2 or DINOv3 backbone through `transformers`) and `dinov3_faster_rcnn.py` (a frozen backbone under a Faster R-CNN head). No weights are shipped and there is no inference API: the scripts are reference implementations that read any pardesline dataset.

    **Coming: one-line model access.** The same registry pattern as datasets, a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`. This page keeps its URL. Follow and vote on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be contributed now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model).

**Reference scripts:** [`dinov3_faster_rcnn.py`](https://github.com/pardesline/pardesline/blob/main/skills/dinov3-dense-features/scripts/dinov3_faster_rcnn.py), [`dinov3_features.py`](https://github.com/pardesline/pardesline/blob/main/skills/dinov3-dense-features/scripts/dinov3_features.py) (shipped in the wheel under `pardesline/skills/dinov3-dense-features/scripts/`, served by the MCP tool `get_skill`).

**Runnable example:** [`examples/dinov2_features_kitti/run.py`](https://github.com/pardesline/pardesline/tree/main/examples/dinov2_features_kitti), executed on 2026-10-16; its outputs are committed next to it.

# DINOv3 dense features for medical and 3D work

## The problem DINOv3 solved

Self-supervised ViTs (DINO, DINOv2) are trained with an image-level
objective (`L_DINO`, teacher-student distillation of the class token) plus
a masked patch objective (`L_iBOT`) and a spreading term (`L_KoLeo`). When
training is scaled (more data, bigger model, longer schedules), **global
metrics keep improving while dense metrics peak around 200k iterations and
then degrade**: patch features lose local coherence, segmentation and depth
probes fall, correspondence maps turn noisy. Two objectives pulling in
opposite directions.

DINOv3 adds **Gram anchoring**:

```
L_Gram = || X_S X_S^T  -  X_G X_G^T ||_F^2
X_S : L2-normalised student patch features (P x d)
X_G : patch features from an earlier "Gram teacher" checkpoint (clean dense structure)
X X^T : the P x P matrix of patch-to-patch cosine similarities
```

It constrains the *relations between patches*, not the patches themselves: the
student may move its features anywhere as long as patches that were similar
stay similar. Applied late in training (and with the teacher run at higher
resolution), it removes the degradation and unlocks scaling:

| | DINOv2 | DINOv3 |
|---|---|---|
| Data | LVD-142M | LVD-1689M (~1.7 B curated) |
| Largest model | ViT-g/14 (1.1 B) | ViT-7B/16 (6.7 B) |
| ADE20K segmentation, frozen backbone | linear probe | 63.0 mIoU (+6) |
| COCO detection, frozen backbone | - | 66.1 mAP |
| Instance retrieval / video tracking | - | +10.9 mAP / +6.7 J&F |
| Distilled family | few sizes | ViT-S/B/L/H+ and ConvNeXt T-L (29 M-198 M) |

Consequence for engineers: the fine-tuning stage that used to be needed
before any correspondence or dense task is largely gone; a frozen backbone
plus a small head is a legitimate production design.

## Using the features

```python
# scripts/dinov3_features.py extracts patch tokens; the core is:
model = AutoModel.from_pretrained(
    "facebook/dinov3-vitl16-pretrain-lvd1689m"
)  # gated: accept the licence on the Hub
x = preprocess(image, size=512)  # multiples of 16; ImageNet mean/std; grayscale -> 3 channels
tokens = model(pixel_values=x).last_hidden_state  # (1, 1 + R + P, d): CLS, register tokens, P patches
patches = tokens[:, 1 + n_registers :]  # (1, 32*32, 1024) for 512 px / 16
fmap = patches.reshape(1, 32, 32, 1024)
```

- Resolution: patch 16; 512 px gives a 32 x 32 map, 1024 px a 64 x 64 map
  (memory grows with P^2 in attention). For small lesions, tile or upsample
  features (bilinear or FeatUp) rather than upsampling the image blindly.
- Register tokens (4) sit between CLS and patches in DINOv3; drop them for
  dense maps.
- Visualise with PCA on the patch tokens (3 components to RGB): the first
  look that tells whether the modality transfers (myocardium / blood pool /
  pericardium separate on echo).
- Normalise features (L2) before cosine similarity; for matching use mutual
  nearest neighbours + a ratio test.

## Heads on a frozen backbone

| Task | Head | Notes |
|---|---|---|
| Classification | linear or small MLP on CLS (+ mean of patches) | the baseline every claim is measured against |
| Segmentation | linear per patch, or a light decoder (UperNet / DPT style) on 4 intermediate layers | 1x1 conv on upsampled tokens already beats many trained CNNs |
| Detection | **ViTDet simple feature pyramid**: from the single 1/16 token map build P2-P5 by deconv / identity / pooling, 256 channels, then a standard Faster R-CNN (RPN + RoIAlign + box head) or a DETR-style decoder | the pericardial-effusion recipe: ViT-L/16 frozen (300 M params, 0 updates), ~25 M trainable, focal loss for the rare class, NMS 0.5 |
| Dense correspondence / registration init | cosine similarity between patch tokens of two views, RANSAC on the matches | gives an initial pose for `point-cloud-registration` from images |
| Retrieval / anomaly | k-NN on CLS or patch tokens against a bank of normal images | see `vae-anomaly-detection` for the reconstruction route |

Training a head: AdamW 1e-4 (head only), batch 8-16, 20-50 epochs, strong
photometric augmentation (gain, speckle noise, gamma for ultrasound), mild
geometric augmentation (the backbone is frozen, geometry invariances come from
it). Store features once (no backbone forward during epochs) when the dataset
fits on disk: training then takes minutes.

## Medical transfer: where it works and where it breaks

- Works out of the box: B-mode ultrasound (effusion detection, chamber
  structure), chest X-ray, endoscopy frames, dermatology, fundus - 2D images
  with natural-image-like statistics.
- Needs adaptation: histopathology (stain statistics; use a pathology
  foundation model or stain-normalise), OCT, mammography at full resolution
  (tile).
- Does not apply directly: **3D volumes** (CT/MRI). Options: run per slice and
  aggregate (2.5D), use the features as a prior for a 3D decoder, or use a 3D
  self-supervised backbone (`jepa-pretraining`). Do not feed Hounsfield units
  as RGB without windowing.
- Validate on a *modality-specific* held-out set split by patient; report the
  linear-probe baseline so the head's contribution is visible.

## For 3D

Dense, spatially coherent features at high resolution are the primitive for
multi-view matching (two endoscopy frames, two photographs of a scan subject),
for novel-view synthesis priors (feature splatting, `gaussian-splatting`), and
for lifting 2D predictions onto a mesh (project the mesh into each view,
sample the feature map, vote). The `c3vd_endoscopy_splats` and `hf_3d_arena`
datasets give posed images and 3D outputs to try it on.

## Weights, licences, deployment

- DINOv3 weights are gated on the Hub under Meta's DINOv3 licence (accept the
  terms, use your token: `huggingface-cli login`); check the commercial
  clause for your product. DINOv2 is Apache-2.0.
- Distilled models: ViT-S/16 (21 M) for edge, ConvNeXt variants for ONNX /
  TensorRT without attention kernels.
- Export: the frozen backbone is a fixed graph; quantise to int8 with a
  calibration set of your modality, validate the head's metrics again.

Scripts: [`scripts/dinov3_features.py`](https://github.com/pardesline/pardesline/blob/main/skills/dinov3-dense-features/scripts/dinov3_features.py) (extract, PCA-colour, save `.npz` of
patch tokens), [`scripts/dinov3_faster_rcnn.py`](https://github.com/pardesline/pardesline/blob/main/skills/dinov3-dense-features/scripts/dinov3_faster_rcnn.py) (frozen backbone + simple
feature pyramid + torchvision Faster R-CNN, training and evaluation on a COCO-
style box dataset). Both need `torch`, `torchvision`, `transformers`.

<sub>Source: `skills/dinov3-dense-features/SKILL.md`, published on 2026-10-14.</sub>
