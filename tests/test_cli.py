from __future__ import annotations

import pytest

from pardesline import __version__
from pardesline.cli import _parse_params, main


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_list_and_filters(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "point_cloud_processing" in out and "voxel_downsample" in out
    assert main(["list", "--ext", "mha"]) == 0
    out = capsys.readouterr().out
    assert "simpleitk_registration" in out and "point_cloud_processing" not in out
    assert main(["list", "--category", "sdf"]) == 0


def test_describe(capsys):
    assert main(["describe", "point_cloud_reconstruction.poisson"]) == 0
    assert "depth" in capsys.readouterr().out
    assert main(["describe", "nope"]) == 1
    assert "Unknown module" in capsys.readouterr().err


def test_parse_params():
    assert _parse_params(["--a", "1", "--b=x", "--c", "true"]) == {"a": "1", "b": "x", "c": "true"}
    with pytest.raises(SystemExit, match="needs a value"):
        _parse_params(["--flag"])
    with pytest.raises(SystemExit, match="unexpected argument"):
        _parse_params(["stray"])


def test_run_reports_errors_as_exit_1(tmp_path, capsys):
    f = tmp_path / "a.ply"
    f.write_bytes(b"ply")
    assert main(["run", "point_cloud_processing.voxel_downsample", str(f), "--voxel", "1"]) == 1
    assert "unknown parameter" in capsys.readouterr().err
    assert main(["run", "point_cloud_processing.voxel_downsample", str(tmp_path / "missing.ply")]) == 1
