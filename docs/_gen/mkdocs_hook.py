"""mkdocs-gen-files hook: regenerate the dataset, algorithm, model and guide pages at build time.

Runs inside ``mkdocs build`` (plugin ``gen-files``). The generators write real
files under ``docs/`` so the pages are also readable on GitHub; this hook only
makes sure a build never ships stale pages.
"""

from __future__ import annotations

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
for script in ("datasets_pages.py", "algorithm_pages.py", "guides_pages.py"):
    runpy.run_path(str(HERE / script), run_name="__main__")
