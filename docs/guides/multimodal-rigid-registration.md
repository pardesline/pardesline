---
title: "Rigid CT / MR registration with SimpleITK"
description: "Expert guide to intensity-based rigid and affine registration of CT, MRI, PET and CBCT volumes with SimpleITK (and pardesline's simpleitk_registration modu"
---

# Rigid CT / MR registration with SimpleITK

**Reference scripts:** [`rigid_ct_mr.py`](https://github.com/pardesline/pardesline/blob/main/skills/multimodal-rigid-registration/scripts/rigid_ct_mr.py).

# Multimodal rigid registration with SimpleITK

## The problem in one line

Find the rigid transform `T` (3 rotations + 3 translations, `Euler3DTransform`)
such that the moving image resampled through `T` lines up with the fixed
image, when the two modalities do not share intensities: bone is bright in CT
(+1000 HU) and dark in T1 MRI, CSF is dark in CT and bright in T2. Mean
squares or correlation assume a linear intensity relation and fail; **mutual
information** only assumes a statistical dependence between the two
intensity distributions.

## The stack, component by component

| Component | Setting | Why |
|---|---|---|
| Transform | `Euler3DTransform` initialised with `CenteredTransformInitializer` | 6 DoF; the rotation centre at the fixed image centre (GEOMETRY) or the intensity centre of mass (MOMENTS) so rotations do not sweep the volume out of view |
| Metric | `MattesMutualInformation`, 50 bins | Parzen-window joint histogram; 32-64 bins is the sweet spot (fewer = smooth but blurry, more = noisy) |
| Sampling | RANDOM, 1-15 % of voxels, fixed seed | MI on all voxels is slow and over-fits noise; random sampling adds stochasticity that helps escape local minima |
| Optimizer | `RegularStepGradientDescent` or `GradientDescent` (lr 1.0 then 0.2), `SetOptimizerScalesFromPhysicalShift` | rotations (rad) and translations (mm) have different sensitivities: physical-shift scales equalise them |
| Multi-resolution | shrink 4,2,1 with smoothing sigmas 2,1,0 mm | capture-range at coarse levels, precision at fine; sigmas in physical units so anisotropic voxels are handled |
| Interpolator | linear during optimisation, linear for the final image, nearest for labels, B-spline for the final image when quality matters | |
| Convergence | minimum value 1e-6 over a 10-iteration window, 100-500 iterations | watch the metric curve: a plateau in the first 20 iterations means the capture range was missed |

In pardesline every one of these is a parameter of `simpleitk_registration.rigid`:

```python
import pardesline as pl

ds = pl.load("rire_brain")  # CT + MR-T1 of one brain, LPS mm
s = ds[0]
moved = s.ct.align(
    s.mr_t1,  # fixed = CT, moving = MR
    metric="mattes_mutual_information",
    number_of_histogram_bins=50,
    initializer="GEOMETRY",
    sampling_strategy="RANDOM",
    sampling_percentage=0.05,
    learning_rate=1.0,
    num_iterations=200,
    shrink_factors="4,2,1",
    smoothing_sigmas="2,1,0",
    smoothing_sigmas_in_physical_units=True,
    optimizer_scales_from_physical_shift=True,
    interpolator="LINEAR",
)
moved.transform  # rotation_deg, translation_mm, matrix_4x4, final metric
```

`simpleitk_registration.advanced_rigid` adds an **exhaustive rotation search**
(`exhaustive_steps_per_axis`, phase 1) before gradient descent: use it when
the initial misalignment exceeds ~30 deg or when the two scans were acquired
in different patient positions. `simpleitk_registration.affine` adds scale
and shear (12 DoF) for scanner calibration differences; `bspline` and `demons`
are deformable (see the bottom of this page).

## Frames: the part that breaks silently

- DICOM and every ITK reader give **LPS millimetres** with origin, spacing and
  direction cosines; NIfTI headers are RAS and ITK converts them on read.
  pardesline's `Volume.frame` carries the affine; the registration operates
  in physical space, so two volumes with different spacing and orientation
  register without resampling first.
- Never register voxel arrays (`GetArrayFromImage`) directly: you would lose
  the geometry and the transform would be meaningless in the scanner frame.
- The output transform maps **fixed physical points to moving physical
  points** (ITK convention). To move an annotation from fixed to moving, apply
  `T`; to bring the moving image onto the fixed grid, `Resample(moving, fixed,
  T)`. Label maps: nearest-neighbour interpolation, `defaultPixelValue=0`.
- Composite registrations (rigid then B-spline): `CompositeTransform`, applied
  inner-to-outer; keep each stage's transform file (`.tfm`).

## Diagnostics and validation

1. Plot the metric per iteration (SimpleITK `AddCommand(sitkIterationEvent)`),
   check it decreases at each level and the level changes are visible.
2. Checkerboard and colour overlay of fixed vs resampled moving
   (`simpleitk_registration.difference_analysis` gives a difference map).
3. **Target registration error** on 5-10 anatomical landmarks placed
   independently in both volumes (not used by the algorithm): `||T(p_fixed) -
   p_moving||` in mm; sub-voxel on rigid brain CT/MR (RIRE reports ~1 mm).
4. Dice of propagated masks when segmentations exist (skull, ventricles).
5. Run twice with different random seeds / sampling: a stable result moves by
   less than the voxel size; otherwise increase sampling or bins.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Metric flat, no motion | capture range missed, initial misalignment too large | MOMENTS initializer, `advanced_rigid` exhaustive search, coarser first level (shrink 8) |
| Converges to a wrong but plausible pose | local minimum of MI (symmetric head, repeated vertebrae) | multi-start, more bins, larger sampling, mask the field of view to the common anatomy |
| Drifts with iterations | learning rate too high | 0.2-0.5 with physical-shift scales; RegularStepGradientDescent with relaxation |
| Good at centre, bad at edges | not rigid: scanner distortion, patient deformation | affine then B-spline (`grid_spacing` 30-50 mm) |
| PET-CT off by a slice | different acquisition times / breathing | rigid on the torso mask only, then deformable |
| Works on brain, fails on abdomen | organs move independently | mask the organ of interest; deformable (`demons` for same-modality, B-spline MI for multimodal) |

## Going deformable

- `simpleitk_registration.bspline`: B-spline FFD on a control-point grid
  (`grid_spacing` mm, multi-resolution `scale_factors`), LBFGSB, MI for
  multimodal. Validate with the Jacobian determinant (no folding) and TRE.
- `simpleitk_registration.demons`: diffeomorphic demons on **same-modality**
  images (intensities must match), `standard_deviations` smooth the update
  field; fast, dense, not for CT-MR.
- Always rigid (or affine) first; deformable models should correct millimetres,
  not centimetres.

## Datasets to practise on

`rire_brain` (CT + MR-T1, the reference multimodal pair), `popi_lung_4dct`
(same-modality breathing phases: rigid then B-spline/demons), `ixi_brain_mri`
(T1 vs T2 vs PD of the same subject), `chaos_abdomen` (CT and MR of different
patients: atlas-style registration), `tcia_nsclc_radiomics_dicom` (DICOM
series as input), `hf_openmind` (T1 vs T2).

[`scripts/rigid_ct_mr.py`](https://github.com/pardesline/pardesline/blob/main/skills/multimodal-rigid-registration/scripts/rigid_ct_mr.py) registers the RIRE pair through pardesline, repeats
the registration directly with SimpleITK to expose every setting, exports the
checkerboard, and reports the metric trace and the transform.

<sub>Source: `skills/multimodal-rigid-registration/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-16.</sub>
