---
title: How to register CT and MRI of the same patient in Python
description: Rigid CT to MRI registration in Python with SimpleITK through one call: mutual information, multi-resolution, physical-shift optimizer scales; the transform in degrees and millimetres, the resampled volume, a checkerboard check, and what to do when it fails.
---

# How to register CT and MRI of the same patient in Python

Mean squares fails across modalities (bone is bright in CT and dark in T1); mutual information does not assume an intensity relation. The call below runs SimpleITK's rigid registration with Mattes MI, three resolution levels and optimizer scales from physical shift, which is what makes one learning rate work on any pair.

```python
import pardesline as pl

s = pl.load("rire_brain")[0]  # CT 0.65x0.65x4 mm, MR T1 1.25x1.25x4 mm, 19 MB
moved = s.ct.align(s.mr_t1)  # fixed = CT, moving = MR; 8.8 s on a laptop
t = moved.transform["sub_transforms"][0]
print(t["rotation_deg"], t["translation_mm"])  # [0.34, -0.35, -4.38] [16.2, -33.1, -21.6]
moved.save("mr_on_ct.nii.gz")  # the MR resampled on the CT grid + sidecar
```

Your own volumes: `pl.load("ct.nii.gz").align(pl.load("mr.nii.gz"))`, or a DICOM folder for either. The registration runs in physical space (origin, spacing, direction from the headers), so different spacings and fields of view need no resampling first.

## Check it

```python
import pyvista as pv

ct, mr = s.ct.to_pyvista(), moved.to_pyvista()
p = pv.Plotter()
p.add_mesh(ct.slice("z"), cmap="gray")
p.add_mesh(mr.slice("z"), cmap="magma", opacity=0.5)
p.show()
```

Or `s.ct.run("simpleitk_registration.difference_analysis", moving=moved)` for a difference map. The clinical check is a target registration error on landmarks placed in both volumes and not used by the algorithm; RIRE reports about 1 mm for rigid brain CT/MR.

## When it fails

| Symptom | Cause | Do |
|---|---|---|
| metric flat from the first iterations | the initial offset is outside the capture range (above ~30° or different patient position) | `s.ct.run("simpleitk_registration.advanced_rigid", moving=s.mr_t1)`: exhaustive rotation search first |
| converges, visibly wrong | wrong centre initialisation when one field of view is much larger | `initializer="MOMENTS"` |
| noisy metric, jittery result | too few samples on a small field of view | `sampling_percentage=0.05` to `0.15` |
| same modality follow-up | MI is overkill | `metric="mean_squares"`, faster |
| scanner scale or shear | not rigid | `simpleitk_registration.affine`; deformation: `bspline`, `demons` |

`print(pl.describe("simpleitk_registration.rigid"))` lists the fourteen parameters, their ranges and the reason for each default.

Related: [Guide: multimodal rigid registration](../guides/multimodal-rigid-registration.md) (a hand-written SimpleITK stack next to the one-liner, metric traced per iteration) · [RIRE dataset](../datasets/rire_brain.md) · [Why our defaults work](../algorithms/why-our-defaults-work.md#rigid-registration-of-volumes-simpleitk_registration)
