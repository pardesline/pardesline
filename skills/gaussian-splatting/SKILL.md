---
name: gaussian-splatting
description: >-
  Expert guide to 3D Gaussian Splatting for engineers coming from point clouds and
  medical 3D: what a Gaussian primitive stores (mean, scale, quaternion, opacity,
  spherical-harmonic colour, ~59 floats), the per-point initialisation from a cloud
  (k-NN scale, identity rotation, logit opacity, SH degree-0 colour, Sigma = R S S^T R^T),
  the standard PLY field layout (x y z, nx ny nz, f_dc_*, f_rest_*, opacity, scale_*,
  rot_*), the tile-based differentiable rasteriser, the training loop (L1 + D-SSIM,
  densify / prune / reset), evaluation (PSNR, SSIM, LPIPS on held-out views), memory
  and real-time trade-offs versus NeRF and meshes, medical and endoscopy uses (C3VD,
  surgical scene replay), conversions to and from points and meshes, and the pardesline
  datasets and script that write a splat PLY from any cloud. Use when converting
  points to splats, reading or writing 3DGS files, planning a splat reconstruction,
  or deciding splats versus meshes.
---

# 3D Gaussian Splatting

## What a primitive is

A scene is a set of N anisotropic 3D Gaussians `G_i(x) = exp(-1/2 (x - mu_i)^T
Sigma_i^-1 (x - mu_i))`, each with

| Attribute | Parameters | Stored as |
|---|---|---|
| position `mu` | 3 | `x y z` |
| covariance `Sigma = R S S^T R^T` | 3 log-scales + 4 quaternion | `scale_0..2` (log), `rot_0..3` (w x y z, unnormalised) |
| opacity `alpha = sigmoid(o)` | 1 | `opacity` (logit) |
| colour, spherical harmonics degree 3 | 3 + 45 | `f_dc_0..2`, `f_rest_0..44` |

59 floats, versus 6 for a point with a normal. The factorisation
`R S S^T R^T` keeps `Sigma` positive semi-definite under gradient descent:
`R` comes from a normalised quaternion and `S` from exponentiated scales.

## Point cloud -> splats: the five-step initialisation

1. `mu_i = p_i` (keep the cloud's frame and units; splats have no unit
   either).
2. `s_i = log(mean distance to the k = 3 nearest neighbours)` on all three
   axes: dense regions get small Gaussians, sparse ones large; an isotropic
   start that the optimiser can stretch.
3. `q_i = (1, 0, 0, 0)` identity rotation.
4. `o_i = logit(0.1)` so every primitive starts faint and the optimiser can
   raise the useful ones.
5. `f_dc = (rgb - 0.5) / C_0`, `C_0 = 0.28209479` (the degree-0 SH basis
   constant); `f_rest = 0` (view-independent start).

`scripts/points_to_gaussians.py` does exactly this with NumPy and writes the
PLY that gsplat, the reference implementation and web viewers read. Without
images to optimise against the result is a *visualisation* of the cloud (it
fills gaps and renders fast); with posed images it is the standard
initialisation (the original method starts from a COLMAP SfM cloud).

## Rendering (why it is real time)

Project each Gaussian to the image plane with the camera Jacobian `J`:
`Sigma' = J W Sigma W^T J^T` (a 2D Gaussian). Tile the screen (16 x 16),
sort the Gaussians touching each tile by depth (one radix sort per frame),
then alpha-blend front to back: `C = sum_i c_i alpha_i prod_{j<i} (1 -
alpha_j)`. Every step is differentiable w.r.t. all attributes, so the
photometric loss trains geometry and appearance together. 30+ fps at 1080p
on a consumer GPU for 1-3 M primitives; NeRF needs seconds per frame.

## Training (the reference recipe, Kerbl et al. 2023)

- Loss: `(1 - lambda) L1 + lambda (1 - SSIM)`, `lambda = 0.2`.
- Adam with per-attribute learning rates: position 1.6e-4 (scaled by scene
  extent, decayed to 1.6e-6), SH 2.5e-3 (f_rest at 1/20), opacity 0.05, scale
  5e-3, rotation 1e-3.
- Adaptive density control every 100 iterations from 500 to 15 000: **clone**
  small Gaussians with large positional gradient (> 2e-4) in under-reconstructed
  areas, **split** large ones (scale > 1 % of extent) in over-reconstructed
  areas, **prune** opacity < 0.005 and oversized Gaussians; **reset** opacities
  every 3 000 iterations to kill floaters.
- 30 000 iterations; SH degree raised by one every 1 000 iterations.
- Evaluate on held-out views: PSNR (> 25 dB good indoors), SSIM, LPIPS (lower
  is better). Report memory (primitives, MB) and fps.

Libraries: `gsplat` (Nerfstudio, CUDA, pip), the original
`graphdeco-inria/gaussian-splatting`, `nerfstudio` (`splatfacto`), web
viewers (antimatter15/splat, gsplat.js on the Hub). Variants: 2DGS (surfels,
better geometry), SuGaR (mesh extraction), Mip-Splatting (aliasing), 4DGS /
Deformable-GS (dynamic scenes, surgery).

## Medical and endoscopy

- Endoscopy / laparoscopy: EndoGaussian, EndoGSLAM, PR-ENDO on EndoNeRF, SCARED
  and C3VD. Tissue deforms: dynamic variants add a deformation field
  `mu_i(t)`; depth supervision (stereo or monocular prior) stabilises the
  geometry where texture is poor.
- CT/MRI are **volumes, not photographs**: splats are not a segmentation or
  a volume representation; use them for rendering a surface extracted from a
  volume (initialise from `LabelMap.to_mesh().to_points()`), for surgical
  video replay, or for digital twins of a room/instrument.
- Telemedicine viewers: a splat of a dental arch or a wound renders on a
  phone; a mesh with textures is usually enough and lighter to validate.

## Reading, writing, converting

- A splat PLY is a vertex-only PLY with the fields above; `pl.load` opens it
  as a `PointCloud` (the means), Open3D keeps `x y z` and ignores the rest.
  `c3vd_endoscopy_splats` ships ten such files (`splat` role) and their means
  (`points` role); `hf_3d_arena` has the SAM-3D-Objects-3DGS outputs; the
  KITTI-360 subset stores the attributes as separate `.npy` arrays
  (`hf_kitti360_gs_subset`, roles `gaussian_centers`, `gaussian_scale`, ...).
- Splat -> points: keep means with `sigmoid(opacity) > 0.1`.
- Splat -> mesh: SuGaR / 2DGS extract a surface; validate against a scan or a
  label-map mesh (`evaluation-metrics-3d`).
- Other formats: `.splat` (antimatter15: 32 bytes per Gaussian, SH degree 0),
  `.spz` (Niantic, compressed), glTF `KHR_gaussian_splatting` (draft).

```python
import pardesline as pl

cloud = pl.load("open3d_bunny")[0].mesh.to_points(num_points=50000)
# scripts/points_to_gaussians.py cloud.path out.ply --colour 0.8 0.7 0.6
```

## Trade-offs to state

Splats buy photorealism and speed with memory (10-50x a mesh of the same
surface), a per-frame sort, no explicit surface (normals, areas and volumes
need extraction), and a dependence on good camera poses. For measurement,
simulation or printing, convert to a mesh and validate it.
