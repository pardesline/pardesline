# Contributing to pardesline

Thank you for considering a contribution. The easiest and most useful ones are **a dataset manifest**, **an algorithm**, **a model manifest** and **an example**; each has a template and a checklist below. The rules exist to keep the package trustworthy for people who run it on data that matters.

## Ten-minute setup

```bash
git clone https://github.com/pardesline/pardesline
cd pardesline
python -m venv .venv && . .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[all,dev]"                            # Python 3.10-3.13 (Open3D 0.20) or 3.10-3.12 (0.19)
pre-commit install                                     # ruff on every commit (optional, CI runs it anyway)
pytest -q -m "not local and not medical"               # core tests, about a minute
pytest -q                                              # everything, about ten minutes
mkdocs serve                                           # docs at http://127.0.0.1:8000 (pip install mkdocs-material "mkdocstrings[python]" mkdocs-gen-files)
```

`ruff check .` and `ruff format .` must pass; `ruff format` also formats the Python blocks inside Markdown files.

## Pull request checklist

- [ ] One change per pull request, with a test.
- [ ] `ruff check .`, `ruff format --check .`, `pytest -q -m "not local and not medical"` green locally.
- [ ] No data in the repository: tests generate their inputs, examples download through `pl.load`.
- [ ] No silent guessing: when a format does not carry units, a frame or a label meaning, the code raises or asks.
- [ ] Every new parameter is in the catalog JSON with name, type, default, min, max, description, **and** in `src/pardesline/catalog/data/_defaults.json` with the reason for its default and the data it was validated on (`tests/test_catalog.py` enforces both).
- [ ] CLI contracts never change silently: every op under `pardesline.ops` is callable as `python -m pardesline.ops.<module>.<script> --input … --output …`; renaming or removing a flag is a breaking change with a CHANGELOG entry.
- [ ] A line in `CHANGELOG.md` under *Unreleased*.
- [ ] Commit messages: imperative, prefixed `feat:`, `fix:`, `docs:`, `ci:`, `tests:`, `release:`, body says what changed and what was verified.

## Adding a dataset

