"""The contribution templates stay valid: the dataset manifest template parses, the
model loader stub validates its manifest, the algorithm template has a CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import pardesline as pl

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _strip_private(obj):
    if isinstance(obj, dict):
        return {k: _strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_private(v) for v in obj]
    return obj


def test_new_dataset_manifest_template_is_a_valid_manifest():
    raw = json.loads((TEMPLATES / "new_dataset" / "manifest.json").read_text(encoding="utf-8"))
    m = pl.Manifest.from_dict(_strip_private(raw))
    assert m.name == "my_dataset_name" and m.source.scheme == "archive"
    assert set(m.roles) == {"ct", "mask"} and m.roles["mask"].labels == {1: "organ", 2: "tumor"}
    assert m.license.spdx == "CC-BY-4.0" and m.license.redistribution == "allowed"


def test_new_model_loader_stub_validates_the_template():
    out = subprocess.run(
        [
            sys.executable,
            str(TEMPLATES / "new_model" / "loader_stub.py"),
            str(TEMPLATES / "new_model" / "manifest.json"),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "my_model_name: segmentation on volume -> labels" in out.stdout
    assert "download from hf org/model-repo" in out.stdout


@pytest.mark.parametrize("script", ["new_algorithm/my_method.py", "new_dataset/live_check.py"])
def test_template_scripts_have_a_help(script):
    out = subprocess.run([sys.executable, str(TEMPLATES / script), "--help"], capture_output=True, text=True)
    assert out.returncode == 0 and "--" in out.stdout


def test_pipeline_template_compiles():
    # running it would download the bunny and write files into templates/: compile only
    import py_compile

    py_compile.compile(str(TEMPLATES / "new_pipeline" / "run.py"), doraise=True)


def test_issue_list_parses():
    sys.path.insert(0, str(ROOT / "docs" / "seo"))
    import apply_github

    issues = apply_github.parse_issues()
    titles = [i["title"] for i in issues]
    assert len(titles) == len(set(titles)) and len(issues) >= 30
    assert sum("good first issue" in i["labels"] for i in issues) >= 15
    assert sum("help wanted" in i["labels"] for i in issues) >= 10
    assert any(i["title"].startswith("Model registry") for i in issues)
