## What this changes

<!-- One paragraph. Link the issue: "Closes #123". -->

## Kind of change

- [ ] dataset manifest (`src/pardesline/data/manifests/`)
- [ ] algorithm (`src/pardesline/ops/` + catalog JSON + `_defaults.json`)
- [ ] model manifest (`templates/new_model` pattern)
- [ ] example (`examples/`)
- [ ] skill / docs
- [ ] bug fix
- [ ] other

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pytest -q -m "not local and not medical"` passes locally
- [ ] a test covers the change (generated data, no files committed)
- [ ] every new parameter is in the catalog JSON **and** in `_defaults.json` with its rationale and validation regime
- [ ] for a dataset: licence copied from the source with the date checked; one sample fetched live; sample count matches the source
- [ ] for an algorithm: CLI contract (`--input`, `--output`, flags) documented; smoke test added
- [ ] `CHANGELOG.md` has a line under *Unreleased*
- [ ] no data, weights or secrets in the diff

## How I verified it

<!-- Commands run and what they printed. Images welcome for anything visual. -->
