# Template: a new example (pipeline)

One folder under `examples/`, titled `<algorithm or model> on <dataset>`. The script must be self-contained: it loads a bundled dataset, runs one algorithm or model, writes one image and a JSON summary next to itself, and prints the key numbers.

```
examples/<slug>/
  run.py          # this template, filled
  README.md       # the block below, filled
  <slug>.png      # written by run.py, committed
  result.json     # written by run.py, committed
```

README block:

```markdown
# <Algorithm or model> on <dataset>

| | |
|---|---|
| Dataset | `<name>` (<size>, <licence>) |
| Call | `<the one-liner or the script>` |
| Runtime, cold | <seconds> on <hardware> |
| What the defaults handled | <the data characteristics> |
| Result | <the metric with its unit> |

![alt text](<slug>.png)

`python examples/<slug>/run.py`
```

Then: a row in `examples/README.md`, a card in the README gallery if it is one of the twelve strongest, `pytest -q tests/test_scripts_help.py` (every script's `--help` must work), a CHANGELOG line. Large outputs (`.ply`, `.stl`, `.npz`, `.pt`, folders) are ignored by `.gitignore`; images and `result.json` are committed.
