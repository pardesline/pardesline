---
title: How to download a medical imaging dataset in Python
description: Download one sample or a whole medical imaging dataset (Medical Segmentation Decathlon, AMOS, TotalSegmentator, LUNA16, IXI, TCIA) in Python with pardesline, with the licence and citation attached, without scraping or format conversion.
---

# How to download a medical imaging dataset in Python

Pick a name from the [datasets catalog](../datasets/index.md), load it, touch a sample. The licence and the citation come with it; files are verified and cached; archives are read by HTTP Range so one case costs one case.

```python
import pardesline as pl

print([m.name for m in pl.datasets(tag="ct")])  # the CT datasets

ds = pl.load("msd_task09_spleen")  # lazy: the 1.6 GB tar is indexed, not downloaded
print(ds.describe())  # roles, labels, licence CC-BY-SA-4.0, citation
case = ds.filter(split="Tr")[0]  # the first labelled case
ct, mask = case.ct, case.mask  # two files fetched now (about 30 MB)
print(ct.info(), mask.labels)  # {'size': ..., 'spacing': ...}  {1: 'spleen'}
```

Expected output:

```
{'size': (512, 512, 55), 'spacing': (0.976, 0.976, 5.0), 'origin': (...), 'pixel_type': '32-bit float', ...} {1: 'spleen'}
```

## The whole dataset, or a subset

```python
ds.take(10).fetch_all()  # download the first ten cases now (returns the file count)
ds.sample(20, seed=0).fetch_all()  # a reproducible random subset
pl.load("msd_task09_spleen").fetch_all()  # everything (1.6 GB)
```

From the command line: `pardesline fetch msd_task09_spleen` and `pardesline export msd_task09_spleen ./out`.

## Where it went

`~/.cache/pardesline/datasets/msd_task09_spleen/` keeps the original files and the archive index; `pl.set_cache_dir("/data/cache")` or `PARDESLINE_CACHE=/data/cache` moves it. `ds.export("./spleen_std")` writes standard MetaImage files with sidecars instead.

## Patient-level splits

```python
train, test = ds.filter(split="Tr").split(by="id", fractions=(0.8, 0.2), seed=0)
```

`split(by=...)` groups by a sample field before splitting, so a patient never appears on both sides.

## When it fails

| Message | Meaning | Do |
|---|---|---|
| `licence unknown - check the terms` | the source has no standard licence | read the note in `ds.describe()`; the warning is deliberate |
| `requires_agreement` / HTTP 401 on a Hub repo | gated dataset (AbdomenAtlas, CT-RATE) | accept the terms on the Hub, `huggingface-cli login`, retry |
| HTTP 429 from Zenodo | too many requests | the loader retries with backoff; wait a minute |
| the first `load` of an MSD task takes minutes | the tar index is built by walking headers | cached afterwards; archives below 64 MB are downloaded whole on `main` |

## Datasets not bundled

BraTS (Synapse DUA), ModelNet, ShapeNet, ScanNet (registration-gated): see the [FAQ](../faq.md#which-datasets-are-not-supported-and-why). Any other public source: [Hugging Face repos](load-a-hugging-face-3d-dataset-in-python.md), [TCIA collections](download-a-tcia-collection-in-python.md), `s3://openneuro.org/dsXXXXXX`, or a remote zip / tar URL.

Related: [Datasets catalog](../datasets/index.md) · [Concepts: manifest](../getting-started/concepts.md#manifest) · [Standardize your own folder](standardize-a-folder-of-medical-images-in-python.md)
