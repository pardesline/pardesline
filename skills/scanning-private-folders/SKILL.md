---
name: scanning-private-folders
description: >-
  Load a user's own folder of 3D / medical data with pardesline: `pl.scan(folder)`
  drafts a manifest (samples grouped by sub-folder, name prefix or file; roles named
  after folders or types; label maps detected by name hints; volume headers read) and
  lists the questions it will not answer by guessing (licence, units and frame of
  formats that carry none, label meanings, uncertain pairing). Covers the four
  answering modes of `pl.load(folder, ...)`: strict `NeedsConfirmation` with a saved
  draft `pardesline.manifest.json`, answers as keyword arguments (`license=`, `units=`,
  `frame=`, `labels=`, `pairing=`), `interactive=True`, `assume=True`; and how an AI
  agent should relay the questions to the human; the same flow for a Hugging Face repo
  without a bundled manifest (`pl.load("hf://org/name/sub")`, `pl.scan("hf://...")`),
  including the `types=` / `layout=` answers that raw `.npy` `.npz` `.bin` arrays need.
  Use whenever `pl.load` is given a directory or an un-manifested hub repo, or the user
  says "my data", "my folder", "our study".
---

# Scanning a private folder

```python
import pardesline as pl

pl.load("/data/study_A")
```

raises `pl.NeedsConfirmation`:

```
study_a: 4 question(s) before this folder can be loaded:
  - license: Who owns this data and under which terms may it be used? (e.g. 'internal, no redistribution', 'CC-BY-4.0')
  - roles.ct.units: p01/ct/scan.vti: the format carries no unit. mm, m, ...?
  - roles.surface.units: p01/surface.stl: the format carries no unit. mm, m, ...?
  - roles.mask.labels: p01/masks/liver.vti looks like a label map (name hint). What does each value mean? e.g. {1: 'liver'}
Answer in the call, e.g.
  pl.load(folder, license='internal, no redistribution', units={'ct': 'mm', 'surface': 'mm'}, labels={'mask': {1: 'organ'}})
or edit the saved draft, or pass assume=True to proceed with unknowns, or interactive=True.
Draft saved: /data/study_A/pardesline.manifest.json
```

The exception carries `.questions` (list of `Question(field, message,
suggestion)`), `.manifest` (the draft) and `.draft_path`.

## What the scan does (so you can predict its output)

1. Collects data files by extension (point clouds, meshes, volumes, images,
   transforms); a folder containing `.dcm` / `.ima` files is one `volume`
   entry. Hidden entries, `.txt`, archives and `.pardesline.json` sidecars
   are ignored (declare them by hand if needed).
2. Groups into samples, in this order of preference:
   `folder` (every top-level sub-folder is a sample: `p01/`, `p02/`),
   `name_prefix` (flat folder with `<id>_<role>` / `<id>-<role>` names
   repeating across ids: `a_image.vti`, `a_seg.vti`, `b_image.vti`, ...),
   `file` (each file its own sample). A `pairing` question is raised when the
   confidence is low.
3. Names roles after the containing sub-folder (`ct/`, `masks/` -> `mask`,
   `images/` -> `image`), the file stem for a file directly in the sample
   folder (`p01/surface.stl` -> `surface`), the name suffix for
   `name_prefix`, else the type (`volume`, `mesh`, `points`). Duplicates get
   `_2`, `_3`.
4. Types a volume as `labels` when its path matches
   `mask|seg|label|gt|ground|annot|roi`; otherwise reads the header and, for
   integer voxels, asks whether it is a label map.
5. Fills frames it can know: ITK formats -> LPS/mm, glTF -> Y-up/m; asks
   units (and frame for meshes/points) for the rest.
6. Asks the licence unless the source states one (a Hub card).
7. Raw arrays (`.npy`, `.npz`, `.bin`, `.raw`) become `attribute` roles with
   a `roles.<role>.layout` question: the type and the layout must be declared
   (`types={"sweep": "points"}`, `layout={"sweep": {...}}`).
8. A folder that wraps everything (`raw/p01/...`) is stripped before
   grouping; one folder holding files of different kinds is one sample whose
   files are its roles, a folder of same-kind files is one sample per file.

`pl.scan(folder, name=None, read_headers=True)` returns the draft `Manifest`
(`.questions`, `.is_draft`, `.describe()`), without raising.
`pl.scan("hf://org/name/sub")` does the same from the repo listing (no
headers read; the licence comes from the Hub card, marked TO CONFIRM); the
draft is saved under `pl.cache_dir()/drafts/` and reused by the next
`pl.load("hf://...")`.

## The four ways to answer

**1. In the call** (idempotent, scriptable):

```python
ds = pl.load(
    "/data/study_A",
    license="internal, no redistribution",  # or an SPDX id "CC-BY-4.0", or a dict
    units="mm",  # one value for every role ...
    frame={"surface": "LPS"},  # ... or per role
    labels={"mask": {1: "liver", 2: "tumor"}},  # per role; {1: "liver"} applies to all label roles
    pairing="folder",
    types={"sweep": "points"},  # raw arrays: what they are ...
    layout={"sweep": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},  # ... and how
)
```

`labels={"mask": None}` says "not a label map" (the role becomes `volume`).
A dict whose keys are not roles raises `pl.ManifestError` listing the roles.

**2. Edit the saved draft** `pardesline.manifest.json` (set `license`, the
roles' `units` / `frame` / `labels`, and empty `questions`), then
`pl.load(folder)` again. The file is a normal manifest: it can be versioned
next to the data and shared with colleagues; its `source.root` is re-pointed
to the folder's current location on load.

**3. Interactive** `pl.load(folder, interactive=True)`: one `input()` prompt
per question; labels are typed as `1: liver, 2: tumor`; `none` means not a
label map; empty keeps the suggestion.

**4. Assume** `pl.load(folder, assume=True)`: loads with unknowns left
unknown and one warning per open question. For exploration only; the
objects' `frame.known` is False and `license.known` is False.

## For an AI agent

Do not answer the questions yourself. Relay `err.questions` to the human,
collect the answers, then call `pl.load(folder, **answers)` once. If the
human cannot answer the licence, use `license="internal, terms unknown"`
rather than inventing an SPDX id, and say the data must not be redistributed.
After a successful load, `ds.manifest.save(path)` keeps the confirmed
manifest for the next session.

## Limits (say them when relevant)

- No reading inside `.npy` / `.npz` / `.bin`: the `layout` answer (or a
  manifest with one) is required; `pl.load("sweep.bin", layout={...})` for a
  single file.
- DICOM series are split per folder, not per `SeriesInstanceUID`; a folder
  mixing series loads as one series (the largest) through SimpleITK.
- `.vti` headers are read fully (no header-only reader), so the scan of a
  large VTK folder takes a moment.
- Pairing heuristics are deliberately simple; when the folder layout is
  unusual, write the `samples` list in the manifest by hand.
