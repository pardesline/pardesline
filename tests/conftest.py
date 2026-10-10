from __future__ import annotations

import importlib.util

import pytest

HAS_LOCAL = all(importlib.util.find_spec(m) is not None for m in ("open3d", "pyvista"))
HAS_MEDICAL = importlib.util.find_spec("SimpleITK") is not None


def pytest_collection_modifyitems(config, items):
    skip_local = pytest.mark.skip(reason="needs pip install 'pardesline[local]'")
    skip_medical = pytest.mark.skip(reason="needs pip install 'pardesline[medical]'")
    for item in items:
        if "local" in item.keywords and not HAS_LOCAL:
            item.add_marker(skip_local)
        if "medical" in item.keywords and not HAS_MEDICAL:
            item.add_marker(skip_medical)


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """Route default outputs of every run into the test's temp folder."""
    import pardesline as pl

    d = tmp_path / "outputs"
    pl.set_output_dir(d)
    yield d
    monkeypatch.setattr(pl.runner, "_output_dir", None, raising=False)
