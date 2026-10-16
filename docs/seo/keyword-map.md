# Keyword map

Which search query lands on which page. Every supported dataset and every public algorithm family has at least one entry. Pages that do not exist yet are created in Phase 3 under the URL structure below, so links written today keep working.

Intent codes: **N** navigational (looking for a thing by name), **I** informational (how do I…), **C** comparative (X vs Y, alternative to X), **T** transactional (install, download, pip).

## URL structure (docs site: https://pardesline.github.io/pardesline/)

| Section | URL pattern | Generated from |
|---|---|---|
| Home | `/` | README |
| Getting started | `/getting-started/install/`, `/getting-started/tutorial/`, `/getting-started/concepts/` | hand-written |
| Datasets | `/datasets/` (catalog), `/datasets/<manifest-name>/` (43 pages) | `src/pardesline/data/manifests/*.json` |
| Algorithms | `/algorithms/` (index), `/algorithms/<module-id>/` (19 pages) | `src/pardesline/catalog/data/*.json` |
| Models | `/models/` (index), `/models/<name>/` (dinov3, jepa, pointnet, vae, medical-segmentation) | `skills/<name>/SKILL.md` + scripts; reserved for the model registry |
| Why our defaults work | `/algorithms/why-our-defaults-work/` | catalog rationale fields + skills |
| How-to | `/how-to/<slug>/` | hand-written, title = query |
| Examples | `/examples/` | `examples/<slug>/` |
| API reference | `/api/` | mkdocstrings |
| Comparison | `/comparison/` | hand-written |
| FAQ, Changelog, Contributing | `/faq/`, `/changelog/`, `/contributing/` | hand-written / CHANGELOG.md / CONTRIBUTING.md |
| Agents | `/agents/mcp/` | docs/mcp.md |

---

## Pillar 1 — Datasets (one-line access, standardized)

### Navigational

| Keyword | Page | Also |
|---|---|---|
| pardesline | `/` | README H1, PyPI |
| pardesline python | `/` | PyPI summary |
| pardesline datasets | `/datasets/` | README §Datasets |
| pardesline hugging face | `/how-to/load-a-hugging-face-3d-dataset-in-python/` | README §Datasets |

### Informational

| Keyword | Page | Also |
|---|---|---|
| 3d datasets python | `/datasets/` | README §Datasets table |
| medical imaging datasets python | `/datasets/` | README §Datasets (Medical group) |
| download medical imaging dataset python | `/how-to/download-a-medical-imaging-dataset-in-python/` | README demo |
| 3d dataset loader python | `/getting-started/concepts/#dataset` | `pardesline.data.load` docstring |
| point cloud dataset python | `/datasets/#general-3d` | `/datasets/kitti_raw_2011_09_26_drive_0001/` |
| lidar dataset python | `/datasets/kitti_raw_2011_09_26_drive_0001/` | `/datasets/hf_uniocc_carla_mini/` |
| ct scan dataset python | `/datasets/#ct` | README §Datasets |
| mri dataset python | `/datasets/#mri` | `/datasets/ixi_brain_mri/` |
| brain mri dataset download | `/datasets/ixi_brain_mri/` | `/datasets/hf_openmind/`, `/datasets/openneuro_ds000228/` |
| lung ct dataset | `/datasets/luna16/` | `/datasets/msd_task06_lung/`, `/datasets/tcia_lidc_idri/` |
| abdominal ct segmentation dataset | `/datasets/amos22/` | `/datasets/totalsegmentator_ct/`, `/datasets/chaos_abdomen/` |
| spine ct dataset | `/datasets/verse19_spine/` | `/datasets/spider_lumbar_mri/` |
| cardiac mri dataset | `/datasets/msd_task02_heart/` | README demo |
| whole body ct segmentation dataset | `/datasets/totalsegmentator_ct/` | `/datasets/totalsegmentator_mri/` |
| dicom dataset python | `/datasets/#dicom` | `/datasets/tcia_pancreas_ct/` |
| nifti dataset python | `/datasets/#nifti` | `/datasets/msd_task04_hippocampus/` |
| 3d mesh dataset | `/datasets/hf_objaverse_glb_shard/` | `/datasets/medshapenet/` |
| anatomical shapes dataset stl | `/datasets/medshapenet/` | |
| gaussian splatting dataset | `/datasets/hf_kitti360_gs_subset/` | `/datasets/c3vd_endoscopy_splats/` |
| hugging face 3d dataset | `/how-to/load-a-hugging-face-3d-dataset-in-python/` | README §Datasets |
| hugging face medical dataset | `/how-to/load-a-hugging-face-3d-dataset-in-python/` | `/datasets/hf_kits23/` |
| dataset manifest | `/getting-started/concepts/#manifest` | `/datasets/#the-manifest` |
| dataset license checker python | `/getting-started/concepts/#licence` | `Dataset.license` docstring |
| dicom to nifti python | `/how-to/convert-a-dicom-series-to-nifti-in-python/` | `Volume.save` docstring |
| standardize medical images python | `/how-to/standardize-a-folder-of-medical-images-in-python/` | README §Why |
| resample ct to isotropic spacing python | `/how-to/standardize-a-folder-of-medical-images-in-python/` | `/algorithms/pyvista_volume_processing/` |
| load npy point cloud python | `/how-to/load-raw-npy-and-bin-point-clouds-with-a-layout/` | `RawArray` docstring |
| kitti bin to ply python | `/how-to/load-raw-npy-and-bin-point-clouds-with-a-layout/` | `/datasets/kitti_raw_2011_09_26_drive_0001/` |
| tcia download python | `/how-to/download-a-tcia-collection-in-python/` | `/datasets/#tcia` |
| openneuro download python | `/datasets/openneuro_ds000228/` | |
| zenodo dataset partial download | `/datasets/#remote-archives-by-http-range` | `/datasets/amos22/` |

