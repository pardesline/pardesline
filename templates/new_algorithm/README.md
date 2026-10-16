# Template: a new algorithm

An algorithm is a script with an `argparse` CLI under `src/pardesline/ops/<module>/`, an entry in the module's catalog JSON, a rationale for every default in `_defaults.json`, a smoke test, and (when it fits) a high-level call on the object model.

## Files in this template

| File | Copy to | What to change |
|---|---|---|
| `my_method.py` | `src/pardesline/ops/<module>/my_method.py` | the parameters, the body of `run()` |
| `catalog_entry.json` | merge into `src/pardesline/catalog/data/<module>.json` under `"methods"` | every parameter with type, default, min, max, description |
| `defaults_entry.json` | merge into `src/pardesline/catalog/data/_defaults.json` | `validated_on` and one sentence per parameter |
| `test_my_method.py` | `tests/test_ops_<module>_my_method.py` | generated input that exercises the method |

A new module (family) also needs a new `<module>.json` with `id`, `name`, `description`, `category`, `order`, `input_formats`, `dual_input`, `theory`.

## Contract

- `--input` (and `--moving` for two-input methods), `--output`, one flag per parameter with the catalog's name and default; exit 0 on success, a non-zero code with a clear message on failure; logs through loguru; progress lines `PROGRESS <percent>` are picked up by the runner.
- Write the output in the format declared by `output_extension`; write a JSON next to it (`<output>.json`) when the method produces numbers (transforms, metrics, counts): the object model exposes it as `obj.transform`.
- Keep the script importable without the native library at module level: import Open3D / SimpleITK inside `run()` so `pardesline list` works on the core install.
- Defaults must come with a reason: `_defaults.json` is enforced by `tests/test_catalog.py`. Run the method on a bundled dataset and write what you measured in `validated_on`; "generated test data" is the honest regime when that is all you ran.

## Then

- `pytest -q tests/test_catalog.py tests/test_ops_smoke.py tests/test_ops_<module>_my_method.py`
- `pl.describe("<module>.my_method")` reads well.
- A high-level call if the method is the natural one for an object type (`src/pardesline/object/__init__.py`, with a docstring), a how-to page if it answers a searched question, an example if it runs on a bundled dataset, a CHANGELOG line.
