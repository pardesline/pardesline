---
title: Why ICP fails on real scans and what we set by default — 3D algorithm defaults that work on real data
description: The failure modes of textbook defaults in point cloud registration, surface reconstruction, outlier removal, volume registration and threshold segmentation, the parameters behind them, what pardesline sets, the data it was validated on, and when to override.
---

# Why ICP fails on real scans, and what we set by default

Upstream libraries give you the method with the defaults of the paper or the tutorial. Those defaults are tuned for the tutorial's data. Real scans are partial, noisy, anisotropic and at a scale the tutorial never saw. This page is the written proof behind the one-liners: for each algorithm family, the failure on textbook defaults, the parameters that matter, what pardesline sets, the data it was validated on, and when you should override.

Every number here is reproducible from the committed examples (`examples/<name>/result.json`) and every parameter is in the catalog with the same rationale (`pl.describe("module.method")`, the [algorithm pages](index.md)). Where a claim is only backed by generated test data, it says so.

## Registration of point clouds (`registration`)

**The failure.** Open3D's `registration_icp(source, target, 0.02, identity, PointToPoint())`, the call from the tutorial, on the Stanford bunny against a copy rotated by 35°, trimmed to 70 % overlap and jittered by 0.5 % of the diagonal: it stops **32.0°** off and reports a fitness of **0.98**. Two things went wrong at once: ICP is a local optimiser whose basin is a few degrees wide, so a 35° start converges to the nearest wrong minimum; and the threshold 0.02 (in file units, here metres on a 15 cm object) is so wide that almost every point finds a "correspondence", which is why the fitness looks excellent.

**What pardesline sets** (`target.align(moving)` = `registration.ransac_icp_pipeline`):

| Parameter | Value | Why |
|---|---|---|
| `voxel_size` | 0 → 1.3 % of the bounding-box diagonal | every other distance is a multiple of it; the pipeline scales itself to a 15 cm part and a 15 m facade; the same code runs in mm and in m |
| `normal_radius_factor`, `fpfh_radius_factor` | 2×, 5× the voxel | normals need a neighbourhood slightly larger than a cell; FPFH needs about five cells of support to be descriptive and still local on partial views |
| `distance_threshold_factor` | 1.5× the voxel (RANSAC) | tolerant to scanner noise, still rejects outliers |
| `mutual_filter` | on | both directions of the feature match must agree: the setting that most reduces false correspondences on symmetric parts |
| `ransac_n`, `edge_length_threshold` | 3, 0.9 | the minimum sample for a rigid transform; triplets whose pairwise distances disagree by more than 10 % are pruned before the expensive inlier count |
| `icp_threshold_factor` | 0.4× the voxel | the final ICP is tight so the 30 % of points without a counterpart cannot pull it |
| `icp_estimation_method` | point-to-plane (point-to-point fallback without normals) | converges in far fewer iterations and does not fight the surface |

