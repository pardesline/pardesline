---
title: 3D computer vision and medical imaging algorithms in Python
description: 73 algorithms in 19 families for point clouds, meshes and CT/MRI volumes, each with documented, data-tied defaults: registration (RANSAC, ICP, rigid, affine, B-spline, demons), reconstruction, segmentation, LiDAR, SDF, mesh and volume processing.
---

# Algorithms

Nineteen families, 73 methods, 371 parameters, every default documented with the reason it was chosen and the data it was checked on. The methods are Open3D, PyVista/VTK, SimpleITK and SciPy code behind one call; `pl.run("module.method", file, **params)` validates the parameters before anything runs, and the high-level calls (`align`, `segment`, `to_mesh`, `clean`...) pick the method for the object type.

Start with [Why our defaults work](why-our-defaults-work.md) if you have been burnt by textbook parameters.

| Family | Methods | Works on | High-level calls |
|---|---|---|---|
| [Point Cloud Processing](point_cloud_processing.md) | `voxel_downsample`, `statistical_outlier_removal`, `radius_outlier_removal`, `mesh_to_pointcloud` | `.ply`, `.pcd`, `.txt`, `.xyz` | `points.downsample(voxel_size=...)`; `points.clean()` |
| [Mesh Processing](mesh_processing.md) | `subdivision`, `simplification`, `mesh_to_pcd_uniform`, `mesh_to_pcd_poisson_disk` | `.ply`, `.obj`, `.stl`, `.off` | `mesh.decimate()`; `mesh.to_points(num_points=...)` |
| [Voxelization & Volume](voxel_to_mesh.md) | `voxelization`, `binary_erosion` | `.ply`, `.obj`, `.stl`, `.off` |  |
| [Signed Distance Fields](sdf.md) | `compute_sdf`, `occupancy_reconstruction`, `sdf_voxel_visualization` | `.ply`, `.obj`, `.stl`, `.off` |  |
| [Surface Reconstruction](point_cloud_reconstruction.md) | `poisson`, `convex_hull`, `alpha_shape`, `ball_pivoting` | `.ply`, `.pcd`, `.txt`, `.xyz` | `points.to_mesh()` |
| [Point Cloud Registration](registration.md) | `ransac_global`, `icp_refinement`, `ransac_icp_pipeline` | `.ply`, `.pcd`, `.txt`, `.xyz` | `points.ransac(moving=...)`; `points.icp(moving=...)`; `target.align(moving)` on a `PointCloud` |
| [Deformable Registration](deformable_registration.md) | `cpd_deformable`, `gaussian_deformation` | `.ply`, `.pcd`, `.txt`, `.xyz` |  |
| [Point Cloud Segmentation](point_cloud_segmentation.md) | `ransac_plane`, `dbscan_clustering` | `.ply`, `.pcd`, `.txt`, `.xyz` | `points.segment(eps=..., min_points=...)` |
| [Stereo & Depth Estimation](stereo_3d_reconstruction.md) | `depth_colorization`, `depth_filter` | `.ply`, `.pcd`, `.txt`, `.xyz` |  |
| [LiDAR Scene Analysis](lidar_scene_detection.md) | `height_colorization`, `ground_removal`, `object_clustering` | `.ply`, `.pcd`, `.txt`, `.xyz`, `.las` |  |
| [LiDAR-Camera Fusion](lidar_camera_fusion.md) | `intensity_colorization`, `roi_extraction`, `multi_resolution` | `.ply`, `.pcd`, `.txt`, `.xyz`, `.las` |  |
| [Features Extraction](features_extraction.md) | `normal_estimation`, `fpfh_features`, `curvature_estimation` | `.ply`, `.pcd`, `.txt`, `.xyz` | `points.normals()` |
| [Collision Detection & Measurement](collision_detection.md) | `sdf_collision`, `penetration_depth` | `.ply`, `.obj`, `.stl`, `.off` |  |
| [PyVista Mesh Processing](pyvista_mesh_processing.md) | `pv_decimate`, `pv_subdivide`, `pv_smooth_laplacian`, `pv_smooth_taubin`, `pv_clean`, `pv_fill_holes`, `pv_compute_normals`, `pv_triangulate`, `pv_extract_surface` | `.ply`, `.obj`, `.stl`, `.vtk`, `.vtu` | `mesh.smooth()`; `mesh.clean()` |
| [PyVista Point Cloud Processing](pyvista_pointcloud_processing.md) | `pv_threshold`, `pv_clip_plane`, `pv_clip_box`, `pv_random_sample`, `pv_extract_points` | `.ply`, `.pcd`, `.vtk`, `.vtu`, `.obj`, `.stl` |  |
| [PyVista Volume Processing](pyvista_volume_processing.md) | `pv_contour`, `pv_slice`, `pv_slice_orthogonal`, `pv_threshold_volume`, `pv_extract_geometry`, `pv_extract_cells` | `.vti`, `.vtk`, `.vtu`, `.ply`, `.obj`, `.stl` |  |
| [PyVista Analysis](pyvista_analysis.md) | `pv_curvature`, `pv_distance`, `pv_glyph`, `pv_vector_magnitude`, `pv_scalar_stats`, `pv_extract_feature_edges` | `.ply`, `.obj`, `.stl`, `.vtk`, `.vtu` |  |
| [SimpleITK Registration](simpleitk_registration.md) | `rigid`, `advanced_rigid`, `affine`, `bspline`, `demons`, `difference_analysis` | `.vti`, `.mha`, `.nrrd`, `.nii`, `.dcm` | `fixed.align(moving)` on a `Volume` |
| [SimpleITK Segmentation](simpleitk_segmentation.md) | `otsu_threshold`, `manual_threshold`, `connected_components`, `watershed` | `.vti`, `.mha`, `.nrrd`, `.nii` | `volume.segment()`; `volume.segment(lower=..., upper=...)` |

## Models

Deep-learning models (PointNet, DINOv3 features, 3D JEPA, VAE anomaly detection, nnU-Net preparation) are documented under [Models](../models/index.md): reference scripts today, one-line pretrained access on the roadmap.
