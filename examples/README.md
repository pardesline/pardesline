# Examples

One folder per use case, titled `<algorithm or model> on <dataset>`. Each `run.py` is self-contained: it downloads what it needs through `pl.load(...)`, runs, prints a JSON summary or the key numbers, and writes its images next to itself. Nothing in this folder is faked: every image and number committed here was produced by the script beside it.

```bash
pip install "pardesline[all]"          # PyTorch examples: pip install torch (CPU is enough), the DINOv2 one also transformers
python examples/<folder>/run.py
```

| Example | Dataset | What it shows | Extra deps | Cold runtime on a laptop (CPU) |
|---|---|---|---|---|
| [register_ct_mr_rire](register_ct_mr_rire) | `rire_brain` (19 MB) | SimpleITK rigid registration, CT fixed / MR moving, two-panel render. The README demo. | | 21 s |
| [icp_registration_bunny](icp_registration_bunny) | `open3d_bunny` (3 MB) | Textbook Open3D ICP vs `target.align(moving)` on a 35°, 70 %-overlap, noisy copy: 32.0° vs 0.14° residual (RANSAC is randomised: expect a few hundredths of a degree of spread). Writes `result.json`. | | 40 s |
| [hippocampus_mask_to_mesh](hippocampus_mask_to_mesh) | `msd_task04_hippocampus` (28 MB) | Label map to exact surfaces (anterior, posterior), Taubin smoothing, STL + sidecar, render over MRI slices. | | 15 s (+ one-time archive download) |
| [poisson_reconstruction_bunny](poisson_reconstruction_bunny) | `open3d_bunny` | Mesh to 20 000 points, outlier removal, Poisson surface at the catalog defaults. | | 30 s |
| [spleen_ct_threshold_segmentation](spleen_ct_threshold_segmentation) | `msd_task09_spleen` (one 30 MB CT out of 1.6 GB) | `segment(30, 200 HU)` + connected components vs the expert label: the baseline a model must beat. | | 1–2 min (tar index + one volume) |
| [kitti_lidar_ground_and_objects](kitti_lidar_ground_and_objects) | `kitti_raw_2011_09_26_drive_0001` (one 2 MB sweep) | Raw `(N, 4)` binary read through the manifest layout, ground RANSAC, DBSCAN objects. | | 20 s |
| [atlas_label_transfer_bunny](atlas_label_transfer_bunny) | `open3d_bunny` | Labelled atlas registered onto a noisy rotated copy; label agreement 99.4 %, pose error 0.06°. | | 1 min |
| [points_to_gaussians_bunny](points_to_gaussians_bunny) | `open3d_bunny` | 50 000 points to a 3DGS-compatible PLY (12 MB) that opens in gsplat / Nerfstudio viewers. | SciPy | 20 s |
| [metrics_liver_interobserver](metrics_liver_interobserver) | `liver_tumor_patient01` (2 MB) | Dice 0.82–0.85, HD95 2.5 mm, surface Dice at 2 mm between three radiologists. | | 10 s |
| [pointnet_hippocampus](pointnet_hippocampus) | `msd_task04_hippocampus` | 40 labelled cases to point clouds (2 048 points, normals), PointNet trained 40 epochs: 0.97 mIoU, 0.98 accuracy on the held-out fraction. | torch | 6 min |
| [jepa_hippocampus](jepa_hippocampus) | `msd_task04_hippocampus` | 3D JEPA pretraining, laptop-sized configuration. | torch | minutes |
| [vae_anomaly_hippocampus](vae_anomaly_hippocampus) | `msd_task04_hippocampus` | VAE trained on 24 normal mid-slices, 8 held-out slices scored: the 2 with a synthetic lesion score 0.59 and 0.64, the normals at most 0.33. Writes a contact sheet. | torch, pillow | 2 min |
| [dinov2_features_kitti](dinov2_features_kitti) | `kitti_raw_2011_09_26_drive_0001` | Frozen DINOv2-small patch features on a camera frame, PCA-coloured; swap in DINOv3 after accepting its licence. | torch, transformers | 1 min + 90 MB weights |

Runtimes were measured on 2026-10-16 on a Windows laptop without GPU; downloads depend on your connection. The first access to an archive-backed dataset (MSD tars, KITTI zip) also builds the archive index, cached afterwards.

## Real cases

[real_cases/](real_cases) collects reproducible runs on data that looks like production data: industrial scans, de-identified medical volumes, field LiDAR. See its README for the template and the tracking issue.

## Writing a new example

Copy [`_template/`](../templates/new_pipeline) from the templates folder: a `run.py` that loads a bundled dataset, runs one algorithm or model, writes one image and a JSON summary, plus a README that states the dataset, the licence, the runtime and what the defaults handled. Add a row to the table above and a card to the README gallery.
