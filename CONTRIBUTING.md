# Contributing to PardesLine

Thank you for considering a contribution. This document is short on purpose:
the rules below are the ones that keep the package trustworthy for the people
who run it on data that matters.

## Setting up

```bash
git clone https://github.com/pardesline/pardesline
cd pardesline
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[all,dev]"
pytest -q
```

Python 3.10 to 3.12 are supported with the native libraries (`[local]`,
`[medical]`). The core package also works on 3.13.

## What a good pull request looks like

- **One change per PR**, with a test. An algorithm change must keep its
  reference output test green or update it with a justification.
- **Never change a CLI contract silently.** Every op under `pardesline.ops`
  is callable as `python -m pardesline.ops.<module>.<script> --input … --output …`.
  Renaming or removing a flag is a breaking change and needs a CHANGELOG entry.
- **Parameters live in the catalog.** Add or edit the method's entry in
  `src/pardesline/catalog/data/<module>.json` (name, type, default, min, max,
  description) in the same PR as the script. `pytest tests/test_catalog.py`
  checks that the catalog and the scripts agree.
- **No silent guessing.** If a format does not carry units, a frame or a
  label meaning, the code raises or asks. It never assumes.
- **No data in the repository.** Tests generate their inputs; larger fixtures
  are downloaded on demand with a checksum.
- `ruff check .` and `ruff format .` must pass.

## Adding an algorithm

1. Create `src/pardesline/ops/<module>/<name>.py` following the contract
   (argparse `--input`, `--output`, typed flags, exit 0 on success, logs via
   loguru).
2. Register it in the module's JSON catalog file with every parameter.
3. Add a smoke test in `tests/test_ops_smoke.py` on generated data.

## Reporting a bug

Open an issue with the command or snippet, the full log, the package version
(`python -c "import pardesline; print(pardesline.__version__)"`) and the
versions of Open3D, PyVista and SimpleITK if relevant.

## Licence

By contributing you agree that your contribution is licensed under the
Apache License 2.0, like the rest of the project.
