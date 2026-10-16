---
title: "POPI-model: 4D-CT of one thorax, six breathing phases"
description: "Point-validated Pixel-based Breathing Thorax Model (Leon Berard Cancer Center / CREATIS, Lyon)"
---

# POPI-model: 4D-CT of one thorax, six breathing phases

`pl.load("popi_lung_4dct")` loads this dataset. Point-validated Pixel-based Breathing Thorax Model (Leon Berard Cancer Center / CREATIS, Lyon). Six phases of one respiratory cycle; the phase 00 mask separates air, body and lungs. The reference deformable-registration exercise.

```python
import pardesline as pl

ds = pl.load("popi_lung_4dct")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/popi_lung_4dct
```

## Provenance and licence

| | |
|---|---|
| Source | direct HTTPS downloads with checksums: `POPI/meta/00-P.mhd`, `POPI/meta/10-P.mhd`, `POPI/meta/20-P.mhd`, `POPI/meta/30-P.mhd`, `POPI/meta/40-P.mhd`, `POPI/meta/50-P.mhd` |
| Scheme | `https` |
| Size of the whole source | 500 MB |
| Licence | not a standard licence: see the note |
| Redistribution | unknown |
| Licence note | Free for research with citation of the POPI-model paper. Terms of use TO CONFIRM with the data owner before any redistribution. |
| Terms | <https://www.creatis.insa-lyon.fr/rio/popi-model> |
| Homepage | <https://www.creatis.insa-lyon.fr/rio/popi-model> |
| Cite | Vandemeulebroucke J., Sarrut D., Clarysse P. The POPI-model, a point-validated pixel-based breathing thorax model. ICCR 2007. |
| Samples grouped by | phase |
| Samples listed in the manifest | 6 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `POPI/meta/00-P.mhd, POPI/meta/10-P.mhd, POPI/meta/20-P.mhd`<br>Thorax CT at one breathing phase (MetaImage .mhd + .raw) |
| `mask` | labels | from the file header | from the file header | 1=body, 2=lungs | `POPI/masks/00-air-body-lungs.mhd`<br>Air / body / lungs label map for phase 00 (value meaning inferred from the file name) |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("popi_lung_4dct").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `lung`, `ct`, `4d`, `deformable`, `registration`, `segmentation`

<sub>Generated from `src/pardesline/data/manifests/popi_lung_4dct.json` on 2026-10-16.</sub>
