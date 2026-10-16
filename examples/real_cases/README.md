# Real cases

The claims in the README ("defaults that work on real data") have to stay reproducible. The public datasets in `examples/` are stand-ins: a bunny with synthetic noise is not a cast part from a structured-light scanner, and the RIRE pair is one head. This folder is where real cases go, each one a folder with the data (or a loader for it), the script and the numbers.

## What a real case is

- Data that comes from a production setting: an industrial scan with its actual noise and partial coverage, a de-identified medical volume with the scanner's spacing and artefacts, a LiDAR sweep from the field. Synthetic-but-representative data is accepted if it is labelled as such in the README.
- A licence that allows redistribution (CC BY, CC0, Apache-2.0, or the owner's written permission in the folder), or a loader that fetches it from the owner's server with their terms attached. Files with identifiers are refused: de-identify before contributing (DICOM PS3.15 basic profile or equivalent).
- A `run.py` that loads the data, runs the pardesline call at its defaults, writes the output image and a `result.json` with the metrics, and prints what the defaults handled (spacing, noise level, overlap, intensity range).
- A `README.md` following the template below.

## Template

```
real_cases/<slug>/
  README.md        # the template below, filled
  run.py           # pl.load(...) or pl.scan(...), one call, metrics, image
  data/            # the files, or a manifest.json that points to them
  result.json      # written by run.py, committed
  <slug>.png       # written by run.py, committed
```

README template:

```markdown
# <Use case> on <data>

| | |
|---|---|
| Domain | industrial scanning / medical imaging / LiDAR / ... |
| Data | what it is, how it was acquired, size, spacing or point density |
| Licence | SPDX id or "owner permission, see PERMISSION.txt" |
| De-identification | n/a / method used |
| Algorithm | `module.method` or the high-level call |
| What the defaults handled | the characteristics that break textbook defaults |
| Result | the metric with its unit |
| Runtime | seconds, hardware |

## How to run
## What to look at in the image
## When you would override a default
```

## Contributing a case

1. Open an issue with the "Real case" template (or comment on the [real-cases tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Areal-case)) with the domain, the data and its licence.
2. Copy the template, run it, commit the outputs.
3. Add a row to the "Validated on real cases" table in the README with a link to your folder.

Cases are reviewed for licence, de-identification and reproducibility before merge; the numbers in the README come only from committed `result.json` files.
