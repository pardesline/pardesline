---
title: Examples gallery — 3D algorithms and models on public datasets
description: Twelve executed examples, each a self-contained script on a bundled dataset with its image and numbers committed: registration, ICP comparison, label map to mesh, Poisson, threshold segmentation, LiDAR clustering, atlas transfer, Gaussian splats, metrics, PointNet, JEPA, VAE, DINOv2.
---

# Examples gallery

Each example is one folder under [`examples/`](https://github.com/pardesline/pardesline/tree/main/examples) with a self-contained `run.py` that downloads what it needs through `pl.load(...)`, runs, prints a JSON summary and writes its images next to itself. Every image and number here was produced by the script beside it on 2026-10-16.

```bash
pip install "pardesline[all]"      # PyTorch examples: pip install torch (CPU is enough)
python examples/<folder>/run.py
```

| Example | Dataset | What it shows | Result |
|---|---|---|---|
| [register_ct_mr_rire](https://github.com/pardesline/pardesline/tree/main/examples/register_ct_mr_rire) {#register_ct_mr_rire} | `rire_brain` | SimpleITK rigid registration, CT fixed, MR moving; the README demo | 21 s cold; rotation [0.34, −0.35, −4.38]° |
| [icp_registration_bunny](https://github.com/pardesline/pardesline/tree/main/examples/icp_registration_bunny) {#icp_registration_bunny} | `open3d_bunny` | textbook Open3D ICP vs `target.align(moving)` on a 35°, 70 %-overlap, noisy copy | 32.0° vs 0.14° residual |
| [hippocampus_mask_to_mesh](https://github.com/pardesline/pardesline/tree/main/examples/hippocampus_mask_to_mesh) {#hippocampus_mask_to_mesh} | `msd_task04_hippocampus` | label map to exact surfaces, Taubin smoothing, STL + sidecar | two meshes over the MRI slices |
| [poisson_reconstruction_bunny](https://github.com/pardesline/pardesline/tree/main/examples/poisson_reconstruction_bunny) {#poisson_reconstruction_bunny} | `open3d_bunny` | 20 000 points, outlier removal, Poisson at the defaults | clean density-trimmed surface |
| [spleen_ct_threshold_segmentation](https://github.com/pardesline/pardesline/tree/main/examples/spleen_ct_threshold_segmentation) {#spleen_ct_threshold_segmentation} | `msd_task09_spleen` | soft-tissue window + connected components vs the expert label | the baseline a model must beat |
| [kitti_lidar_ground_and_objects](https://github.com/pardesline/pardesline/tree/main/examples/kitti_lidar_ground_and_objects) {#kitti_lidar_ground_and_objects} | `kitti_raw_2011_09_26_drive_0001` | raw `(N, 4)` binary through the layout, ground RANSAC, DBSCAN | 35 476 points clustered |
| [atlas_label_transfer_bunny](https://github.com/pardesline/pardesline/tree/main/examples/atlas_label_transfer_bunny) {#atlas_label_transfer_bunny} | `open3d_bunny` | labelled atlas registered onto a noisy rotated copy, labels transferred | 99.4 % agreement, 0.06° |
| [points_to_gaussians_bunny](https://github.com/pardesline/pardesline/tree/main/examples/points_to_gaussians_bunny) {#points_to_gaussians_bunny} | `open3d_bunny` | 50 000 points to a 3DGS PLY | 12 MB file, opens in gsplat |
| [metrics_liver_interobserver](https://github.com/pardesline/pardesline/tree/main/examples/metrics_liver_interobserver) {#metrics_liver_interobserver} | `liver_tumor_patient01` | Dice, HD95, surface Dice between three radiologists | Dice 0.82–0.85, HD95 2.5 mm |
| [pointnet_hippocampus](https://github.com/pardesline/pardesline/tree/main/examples/pointnet_hippocampus) {#pointnet_hippocampus} | `msd_task04_hippocampus` | 40 cases to labelled point clouds, PointNet trained 40 epochs on CPU | 0.97 mIoU, 0.98 accuracy |
| [jepa_hippocampus](https://github.com/pardesline/pardesline/tree/main/examples/jepa_hippocampus) {#jepa_hippocampus} | `msd_task04_hippocampus` | 3D JEPA pretraining, laptop-sized | loss 0.48 → 0.26 in 3 epochs |
| [vae_anomaly_hippocampus](https://github.com/pardesline/pardesline/tree/main/examples/vae_anomaly_hippocampus) {#vae_anomaly_hippocampus} | `msd_task04_hippocampus` | VAE on 24 normal slices, 8 scored, 2 with a synthetic lesion | lesions 0.59 / 0.64, normals ≤ 0.33 |
| [dinov2_features_kitti](https://github.com/pardesline/pardesline/tree/main/examples/dinov2_features_kitti) {#dinov2_features_kitti} | `kitti_raw_2011_09_26_drive_0001` | frozen DINOv2-small patch features, PCA-coloured | 10×32 grid, 384-d |

## Images

<div class="grid" markdown>

![CT slice and registered MR overlay](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/register_ct_mr_rire/rire_ct_mr.png){ width="100%" }
*SimpleITK rigid registration on RIRE*

![Two bunny point clouds aligned](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/icp_registration_bunny/pardesline_defaults.png){ width="100%" }
*RANSAC + ICP on the Stanford bunny, 0.14° off*

![Hippocampus meshes over MRI slices](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/hippocampus_mask_to_mesh/hippocampus.png){ width="100%" }
*Label map to mesh on MSD hippocampus*

![Bunny points and the Poisson surface](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/poisson_reconstruction_bunny/bunny_poisson.png){ width="100%" }
*Poisson reconstruction on the Stanford bunny*

![Threshold segmentation vs reference spleen label](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/spleen_ct_threshold_segmentation/spleen_ct.png){ width="100%" }
*Threshold segmentation on MSD spleen*

![KITTI sweep with ground removed and objects coloured](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/kitti_lidar_ground_and_objects/kitti_objects.png){ width="100%" }
*Ground removal and clustering on KITTI*

![Bunny atlas in grey with the scan coloured by transferred labels](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/atlas_label_transfer_bunny/atlas_transfer.png){ width="100%" }
*Atlas label transfer on the Stanford bunny*

![Bunny Gaussian centres coloured by height](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/points_to_gaussians_bunny/bunny_splats.png){ width="100%" }
*Gaussian splats on the Stanford bunny*

![Test slices, VAE reconstructions and residual maps with scores](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/vae_anomaly_hippocampus/vae_anomaly.png){ width="100%" }
*VAE anomaly detection on MSD hippocampus slices*

![KITTI camera frame above its PCA-coloured DINOv2 patch features](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/dinov2_features_kitti/dinov2_kitti.png){ width="100%" }
*DINOv2 features on KITTI*

</div>

## Real cases

[`examples/real_cases/`](https://github.com/pardesline/pardesline/tree/main/examples/real_cases) is where runs on data that looks like production data go (industrial scans, de-identified medical volumes, field LiDAR), with the template and the review rules. The README's "Validated on real cases" table only lists folders that exist there or in `examples/`.

## Writing one

Copy [`templates/new_pipeline/`](https://github.com/pardesline/pardesline/tree/main/templates/new_pipeline): a `run.py` that loads a bundled dataset, runs one algorithm or model, writes one image and a JSON summary, and a README stating the dataset, the licence, the runtime and what the defaults handled.
