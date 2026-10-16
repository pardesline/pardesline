---
title: FAQ — pardesline
description: Answers on supported datasets, licences, Python 3.13, Open3D wheels, GPU, pretrained models, the cloud client, DICOM de-identification, offline use and how to cite.
---

# FAQ

## Which datasets are not supported, and why?

BraTS is distributed through Synapse under a data-use agreement; ModelNet, ShapeNet and ScanNet require registration before download. pardesline never mirrors data and never bypasses a gate, so these are not bundled. A manifest that fetches them with the user's own credentials after they accept the terms is welcome: see [Datasets wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Adataset). Gated Hugging Face repos (AbdomenAtlas, CT-RATE) work once you have accepted the terms and run `huggingface-cli login`.

## Does pardesline redistribute datasets?

No. Every loader fetches from the owner's server (S3, Zenodo, TCIA, OpenNeuro, the Hub, university servers). The manifest records the licence as stated by the source and the loader warns when the terms are not a standard licence. Mirroring permissive datasets on a pardesline Hugging Face organisation is on the roadmap and will only cover licences that allow it.

## Why does it print "licence unknown - check the terms"?

Because the source states terms outside a standard licence (the RIRE and SimpleITK notebook excerpts, the Open3D demo data). The manifest's `note` quotes them; `ds.describe()` prints the note. The package will not guess a licence for you.

## Python 3.13?

The core package runs on 3.10 to 3.13. The native extras depend on Open3D wheels: 0.20 (September 2026) has them for 3.13, 0.19 stops at 3.12. pardesline 0.2.0 on PyPI pins Open3D below 0.20; `main` accepts 0.20 and the native test suite passes on 3.13 with it. Until 0.3.0 is released, use Python 3.12 or install from `main`.

## GPU?

Nothing in the package needs one. The classical algorithms run on CPU through Open3D, VTK and SimpleITK. The PyTorch reference scripts use CUDA when available and run on CPU at the sizes the examples use.

## Does it ship pretrained models?

Not yet. Today the deep-learning content is expert guides with reference scripts (PointNet, DINOv3 features, 3D JEPA, VAE anomaly detection, nnU-Net preparation) that read any pardesline dataset. One-line pretrained model access through a model registry is the top roadmap item; the [Models](models/index.md) pages keep their URLs for it.

## What is the cloud client?

`pardesline.cloud` is the optional client of the hosted PardesLine platform (sharing, GPU jobs, viewers). It is in the package because the same object model is used on both sides, it is off unless you call its functions, and this documentation covers the local, Apache-2.0 part.

## Can I use it offline?

Yes, once the data is cached: `pl.load` reads the on-disk index and files; `pardesline fetch <dataset>` downloads a dataset ahead of time; `ds.export(folder)` writes standard files you can carry anywhere.

## How do I load DICOM, and what about identifiers?

A DICOM series folder loads as one `Volume` (`pl.load("series_folder/")`, or a `tcia://` collection). pardesline reads pixel data and geometry and does not de-identify: do that before the data reaches any tool, with the DICOM PS3.15 basic profile or your institution's process. Contributions of real cases must be de-identified by the contributor.

## How is this different from MONAI or TorchIO?

They are training frameworks for medical volumes with excellent transforms. pardesline is the layer before and around them: datasets with licences, one object for points, meshes and volumes, classical algorithms with documented defaults, and an MCP server. See the [comparison](comparison.md); `ds.export()` and `prepare_nnunet_dataset.py` hand data to them.

## Where do outputs go?

Algorithm outputs go to a temporary folder unless you set `pl.set_output_dir(...)` or pass `output=`; `obj.save(path)` writes where you say, with a `.pardesline.json` sidecar next to it. Datasets are cached under `~/.cache/pardesline/datasets/` (`PARDESLINE_CACHE` or `pl.set_cache_dir()` to move it).

## How do I cite it?

`CITATION.cff` at the repository root (the "Cite this repository" button on GitHub), or the BibTeX block in the README. Cite the datasets you use as well: `ds.citation` returns the reference each owner asks for.

## How do I report a bug or a security issue?

Bugs: [an issue](https://github.com/pardesline/pardesline/issues/new/choose) with the snippet, the full log and `pardesline version`. Security: GitHub's private vulnerability reporting on the repository, as described in [SECURITY.md](https://github.com/pardesline/pardesline/blob/main/SECURITY.md).
