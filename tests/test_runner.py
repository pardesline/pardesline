"""The runner builds the right command and reports failures clearly.
These tests do not need the native libraries."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

import pardesline as pl
from pardesline.catalog import Method, Parameter
from pardesline.runner import _stream, build_command


def test_build_command_matches_the_platform_contract(tmp_path):
    m = pl.catalog().method("simpleitk_registration", "rigid")
    cmd = build_command(m, Path("ct.mha"), Path("out.vti"), {"num_iterations": "50"}, Path("mr.mha"))
    assert cmd[:3] == [sys.executable, "-m", "pardesline.ops.simpleitk_registration.rigid_registration"]
    assert cmd[3:] == [
        "--input",
        "ct.mha",
        "--output",
        "out.vti",
        "--moving",
        "mr.mha",
        "--num_iterations",
        "50",
    ]


def test_run_rejects_bad_calls(tmp_path):
    f = tmp_path / "scan.ply"
    f.write_bytes(b"ply\n")
    with pytest.raises(FileNotFoundError):
        pl.run("point_cloud_processing", "voxel_downsample", tmp_path / "missing.ply")
    with pytest.raises(pl.ParameterError, match=r"does not accept '\.ply'"):
        pl.run("simpleitk_segmentation", "otsu_threshold", f)
    with pytest.raises(pl.ParameterError, match="pass moving="):
        pl.run("registration", "icp_refinement", f)
    with pytest.raises(pl.ParameterError, match="takes a single input"):
        pl.run("point_cloud_processing", "voxel_downsample", f, moving=f)
    with pytest.raises(pl.ParameterError, match="unknown parameter"):
        pl.run("point_cloud_processing", "voxel_downsample", f, voxel=0.1)
    with pytest.raises(pl.ParameterError, match="given twice"):
        pl.run("point_cloud_processing", "voxel_downsample", f, params={"voxel_size": 0.1}, voxel_size=0.2)
    with pytest.raises(pl.ParameterError, match=r"must end with '\.ply'"):
        pl.run("point_cloud_processing", "voxel_downsample", f, output=tmp_path / "out.obj")
    with pytest.raises(pl.CatalogError):
        pl.run("nope", "voxel_downsample", f)


def test_run_positional_shift(tmp_path, monkeypatch):
    """run('module.method', input, output) is accepted."""
    f = tmp_path / "scan.ply"
    f.write_bytes(b"ply\n")
    seen = {}

    def fake_stream(cmd, timeout, on_log, on_progress, cwd):
        seen["cmd"] = cmd
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"ok")
        return 0, "PROGRESS:50\nhello", False

    monkeypatch.setattr(pl.runner, "_stream", fake_stream)
    res = pl.run("point_cloud_processing.voxel_downsample", f, tmp_path / "o.ply", voxel_size=0.1)
    assert res.output == tmp_path / "o.ply"
    assert seen["cmd"][-2:] == ["--voxel_size", "0.1"]
    assert res.provenance()["method"] == "voxel_downsample"
    assert res.provenance()["pardesline"] == pl.__version__
    with pytest.raises(pl.ParameterError, match="at most two files"):
        pl.run("point_cloud_processing.voxel_downsample", f, tmp_path / "o.ply", tmp_path / "x.ply")


def _fake_method(tmp_path, body: str) -> Method:
    """A Method whose python_module points at a throwaway script."""
    pkg = tmp_path / "fakeops"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "script.py").write_text(textwrap.dedent(body))
    m = Method(
        id="fake",
        name="Fake",
        module_id="fake",
        script="script.py",
        output_extension=".txt",
        parameters=(Parameter(name="n", type="int", default=1),),
    )
    return m


def test_stream_captures_log_progress_and_exit_code(tmp_path):
    m = _fake_method(
        tmp_path,
        """
        import argparse, sys
        p = argparse.ArgumentParser()
        p.add_argument("--input"); p.add_argument("--output"); p.add_argument("--n", type=int)
        a = p.parse_args()
        print("PROGRESS:10", flush=True)
        print("working", flush=True)
        print("oops", file=sys.stderr, flush=True)
        open(a.output, "w").write("x" * a.n)
        sys.exit(3 if a.n == 3 else 0)
        """,
    )
    cmd = [
        sys.executable,
        "fakeops/script.py",
        "--input",
        "i",
        "--output",
        str(tmp_path / "o.txt"),
        "--n",
        "2",
    ]
    logs, progress = [], []
    code, log, timed_out = _stream(cmd, 30, logs.append, progress.append, cwd=tmp_path)
    assert (code, timed_out) == (0, False)
    assert progress == [10]
    assert logs == ["working", "oops"]  # stderr is merged, PROGRESS lines are not logged
    assert "working" in log and "PROGRESS" in log
    assert (tmp_path / "o.txt").read_text() == "xx"
    assert m.param_names == ("n",)


def test_stream_timeout(tmp_path):
    cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    _code, _log, timed_out = _stream(cmd, 1, None, None, None)
    assert timed_out


def test_run_error_message_shows_log_tail():
    err = pl.RunError(
        "x failed (exit code 2).", command=["py", "-m", "x"], returncode=2, log="a\nb\nTraceback: boom"
    )
    text = str(err)
    assert "exit code 2" in text and "command: py -m x" in text and "Traceback: boom" in text
    assert err.code == "run_error"
