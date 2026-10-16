# Template: a model manifest

The model registry (one-line access to pretrained 3D and medical models, the same pattern as datasets: `pl.load_model("name")` then `pl.run(model, dataset)`) is the top roadmap item. It does not exist yet. What can be written now, so the runner has something to load when it lands, is the **manifest**: where the weights are, under which licence, what the model takes and returns, what it needs to run, where it came from.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | the facts, with every field explained inline |
| `loader_stub.py` | what the loader will do: download, instantiate, preprocess, postprocess; runs `--dry-run` today and prints the plan |
| `docs_page.md` | the page under `docs/models/<name>.md`: task, inputs, outputs, licence, how to run it today with the model's own tooling |

## Rules

- Licence of the weights, copied from the model card or the repository, with the date. Gated weights (DINOv3) must say so; the loader will use the user's own token.
- Input type in pardesline terms (`volume`, `labels`, `points`, `mesh`, `image`), with spacing / size expectations; output type the same way (a `LabelMap` with named labels, a feature array with its shape).
- Memory and GPU needs measured, not guessed (`nvidia-smi` peak, or "CPU, 2 GB RAM for a 256^3 volume").
- Provenance: paper, repository, commit or version, who trained it on what.
- No weights in the repository.

Open an issue with the "Algorithm or model request" form or add the manifest to the [Models wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Amodel) list; put the files under `models/<name>/` in your pull request.
