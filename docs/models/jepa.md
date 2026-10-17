---
title: "JEPA self-supervised pretraining on 3D medical volumes in Python"
description: "Expert guide to Joint-Embedding Predictive Architectures (I-JEPA, V-JEPA, their 3D and signal variants) for self-supervised pretraining on medical volumes "
---

# JEPA self-supervised pretraining on 3D medical volumes in Python

!!! info "What ships today, and what is coming"
    **Today:** `jepa3d_pretrain.py`: a 3D ViT context encoder, a predictor and an EMA target encoder trained on masked blocks of any pardesline volume dataset. No weights are shipped and there is no inference API: the scripts are reference implementations that read any pardesline dataset.

    **Coming: one-line model access.** The same registry pattern as datasets, a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`. This page keeps its URL. Follow and vote on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be contributed now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model).

**Reference scripts:** [`jepa3d_pretrain.py`](https://github.com/pardesline/pardesline/blob/main/skills/jepa-pretraining/scripts/jepa3d_pretrain.py) (shipped in the wheel under `pardesline/skills/jepa-pretraining/scripts/`, served by the MCP tool `get_skill`).

**Runnable example:** [`examples/jepa_hippocampus/run.py`](https://github.com/pardesline/pardesline/tree/main/examples/jepa_hippocampus), executed on 2026-10-16; its outputs are committed next to it.

# JEPA: predicting in latent space instead of reconstructing pixels

## The idea

An autoencoder (and MAE) learns `z = f(x)` by reconstructing `x_hat = g(z)` and
paying `||x - x_hat||^2` on every pixel - including speckle, breathing motion,
contrast timing and scanner noise that carry no semantics. Capacity goes to
modelling noise.

JEPA removes the decoder. Mask part of the input; encode the visible
**context** with `s_theta`; encode the hidden **target** with a second network
`s_bar` (an exponential moving average of `s_theta`, no gradient); train a
**predictor** `q_phi` to predict the target *embeddings* from the context
embeddings plus the positions of the target patches:

```
L = || q_phi( s_theta(x_context), pos_target )  -  sg( s_bar(x_target) ) ||^2
```

The model predicts only what is predictable from context - anatomy, structure,
texture statistics - and is free to ignore unpredictable detail. No pixel
decoder, no reconstruction, no contrastive negatives.

| | Encoder-decoder / MAE | JEPA |
|---|---|---|
| Output | pixels / signal | embeddings |
| Loss | reconstruction (L2 / BCE) | latent prediction (L2 / smooth L1) |
| What it models | everything, noise included | the predictable structure |
| Collapse risk | none (decoder constrains) | handled by EMA target + stop-gradient + predictor |
| Compute | decoder forward/backward on all patches | encoder on context only (~25 %), predictor is light |
| Transfer | good with long schedules | better linear-probe and low-shot transfer at a fraction of the epochs |

## Why it fits medical data

- Cardiac MRI / CT: breathing, ECG gating, contrast phase, coil shading are
  nuisance; chamber geometry and wall texture are predictable from context.
- 3D ultrasound: speckle is by construction unpredictable; anatomy is not.
- ECG: baseline wander and electrode noise vs the P-QRS-T structure.
- Labels are scarce; the pretrained encoder is fine-tuned (or probed) for
  segmentation, classification and anomaly detection with 10-100x fewer
  labels than from scratch.

## Architecture details that matter

- **Tokenisation.** 2D: ViT patches 16 x 16 at 224-448 px. Volumes: 3D
  patches (tubelets) of 16 x 16 x 16 or anisotropic 8 x 16 x 16 when the
  through-plane spacing is coarse; add learnable or sinusoidal 3D position
  embeddings; scale positions by voxel spacing when spacing varies across the
  dataset (pardesline volumes carry it in `frame.affine`). Signals: 1-D
  patches of 50-100 samples at 250-500 Hz, position = time.
- **Masking.** I-JEPA samples 4 target blocks (15-20 % of tokens each, aspect
  0.75-1.5) and one large context block (85-100 %) *minus the targets*; V-JEPA
  masks 3D tubelets with high ratios (~90 %). Masks must be large and
  semantic (blocks), not random pixels, or the task reduces to interpolation.
- **Target encoder.** EMA of the context encoder, momentum from 0.996 to 1.0
  over training; its outputs are layer-normalised per token; no gradient.
- **Predictor.** A narrow ViT (depth 6-12, width 384) that takes context
  tokens plus mask tokens with the target positions; narrower than the
  encoder so the information must sit in the encoder.
- **Loss.** L2 (or smooth L1) between predicted and target tokens, averaged
  over target tokens only.
- **Optimiser.** AdamW, lr 1e-3 with warm-up 40 epochs then cosine, weight
  decay 0.04-0.4, batch 2 048 images (scale lr with batch), 300-800 epochs on
  ImageNet-1k scale; for 10k medical volumes, 100-300 epochs at batch 64 of
  96^3 crops is a realistic budget (1-3 GPU-days on one 80 GB card with
  bf16).
- **Collapse diagnostics.** Monitor the per-dimension standard deviation of
  target embeddings and the effective rank: a sudden drop means collapse
  (raise EMA momentum start, shorten warm-up, lower lr).

## Evaluation

1. Linear probe / k-NN on the frozen encoder for classification (pathology
   present / absent, view classification).
2. Fine-tuning for segmentation with a light decoder (UNETR-style) on 10 %,
   50 %, 100 % of labels: the low-label regime is where pretraining shows;
   compare Dice / HD95 to from-scratch at equal compute.
3. Anomaly detection: distance in latent space to a bank of normal cases
   (AUROC), complementary to `vae-anomaly-detection`.
4. Always split pretraining and downstream sets by patient; pretraining on
   the downstream test patients is leakage even without labels.

## Datasets to pretrain on (bundled, lazy)

`hf_openmind` (114k head MRI, any study: `hf://MIC-DKFZ/OpenMind/OpenMind/dsXXXXXX`),
`hf_ct_rate_valid` (chest CT, gated; 50k volumes in the full repo), `totalsegmentator_ct`
(1 228 whole-body CT), `amos22`, `ixi_brain_mri`, `tcia_lidc_idri` (1 018 CT
series), `luna16`; cardiac: `msd_task02_heart`; signals: not bundled yet (use
PhysioNet PTB-XL with the same recipe).

```python
import pardesline as pl

ds = pl.load("totalsegmentator_ct")  # 1 228 CTs, fetched on access
vol = ds[0].ct.to_sitk()  # resample to 1.5 mm isotropic, clip HU, crop 96^3 patches
```

[`scripts/jepa3d_pretrain.py`](https://github.com/pardesline/pardesline/blob/main/skills/jepa-pretraining/scripts/jepa3d_pretrain.py) is a complete reference: 3D ViT encoder, EMA
target, block masking in 3D, predictor, loss, collapse monitor, a loader that
reads any pardesline dataset volume role (resampled, windowed, cropped), and
a linear-probe evaluation hook. Needs `torch`; runs on CPU at toy size for a
smoke test.

<sub>Source: `skills/jepa-pretraining/SKILL.md`, published on 2026-10-14.</sub>
