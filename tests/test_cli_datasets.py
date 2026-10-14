from __future__ import annotations

import numpy as np

import pardesline as pl
from pardesline.cli import main


def test_datasets_listing_and_describe(capsys):
    assert main(["datasets"]) == 0
    out = capsys.readouterr().out
    assert "msd_task02_heart" in out and "archive" in out and "CC-BY-NC-SA-3.0 (NC)" in out
    assert main(["datasets", "--scheme", "hf"]) == 0
    out = capsys.readouterr().out
    assert "hf_openmind" in out and "rire_brain" not in out
    assert main(["datasets", "--tag", "nothing-like-this"]) == 0
    assert "no bundled dataset" in capsys.readouterr().out
    assert main(["describe", "msd_task02_heart"]) == 0
    out = capsys.readouterr().out
    assert "left_atrium" in out and "CC-BY-SA-4.0" in out


def test_export_from_the_command_line(tmp_path, capsys):
    root = tmp_path / "study"
    d = root / "p01"
    d.mkdir(parents=True)
    np.zeros((3, 4), dtype=np.float32).tofile(d / "sweep.bin")
    ds = pl.load(
        root,
        license="CC0-1.0",
        types={"sweep": "points"},
        layout={"sweep": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
        units="m",
    )
    assert not ds.is_draft  # the answers were saved? no - the draft is confirmed in memory only
    ds.manifest.save(root / "pardesline.manifest.json")
    assert main(["export", str(root), str(tmp_path / "out"), "--take", "1"]) == 0
    assert "1 sample(s)" in capsys.readouterr().out
    assert (tmp_path / "out" / "p01" / "sweep.ply").is_file()
    assert main(["export", str(root), str(tmp_path / "out")]) == 1  # exists, no --overwrite
    assert "exists" in capsys.readouterr().err
    assert main(["fetch", str(root)]) == 0
    assert "1 file(s)" in capsys.readouterr().out
