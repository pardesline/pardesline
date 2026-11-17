---
name: contributing-algorithms
description: >-
  How the pardesline repository is organised and how to extend it without breaking
  the contracts: adding an algorithm (script under `src/pardesline/ops/<module>/`
  following the argparse `--input/--output[/--moving]` contract, its entry in
  `src/pardesline/catalog/data/<module>.json` with typed parameters, a smoke test),
  adding a bundled dataset manifest (`src/pardesline/data/manifests/`, SHA-512, licence
  tiers), the test layers (fast / local / medical / slow / network markers, the 73
  `--help` checks, catalog-script consistency), ruff rules and which migrated code is
  exempt, CI matrix and PyPI Trusted Publishing, the source-of-truth relationship with
  the hosted platform, and the gotchas already hit (hatchling honours .gitignore,
  positional-only run args, VTI needs PyVista). Use for any change to the package itself.
---

# Contributing to the package

## Layout

```
src/pardesline/
  _version.py            single version source (hatchling reads it)
  __init__.py            public API; cloud helpers and pl.o3d/pv/sitk/np resolved lazily
  errors.py              PardesLineError (shared with cloud) + Catalog/Parameter/Run/Manifest/Fetch/NeedsConfirmation
  catalog/               Catalog, Module, Method, Parameter + data/<module>.json (19 files, the 73 methods)
  runner.py              pl.run: validation, subprocess, log/progress capture, RunResult
  object/                Object classes, frame.py (Frame, License, format defaults), convert.py (in-process conversions)
  data/                  manifest.py (pydantic schema incl. Layout), dataset.py (+ export), scan.py (folders and listings), cache.py, sources/{local,https,hf,archive,s3,tcia,urllist,open3d}.py, manifests/*.json
  object/arrays.py       raw .npy/.npz/.bin decoding through a layout; pure-NumPy PLY writer; grid -> MetaImage
  ops/<module>/*.py      the 73 scripts, byte-identical to the hosted platform's modules/*/scripts
  medical/               _service.py + pyvista_adapter.py (the platform's SimpleITK service), public re-exports
  cloud/                 the 0.1.0 cloud client, verbatim
tests/                   fast tests + ops smoke tests + 73 --help checks + network tests
skills/                  these skills (installable as a Claude Code plugin)
```

The hosted platform's `modules/` folder and services are the **source of
truth** for `ops/`, `catalog/data/` and `medical/` until the platform
depends on this package; those files are excluded from ruff and must stay
byte-identical (only the ten SimpleITK scripts have their import rewired to
`pardesline.medical._service`). Edit algorithms upstream, or deliberately
fork here and document it in CHANGELOG.

## Adding an algorithm

1. `src/pardesline/ops/<module>/<name>.py`: argparse with `--input`,
   `--output`, optional `--moving`, typed flags for every parameter (`_b` helper
   for booleans accepting `true/false`), loguru logging, `sys.exit(1)` on
   failure, `if __name__ == "__main__": main()`. Lists arrive as `"4,2,1"`
   strings, enums as their option text, booleans as `true`/`false`. Print
   `PROGRESS:NN` for long runs. Write the output at `--output` exactly; a
   registration op writes `<output>.json` beside it.
2. Catalog entry in `src/pardesline/catalog/data/<module>.json`:
   `{"id", "name", "script", "output_extension", "dual_input"?, "parameters": [
   {"name", "type": float|int|bool|enum|string|list, "default", "description",
   "min"?, "max"?, "options"? (enum), "advanced"?}]}`. Parameter names must not
   be `output`, `moving`, `params`, `timeout`, `python`, `on_log`,
   `on_progress`, `cwd`. Every parameter needs a description and a default
   that passes its own range; `tests/test_catalog.py` checks that each
   `--name` exists in the script (shared registration flags may live in
   `medical/_service.py`).
3. A smoke test in `tests/test_ops_smoke.py` on generated data, marked
   `local` or `medical`. `tests/test_scripts_help.py` will run `--help` on it.
