---
title: How to load a Hugging Face 3D dataset in Python
description: Load any Hugging Face Hub repository of 3D or medical files (NIfTI, PLY, GLB, npz) as typed objects in Python: bundled manifests for KiTS23, OpenMind, Objaverse, 3D Arena, BiomedSegFM, UniOcc, or hf://org/repo with a drafted manifest.
---

# How to load a Hugging Face 3D dataset in Python

The Hub stores 3D files it cannot open: a repository of NIfTI, PLY or GLB files comes back from `datasets.load_dataset` as paths at best. pardesline lists the repository tree, groups files into samples with a manifest, and opens them as volumes, meshes, point clouds or label maps.

## A bundled Hub dataset

```python
import pardesline as pl

ds = pl.load("hf_kits23")  # neheller/KiTS-Challenge-Imaging, CC-BY-NC-SA-4.0
print(ds.describe())
case = ds[0]
print(case.roles)  # ['ct', 'mask']
mask = case.mask  # downloaded through huggingface_hub, cached in its cache
print(mask.labels)  # {1: 'kidney', 2: 'tumor', 3: 'cyst'}
```

Ten Hub datasets ship with a manifest (`pl.datasets(scheme="hf")`): KiTS23, OpenMind, NSCLC-Radiomics NIfTI, AbdomenAtlas mini, CT-RATE, BiomedSegFM, Objaverse (one shard), 3D Arena, UniOcc, KITTI-360 Gaussian splats.

## Any repository: `hf://`

```python
ds = pl.load("hf://farrell236/NSCLC-Radiomics-NIFTI")  # a bundled manifest matches: used as is
ds = pl.load("hf://some-org/some-3d-repo")  # no manifest: the tree is listed and a draft is made
```

For an unknown repository the second call raises `NeedsConfirmation` with the questions the files cannot answer (which role is a label map and what its labels mean, the units of a mesh, the licence) and the path of the saved draft. Answer once:

```python
ds = pl.load("hf://some-org/some-3d-repo", license="CC-BY-4.0", units="mm", labels={"mask": {1: "tumor"}})
```

or `assume=True` to load with unknowns left unknown (the objects carry `None` and a warning), or `interactive=True` to answer in the terminal. The confirmed manifest is saved next to the draft and reused next time. Large repositories: `pl.scan("hf://org/repo", max_files=5000)` limits the listing, and the bundled manifests scope their `paths` to sub-folders because listing a 266 721-file repository anonymously takes 15 minutes and ends in HTTP 429.

## Gated repositories

AbdomenAtlas and CT-RATE require accepting the terms on the Hub. Then `huggingface-cli login`; the manifests mark `requires_agreement: true` and the loader explains the 401 otherwise.

## Raw arrays on the Hub

BiomedSegFM ships `.npz` files; UniOcc ships occupancy grids. The manifests carry the `layout` (`key`, `dtype`, `shape`) that turns them into volumes, and `allow_pickle` stays off. See [raw point clouds with a layout](load-raw-npy-and-bin-point-clouds-with-a-layout.md).

## When it fails

| Message | Do |
|---|---|
| HTTP 429 while listing | log in (`huggingface-cli login`), or pass `paths=` in a manifest to scope the listing |
| `NeedsConfirmation` | answer the questions as keyword arguments, or `interactive=True` |
| the repo has `parquet` tables, not files | that is a `datasets`-style repo: use `datasets.load_dataset`; pardesline is for file-based 3D repos |

Related: [Datasets catalog](../datasets/index.md) · [Standardize a folder](standardize-a-folder-of-medical-images-in-python.md) · [Contributing a manifest](../contributing.md#adding-a-dataset)