**Validated on**: the bunny experiment ([examples/icp_registration_bunny](../examples.md#icp_registration_bunny)): **0.14°** residual, inlier RMSE 0.9 mm against a 1.4 mm noise floor; the bunny atlas transfer ([examples/atlas_label_transfer_bunny](../examples.md#atlas_label_transfer_bunny)): 99.4 % label agreement, 0.06° pose error; the Open3D indoor fragments (`open3d_icp_demo`). The ultrasound and CBCT cases of the [point-cloud registration guide](../guides/point-cloud-registration.md) are the founder's production experience and are not reproducible here: the honest claim is "the same settings, on public data with the same characteristics".

**When to override**

- RANSAC fitness below 0.3 and ICP does nothing: the features are meaningless because the voxel is wrong for the data. Pass `voxel_size` explicitly, 2–5× the point spacing. Check units first (`obj.frame`): mm read as m makes every radius wrong.
- Symmetric objects (cylinders, vertebral bodies, single teeth): the global stage converges to a mirrored pose. `ransac_n=4`, a prior pose, or more context in the scan.
- Flat scenes (floors, walls): point-to-plane slides. `icp_estimation_method="point_to_point"`, or constrain the degrees of freedom.
- Different devices with unknown scale: `ransac_with_scaling=True` once, then fix the scale.

Judge by inlier RMSE and the pose error on the overlapping region, not by fitness alone: fitness counts source points within the threshold and caps at the overlap ratio.

## Surface reconstruction (`point_cloud_reconstruction`)

**The failure.** Poisson reconstruction at Open3D's `depth=8` with no density trimming on a partial scan: the surface balloons over holes and the back of the object becomes a smooth bubble that looks plausible and is wrong. At `depth=11` on 20k points it fits the noise and takes minutes.

**What pardesline sets** (`points.to_mesh()` = `point_cloud_reconstruction.poisson`): `depth=9` (512 cells across the bounding cube: organ- and part-level detail on 20k–200k points), `scale=1.1` (Kazhdan's reference), `density_quantile=0.01` (the 1 % of vertices with the least sample support are removed, which is exactly where Poisson balloons), normals estimated at `normal_radius=0.1` with `normal_orient_k=15` when the cloud has none. The result is a clean, density-trimmed surface, not a closed one, and the sidecar says so.

**Validated on**: the bunny, 20 000 Poisson-disk points after outlier removal ([examples/poisson_reconstruction_bunny](../examples.md#poisson_reconstruction_bunny)); generated clouds in `tests/test_ops_smoke.py`.

**When to override**: very partial scans, `density_quantile=0.05–0.1`; dense metrology scans (millions of points), `depth=10–11`; thin structures (vessels, wires), ball pivoting with `radius_factor=1.5–2` instead of Poisson.

## Downsampling and cleaning (`point_cloud_processing`)

**The failure.** `voxel_size=0.05` from the tutorial on a dental scan in millimetres keeps one point per 5 cm, i.e. one point. `statistical_outlier_removal` with `std_ratio=1.0` removes the thin parts of a scan along with the noise.

**What pardesline sets**: `voxel_downsample` has an absolute `voxel_size=0.02` in file units because a downsample is a measurement choice (2 cm on a room, 0.5 mm on a tooth): the registration and feature pipelines derive their own voxel from the bounding box instead. `points.clean()` uses `nb_neighbors=20, std_ratio=2.0`: 20 neighbours give a stable mean distance per point; two standard deviations drop the flying pixels of scanners and keep edges and thin parts.

**Validated on**: the bunny with 0.5 % Gaussian noise (both bunny examples); KITTI sweeps; generated clouds.

**When to override**: depth cameras indoors, `std_ratio=1.0`; clean CAD-derived clouds, `std_ratio=3.0`; always set `voxel_size` in the units of your file.

## LiDAR scenes (`lidar_scene_detection`)

**The failure.** A ground plane fitted with a 1 cm RANSAC threshold on a 100 m sweep: the road is not flat (camber, slope, curbs), so half the road survives as "objects" and the clustering explodes. DBSCAN with `eps=0.02` on an HDL-64E sweep: the ring spacing reaches 0.3–0.5 m at 30 m, so every car becomes thirty stripes.

**What pardesline sets** (`lidar_scene_detection.object_clustering`): `ground_threshold=0.3` m (a band that follows a real road while car sills at 0.4–0.5 m stay out), `cluster_eps=0.5` m (bridges the ring spacing at 30 m without merging parked cars), `min_cluster_points=10` (a pedestrian at 20 m still clusters, ring fragments do not).

**Validated on**: KITTI drive 2011_09_26_0001, Velodyne HDL-64E in the sensor frame ([examples/kitti_lidar_ground_and_objects](../examples.md#kitti_lidar_ground_and_objects)): 35 476 points after ground removal clustered into cars, poles and walls.

**When to override**: 16-beam sensors, `cluster_eps=0.8–1.0`; indoor robots, `ground_threshold=0.05–0.1`; the sweep must be in metres, which the manifest layout guarantees for KITTI (`frame` sensor, `units` m).

## Rigid registration of volumes (`simpleitk_registration`)

**The failure.** SimpleITK's `ImageRegistrationMethod` with mean squares between a CT and a T1 MRI: bone is bright in one and dark in the other, so the metric is minimised by a wrong pose. With `GradientDescent(learningRate=1.0)` and no optimizer scales, one radian of rotation and one millimetre of translation are treated as the same step, so the rotation explodes on the first iteration. Without multi-resolution, a 40 mm initial offset is outside the capture range.

**What pardesline sets** (`fixed.align(moving)` = `simpleitk_registration.rigid`): Mattes mutual information with 50 bins (works across modalities), `sampling_percentage=0.01` RANDOM (cheap and slightly stochastic, which helps leave shallow minima), `initializer=GEOMETRY` (centres aligned before the first iteration), `shrink_factors=4,2,1` with `smoothing_sigmas=2,1,0` mm (capture range at the coarse level, sub-voxel precision at the fine one; sigmas in physical units so 4 mm slices are handled), `optimizer_scales_from_physical_shift=True` (the setting that makes `learning_rate=1.0` work on any dataset), 100 iterations per level with a 10-iteration convergence window.

**Validated on**: RIRE training_001, CT 0.65×0.65×4 mm against MR 1.25×1.25×4 mm, 40 mm initial offset, registered in 8.8 s ([examples/register_ct_mr_rire](../examples.md#register_ct_mr_rire), the README demo). The [CT/MR registration guide](../guides/multimodal-rigid-registration.md) traces the metric per iteration and compares with a hand-written SimpleITK stack.

**When to override**: initial misalignment above 30° or different patient positions, `simpleitk_registration.advanced_rigid` (exhaustive rotation search first); same modality follow-ups, `metric="mean_squares"` is faster; small fields of view, `sampling_percentage=0.05–0.15`; scanner calibration differences, `affine`.

## Threshold segmentation of volumes (`simpleitk_segmentation`)

**The failure.** Otsu on a whole CT splits air from everything else, not the organ from its neighbours. A fixed `threshold=100` on an 8-bit windowed image and on a 16-bit HU image mean different things. Connected components with `fully_connected=True` (26-connectivity) joins two organs that touch at a corner.

**What pardesline sets**: `volume.segment()` without bounds is Otsu with 128 bins (resolves the bimodal CT and MR histograms); `volume.segment(lower, upper)` takes the window you mean in intensity units (30–200 HU soft tissue, 300+ bone); `connected_components` uses 6-connectivity so diagonal contacts do not merge structures, and `min_size=15` voxels drops speckle.

**Validated on**: MSD spleen, soft-tissue window then components of at least 1 000 voxels against the expert label ([examples/spleen_ct_threshold_segmentation](../examples.md#spleen_ct_threshold_segmentation)). The example shows the honest result: a threshold finds soft tissue, not the spleen. That is the baseline a learned model has to beat, which is why the [models](../models/index.md) section exists.

**When to override**: MR has no absolute scale, so pass bounds from the volume's percentiles, not HU; contrast-enhanced CT, raise the upper bound; for organs, go to [medical segmentation models](../models/medical-segmentation.md).

## Mesh processing (`pyvista_mesh_processing`, `mesh_processing`)

**The failure.** Laplacian smoothing for 100 iterations on a marching-cubes organ surface shrinks it by a visible fraction of a millimetre and rounds every edge; quadric decimation to a fixed triangle count on a mesh with open boundaries pulls the rim inward.

**What pardesline sets**: `mesh.smooth()` is Taubin smoothing (`pass_band=0.1`, 20 iterations): a low-pass filter that removes the voxel staircase and keeps the volume, so it can run longer than Laplacian smoothing without shrinkage; `mesh.decimate()` removes 50 % of the triangles, which on marching-cubes output is the redundant co-planar half; `mesh.clean()` merges exact duplicates only (`tolerance=0`), which is safe on any mesh.

**Validated on**: MSD hippocampus label surfaces ([examples/hippocampus_mask_to_mesh](../examples.md#hippocampus_mask_to_mesh)); generated meshes.

**When to override**: volume measurements, `decimate(volume_preservation=True)`; CAD parts with sharp edges, `smooth(feature_smoothing=True)`; closing scan seams, `clean(tolerance=<spacing>)`.

## What is not covered yet

Deformable registration (`cpd_deformable`, `bspline`, `demons`), SDF and voxel operations, stereo depth and the PyVista analysis filters are validated on generated data only (`tests/test_ops_smoke.py`) and their rationale lines say so. The [benchmarks](../benchmarks.md) page regenerates the numbers above from scripts; real industrial and medical cases go to [examples/real_cases](https://github.com/pardesline/pardesline/tree/main/examples/real_cases) with the data or a loader for it.
