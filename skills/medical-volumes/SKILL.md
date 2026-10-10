---
name: medical-volumes
description: >-
  Medical volumes with pardesline on the user's machine (needs the [medical] extra):
  load NIfTI / NRRD / MHA / MHD / VTI / DICOM folders as `Volume` with LPS mm frames,
  rigid / advanced_rigid / affine / bspline / demons registration and the
  difference_analysis QC (two inputs, GEOMETRY init, transform JSON sidecar),
  threshold / Otsu / watershed / connected-components segmentation to a `LabelMap`,
  exact label-to-surface extraction in world coordinates, the `pardesline.medical`
  function library (SimpleITK service: load_volume, load_dicom, register_*,
  threshold_*, resample, apply_transform, transform_to_dict), the (z,y,x) numpy
  convention and the VTI / .mha gotchas. Use for CT, MR, DICOM, "register these
  scans", "segment this volume", "check the deformation", "export a surface".
---

# Medical volumes

Requires `pip install "pardesline[medical]"` (SimpleITK + PyVista). `.vti`
outputs are written by every SimpleITK op and read back through the PyVista
adapter; a sibling `.mha` next to a `.vti` is preferred when present (3x faster).

## Load

```python
ct = pl.load("ct.nii.gz")  # Volume; frame "LPS, mm (file)", affine from the header
ct = pl.load("/data/p01/dicom")  # a DICOM folder (one series) is a Volume too
ct.info()  # size (x,y,z), spacing, origin, direction, pixel_type, components, affine
img = ct.to_sitk()  # SimpleITK.Image
arr = ct.to_numpy()  # (z, y, x) - SimpleITK convention
```

SimpleITK loads every format into LPS millimetres (NIfTI RAS is converted),
which is why the package states LPS/mm for these files. Index to world is
`world = direction * spacing * index + origin` (`ct.frame.affine`).

## Registration (two inputs: `input` fixed, `moving` moving)

```python
moved = ct.align(mr)  # rigid, GEOMETRY initialisation (centres aligned)
moved = ct.run(
    "simpleitk_registration.affine", moving=mr, num_iterations=300, metric="mattes_mutual_information"
)
moved = ct.run("simpleitk_registration.bspline", moving=moved, grid_spacing=50.0)
moved = ct.run(
    "simpleitk_registration.advanced_rigid", moving=mr
)  # exhaustive rotation search first: slow, handles large rotations
diff = ct.run(
    "simpleitk_registration.difference_analysis", moving=moved
)  # difference volume + statistics in the sidecar
moved.transform  # {"rotation_deg": [...], "translation_mm": [...], "matrix_3x3": ...} from <output>.json
moved.registration_sidecar  # the whole JSON (metric values, iterations ...)
```

Shared registration parameters (print with `pl.describe("simpleitk_registration.rigid")`):
`num_iterations`, `learning_rate`, `sampling_percentage`, `metric`
(`mattes_mutual_information` | `mean_squares` | `correlation` |
`joint_histogram_mi`), `initializer` (`GEOMETRY` | `MOMENTS`),
`sampling_strategy`, `interpolator`, `shrink_factors="4,2,1"`,
`smoothing_sigmas="2,1,0"`, `number_of_histogram_bins`. Use GEOMETRY (aligns
image centres); MOMENTS (mass centres) can fail on partial fields of view.
Mutual information for multimodal pairs (CT/MR), mean squares for same
modality. Deformable: `bspline(grid_spacing)`, `demons(num_iterations,
standard_deviations)`. Rigid first, then affine, then B-spline.

Passing `moving` is mandatory; the scripts' self-alignment demo mode is not
reachable through the package.

## Segmentation

```python
mask = ct.segment()  # Otsu -> LabelMap {1: "foreground"}
mask = ct.segment(lower=200, upper=600)  # manual_threshold in intensity units (HU for CT)
mask = mask.run("simpleitk_segmentation.connected_components", min_size=500)  # keep components >= 500 voxels
ws = mask.run("simpleitk_segmentation.watershed", seed_radius=10.0)
mask = mask.with_labels({1: "bone"})  # name the label
```

`Volume.segment` always returns a `LabelMap`. Other outputs are Volumes:
declare them with `as_labels({...})` when they are label maps.

## Label map to surface (exact, world coordinates)

```python
bone = mask.to_mesh(label=1)  # .ply, LPS mm; provenance step op="volume_to_mesh", exact=True
bone = bone.decimate(target_reduction=0.8).smooth(n_iterations=20)
bone.save("bone.stl")  # sidecar keeps frame LPS/mm, licence, every step
```

Marching cubes at 0.5 on the binary `voxel == label`, through PyVista with
the direction matrix applied, triangulated, no attributes. For a grey-level
isosurface use `ct.to_mesh(isovalue=300)`. Vertices are in the volume's
physical frame, so a surface and its volume overlay directly.

## The function library (`from pardesline import medical`)

I/O: `load_volume(path)` (MHA/NRRD/NIfTI/VTI...), `load_dicom(folder)`
(largest series, size-grouping fallback), `save_volume`, `volume_to_vti`,
`volume_metadata`, `numpy_to_volume(array, reference)`, `volume_to_binary`.
Transforms: `save_transform`, `load_transform`, `transform_to_dict`
(composite transforms cannot be saved as .tfm; the JSON dict is the
portable form), `apply_transform(volume, transform, reference)`,
`get_initial_transform(fixed, moving, mode)`.
Registration: `register_rigid`, `register_rigid_advanced`, `register_affine`,
`register_bspline`, `register_demons`, `compute_difference_image`,
`compute_difference_thresholded`.
Segmentation: `threshold_otsu`, `threshold_manual`, `segment_region_growing`,
`segment_watershed`, `connected_components`, `resample`, `smooth_gaussian`.

These are the exact functions the hosted registration studio runs.

## Gotchas

- `sitk.ReadImage` cannot open `.vti`; use `medical.load_volume` (or
  `obj.to_sitk()`), which routes VTK grids through PyVista.
- Arrays are `(z, y, x)`; `img.GetSize()` is `(x, y, z)`.
- A DICOM folder given to an op is materialised once as `.mha` in
  `pl.output_dir()`.
- Datasets: `rire_brain` (CT/MR pair), `popi_lung_4dct` (6 phases + mask),
  `liver_tumor_patient01` (CT + 3 observer masks), `visible_human_head_mri`.
