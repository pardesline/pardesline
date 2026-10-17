---
title: "VAE anomaly detection on medical images in Python"
description: "Expert guide to unsupervised anomaly detection by reconstruction with variational autoencoders on medical images and volumes (dental X-ray caries, chest X-"
---

# VAE anomaly detection on medical images in Python

!!! info "What ships today, and what is coming"
    **Today:** `vae_anomaly.py`: train on normal images, score any image by reconstruction residual, AUROC when labels exist. No weights are shipped and there is no inference API: the scripts are reference implementations that read any pardesline dataset.

    **Coming: one-line model access.** The same registry pattern as datasets, a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`. This page keeps its URL. Follow and vote on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be contributed now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model).

**Reference scripts:** [`vae_anomaly.py`](https://github.com/pardesline/pardesline/blob/main/skills/vae-anomaly-detection/scripts/vae_anomaly.py) (shipped in the wheel under `pardesline/skills/vae-anomaly-detection/scripts/`, served by the MCP tool `get_skill`).

**Runnable example:** [`examples/vae_anomaly_hippocampus/run.py`](https://github.com/pardesline/pardesline/tree/main/examples/vae_anomaly_hippocampus), executed on 2026-10-16; its outputs are committed next to it.

# Reconstruction-based anomaly detection with a VAE

## The idea

Train a model that only knows normal data. At test time it reconstructs the
normal part of an input and smooths away what it has never seen; the
residual `|x - x_hat|` highlights the anomaly without a single abnormal
training example. "A model that only knows healthy teeth reveals the cavity."

## The VAE

Encoder `q(z|x) = N(mu(x), diag(sigma^2(x)))`, decoder `p(x|z)`, loss

```
L = E_q[ -log p(x|z) ]  +  beta * KL( q(z|x) || N(0, I) )
  = reconstruction (L2 / BCE / SSIM)  +  beta * 1/2 sum (mu^2 + sigma^2 - log sigma^2 - 1)
```

with the reparameterisation `z = mu + sigma * eps`. The KL term makes the
latent space smooth and prevents the identity mapping; `beta` sets the
trade-off: `beta < 1` sharper reconstructions, weaker regularisation;
`beta > 1` (beta-VAE) more disentangled, blurrier. For anomaly detection a
*slightly under-capacity* model is the point: it must not be able to
reconstruct the anomaly.

Reference design (dental panoramic X-ray, 1 x 256 x 256): encoder of 5 blocks
Conv2d(3x3, stride 2) + BatchNorm + ReLU (32-64-128-256-512 channels) to 8 x 8,
fully connected to `mu, logvar` of 512 dims; decoder mirrors with
ConvTranspose2d; sigmoid output; loss L2 (or BCE) + KL; Adam 1e-3 to 1e-4,
batch 32, 100-300 epochs; cyclic or warm-up annealing of beta (0 -> 1 over 10
epochs) avoids posterior collapse. For volumes: 3D convolutions on 64^3 or
96^3 patches, latent 256-1024.

## Residual maps and scores

1. `r = |x - x_hat|` (or 1 - SSIM map, which is less sensitive to small
   intensity shifts).
2. Smooth with a Gaussian (sigma 2-4 px) to suppress pixel noise.
3. Image score = mean of the top 1 % of `r` (or the 99th percentile); pixel
   map = `r` thresholded.
4. Threshold from the **validation set of normal images**: e.g. the 99th
   percentile of normal scores for a 1 % false-positive rate; never from the
   test set.
5. Morphological opening removes 1-2 px specks; keep components above a
   minimum area in physical units (mm^2 via the pixel spacing).

Variants that help: masking the field of view (teeth region only), averaging
residuals over several latent samples (the VAE is stochastic), comparing
against the k nearest normal training images instead of a single
reconstruction.

## Evaluation (see `evaluation-metrics-3d`)

- Image level: AUROC and AUPRC of the score on a test set with both classes.
- Pixel level: AUROC / AUPRC on pixels when masks exist (AUPRC is the honest
  one at 1 % anomaly pixels), Dice of the thresholded map at the chosen
  operating point, per-lesion detection rate at an IoU of 0.3.
- Baselines to beat: a Gaussian on raw pixels, PCA reconstruction, k-NN on
  DINOv3 features (`dinov3-dense-features`); report them.

## Honest limits

- The decoder may reconstruct the anomaly when it is large or low-frequency
  (a bright implant is "easy"): the score then drops. Limit capacity, add
  noise or masking to the input (denoising / inpainting VAE).
- Blurry reconstructions produce residuals on every edge: SSIM or perceptual
  losses, or compare at a lower resolution.
- Domain shift (another scanner, exposure) raises every score: normalise
  intensities, calibrate thresholds per site, monitor the score distribution.
- Subtle anomalies below the reconstruction error floor are invisible;
  report the floor (mean residual on normal images).
- A detector that never saw caries can still flag them, but it cannot name
  them: pair with a classifier when a diagnosis is needed.

## Alternatives worth knowing

Feature-space methods (PatchCore, k-NN on frozen DINOv3 patch tokens) beat
reconstruction on many 2D benchmarks and need no training; latent-space
distance with a JEPA encoder (`jepa-pretraining`) scales to 3D; diffusion
restoration (AnoDDPM) gives sharper residuals at 100x the compute; for 3D
volumes, a 3D VAE on patches or slice-wise 2D with aggregation.

## Building normal-only sets with pardesline

Healthy controls: `ixi_brain_mri` (healthy subjects, T1/T2/PD), `hf_openmind`
(mostly healthy OpenNeuro cohorts), `openneuro_ds000228`; CT controls can be
cut from `totalsegmentator_ct` regions without lesions; abnormal test cases:
`msd_task01_braintumour`, `hf_kits23` (tumours), `luna16` (nodules). Split by
patient, keep the licence.

[`scripts/vae_anomaly.py`](https://github.com/pardesline/pardesline/blob/main/skills/vae-anomaly-detection/scripts/vae_anomaly.py): 2D VAE (256 px) with beta warm-up, training on a
folder of normal images, scoring of a folder with residual heatmaps (PNG) and
image scores (CSV), evaluation (AUROC / AUPRC) when a labels file is given.
Needs `torch`, `pillow`; runs a smoke test on synthetic images with `--smoke`.

<sub>Source: `skills/vae-anomaly-detection/SKILL.md`, published on 2026-10-14.</sub>
