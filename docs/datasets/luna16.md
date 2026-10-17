---
title: "LUNA16: 888 thoracic CTs (LIDC-IDRI subset) for lung nodule detection"
description: "The LUNA16 challenge scans: 888 CTs from LIDC-IDRI with slice thickness <= 2.5 mm, as MetaImage (.mhd + .raw), in ten subsets for cross-validation"
---

# LUNA16: 888 thoracic CTs (LIDC-IDRI subset) for lung nodule detection

`pl.load("luna16")` loads this dataset. The LUNA16 challenge scans: 888 CTs from LIDC-IDRI with slice thickness <= 2.5 mm, as MetaImage (.mhd + .raw), in ten subsets for cross-validation. Each subset is a 6-7 GB zip on Zenodo read scan by scan with HTTP Range (the .raw sibling is fetched with its header). Nodule annotations (annotations.csv, candidates.csv) are separate files on the Zenodo record.

```python
import pardesline as pl

ds = pl.load("luna16")
print(ds.describe())  # roles, frames, units, labels, licence, citation
s = ds[0]
obj = s.ct  # fetched now, cached under ~/.cache/pardesline/datasets/luna16
```

## Provenance and licence

| | |
|---|---|
| Source | remote archive read by HTTP Range: `https://zenodo.org/records/3723295/files/subset0.zip`, `https://zenodo.org/records/3723295/files/subset1.zip`, `https://zenodo.org/records/3723295/files/subset2.zip`, `https://zenodo.org/records/3723295/files/subset3.zip`, `https://zenodo.org/records/3723295/files/subset4.zip`, `https://zenodo.org/records/3723295/files/subset5.zip`, `https://zenodo.org/records/3723295/files/subset6.zip`, `https://zenodo.org/records/4121926/files/subset7.zip`, `https://zenodo.org/records/4121926/files/subset8.zip`, `https://zenodo.org/records/4121926/files/subset9.zip` |
| Scheme | `archive` |
| Size of the whole source | 64.8 GB |
| Licence | CC-BY-4.0 |
| Commercial use | allowed by the licence |
| Redistribution | allowed |
| Licence note | CC BY 4.0 on the Zenodo records (checked 2026-10-14); the underlying LIDC-IDRI collection is CC BY 3.0 (TCIA). |
| Terms | <https://zenodo.org/records/3723295> |
| Homepage | <https://luna16.grand-challenge.org/> |
| Cite | Setio A.A.A., Traverso A., de Bel T., et al. Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in computed tomography images: the LUNA16 challenge. Med Image Anal 42:1-13, 2017. |
| Samples grouped by | subset |

## Roles (what each sample contains)

| Role | Type | Frame | Units | Labels / layout | Pattern or file |
|---|---|---|---|---|---|
| `ct` | volume (CT) | from the file header | from the file header |  | `subset{subset}/{id}.mhd`<br>Thorax CT (MetaImage header + raw; LPS mm from the header); field subset = fold 0..9 |

## Standardized layout

Files are fetched on first access into the dataset cache and stay in their original format; `ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above.

```python
ds = pl.load("luna16").take(2)
ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json
```

## Algorithms and models that run on it

- **volume** roles: `volume.align(moving)`, `volume.segment(lower, upper)`, `volume.to_mesh(isovalue=...)`, `volume.to_sitk()` ; catalog modules: [`pyvista_volume_processing`](../algorithms/pyvista_volume_processing.md), [`simpleitk_registration`](../algorithms/simpleitk_registration.md), [`simpleitk_segmentation`](../algorithms/simpleitk_segmentation.md)
- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly.

## Related

- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)
- Tags: `medical`, `ct`, `lung`, `nodules`, `detection`, `metaimage`, `lidc`

<sub>Generated from `src/pardesline/data/manifests/luna16.json` on 2026-10-17.</sub>
