# 3D JEPA self-supervised pretraining on MSD hippocampus MRIs (reference implementation)

| | |
|---|---|
| Dataset | `msd_task04_hippocampus` |
| What it shows | 3D JEPA pretraining, laptop-sized configuration. |
| Extra dependencies | torch |
| Cold runtime (Windows laptop, CPU) | minutes |

Runs ``jepa3d_pretrain.py`` from the ``jepa-pretraining`` skill on eight
hippocampus volumes: context encoder (3D ViT) -> predictor -> L2 against an
EMA target encoder on masked blocks. Sizes are reduced so it runs on a laptop;
the real recipe (crop 96, dim 384, 100 epochs) is in the skill.

```bash
pip install "pardesline[all]" torch
python examples/jepa_hippocampus/run.py                 # small model, CPU, a few minutes
```

Outputs are written next to this file; `result.json` and the images are committed, large files are ignored. See [`examples/README.md`](../README.md) for the full gallery.
