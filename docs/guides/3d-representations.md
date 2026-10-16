---
title: "Point clouds, meshes, voxels and implicit fields: choosing a 3D representation"
description: "Expert guide to choosing and converting between the four 3D representations deep-learning pipelines run on - point clouds, meshes, voxel grids / SDFs and 3"
---

# Point clouds, meshes, voxels and implicit fields: choosing a 3D representation

# 3D representations for deep learning

> "Your choice of 3D data structure shapes everything downstream: memory, model
> architecture, and what is even possible." The representation is a modelling
> decision, not a file format. pardesline keeps one `Object` per kind
> (`PointCloud`, `Mesh`, `Volume`/`LabelMap`, splat as a `PointCloud` with
> attributes) and converts between them only where the conversion is well posed.

## The four, side by side

| | Point cloud | Mesh | Voxel grid / SDF | 3D Gaussian splat |
|---|---|---|---|---|
| Stores | unordered set {(x,y,z, attrs)} | vertices + faces (+ topology) | regular grid of occupancy / density / signed distance | set of anisotropic Gaussians: mean, covariance (scale + quaternion), opacity, SH colour |
| Invariance to exploit | permutation | permutation of vertex order, but faces fix connectivity | translation (convolution) | none built in; differentiable rendering is the supervision |
| Memory | O(N), ~6 floats/point (xyz + normal) | O(V + F), compact for surfaces | O(n^3): a 512^3 float32 CT is 512 MB, 1 mm^3 over a torso | ~59 floats/primitive (3 + 3 + 4 + 1 + 48 SH); 1-5 M primitives per scene |
| Architectures | PointNet / PointNet++ (set abstraction, FPS + ball query), DGCNN (edge conv on k-NN graph), Point Transformer v3, KPConv | MeshCNN (edge-based), GNNs on the vertex graph, spectral CNNs, DiffusionNet | 3D U-Net / nnU-Net, V-Net, MinkowskiNet and SpConv (sparse), octree CNNs (O-CNN), Swin-UNETR | 3DGS rasteriser (tile-based, depth-sorted alpha blending), gsplat, feature splatting |
| Strength | sparse, native output of LiDAR / depth / scanners, no topology to maintain | compact explicit surface, FEM-ready, exact normals and areas | dense fields (CT, MRI, PET), convolutions, implicit surfaces at any iso-level | photorealistic real-time novel views, differentiable w.r.t. images |
| Weakness | no surface, no neighbourhood structure without k-NN, density varies with distance | hard to learn topology changes; needs clean (manifold) input | cubic memory, aliasing of thin structures, resolution fixed | heavy, needs posed images, geometry is implicit in opacities |
| Where it is the native format | LiDAR (KITTI, nuScenes), robotics, photogrammetry, intra-oral and surface scanners, ultrasound reconstructions | CAD, graphics, biomechanics (heart / bone FEM), MedShapeNet, printed anatomy | CT, MRI, PET, micro-CT, DBT, occupancy grids | multi-view capture, endoscopy reconstruction (C3VD), KITTI-360 scene fits |

Rule of thumb: **learn on the representation your labels live in**, convert
only at the boundaries. Segmentation labels drawn on CT voxels train a voxel
network; tooth labels painted on an intra-oral mesh train a mesh or point
network; detection boxes from LiDAR train a point / pillar network.

## Memory and resolution arithmetic (do it before training)

- Voxel grids: `n^3 * bytes`. 256^3 float16 = 32 MB per channel; 3D U-Net
  activations at batch 2 with 32 base channels need ~10-16 GB. Patch-based
  training (128^3 or 96^3 crops, nnU-Net style) is the norm, never whole
  volumes. Isotropic resampling first: a 0.7 x 0.7 x 5 mm CT is *not* a cube.
- Point clouds: PointNet++ with 4 096 input points, ball-query radii 0.1 / 0.2 /
  0.4 in a unit sphere; a 3-M-point LiDAR chunk must be voxel-downsampled
  (`point_cloud_processing.voxel_downsample`) or tiled first. Normalise to the
  unit sphere per sample and **keep the scale factor** to map predictions back.
- Meshes: MeshCNN wants a fixed edge budget (e.g. 750-2 250 edges); decimate
  with `pyvista_mesh_processing.pv_decimate` (`target_reduction`) and keep it
  manifold (`pyvista_mesh_processing.pv_clean`). Faces are not a learnable
  quantity for most nets: they only define the graph.
- Splats: 1 M Gaussians ~ 240 MB on disk as float32 PLY; training needs the
  rasteriser's per-tile sort each step (GPU only).

## Conversion matrix and the pardesline call for each arrow

