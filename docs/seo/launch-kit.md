# Launch kit

Ready to copy-paste. Every number comes from the repository (manifests, catalog, committed example outputs, benchmarks); nothing is estimated. Tone: we help practitioners get 3D and medical imaging done in Python; upstream libraries are credited everywhere.

Facts used below: 43 datasets (35 medical), 19 algorithm families, 73 methods, 371 documented parameters, 20 expert guides, 14 MCP tools, README demo 21 s cold, bunny registration benchmark 0.11° median vs 32.5° (Open3D tutorial ICP call), Apache-2.0, Python 3.10–3.13.

---

## Awesome-list pull requests

Open each as a one-line PR following the list's own format; the title is "Add pardesline". Check the list's contribution rules first (some require a minimum age or star count: come back when they are met).

| List | Section | Entry |
|---|---|---|
| [vinta/awesome-python](https://github.com/vinta/awesome-python) | Science → (new) or Image Processing | `* [pardesline](https://github.com/pardesline/pardesline) - 3D vision and medical imaging: datasets in one line, algorithms with documented defaults, MCP server for AI agents.` |
| [jbhuang0604/awesome-computer-vision](https://github.com/jbhuang0604/awesome-computer-vision) | Software → 3D / Medical | `- [pardesline](https://github.com/pardesline/pardesline) - Python library: 43 public 3D and medical imaging datasets loadable in one line, 73 algorithms (registration, reconstruction, segmentation) over Open3D, PyVista and SimpleITK, MCP server.` |
| [Yochengliu/awesome-point-cloud-analysis](https://github.com/Yochengliu/awesome-point-cloud-analysis) | Datasets / Tools | `- [pardesline](https://github.com/pardesline/pardesline): one-line loaders for KITTI raw, KITTI-360 splats, UniOcc, Objaverse, MedShapeNet; RANSAC + ICP with data-tied defaults.` |
| [sfikas/medical-imaging-datasets](https://github.com/sfikas/medical-imaging-datasets) | Tools / Loaders | `- [pardesline](https://github.com/pardesline/pardesline): Python loaders with licence and citation for MSD, AMOS, TotalSegmentator, LUNA16, IXI, VerSe, SPIDER, CHAOS, KiTS23, TCIA collections, OpenNeuro.` |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | Data Science / Science | `- [pardesline/pardesline](https://github.com/pardesline/pardesline) 🐍 🏠 - 3D vision and medical imaging: browse 43 datasets, run 73 algorithms on point clouds, meshes and CT/MRI volumes, read 20 expert guides.` |
| [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) | Community servers | `- **[pardesline](https://github.com/pardesline/pardesline)** - 3D and medical imaging datasets and algorithms as MCP tools, local, no account.` |
| [timzhang642/3D-Machine-Learning](https://github.com/timzhang642/3D-Machine-Learning) | Datasets / Tools | `- [pardesline](https://github.com/pardesline/pardesline): typed loaders for 3D and medical datasets, PointNet / DINOv3 / JEPA reference scripts on them.` |
| [MONAI community / awesome-medical-imaging lists](https://github.com/topics/awesome-medical-imaging) | Python libraries | `- [pardesline](https://github.com/pardesline/pardesline): dataset layer and domain-vocabulary API (align, segment, to_mesh) over SimpleITK, Open3D and PyVista; exports to MONAI / nnU-Net layouts.` |

---

## Show HN

**Title (74 chars):** Show HN: pardesline – 3D and medical imaging datasets in one line, in Python

**Body:**

I maintain pardesline, an Apache-2.0 Python library for 3D computer vision and medical imaging. It started from a recurring pain: every public dataset (Medical Segmentation Decathlon, TCIA, TotalSegmentator, KITTI, Hugging Face repos) ships in a different format behind a different portal, and every tutorial's algorithm defaults break on real scans.

What it does:

- `pl.load("msd_task09_spleen")` loads one of 43 datasets lazily. A manifest says where the files are, how they pair into samples, the frame and units, label names, the licence and the citation. Archives are read by HTTP Range, so one case costs one case (one 30 MB CT out of a 1.6 GB tar).
- One typed object for point clouds, meshes, volumes and label maps over Open3D, PyVista and SimpleITK, with `to_open3d()` / `to_pyvista()` / `to_sitk()` when you want the library itself.
- 73 algorithms behind calls like `target.align(moving)` or `mask.to_mesh(label=1)`. Every one of the 371 parameters has a written rationale and a validation regime (`pl.describe("registration.ransac_icp_pipeline")`). On the Stanford bunny with a 35° offset, 70 % overlap and 0.5 % noise, the Open3D tutorial ICP call ends 32.5° off; the one-liner ends 0.11° off (benchmark scripts in the repo).
- A local MCP server (`pardesline mcp`) that exposes all of it, plus 20 expert guides, to Claude, Cursor, Gemini CLI and Codex.

What it does not do yet: ship pretrained models. The deep-learning part is reference scripts (PointNet, DINOv3 features, 3D JEPA, VAE) that read any dataset; one-line model access through the same manifest pattern is the top roadmap item.

Repo: https://github.com/pardesline/pardesline — docs: https://pardesline.github.io/pardesline/

I'd like feedback on the manifest format and on which datasets and models to add first.

---

## Reddit

### r/Python

**Title:** pardesline: 43 public 3D and medical imaging datasets loadable in one line, with their licences, plus 73 algorithms with documented defaults (Apache-2.0)

**Body:**

What my project does: `pip install "pardesline[all]"`, then `pl.load("msd_task04_hippocampus")` returns a dataset whose samples are typed objects (volume, label map, mesh, point cloud) that know their frame, units, label names, licence and citation. 43 datasets are described by manifests (Decathlon, AMOS, TotalSegmentator, LUNA16, IXI, TCIA collections, OpenNeuro, KITTI, Objaverse, Hugging Face repos); archives are read by HTTP Range so you fetch one case, not 24 GB. On top: one object model over Open3D, PyVista and SimpleITK, 73 algorithms where every default has a written reason (`pl.describe("...")` prints it), and a local MCP server for AI agents.

Target audience: people doing 3D vision or medical imaging in Python who are tired of scraping portals and tuning ICP by hand. Production-ready for the dataset and classical-algorithm parts; the deep-learning part is reference scripts, not shipped weights.

Comparison: Open3D / PyVista / SimpleITK are the engines underneath, not competitors (it hands you their objects). MONAI and TorchIO are training frameworks for volumes with excellent transforms; pardesline is the layer before them (datasets with licences, point clouds and meshes too, classical algorithms with documented defaults) and exports to their layouts. A comparison table with sources is in the docs.

https://github.com/pardesline/pardesline

### r/computervision

**Title:** Why ICP fails on real scans, with numbers: 32.5° off with tutorial defaults vs 0.11° with data-tied defaults (open-source benchmark)

**Body:**

I benchmarked the Open3D tutorial registration calls against defaults derived from the data on the Stanford bunny: a copy rotated 35°, trimmed to 70 % overlap, jittered with 0.5 % noise, five noise draws. The tutorial ICP call (identity start, point-to-point, threshold 0.02) stays 32.5° off with a 0.98 fitness, because ICP is a local optimiser and the fitness counts anything within a wide threshold. The tutorial global registration with its fixed `voxel_size = 0.05` fails worse (134°) because the voxel is a third of the object. Deriving the voxel from the bounding box (1.3 % of the diagonal) and tying every other distance to it gives 0.11° median, 0.24° worst.

The scripts, the numbers and the page explaining each parameter are in the pardesline repo (Apache-2.0): `benchmarks/registration_bunny.py`, "Why our defaults work". The same package loads 43 public 3D / medical datasets in one line and runs 73 algorithms behind one call. Interested in what other failure modes people hit on industrial scans: the "real cases" folder takes reproducible runs.

https://github.com/pardesline/pardesline

### r/MachineLearning

**Title:** [P] pardesline: a dataset layer for 3D and medical imaging (manifests, licences, patient-level splits) with reference scripts for PointNet, DINOv3 features and 3D JEPA on any of the 43 datasets

**Body:**

Training on 3D medical data usually starts with a week of plumbing: find the archive, decode the format, guess the label meanings, split by patient. pardesline describes 43 public datasets with manifests (files, roles, frame, units, labels, licence, citation) and loads them lazily; `ds.split(by="patient")` never leaks a patient; `ds.export(folder)` writes standard files; `prepare_nnunet_dataset.py` writes the nnU-Net v2 layout. The reference scripts (PointNet segmentation, DINOv2 / DINOv3 dense features, 3D JEPA pretraining, VAE anomaly detection) read any dataset through the same API; the committed examples ran on MSD hippocampus (PointNet 0.97 mIoU on anterior / posterior after 40 epochs on CPU) and on a KITTI camera frame.

No weights are shipped; one-line pretrained model access through a model manifest is the roadmap item we are designing in the open (tracking issue in the repo). Apache-2.0.

https://github.com/pardesline/pardesline

### r/3Dscanning (or r/photogrammetry)

**Title:** Open-source: align two scans in one call with defaults that follow the scan's own scale (RANSAC + ICP, Open3D underneath)

**Body:**

If you have fought `max_correspondence_distance` and ICP that converges to the wrong pose on a partial scan: pardesline wraps Open3D's RANSAC + FPFH + ICP in `target.align(moving)` with every distance derived from the bounding box of the data, so the same call works on a 15 cm part and a 15 m facade. The transform, fitness and inlier RMSE come back, and a sidecar records every parameter used. It also reads raw `.bin` / `.npy` clouds through a declared layout, reconstructs surfaces (Poisson, density-trimmed so holes do not balloon), and loads public scans (Stanford bunny, KITTI, MedShapeNet). Apache-2.0, `pip install "pardesline[local]"`.

https://github.com/pardesline/pardesline

---

## LinkedIn post (founder profile)

```
Your ICP converged. The fitness says 0.98. The part is 32 degrees off.

That is what the Open3D tutorial call does on a partial, noisy scan.
Fitness counts anything inside a wide threshold, and ICP never left its starting basin.

We ran the numbers on the Stanford bunny, five noise draws:
- tutorial ICP call: 32.5° off
- tutorial RANSAC with its fixed voxel: 134° off
- defaults derived from the data: 0.11° off

The fix is not a smarter algorithm. It is tying every distance to the scan's own scale and writing down why.

pardesline does that for 73 algorithms, with a written rationale per parameter, and loads 43 public 3D and medical datasets in one line with their licences. Apache-2.0, Python 3.10–3.13, Open3D / PyVista / SimpleITK underneath.

I need you to contribute and make the future of 3D vision and medical imaging possible: a dataset manifest, an algorithm default you disagree with, a real scan that breaks it.

Comment REPO and I will send you the repository and the benchmark page.
```

First comment: `Repository: https://github.com/pardesline/pardesline · Benchmark: https://pardesline.github.io/pardesline/benchmarks/ · Why our defaults work: https://pardesline.github.io/pardesline/algorithms/why-our-defaults-work/`

---

## X / Twitter thread (8 tweets)

1. Your ICP converged with a 0.98 fitness and the part is 32° off. Thread on why tutorial defaults fail on real scans, with numbers, and an open-source fix. 🧵
2. ICP is a local optimiser. From a 35° start it converges to the nearest wrong minimum. The tutorial threshold (0.02 m on a 15 cm object) makes almost every point "match", so the fitness looks great.
3. Benchmark, Stanford bunny, 70 % overlap, 0.5 % noise, 5 draws: tutorial ICP 32.5° off; tutorial RANSAC with its fixed voxel 134° off; defaults derived from the bounding box 0.11° median. Scripts in the repo.
4. The rule: one number, the voxel (1.3 % of the diagonal), and every other distance a multiple of it. Normals at 2×, FPFH at 5×, RANSAC inliers at 1.5×, final ICP at 0.4×. Same code for a part and a facade.
5. pardesline writes this down for 73 algorithms: every one of 371 parameters has a rationale and a validation regime. `pl.describe("registration.ransac_icp_pipeline")` prints them.
6. It also loads 43 public 3D and medical datasets in one line (Decathlon, TCIA, TotalSegmentator, KITTI, Hugging Face repos) with licence and citation attached, reading archives by HTTP Range so one case costs one case.
7. And it is an MCP server: `pardesline mcp` gives Claude, Cursor, Gemini CLI and Codex the datasets, the algorithms and 20 expert guides. Local, no account.
8. Apache-2.0, pip install pardesline. Open3D, PyVista and SimpleITK underneath, credited everywhere. Contributions wanted: dataset manifests, algorithm defaults you disagree with, real scans. https://github.com/pardesline/pardesline

---

## Launch Discussion (GitHub, category Announcements)

**Title:** pardesline 0.2: datasets in one line, defaults that work on real scans, MCP for agents — and what we need from you

**Body:**

pardesline is on PyPI and the documentation is live. In one paragraph: 43 public 3D and medical imaging datasets loadable in one line with their manifests and licences; one typed object for point clouds, meshes, volumes and label maps over Open3D, PyVista and SimpleITK; 73 algorithms whose 371 parameters each have a written rationale and validation regime; a local MCP server with 20 expert guides for AI agents. Twelve executed examples with their images are in the gallery; two benchmarks against upstream defaults are regenerated by script.

What we need, in order of leverage:

1. **Dataset manifests.** The "Datasets wanted" issue lists candidates; `templates/new_dataset/` is the template; a live check script tells you when it works.
2. **Disagreement on defaults.** Every parameter's rationale is public. If you have data where a default is wrong, open an issue with the numbers: that is how the rationale improves.
3. **Real cases.** `examples/real_cases/` takes reproducible runs on production-like data. The README's "validated on real cases" table only lists what is reproducible.
4. **Model manifests.** The model registry (one-line pretrained model access) is designed in the open on its tracking issue; manifests can be written now from `templates/new_model/`.

Everything else: `CONTRIBUTING.md`, 16 good first issues, Discussions for questions.

---

## Registries and directories

- **PyPI**: the long description is the README (absolute image URLs, renders on PyPI); keywords and classifiers are in `pyproject.toml`. Nothing else to submit.
- **MCP registries**: `.mcp.json` at the repository root declares the server; submit to the official MCP registry (`https://registry.modelcontextprotocol.io/`) with name `io.github.pardesline/pardesline`, command `pardesline mcp`, package `pardesline` on PyPI, and to the awesome-mcp-servers lists above. Pitch line: *3D vision and medical imaging for agents: 43 datasets, 73 algorithms, 20 expert guides, local and licence-aware.*
- **Papers With Code**: no paper yet; when the model registry ships with benchmark tables, submit the benchmark page as a dataset / task entry.
- **Hugging Face**: create the `pardesline` organisation; for every bundled dataset whose licence allows redistribution (CC0, CC BY, PDDL, MIT, ODC-By), mirror it with a dataset card that documents `pip install pardesline` and `pl.load("<name>")` as the loader, links the manifest, and credits the owner; for non-commercial or gated sources, no mirror: a dataset card pointing to the owner with the same loader snippet is still allowed and still indexes. Add the `pardesline` tag to the cards. A Space running the README demo (RIRE registration, 21 s) makes the loop visible; model cards come with the model registry, each pointing back with `pl.load_model("<name>")`.
- **conda-forge**: a feedstock once the Open3D 0.20 pin is released (0.3.0); until then the README documents `pip` inside conda.

---

## Timing

Post the LinkedIn piece first (Tuesday to Thursday, mid-afternoon Israel time), the Show HN the next morning (US time), Reddit the same week one subreddit per day, the awesome-list PRs after the first stars land so the entries survive review. Reply to every comment in the first hour; the ask in each piece is specific (a manifest, a default, a scan), not "star us".
