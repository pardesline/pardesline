# Inter-observer Dice and HD95 between three radiologists on one liver tumour CT

| | |
|---|---|
| Dataset | `liver_tumor_patient01` (2 MB) |
| What it shows | Dice 0.82–0.85, HD95 2.5 mm, surface Dice at 2 mm between three radiologists. |
| Extra dependencies | none beyond `pardesline[all]` |
| Cold runtime (Windows laptop, CPU) | 10 s |

Runs the ``evaluation-metrics-3d`` reference implementation on the
``liver_tumor_patient01`` dataset (2 MB, one CT and three expert masks): the
numbers show how far two experts are from each other, which is the ceiling
any segmentation model should be measured against.

```bash
pip install "pardesline[medical]"
python examples/metrics_liver_interobserver/run.py
```

Outputs are written next to this file; `result.json` and the images are committed, large files are ignored. See [`examples/README.md`](../README.md) for the full gallery.