### Per-dataset queries (one page each; all 43 covered)

| Keyword | Page |
|---|---|
| medical segmentation decathlon python | `/datasets/#medical-segmentation-decathlon` (links the 10 tasks) |
| msd brain tumour dataset | `/datasets/msd_task01_braintumour/` |
| msd heart left atrium dataset | `/datasets/msd_task02_heart/` |
| msd liver dataset download | `/datasets/msd_task03_liver/` |
| msd hippocampus dataset | `/datasets/msd_task04_hippocampus/` |
| msd prostate dataset | `/datasets/msd_task05_prostate/` |
| msd lung dataset | `/datasets/msd_task06_lung/` |
| msd pancreas dataset | `/datasets/msd_task07_pancreas/` |
| msd hepatic vessel dataset | `/datasets/msd_task08_hepaticvessel/` |
| msd spleen dataset | `/datasets/msd_task09_spleen/` |
| msd colon dataset | `/datasets/msd_task10_colon/` |
| amos dataset python | `/datasets/amos22/` |
| totalsegmentator dataset python | `/datasets/totalsegmentator_ct/` |
| totalsegmentator mri dataset | `/datasets/totalsegmentator_mri/` |
| luna16 python | `/datasets/luna16/` |
| ixi dataset python | `/datasets/ixi_brain_mri/` |
| verse dataset vertebrae python | `/datasets/verse19_spine/` |
| spider lumbar spine mri dataset | `/datasets/spider_lumbar_mri/` |
| chaos abdominal dataset | `/datasets/chaos_abdomen/` |
| lidc-idri python | `/datasets/tcia_lidc_idri/` |
| nsclc-radiomics download | `/datasets/tcia_nsclc_radiomics_dicom/`, `/datasets/hf_nsclc_radiomics/` |
| pancreas-ct tcia python | `/datasets/tcia_pancreas_ct/` |
| prostate-3t tcia | `/datasets/tcia_prostate_3t/` |
| openneuro ds000228 | `/datasets/openneuro_ds000228/` |
| kits23 dataset python | `/datasets/hf_kits23/` |
| abdomenatlas dataset | `/datasets/hf_abdomenatlas_mini/` |
| ct-rate dataset | `/datasets/hf_ct_rate_valid/` |
| cvpr 2025 biomedical segmentation foundation model dataset | `/datasets/hf_biomedsegfm_3d_val/` |
| openmind mri dataset | `/datasets/hf_openmind/` |
| medshapenet python | `/datasets/medshapenet/` |
| c3vd colonoscopy dataset | `/datasets/c3vd_endoscopy_splats/` |
| kitti raw data python | `/datasets/kitti_raw_2011_09_26_drive_0001/` |
| kitti-360 gaussian splatting | `/datasets/hf_kitti360_gs_subset/` |
| uniocc dataset | `/datasets/hf_uniocc_carla_mini/` |
| objaverse download python | `/datasets/hf_objaverse_glb_shard/` |
| 3d arena dataset | `/datasets/hf_3d_arena/` |
| open3d bunny dataset | `/datasets/open3d_bunny/` |
| open3d armadillo | `/datasets/open3d_armadillo/` |
| open3d icp demo point clouds | `/datasets/open3d_icp_demo/` |
| rire registration dataset | `/datasets/rire_brain/` |
| popi 4d ct dataset | `/datasets/popi_lung_4dct/` |
| visible human mri | `/datasets/visible_human_head_mri/` |
| liver tumor segmentation dataset inter-observer | `/datasets/liver_tumor_patient01/` |

