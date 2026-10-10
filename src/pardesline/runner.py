"""Run one algorithm from the catalog as a subprocess, on this machine.

Each op is an argparse script (``python -m pardesline.ops.<module>.<script>
--input … --output … [--flag value …]``). Running it in a child process keeps
the exact contract the platform uses and isolates native-library crashes
from the caller.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from .catalog import Method, load_catalog
from .errors import ParameterError, RunError

__all__ = ["RunResult", "output_dir", "run", "set_output_dir"]

DEFAULT_TIMEOUT = 600
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")  # colour codes a child logger may emit
_output_dir: Path | None = None


def output_dir() -> Path:
    """Where runs write their result when no ``output`` is given.
    Defaults to ``<system temp>/pardesline-outputs``; change it with
    :func:`set_output_dir`."""
    global _output_dir
    if _output_dir is None:
        _output_dir = Path(tempfile.gettempdir()) / "pardesline-outputs"
    _output_dir.mkdir(parents=True, exist_ok=True)
    return _output_dir


def set_output_dir(path: str | os.PathLike) -> Path:
    global _output_dir
    _output_dir = Path(path).expanduser().resolve()
    _output_dir.mkdir(parents=True, exist_ok=True)
    return _output_dir


@dataclass
class RunResult:
    """What a run produced."""

    method: Method
    output: Path
    input: Path
    moving: Path | None
    params: dict[str, str]
    command: list[str]
    log: str
    duration_s: float
    sidecar: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def provenance(self) -> dict[str, Any]:
        from ._version import __version__

        return {
            "module": self.method.module_id,
            "method": self.method.id,
            "params": dict(self.params),
            "input": str(self.input),
            "moving": str(self.moving) if self.moving else None,
            "output": str(self.output),
            "duration_s": round(self.duration_s, 3),
            "pardesline": __version__,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }


def _default_output(method: Method, input_path: Path) -> Path:
    stem = input_path.stem[:48] or "result"
    return output_dir() / f"{stem}_{method.id}_{uuid.uuid4().hex[:8]}{method.output_extension}"


def build_command(
    method: Method,
    input_path: Path,
    output_path: Path,
    params: dict[str, str],
    moving_path: Path | None = None,
    python: str | None = None,
) -> list[str]:
    cmd = [
        python or sys.executable,
        "-m",
        method.python_module,
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    if moving_path is not None:
        cmd += ["--moving", str(moving_path)]
    for key, value in params.items():
        cmd += [f"--{key}", value]
    return cmd


def _stream(cmd: list[str], timeout: float, on_log, on_progress, cwd) -> tuple[int | None, str, bool]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("MPLBACKEND", "Agg")
    env.setdefault("PYVISTA_OFF_SCREEN", "true")
    env.setdefault("LOGURU_COLORIZE", "False")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd)
    timed_out = False

    def _kill() -> None:
        nonlocal timed_out
        timed_out = True
        proc.kill()

    timer = threading.Timer(timeout, _kill)
    timer.daemon = True
    timer.start()
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = _ANSI.sub("", raw.decode("utf-8", errors="replace")).rstrip("\r\n")
            lines.append(line)
            stripped = line.strip()
            if stripped.startswith("PROGRESS:"):
                try:
                    pct = int(stripped.split(":", 1)[1])
                except ValueError:
                    pct = None
                if pct is not None and on_progress is not None:
                    on_progress(pct)
                continue
            if on_log is not None:
                on_log(line)
            else:
                logger.opt(depth=0).debug("[{}] {}", cmd[2].rsplit(".", 1)[-1], line)
        proc.wait()
    finally:
        timer.cancel()
    return proc.returncode, "\n".join(lines), timed_out


def run(
    module: str,
    method: str | None = None,
    input: str | os.PathLike | None = None,
    /,
    output: str | os.PathLike | None = None,
    *,
    moving: str | os.PathLike | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    python: str | None = None,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[int], None] | None = None,
    cwd: str | os.PathLike | None = None,
    **kwargs: Any,
) -> RunResult:
    """Run one algorithm on a local file and return a :class:`RunResult`.

    ``run("point_cloud_processing", "voxel_downsample", "scan.ply", voxel_size=0.05)``
    or ``run("point_cloud_processing.voxel_downsample", "scan.ply", ...)``.

    Parameters go as keyword arguments (or in ``params``); they are validated
    against the catalog before anything runs. The first three arguments are
    positional-only, so a parameter that happens to be called ``method`` or
    ``input`` can still be passed by keyword. Two-input methods (registration)
    take the moving file through ``moving``. The result is written to
    ``output`` or to :func:`output_dir`. Raises :class:`ParameterError` or
    :class:`RunError`.
    """
    if "." in module and method is not None:
        # run("mod.meth", input[, output]) — shift the positional arguments
        if output is not None:
            raise ParameterError("run('module.method', input, output) takes at most two files.")
        module, method, input, output = module, None, method, input
    spec = load_catalog().method(module, method)
    if input is None:
        raise ParameterError(f"{spec.qualname}: an input file is required.")
    input_path = Path(input).expanduser()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    mod = load_catalog().module(spec.module_id)
    if not mod.accepts(input_path.suffix):
        raise ParameterError(
            f"{spec.qualname} does not accept {input_path.suffix!r} files. "
            f"Accepted: {', '.join(mod.input_formats)}."
        )
    moving_path: Path | None = None
    if spec.dual_input:
        if moving is None:
            raise ParameterError(
                f"{spec.qualname} aligns two inputs: pass moving=<file> "
                "(input is the fixed reference, moving is the one to transform)."
            )
        moving_path = Path(moving).expanduser()
        if not moving_path.is_file():
            raise FileNotFoundError(f"Moving file not found: {moving_path}")
    elif moving is not None:
        raise ParameterError(f"{spec.qualname} takes a single input; 'moving' is not accepted.")

    merged = dict(params or {})
    for k, v in kwargs.items():
        if k in merged:
            raise ParameterError(f"{spec.qualname}: parameter {k!r} given twice.")
        merged[k] = v
    cli_params = spec.validate(merged)

    output_path = Path(output).expanduser() if output is not None else _default_output(spec, input_path)
    if output_path.suffix.lower() != spec.output_extension.lower():
        raise ParameterError(
            f"{spec.qualname} writes {spec.output_extension} files; "
            f"output must end with {spec.output_extension!r} (got {output_path.suffix!r})."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_command(spec, input_path, output_path, cli_params, moving_path, python)
    logger.info("run {} on {}", spec.qualname, input_path.name)
    t0 = time.perf_counter()
    returncode, log, timed_out = _stream(cmd, timeout, on_log, on_progress, cwd)
    duration = time.perf_counter() - t0
    if timed_out:
        raise RunError(
            f"{spec.qualname} timed out after {timeout:.0f}s.", command=cmd, returncode=None, log=log
        )
    if returncode != 0:
        raise RunError(
            f"{spec.qualname} failed (exit code {returncode}).", command=cmd, returncode=returncode, log=log
        )
    if not output_path.is_file():
        raise RunError(
            f"{spec.qualname} exited 0 but wrote no output at {output_path}.",
            command=cmd,
            returncode=returncode,
            log=log,
        )
    sidecar = output_path.with_suffix(".json")
    if not sidecar.is_file():
        sidecar = None
    logger.info("done {} in {:.1f}s -> {}", spec.qualname, duration, output_path)
    return RunResult(
        method=spec,
        output=output_path,
        input=input_path,
        moving=moving_path,
        params=cli_params,
        command=cmd,
        log=log,
        duration_s=duration,
        sidecar=sidecar,
    )
