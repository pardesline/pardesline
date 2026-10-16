---
title: "<Model> for <task> on <modality> in Python"
description: "What the model does, what it takes and returns, its licence, and how to run it today with its own tooling; one-line access through the pardesline model registry is coming."
---

# <Model> for <task> on <modality>

!!! info "Status"
    Reference facts and the manifest today; `pl.load_model("<name>")` when the registry ships. This page keeps its URL.

| | |
|---|---|
| Task | segmentation / detection / features / ... |
| Input | `volume` (CT, 1.5 mm isotropic, HU) |
| Output | `labels` with named labels |
| Weights | <where>, <licence>, gated: yes / no |
| Runtime | torch >= 2.2, GPU optional, 4 GB |
| Paper | <citation> |
| Validated on | <bundled dataset>, <metric> |

## Run it today

```bash
# prepare a pardesline dataset in the model's layout, run the model's own CLI, load the result back
```

## What the manifest says

Link to `models/<name>/manifest.json`.

## Limits and failure modes

Spacing outside the training range, contrast phase, cropping, label definitions.
