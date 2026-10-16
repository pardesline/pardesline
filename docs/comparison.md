---
title: pardesline vs Open3D, PyVista, SimpleITK, trimesh, MONAI, TorchIO and Hugging Face datasets
description: Where pardesline sits next to the 3D and medical imaging libraries it builds on: dataset access, standardization, manifests, high-level API, data-tied defaults, pretrained models, MCP. Facts with sources, not marketing.
---

# Comparison with other libraries

pardesline is the dataset layer and the domain-vocabulary API **on top of** these libraries. It imports Open3D, PyVista, VTK and SimpleITK, runs their algorithms, and hands you their objects (`to_open3d()`, `to_pyvista()`, `to_sitk()`). Nothing here is a criticism of them: without them there would be nothing to wrap. Each cell links to the documentation it was checked against (October 2026); corrections are welcome as issues.

## Datasets

| | pardesline | Open3D | PyVista | SimpleITK | trimesh | MONAI | TorchIO | HF `datasets` |
|---|---|---|---|---|---|---|---|---|
| Public 3D / medical datasets loadable by name | 43 manifests: MSD, AMOS, TotalSegmentator, LUNA16, IXI, VerSe, SPIDER, CHAOS, TCIA collections, OpenNeuro, KiTS, MedShapeNet, KITTI, Objaverse, 3D Arena, UniOcc, C3VD | demo data (`open3d.data`: bunny, armadillo, fragments) [[doc]](https://www.open3d.org/docs/release/python_api/open3d.data.html) | example datasets (`pyvista.examples.download_*`) [[doc]](https://docs.pyvista.org/api/examples/_autosummary/pyvista.examples.downloads) | notebook data fetcher (`fetch_data`) [[doc]](https://insightsoftwareconsortium.github.io/SimpleITK-Notebooks/) | no | `DecathlonDataset`, `TciaDataset`, `MedNISTDataset` [[doc]](https://docs.monai.io/en/stable/apps.html) | IXI, EPISURG, RSNA-MICCAI and others [[doc]](https://torchio.readthedocs.io/datasets.html) | any Hub repo; files are returned untyped [[doc]](https://huggingface.co/docs/datasets) |
| Any Hugging Face repo, TCIA collection, S3 bucket, remote archive by URI | `hf://`, `tcia://`, `s3://`, `https://…zip` | no | no | no | no | TCIA through its own client | no | Hub only |
| Lazy download inside archives (HTTP Range) | yes (zip, zip64, tar) | n/a | no | no | no | no | no | no |
| Licence, citation and provenance attached to each object | yes | no | no | no | no | no | no | licence field on the card |
| Manifest describing roles, frames, units, labels, layouts | yes, JSON, drafted by `scan` for your folders | no | no | no | no | MSD `dataset.json` read | no | dataset card |
| Patient-level splits | `ds.split(by="patient")` | no | no | no | no | user code | user code | user code |

## Objects and standardization

| | pardesline | Open3D | PyVista | SimpleITK | trimesh | MONAI | TorchIO | HF `datasets` |
|---|---|---|---|---|---|---|---|---|
| Point clouds, meshes and volumes in one object model | yes, plus label maps, splats, raw arrays, images | points, meshes, voxel grids | meshes, grids, volumes | volumes | meshes | volumes (tensors) | volumes | no |
| Frame, units, labels carried with the data | yes (sidecar on save) | no | no | geometry in the image | units attribute | metadata dict | metadata | no |
| Standardization transforms (spacing, orientation, intensity) | explicit algorithms (`pyvista_volume_processing`, `simpleitk_registration`), never applied silently | no | VTK filters | ITK filters | no | `Spacingd`, `Orientationd`, `ScaleIntensityd` [[doc]](https://docs.monai.io/en/stable/transforms.html) | `Resample`, `ToCanonical`, `RescaleIntensity` [[doc]](https://torchio.readthedocs.io/transforms/preprocessing.html) | no |
| Conversions named after the job (`to_mesh`, `to_points`, `segment`, `align`) | yes | algorithm names | filter names | filter names | geometry names | transforms, bundles | transforms | no |
| Hand-off to the library's own objects | `to_open3d()`, `to_pyvista()`, `to_sitk()`, `to_numpy()` | is Open3D | is PyVista | is SimpleITK | is trimesh | tensors | tensors | arrays |

## Algorithms, defaults and models

| | pardesline | Open3D | PyVista | SimpleITK | trimesh | MONAI | TorchIO | HF `datasets` |
|---|---|---|---|---|---|---|---|---|
| Classical 3D algorithms | 73 methods in 19 families (through Open3D, PyVista/VTK, SimpleITK, SciPy, pycpd) | registration, reconstruction, segmentation, features | VTK filters | registration, segmentation, filtering | geometry, booleans, ray casting | transforms, losses, metrics | no | no |
| Every parameter validated before running, with type, range and description | yes (`ParameterError` with the accepted list) | Python signatures | signatures | signatures | signatures | signatures | signatures | n/a |
| Defaults tied to the data scale (voxel from the bounding box, thresholds as multiples) | yes, documented per parameter ([why](algorithms/why-our-defaults-work.md)) | fixed numbers in tutorials | VTK defaults | ITK defaults | n/a | per bundle | per transform | n/a |
| Validated on real industrial / medical data | public stand-ins with committed numbers + `examples/real_cases/` mechanism | tutorials | gallery | notebooks | tests | Model Zoo benchmarks | papers | n/a |
| One-line pretrained model access | **roadmap** (model registry; reference scripts today) | Open3D-ML weights (RandLA-Net, KPConv) [[doc]](https://github.com/isl-org/Open3D-ML) | no | no | no | Model Zoo bundles [[doc]](https://monai.io/model-zoo.html) | no | through `transformers` |
| Local MCP server for AI agents | 14 tools, 20 skills | no | no | no | no | no | no | no |
| Licence | Apache-2.0 | MIT | MIT | Apache-2.0 | MIT | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Latest release checked | 0.2.0 (2026-10-14) | 0.20.0 (2026-09-16), wheels for Python 3.10–3.14 | 0.49.1 (2026-10-11) | 2.5.6 (2026-07-30) | 5.1.1 (2026-10-02) | 1.6.1 (2026-09-27) | 1.2.1 (2026-06-02) | 5.1.0 (2026-10-05) |

Release dates and wheel tags come from the PyPI JSON API on 2026-10-16.

## Which one should you use?

- You work on **one library's objects** and know its parameters: use it directly. pardesline will not get in the way, it hands you those objects.
- You need **a dataset**, in a format you can compute on, with its licence: pardesline, then whichever library you like.
- You need **MONAI or TorchIO transforms and training loops** on medical volumes: use them; pardesline can feed them (`ds.export(folder)` writes NIfTI-compatible MetaImage files, `prepare_nnunet_dataset.py` writes the nnU-Net layout) and will load their model outputs back as label maps.
- You need **registration, reconstruction or segmentation that works on first call** on data that is not the tutorial's: pardesline's defaults, with the reasons written down.
- You are building **an agent** that must browse datasets and run pipelines: pardesline's MCP server.
