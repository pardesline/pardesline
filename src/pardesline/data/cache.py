"""Where downloaded dataset files live.

``PARDESLINE_CACHE`` overrides the default ``~/.cache/pardesline``.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["cache_dir", "dataset_cache_dir", "set_cache_dir"]

_override: Path | None = None


def cache_dir() -> Path:
    """The root folder where datasets are cached.

    ``PARDESLINE_CACHE`` or :func:`set_cache_dir` override the default
    ``~/.cache/pardesline``. The folder is created on first use.

    Examples:
        >>> import pardesline as pl
        >>> pl.cache_dir().name
        'pardesline'
    """

    if _override is not None:
        root = _override
    elif os.environ.get("PARDESLINE_CACHE"):
        root = Path(os.environ["PARDESLINE_CACHE"]).expanduser()
    else:
        root = Path.home() / ".cache" / "pardesline"
    root.mkdir(parents=True, exist_ok=True)
    return root


def set_cache_dir(path: str | os.PathLike | None) -> Path:
    """Point the cache somewhere else (``None`` restores the default)."""
    global _override
    _override = Path(path).expanduser().resolve() if path is not None else None
    return cache_dir()


def dataset_cache_dir(name: str) -> Path:
    """The cache folder of one dataset (``<cache_dir>/datasets/<name>``), created if needed."""

    d = cache_dir() / "datasets" / name
    d.mkdir(parents=True, exist_ok=True)
    return d
