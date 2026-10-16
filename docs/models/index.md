---
title: Pretrained 3D and medical imaging models in Python: what pardesline ships and what is coming
description: Reference implementations and expert guides for DINOv3 features, 3D JEPA pretraining, PointNet segmentation, VAE anomaly detection, nnU-Net preparation and 3D metrics; one-line pretrained model access is on the roadmap.
---

# Models

Deep learning in pardesline today is **reference implementations and expert guides** that read any pardesline dataset: no weights are shipped and there is no inference API yet. Each page below documents the scripts, the example that ran them on a bundled dataset, and the recipe at full scale.

!!! info "Coming: one-line model access"
    Models will get the same treatment as datasets: a **model manifest** (source, weights URI, licence, input type, task, memory and GPU needs, provenance) and a single loader / runner API that looks the same whatever the source (Hugging Face Hub, torch.hub, vendor repositories): `pl.load_model("dinov3")` then `pl.run(model, dataset)`, then visualise. The URLs under `/models/<name>/` are reserved so these pages fill in without breaking links. Vote and comment on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be written now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model) and listed on [Models wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Amodel).

| Model page | Task | What ships today | Example (executed) |
|---|---|---|---|
| [DINOv3 and DINOv2 features for 3D and medical imaging](dinov3.md) | dinov3 dense features | `dinov3_faster_rcnn.py`, `dinov3_features.py` | [`dinov2_features_kitti`](https://github.com/pardesline/pardesline/tree/main/examples/dinov2_features_kitti) |
| [JEPA self-supervised pretraining on 3D medical volumes](jepa.md) | jepa pretraining | `jepa3d_pretrain.py` | [`jepa_hippocampus`](https://github.com/pardesline/pardesline/tree/main/examples/jepa_hippocampus) |
| [PointNet segmentation of medical and industrial point clouds](pointnet.md) | pointnet segmentation | `make_point_dataset.py`, `pointnet_seg.py` | [`pointnet_hippocampus`](https://github.com/pardesline/pardesline/tree/main/examples/pointnet_hippocampus) |
| [VAE anomaly detection on medical images](vae-anomaly.md) | vae anomaly detection | `vae_anomaly.py` | [`vae_anomaly_hippocampus`](https://github.com/pardesline/pardesline/tree/main/examples/vae_anomaly_hippocampus) |
| [Pretrained 3D medical image segmentation models: nnU-Net and friends](medical-segmentation.md) | medical segmentation models | `prepare_nnunet_dataset.py` | skill script on MSD spleen |
| [Dice, HD95, Chamfer and the other 3D evaluation metrics](evaluation-metrics.md) | evaluation metrics 3d | `metrics3d.py` | [`metrics_liver_interobserver`](https://github.com/pardesline/pardesline/tree/main/examples/metrics_liver_interobserver) |

The PyTorch scripts need `pip install torch` (CPU is enough for the examples); DINOv3 weights need the licence accepted on the Hub, DINOv2 does not.