### Comparative

| Keyword | Page | Also |
|---|---|---|
| monai dataset loaders vs | `/comparison/#datasets` | README §Comparison |
| torchio datasets alternative | `/comparison/#datasets` | |
| hugging face datasets 3d support | `/comparison/#datasets` | README §Why |
| medical imaging dataset hub | `/datasets/` | |

### Transactional

| Keyword | Page | Also |
|---|---|---|
| pip install medical imaging datasets | `/getting-started/install/` | README §Install |
| download brats dataset python | `/faq/#which-datasets-are-not-supported` (BraTS needs the Synapse DUA; roadmap) | Datasets-wanted issue |
| download modelnet shapenet scannet python | `/faq/#which-datasets-are-not-supported` (gated; roadmap) | Datasets-wanted issue |

---

## Pillar 2 — Algorithms & models

### Navigational

| Keyword | Page | Also |
|---|---|---|
| pardesline algorithms | `/algorithms/` | README §Algorithms & models |
| pardesline catalog | `/algorithms/` | `pardesline list` CLI |
| pardesline mcp | `/agents/mcp/` | README §MCP |

### Informational — classical algorithms (one page per module, all 19 covered)

| Keyword | Page | Also |
|---|---|---|
| 3d computer vision python | `/` | README H1 |
| python 3d vision library | `/` | README H1 |
| medical imaging python library | `/` | README subtitle |
| point cloud processing python | `/algorithms/point_cloud_processing/` | `/algorithms/pyvista_pointcloud_processing/` |
| voxel downsample point cloud python | `/algorithms/point_cloud_processing/#voxel_downsample` | |
| remove outliers point cloud python | `/algorithms/point_cloud_processing/#statistical_outlier_removal` | `PointCloud.clean` docstring |
| mesh processing python | `/algorithms/mesh_processing/` | `/algorithms/pyvista_mesh_processing/` |
| mesh simplification python | `/algorithms/mesh_processing/#simplification` | `/algorithms/pyvista_mesh_processing/#pv_decimate` |
| mesh to point cloud python | `/algorithms/mesh_processing/#mesh_to_pcd_poisson_disk` | `Mesh.to_points` docstring |
| smooth mesh python | `/algorithms/pyvista_mesh_processing/#pv_smooth_taubin` | |
| fill holes mesh python | `/algorithms/pyvista_mesh_processing/#pv_fill_holes` | |
| voxelize mesh python | `/algorithms/voxel_to_mesh/#voxelization` | |
| signed distance field python | `/algorithms/sdf/` | |
| 3d reconstruction python | `/algorithms/point_cloud_reconstruction/` | README §Algorithms |
| point cloud to mesh python | `/how-to/reconstruct-a-surface-from-a-point-cloud-in-python/` | `/algorithms/point_cloud_reconstruction/#poisson` |
| poisson surface reconstruction python | `/algorithms/point_cloud_reconstruction/#poisson` | |
| ball pivoting python | `/algorithms/point_cloud_reconstruction/#ball_pivoting` | |
| alpha shape point cloud python | `/algorithms/point_cloud_reconstruction/#alpha_shape` | |
| 3d registration python | `/algorithms/registration/` | README §Algorithms |
| icp python | `/how-to/register-two-point-clouds-with-icp-in-python/` | `/algorithms/registration/#icp_refinement` |
| point cloud registration python | `/how-to/register-two-point-clouds-with-icp-in-python/` | |
| ransac registration fpfh python | `/algorithms/registration/#ransac_global` | |
| global registration then icp | `/algorithms/registration/#ransac_icp_pipeline` | |
| non rigid registration python | `/algorithms/deformable_registration/` | |
| coherent point drift python | `/algorithms/deformable_registration/#cpd_deformable` | |
| plane segmentation point cloud python | `/algorithms/point_cloud_segmentation/#ransac_plane` | |
| dbscan point cloud clustering python | `/algorithms/point_cloud_segmentation/#dbscan_clustering` | |
| depth map to point cloud python | `/algorithms/stereo_3d_reconstruction/` | |
| lidar ground removal python | `/algorithms/lidar_scene_detection/#ground_removal` | |
| lidar object clustering python | `/algorithms/lidar_scene_detection/#object_clustering` | |
| lidar camera fusion python | `/algorithms/lidar_camera_fusion/` | |
| point cloud normal estimation python | `/algorithms/features_extraction/#normal_estimation` | |
| fpfh features python | `/algorithms/features_extraction/#fpfh_features` | |
| curvature point cloud python | `/algorithms/features_extraction/#curvature_estimation` | `/algorithms/pyvista_analysis/#pv_curvature` |
| mesh collision detection python | `/algorithms/collision_detection/` | |
| penetration depth meshes python | `/algorithms/collision_detection/#penetration_depth` | |
| pyvista clip point cloud | `/algorithms/pyvista_pointcloud_processing/` | |
| contour volume isosurface python | `/algorithms/pyvista_volume_processing/#pv_contour` | `Volume.to_mesh` docstring |
| slice 3d volume python | `/algorithms/pyvista_volume_processing/#pv_slice_orthogonal` | |
| mesh distance comparison python | `/algorithms/pyvista_analysis/#pv_distance` | |
| feature edges mesh python | `/algorithms/pyvista_analysis/#pv_extract_feature_edges` | |
| simpleitk rigid registration python | `/algorithms/simpleitk_registration/#rigid` | `/how-to/register-ct-and-mri-of-the-same-patient-in-python/` |
| ct mri registration python | `/how-to/register-ct-and-mri-of-the-same-patient-in-python/` | |
| bspline registration simpleitk | `/algorithms/simpleitk_registration/#bspline` | |
| demons registration python | `/algorithms/simpleitk_registration/#demons` | |
| ct segmentation python | `/how-to/segment-organs-in-a-ct-scan-in-python/` | `/algorithms/simpleitk_segmentation/` |
| otsu threshold 3d volume python | `/algorithms/simpleitk_segmentation/#otsu_threshold` | |
| watershed segmentation 3d python | `/algorithms/simpleitk_segmentation/#watershed` | |
| connected components 3d python | `/algorithms/simpleitk_segmentation/#connected_components` | |
| segmentation mask to mesh python | `/how-to/turn-a-segmentation-mask-into-a-mesh-in-python/` | `LabelMap.to_mesh` docstring |
| align two meshes python | `/how-to/align-two-scans-in-python/` | `PointCloud.align` docstring |
| dice score hausdorff python | `/models/evaluation-metrics/` | `skills/evaluation-metrics-3d` |
| chamfer distance point cloud python | `/models/evaluation-metrics/` | |

