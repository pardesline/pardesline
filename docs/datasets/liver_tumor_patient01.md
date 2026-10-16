---
title: "Liver tumour CT with three radiologists segmentations"
description: "One abdominal CT and three independent manual segmentations of the tumour, from the SimpleITK segmentation-evaluation notebook"
---

# Liver tumour CT with three radiologists segmentations

`pl.load("liver_tumor_patient01")` loads this dataset. One abdominal CT and three independent manual segmentations of the tumour, from the SimpleITK segmentation-evaluation notebook. The inter-observer agreement exercise (Dice, Hausdorff).

```python
import pardesline as pl

ds = pl.load("liver_tumor_patient01")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/liver_tumor_patient01
```

## Provenance and licence

| | |
|---|---|
| Source | direct HTTPS downloads with checksums: `liverTumorSegmentations/Patient01Homo.mha`, `liverTumorSegmentations/Patient01Homo_Rad01.mha`, `liverTumorSegmentations/Patient01Homo_Rad02.mha`, `liverTumorSegmentations/Patient01Homo_Rad03.mha` |
| Scheme | `https` |
| Size of the whole source | 2 MB |
| Licence | not a standard licence: see the note |
| Redistribution | unknown |
| Licence note | Distributed with the SimpleITK notebooks (Apache-2.0 code; data terms not stated). Terms of use TO CONFIRM with the data owner before any redistribution. |
| Terms | <https://github.com/InsightSoftwareConsortium/SimpleITK-Notebooks> |
| Cite | SimpleITK Notebooks, Insight Software Consortium. |
| Samples grouped by | patient |
| Samples listed in the manifest | 1 |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `liverTumorSegmentations/Patient01Homo.mha`<br>Abdominal CT (8-bit, windowed) |
| `rad01` | labels | from the file header | from the file header | 1=tumor | `liverTumorSegmentations/Patient01Homo_Rad01.mha`<br>Tumour segmentation by radiologist 1 |
| `rad02` | labels | from the file header | from the file header | 1=tumor | `liverTumorSegmentations/Patient01Homo_Rad02.mha`<br>Tumour segmentation by radiologist 2 |
| `rad03` | labels | from the file header | from the file header | 1=tumor | `liverTumorSegmentations/Patient01Homo_Rad03.mha`<br>Tumour segmentation by radiologist 3 |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("liver_tumor_patient01").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **labels** roles: `mask.to_mesh(label=k)`, `mask.to_numpy()`, metrics: `dice`, `hd95` (evaluation-metrics-3d) ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces.
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `liver`, `ct`, `segmentation`, `inter-observer`

<sub>Generated from `src/pardesline/data/manifests/liver_tumor_patient01.json` on 2026-10-16.</sub>
