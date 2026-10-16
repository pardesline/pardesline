# GitHub repository metadata

Exact values for `pardesline/pardesline`. Applied through the REST API in Phase 4 when a token is provided (`gh` is not installed on the maintainer's machine); until then the founder can paste them in Settings → About.

## Description (330 characters, limit 350)

```
Python library for 3D computer vision and medical imaging. Load 43 public 3D and medical datasets (MSD, TCIA, TotalSegmentator, KITTI, Hugging Face) in one line with manifests and licences; run 73 algorithms (ICP/RANSAC registration, segmentation, reconstruction) on point clouds, meshes, CT/MRI volumes; MCP server for AI agents.
```

Why these words: "python library", "3d computer vision", "medical imaging", "datasets", "point clouds", "registration", "segmentation" are the highest-volume queries in the keyword map; the dataset names are the navigational queries; "MCP server" is the agent query. No adjectives.

## Topics (exactly 20, lowercase-hyphenated, ordered by search volume)

```
python
computer-vision
medical-imaging
3d
point-cloud
datasets
deep-learning
huggingface
segmentation
registration
3d-reconstruction
mesh-processing
dicom
nifti
ct
mri
open3d
simpleitk
mcp
lidar
```

Dropped from the current list, with reason: `dinov3`, `jepa`, `vae`, `pointnet`, `frcnn`, `gaussian-splatting` (niche; they stay as keywords in the README and PyPI), `pyvista` (kept in PyPI keywords; `open3d` and `simpleitk` carry more searches), `medical-ai` (subsumed by `medical-imaging`), `3d-vision` (GitHub normalises most traffic to `3d` and `computer-vision`), `mesh` (replaced by `mesh-processing`), `point-clouds` (singular `point-cloud` is the canonical GitHub topic). Added: `python`, `computer-vision`, `3d`, `datasets`, `huggingface`, `3d-reconstruction`, `mesh-processing`, `ct`, `mri`, `mcp`, `lidar`.

## Website

```
https://pardesline.github.io/pardesline/
```

Already set. The same URL becomes `Homepage` and `Documentation` in `pyproject.toml` and `url` in `CITATION.cff`, so the brand has one documentation address. The company site https://pardesline.com stays as the `Company` project URL.

## Features to switch on (Settings → General)

- Discussions: on (categories Q&A, Ideas, Show and tell; seeded in Phase 4).
- Issues: on (already).
- Social preview: `docs/assets/social-preview.png` (regenerated in Phase 5; the current file is `docs/showcase/social-preview.png`).
- Releases: "Set as the latest release" on each tag (already for v0.2.0).

## REST API calls (Phase 4, token with `repo` scope)

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/pardesline/pardesline \
  -d '{"description": "<description above>", "homepage": "https://pardesline.github.io/pardesline/", "has_discussions": true}'

curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/pardesline/pardesline/topics \
  -d '{"names": ["python","computer-vision","medical-imaging","3d","point-cloud","datasets","deep-learning","huggingface","segmentation","registration","3d-reconstruction","mesh-processing","dicom","nifti","ct","mri","open3d","simpleitk","mcp","lidar"]}'
```

## Name consistency check (Phase 1 result)

| Surface | Value | Status |
|---|---|---|
| PyPI project | `pardesline` | OK |
| Import name | `pardesline` | OK |
| GitHub | `pardesline/pardesline` | OK |
| CLI | `pardesline` | OK |
| MCP server name | `pardesline` | OK |
| Claude Code plugin | `pardesline` | OK |
| Docs | `https://pardesline.github.io/pardesline/` | OK (GitHub Pages) |
| Casing in prose | `pardesline` for the package, `PardesLine` for the company | Keep both, never `Pardesline` |
| Old client repo | `1904jonathan/pardesline-python` | Redirect notice committed; archive it on GitHub (founder) |

Mismatch found and fixed in Phase 1: `pyproject.toml` pointed `Homepage` to pardesline.com and `Documentation` to the README anchor while GitHub pointed to the Pages site. Now all three point to the Pages site.