### Informational — deep-learning models (reference scripts today; one-line model access is on the roadmap)

Flag: **ranks fully once the model registry ships**. Pages exist now with the reference script, the dataset it runs on and the roadmap note.

| Keyword | Page | Also |
|---|---|---|
| 3d deep learning python | `/models/` | README §Algorithms & models (DL rows) |
| 3d segmentation pytorch | `/models/medical-segmentation/` | `skills/medical-segmentation-models` |
| pretrained 3d segmentation model | `/models/medical-segmentation/` (roadmap note) | Model-registry tracking issue |
| nnunet dataset preparation python | `/models/medical-segmentation/#prepare-an-nnu-net-dataset` | `prepare_nnunet_dataset.py` |
| organ segmentation model | `/models/medical-segmentation/` | `/datasets/totalsegmentator_ct/` |
| dinov3 3d | `/models/dinov3/` | `skills/dinov3-dense-features` |
| dinov3 3d python | `/models/dinov3/` (roadmap note) | |
| dinov3 features medical imaging | `/models/dinov3/` | `dinov3_features.py` |
| frozen backbone faster rcnn echocardiography | `/models/dinov3/#detection-head` | `dinov3_faster_rcnn.py` |
| foundation model medical imaging | `/models/` | `/models/dinov3/`, `/models/jepa/` |
| jepa 3d | `/models/jepa/` | `skills/jepa-pretraining` |
| v-jepa medical volumes pretraining | `/models/jepa/` | `jepa3d_pretrain.py` |
| pointnet segmentation python | `/models/pointnet/` | `pointnet_seg.py` |
| pointnet medical point cloud | `/models/pointnet/` | `/datasets/msd_task04_hippocampus/` |
| vae anomaly detection medical images | `/models/vae-anomaly/` | `vae_anomaly.py` |
| unsupervised anomaly detection dental xray | `/models/vae-anomaly/` | |
| point cloud to gaussian splatting python | `/how-to/convert-a-point-cloud-to-gaussian-splats-in-python/` | `skills/gaussian-splatting` |
| sam 3d python | `/models/` (roadmap note) | Model-registry tracking issue |
| load pretrained model medical imaging python | `/models/` (roadmap note) | Model-registry tracking issue |
| hugging face 3d model | `/models/` (roadmap note) | Model-registry tracking issue |
| atlas based segmentation python | `/how-to/label-a-scan-from-an-atlas-in-python/` | `skills/atlas-label-transfer` |