| From -> to | Nature | pardesline | Notes |
|---|---|---|---|
| mesh -> points | exact sampling | `Mesh.to_points(num_points=)` (`mesh_processing.mesh_to_pcd_poisson_disk`) | Poisson-disk gives even spacing; sample normals with the faces (`use_triangle_normal`) |
| label map -> mesh | exact (boundary of label k) | `LabelMap.to_mesh(label=k)` | marching cubes at 0.5 on the binary mask, direction cosines applied; result in LPS mm |
| grey volume -> mesh | parametric (iso-level) | `Volume.to_mesh(isovalue=v)` | choose v in the image units (HU for CT); never let code pick it |
| points -> mesh | lossy, parametric | `PointCloud.to_mesh()` (`point_cloud_reconstruction.poisson`, `depth`, `density_quantile`) or `point_cloud_reconstruction.ball_pivoting` | needs oriented normals; say "clean, density-trimmed surface", not watertight |
| mesh -> voxels / SDF | parametric | `voxel_to_mesh.voxelization` (`voxel_size`), `sdf.compute_sdf` (`voxel_size`, `level`) | voxel size sets the aliasing; SDF level 0 recovers the surface |
| points -> voxels | parametric | `voxel_to_mesh.voxelization` after a surface, or an occupancy grid by binning | binning loses sub-voxel detail; keep the spacing in the frame |
| volume -> points | parametric (spacing) | `LabelMap.to_mesh()` then `to_points()` | surface points only; for interior points, sample voxel centres with the affine |
| points -> splat | initialisation only | `gaussian-splatting` skill, [`scripts/points_to_gaussians.py`](https://github.com/pardesline/pardesline/blob/main/skills/3d-representations/scripts/points_to_gaussians.py) | needs posed images to optimise; without them it is a visualisation |
| splat -> points | exact (means) | read the PLY, keep x y z (and f_dc as colour) | opacities below ~0.1 are usually floaters |
| splat -> mesh | best effort | marching cubes on rendered depth / opacity fields (SuGaR, 2DGS) | research-grade; validate against a scan |

Each conversion in pardesline returns a new `Object` whose `provenance` keeps
the method and parameters: a reviewer can see that a surface came from
Poisson depth 9 with the 1 % lowest-density vertices removed.

## Pitfalls that break pipelines silently

1. **Frames and units.** DICOM/ITK volumes are LPS millimetres, NIfTI headers
   are RAS (ITK converts on load), glTF is Y-up metres, PLY/STL/OBJ carry
   nothing. A mesh from a CT (mm) overlaid on a LiDAR scan (m) is 1000x off.
   `obj.frame.describe()` says what is known; `with_frame()` declares, never
   guesses.
2. **Anisotropic voxels.** Networks assume cubic voxels; resample to isotropic
   spacing (nnU-Net uses the median spacing of the dataset, or a fixed
   1 x 1 x 1 mm) *before* cropping, and resample predictions back with
   nearest-neighbour for labels, linear for images.
3. **Label semantics.** A label map is integers with a meaning table
   (`LabelMap.labels`). Resampling labels with linear interpolation invents
   intermediate classes; one-hot then argmax, or nearest-neighbour only.
4. **Point density bias.** LiDAR density falls with distance; sampling 4 096
   points uniformly over-represents near points. Voxel-downsample to a fixed
   spacing, then farthest-point-sample.
5. **Mesh topology.** Poisson output has self-intersections where walls touch
   (nested heart chambers): reconstruct each structure separately.
6. **Orientation of normals.** Poisson and ball pivoting fail on inconsistently
   oriented normals; `features_extraction.normal_estimation` with `orient_k`
   makes them consistent.
7. **Coordinates of a converted mesh.** `LabelMap.to_mesh` applies spacing,
   origin and direction cosines; a hand-written marching cubes on
   `GetArrayFromImage()` (z, y, x order) does not. Compare bounding boxes.

## Choosing, by task (decision list)

- Organ / lesion segmentation on CT/MRI -> voxels (nnU-Net family), export
  surfaces afterwards with `LabelMap.to_mesh`.
- Tooth / bone part segmentation on scanner meshes -> points (PointNet++ /
  Point Transformer) sampled from the mesh with labels transferred per face,
  or a mesh network when the connectivity carries the signal.
- LiDAR detection -> points or pillars/voxels (PointPillars, CenterPoint),
  never meshes.
- Registration -> points for rigid (RANSAC + ICP), voxels for multimodal
  intensity-based (Mattes MI), meshes for statistical shape models.
- Shape statistics / biomechanics -> meshes with fixed correspondence.
- Novel-view synthesis, telemedicine viewers, endoscopy replay -> splats.
- Self-supervised pretraining on volumes (JEPA, MAE) -> voxel patches
  (3D ViT tokens of 16^3 or 8 x 16 x 16).

## Datasets to practise on (bundled)

`open3d_bunny` (mesh -> points -> Poisson -> SDF round trip), `msd_task02_heart`
(label map -> left-atrium surface), `totalsegmentator_ct` (117 organ masks ->
one mesh each), `kitti_raw_2011_09_26_drive_0001` (LiDAR points, sensor frame),
`c3vd_endoscopy_splats` (Gaussian splats + their centres), `medshapenet`
(106 101 anatomical STL meshes).

```python
import pardesline as pl

mask = pl.load("msd_task02_heart").filter(split="Tr")[0].mask  # LabelMap, LPS mm
surface = mask.to_mesh(label=1)  # exact boundary
points = surface.to_points(num_points=4096)  # for a point network
sdf = surface.run("sdf.compute_sdf", voxel_size=1.0)  # implicit field + marching cubes
surface.provenance[-1]["exact"], points.frame.describe()  # True, "LPS, mm (file)"
```

See `references/conversion-matrix.md` for the formulas behind each arrow.

<sub>Source: `skills/3d-representations/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-16.</sub>
