---
title: Install pardesline — pip install for 3D vision and medical imaging in Python
description: pip install pardesline with the local, medical, hf and mcp extras; Python 3.10 to 3.13 on Linux, macOS and Windows; Open3D and SimpleITK wheels; troubleshooting.
---

# Install

```bash
pip install pardesline                 # core: catalog, object model, datasets, CLI; no native libraries
pip install "pardesline[local]"        # + Open3D, PyVista, SciPy, scikit-image, pycpd: points, meshes, LiDAR, SDF
pip install "pardesline[medical]"      # + SimpleITK: volumes, DICOM series, registration, segmentation
pip install "pardesline[hf]"           # + huggingface_hub: datasets on the Hub
pip install "pardesline[mcp]"          # + mcp: the local server for AI agents
pip install "pardesline[all]"          # everything above
```

## Python and operating systems

| | Linux x86_64 / aarch64 | macOS arm64 | Windows x86_64 |
|---|---|---|---|
| Core (`pardesline`) | 3.10 – 3.13 | 3.10 – 3.13 | 3.10 – 3.13 |
| `[local]`, `[all]` | 3.10 – 3.13 | 3.10 – 3.13 | 3.10 – 3.13 |

The native extras depend on Open3D wheels: Open3D 0.20 (September 2026) covers Python 3.10 to 3.13, 0.19 covers 3.10 to 3.12. pardesline 0.2.0 on PyPI pins Open3D below 0.20, so on Python 3.13 use a 3.12 interpreter or install from `main` until 0.3.0 ships:

```bash
pip install "pardesline[all] @ git+https://github.com/pardesline/pardesline"
```

## Conda

Open3D and SimpleITK are installed from PyPI inside the environment:

```bash
conda create -n pl python=3.12
conda activate pl
pip install "pardesline[all]"
```

## Check the install

```bash
pardesline version
pardesline datasets            # 43 names
pardesline list                # 19 modules, 73 methods
python -c "import pardesline as pl; print(pl.load('open3d_bunny')[0].mesh.info())"
```

## Where files go

- Datasets: `~/.cache/pardesline/datasets/<name>/` (`pl.set_cache_dir(...)` or `PARDESLINE_CACHE` to move it).
- Outputs of algorithms: a temporary folder unless `pl.set_output_dir(...)` or `output=` is given; `obj.save(path)` writes where you say.
- Logs: stderr through loguru; `PARDESLINE_LOG=DEBUG` for the HTTP Range and archive details.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `MissingDependency: SimpleITK` | the `[medical]` extra is not installed | `pip install "pardesline[medical]"` |
| `No matching distribution found for open3d` | Python version without an Open3D wheel | use 3.10 – 3.13 with Open3D 0.20, or 3.10 – 3.12 with 0.19 |
| `ImportError: libGL.so.1` on a headless Linux box | Open3D / VTK need the GL runtime | `apt-get install libgl1 libegl1 libglib2.0-0 libgomp1 libxrender1 libsm6` |
| PyVista renders nothing in CI or over SSH | no display | `PYVISTA_OFF_SCREEN=true`, use `Plotter(off_screen=True)` and `screenshot()` |
| `HTTP 429` from the Hugging Face Hub when listing a large repo | anonymous rate limit | `huggingface-cli login`; the bundled manifests scope their listings to sub-folders |
| `HTTP 429` from Zenodo | too many small Range requests | the archive source already groups contiguous members and retries with backoff; wait a minute |
| `licence unknown - check the terms` warning | the source states terms outside a standard licence | read `ds.describe()`; the warning is the point: nothing is guessed |
| `does not accept '.gz' files` | pardesline 0.2.0 checked only the last suffix | fixed on `main` (`.nii.gz` accepted wherever `.nii` is); until 0.3.0, decompress or install from `main` |

Still stuck: [GitHub Discussions](https://github.com/pardesline/pardesline/discussions), or open an issue with the output of `pardesline version` and the full log.