### Comparative

| Keyword | Page | Also |
|---|---|---|
| open3d alternative | `/comparison/#open3d` | README §Comparison |
| open3d vs pyvista | `/comparison/#pyvista` | |
| pyvista vs open3d point cloud | `/comparison/#pyvista` | |
| simpleitk vs itk | `/comparison/#simpleitk` | |
| trimesh vs open3d | `/comparison/#trimesh` | |
| monai alternative | `/comparison/#monai` | |
| torchio vs monai | `/comparison/#torchio` | |
| open3d python 3.13 | `/faq/#python-313` | README §Install matrix |

### Transactional

| Keyword | Page | Also |
|---|---|---|
| pip install 3d vision | `/getting-started/install/` | README §Install |
| pip install open3d pyvista simpleitk together | `/getting-started/install/#extras` | |
| conda 3d vision medical imaging | `/getting-started/install/#conda` | |

---

## "It works out of the box" intent (the differentiator)

Each query gets a how-to page that names the failure, the parameter behind it, and the one-liner that sets it. The written proof is `/algorithms/why-our-defaults-work/`.

| Keyword | Page | Also |
|---|---|---|
| icp not converging | `/how-to/fix-icp-that-does-not-converge/` | `/algorithms/why-our-defaults-work/#registration` |
| open3d icp parameters | `/how-to/fix-icp-that-does-not-converge/#the-parameters` | `/algorithms/registration/` |
| icp max correspondence distance | `/how-to/fix-icp-that-does-not-converge/#max-correspondence-distance` | |
| best parameters for icp | `/algorithms/why-our-defaults-work/#registration` | |
| ransac registration fails | `/how-to/fix-ransac-global-registration-that-fails/` | |
| point cloud registration noisy scan | `/how-to/fix-icp-that-does-not-converge/#noisy-partial-scans` | `/examples/#registration` |
| icp industrial point cloud | `/algorithms/why-our-defaults-work/#registration` | examples/real_cases |
| 3d registration real data | `/algorithms/why-our-defaults-work/` | README §Defaults that work on real data |
| point cloud registration production | `/algorithms/why-our-defaults-work/` | |
| poisson reconstruction holes artifacts | `/algorithms/why-our-defaults-work/#reconstruction` | |
| voxel size for downsampling point cloud | `/algorithms/why-our-defaults-work/#downsampling-and-cleaning` | |
| statistical outlier removal parameters | `/algorithms/why-our-defaults-work/#downsampling-and-cleaning` | |
| simpleitk registration fails mutual information | `/how-to/register-ct-and-mri-of-the-same-patient-in-python/#when-it-fails` | `/algorithms/why-our-defaults-work/#volume-registration` |
| otsu threshold ct fails | `/how-to/segment-organs-in-a-ct-scan-in-python/#when-it-fails` | |
| segmentation model fails on my ct | `/models/medical-segmentation/#why-models-fail-on-new-scanners` | |
| 3d algorithm default parameters | `/algorithms/why-our-defaults-work/` | |
| marching cubes isovalue label map | `/how-to/turn-a-segmentation-mask-into-a-mesh-in-python/` | |

---

## Agents / MCP

| Keyword | Page | Also |
|---|---|---|
| mcp server computer vision | `/agents/mcp/` | README §MCP |
| mcp server medical imaging | `/agents/mcp/` | |
| mcp server point cloud | `/agents/mcp/` | |
| claude code 3d vision | `/agents/mcp/#claude-code` | `.claude-plugin/plugin.json` |
| cursor mcp 3d datasets | `/agents/mcp/#cursor` | |
| gemini cli mcp server python | `/agents/mcp/#gemini-cli` | |
| mcp server datasets | `/agents/mcp/#tools` | |

---

## Coverage check

- 43 datasets: 43 per-dataset rows above.
- 19 algorithm modules: 19 `/algorithms/<module>/` targets above.
- 5 model skills (dinov3, jepa, pointnet, vae-anomaly, medical-segmentation) + metrics + splats + atlas transfer: all mapped.
- Not supported today and said so: BraTS, ModelNet, ShapeNet, ScanNet, pretrained-model loading (roadmap).

Total keywords: 190 (target 80–150 exceeded because every dataset and module gets its own row).