Copy [`templates/new_dataset/`](https://github.com/pardesline/pardesline/tree/main/templates/new_dataset) and follow its README. In short:

1. **Probe the source** before writing anything: Hugging Face tree (`HfApi().list_repo_tree`, scoped to a sub-folder, 1–2 s between calls), a zip or tar on S3 / Zenodo (`RemoteZip` / `RemoteTar` index it by HTTP Range), a TCIA collection (`getSeries`), an S3 bucket, a URL index. Record the licence exactly as the source states it, with the date you checked.
2. **Write the manifest** `src/pardesline/data/manifests/<name>.json`: `source` (scheme and location), `roles` with `type`, `pattern` (`{id}` and other placeholders), `frame`, `units`, `labels`, `layout` for raw arrays, `modality`; `license` (`spdx`, `commercial`, `redistribution`, `requires_agreement`, `note`, `source_url`); `citation`, `homepage`, `pairing`, `size_mb`, `tags`. Never embed data; never guess what the files do not say.
3. **Verify offline**: `pytest -q tests/test_manifest.py tests/test_skills.py`.
4. **Verify live**: `python -c "import pardesline as pl; ds = pl.load('<name>'); print(len(ds.ids)); print(ds[0].describe())"` and fetch one small role. Compare the sample count with the source's own count.
5. **Wire it in**: the table in `docs/datasets.md` and the `datasets-and-manifests` skill, `docs/_gen/datasets_table.py` picks it up for the README, the docs page is generated at build time. Add the name prefix to `tests/test_skills.py` if it is new.

What is not accepted: mirrored data, loaders that bypass a gate or a data-use agreement, licences copied from memory.

## Adding an algorithm

Copy [`templates/new_algorithm/`](https://github.com/pardesline/pardesline/tree/main/templates/new_algorithm). In short:

1. **Script** `src/pardesline/ops/<module>/<name>.py`: `argparse` with `--input`, `--output` (and `--moving` for two-input methods), typed flags for every parameter, exit 0 on success, logs through loguru, a JSON next to the output when the method returns numbers (transforms, metrics).
2. **Catalog entry** in `src/pardesline/catalog/data/<module>.json`: the method with `id`, `name`, `script`, `output_extension` and every parameter (`name`, `type`, `default`, `min`, `max`, `options`, `description`, `advanced`).
3. **Defaults rationale** in `_defaults.json`: `validated_on` for the method and one sentence per parameter saying why the default is what it is and when to change it. Run the method on a bundled dataset and write what you measured; "generated test data" is an acceptable regime when that is the truth.
4. **Tests**: a smoke test in `tests/test_ops_smoke.py` on generated data; `tests/test_catalog.py` checks the catalog and the script agree.
5. **High-level call** when it fits the object model (`align`, `segment`, `to_mesh`, `clean`…): `src/pardesline/object/__init__.py`, with a docstring.
6. **Docs**: the algorithm page is generated; add a how-to page under `docs/how-to/` if the method answers a question people search for, and an example under `examples/` if it runs on a bundled dataset.

## Adding a model manifest

The model registry (one-line access to pretrained models, the same pattern as datasets) is on the roadmap; model manifests can be contributed now so the runner has something to load when it lands. Copy [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model): a `manifest.json` (source, weights URI, licence, input type, task, memory and GPU needs, provenance, citation), a loader stub that says what it would download and how it would be called, and a docs page under `docs/models/`. List it on the [Models wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Amodel) issue.

Reference scripts that read a pardesline dataset and run a model today (as the PointNet, JEPA, VAE and DINOv3 scripts do) go under the matching skill's `scripts/` folder with a `--smoke` mode and are documented in the skill.

## Adding an example

Copy [`templates/new_pipeline/`](https://github.com/pardesline/pardesline/tree/main/templates/new_pipeline): one folder under `examples/`, a `run.py` that loads a bundled dataset, runs one algorithm or model, writes one image and a JSON summary, and a `README.md` with the dataset, the licence, the runtime and what the defaults handled. Title it `<algorithm or model> on <dataset>`, run it, commit the image and the summary (large outputs are ignored by `.gitignore`), add a row to `examples/README.md` and a card to the README gallery.

Real industrial or medical cases go to `examples/real_cases/` with the data or a loader for it, de-identified by you, under a licence that allows redistribution.

## Adding a skill (expert guide)

`skills/<name>/SKILL.md` with front matter (`name`, `description` between 200 and 1 500 characters), the structure of the existing skills (idea, pipeline, parameters by name, metrics, failure modes, datasets to practise on), optional `scripts/`. `tests/test_skills.py` checks that every `module.method`, `pl.<name>` and dataset name you cite exists. The page under `docs/guides/` or `docs/models/` is generated.

## Reporting a bug

Open an issue with the template: the snippet or command, the full log, `pardesline version`, and the versions of Open3D, PyVista and SimpleITK if relevant. Security issues: see [SECURITY.md](https://github.com/pardesline/pardesline/blob/main/SECURITY.md).

## Release process (maintainers)

1. Reproduce the CI locally in a clean venv (`ruff`, core tests on the newest Python).
2. Bump `src/pardesline/_version.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`; date the CHANGELOG section and its compare links; update the README status line.
3. Commit `release: X.Y.Z`, tag `vX.Y.Z`, push both.
4. Publish a GitHub release from the tag: the `publish.yml` workflow uploads to PyPI through Trusted Publishing and the `docs.yml` workflow deploys the versioned documentation.
5. Verify `pip install pardesline==X.Y.Z` in a fresh venv.

## Licence

By contributing you agree that your contribution is licensed under the Apache License 2.0, like the rest of the project. Datasets you describe keep their own licences, which your manifest must state as the source states them.
