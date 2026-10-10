"""Exceptions raised by the local package.

Everything derives from :class:`PardesLineError`, which is shared with the
cloud client so one ``except pl.PardesLineError`` covers both.
"""

from __future__ import annotations

from .cloud.errors import PardesLineError

__all__ = [
    "CatalogError",
    "MissingDependency",
    "ParameterError",
    "PardesLineError",
    "RunError",
]


class CatalogError(PardesLineError, KeyError):
    """Unknown module or method."""

    def __init__(self, message: str):
        PardesLineError.__init__(self, message, code="catalog_error")

    def __str__(self) -> str:  # KeyError quotes its message; we want prose
        return self.message


class ParameterError(PardesLineError, ValueError):
    """A parameter is unknown, has the wrong type, or is out of range."""

    def __init__(self, message: str):
        PardesLineError.__init__(self, message, code="parameter_error")


class MissingDependency(PardesLineError, ImportError):
    """A native library needed by this call is not installed."""

    def __init__(self, library: str, extra: str):
        PardesLineError.__init__(
            self,
            f"{library} is not installed. Install it with:  pip install 'pardesline[{extra}]'",
            code="missing_dependency",
        )
        self.library = library
        self.extra = extra


class RunError(PardesLineError, RuntimeError):
    """An algorithm exited with a non-zero code, timed out, or wrote no output."""

    def __init__(self, message: str, *, command: list[str], returncode: int | None, log: str):
        PardesLineError.__init__(self, message, code="run_error")
        self.command = command
        self.returncode = returncode
        self.log = log

    def __str__(self) -> str:
        tail = "\n".join(self.log.strip().splitlines()[-25:])
        cmd = " ".join(self.command)
        return f"{self.message}\n  command: {cmd}\n  log (last lines):\n" + "\n".join(
            f"    {line}" for line in tail.splitlines()
        )