4. Update the module table in README.md and the catalog-and-run skill.

## Adding a bundled dataset

1. `src/pardesline/data/manifests/<name>.json`: explicit `samples` for a
   small `https` / `open3d` excerpt, or a `pattern` per role for a hub repo
   or a remote archive; `license` (SPDX id, `commercial`, `source_url`,
   `note` ending in `TO CONFIRM` when the terms were not established),
   `citation`, `size_mb`, `tags`. Names: `hf_*` for Hub repos, otherwise the
   dataset's usual short name.
2. `https` files need the SHA-512 (or the upstream md5) of the download;
   archives need `archive: true` and the member path as the key.
   `hf` sources **must** scope the listing with `paths` (a whole 100k-file
   repo is rate-limited before it is listed); check the real tree with
   `HfApi().list_repo_tree(repo, path_in_repo=..., repo_type="dataset")`.
   `archive` sources need a `url` (or `urls`) whose server honours Range
   requests (probe with a `Range: bytes=0-0` GET -> 206); `s3` sources a
   bucket that allows anonymous ListObjectsV2; `tcia` sources the exact
   NBIA collection name (`getCollectionValues`).
   Any `.npy/.npz/.bin` role needs its `layout`; verify it on one real file.
   Record in the description what was measured (index size, fetch time).
3. `tests/test_manifest.py` validates every bundled manifest offline
   (patterns, layouts, licence id, `paths` for hf); add a network test in
   `tests/test_network.py` (`PARDESLINE_NETWORK_TESTS=1`) that lists the
   dataset and fetches its smallest member.
4. Mention it in README (Datasets), CHANGELOG and the datasets skill.

## Tests

```bash
pytest -q -m "not slow"                      # ~1 min: catalog, params, runner, object, manifests, scan, https (local server), cloud unit
pytest -q                                    # + ops smoke (real Open3D/PyVista/SimpleITK runs) + 73 --help checks (~6 min)
PARDESLINE_NETWORK_TESTS=1 pytest tests/test_network.py   # real downloads (RIRE 19 MB, liver, Open3D bunny)
ruff check . && ruff format --check .
```

Markers: `local` (skips without Open3D+PyVista), `medical` (without
SimpleITK), `slow`, `network`. The `conftest.py` fixture `out_dir` routes
`pl.output_dir()` into the test's temp folder. The https source is tested
against a `ThreadingHTTPServer` in-process (hash mismatch, mirrors, archives,
cache reuse).

## CI and release

`.github/workflows/ci.yml`: lint; core tests on 3.10 and 3.13 without
native libs (`-m "not local and not medical"`); full tests on Ubuntu /
Windows / macOS with 3.10 and 3.12 (`apt` installs libgl1, libegl1,
libusb-1.0-0 for Open3D); build + `twine check`. `publish.yml` uses PyPI
Trusted Publishing on a GitHub release (environment `pypi`, no token).
Bump `_version.py` and CHANGELOG, tag `vX.Y.Z`, create the release.

## Gotchas already paid for

- hatchling honours `.gitignore`: a `data/` pattern once dropped
  `catalog/data/*.json` from the wheel. Use anchored patterns (`/data/`).
  Always inspect the wheel (`zipfile`) before a release.
- A catalog parameter is named `method` (`pv_contour`): `pl.run` and
  `Object.run` take `module`, `method`, `input` positional-only.
- `[medical]` needs PyVista: SimpleITK cannot read `.vti`, every SimpleITK op
  writes `.vti`.
- Child processes: set `LOGURU_COLORIZE=False` and strip ANSI; keep
  user-facing strings ASCII (em-dashes and ellipses turn into `?` on Windows
  pipes).
- Open3D 0.19 has no Python 3.13 wheels; pin `open3d>=0.18,<0.20`
  (0.20 broke headless Linux: libEGL/libusb).
- `.txt` is an accepted point-cloud extension for ops but too ambiguous for
  `pl.scan`, which skips it.
