"""Exceptions raised by the local package.

Everything derives from :class:`PardesLineError`, which is shared with the
cloud client so one ``except pl.PardesLineError`` covers both.
"""

from __future__ import annotations

from .cloud.errors import PardesLineError

__all__ = [
    "CatalogError",
    "FetchError",
    "ManifestError",
    "MissingDependency",
    "NeedsConfirmation",
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


class ManifestError(PardesLineError, ValueError):
    """A dataset manifest is missing, malformed or inconsistent."""

    def __init__(self, message: str):
        PardesLineError.__init__(self, message, code="manifest_error")


class FetchError(PardesLineError, OSError):
    """A dataset file could not be downloaded or failed its checksum."""

    def __init__(self, message: str):
        PardesLineError.__init__(self, message, code="fetch_error")


class NeedsConfirmation(PardesLineError):
    """A scanned folder has open questions (licence, units, labels...) that the
    package will not guess. ``.manifest`` is the draft, ``.questions`` the
    list; ``.draft_path`` is where it was saved, if it was."""

    def __init__(self, manifest, draft_path=None):
        self.manifest = manifest
        self.questions = list(manifest.questions)
        self.draft_path = draft_path
        lines = [f"{manifest.name}: {len(self.questions)} question(s) before this folder can be loaded:"]
        for q in self.questions:
            lines.append(f"  - {q.field}: {q.message}")
        lines.append("Answer in the call, e.g.")
        example = ["pl.load(folder"]
        if any(q.field == "license" for q in self.questions):
            example.append("license='internal, no redistribution'")
        units = [q.field.split(".")[1] for q in self.questions if q.field.endswith(".units")]
        if units:
            example.append("units={" + ", ".join(f"{r!r}: 'mm'" for r in units[:2]) + "}")
        frames = [q.field.split(".")[1] for q in self.questions if q.field.endswith(".frame")]
        if frames:
            example.append("frame={" + ", ".join(f"{r!r}: 'Z-up'" for r in frames[:2]) + "}")
        labels = [q.field.split(".")[1] for q in self.questions if q.field.endswith(".labels")]
        if labels:
            example.append("labels={" + ", ".join(f"{r!r}: {{1: 'organ'}}" for r in labels[:2]) + "}")
        layouts = [q.field.split(".")[1] for q in self.questions if q.field.endswith(".layout")]
        if layouts:
            example.append("types={" + ", ".join(f"{r!r}: 'points'" for r in layouts[:2]) + "}")
            example.append(
                "layout={"
                + ", ".join(
                    f"{r!r}: {{'dtype': 'float32', 'shape': '(N,4)', 'columns': ['x', 'y', 'z', 'i']}}"
                    for r in layouts[:2]
                )
                + "}"
            )
        lines.append("  " + ", ".join(example) + ")")
        lines.append(
            "or edit the saved draft, or pass assume=True to proceed with unknowns, or interactive=True."
        )
        if draft_path:
            lines.append(f"Draft saved: {draft_path}")
        PardesLineError.__init__(self, "\n".join(lines), code="needs_confirmation")
