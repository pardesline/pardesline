"""The open-source package is independent of the PardesLine platform: no client, no fallback to a
hosted service, no platform address in the code, the skills or the documentation it ships."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import httpx
import pytest

import pardesline as pl
from pardesline.errors import MissingDependency

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = re.compile(r"appbeta\.pardesline|api\.pardesline|pardesline\.cloud|PARDESLINE_API_KEY|pl\.login\b")
_real_import = importlib.import_module


@pytest.fixture
def no_open3d_no_network(monkeypatch):
    def fake_import(name, *args, **kwargs):
        if name == "open3d":
            raise ImportError("No module named 'open3d'")
        return _real_import(name, *args, **kwargs)

    def no_network(*args, **kwargs):
        raise AssertionError("pardesline made a network request on its own")

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(httpx.Client, "request", no_network)
    monkeypatch.setenv("PARDESLINE_API_KEY", "pl_ignored")  # a key from 0.5 changes nothing


def test_missing_library_fails_locally(no_open3d_no_network):
    o3d = pl.o3d
    assert hasattr(pl, "o3d")  # introspection still works
    assert "pardesline[local]" in repr(o3d)
    with pytest.raises(MissingDependency, match=r"open3d is not installed.*pardesline\[local\]"):
        o3d.io.read_point_cloud("scan.ply")
    with pytest.raises(MissingDependency):
        o3d()


@pytest.mark.parametrize("name", ["login", "upload", "share", "send", "cloud", "Client"])
def test_platform_client_names_are_gone_with_an_explanation(name):
    with pytest.raises(AttributeError, match=r"removed in pardesline 0.6"):
        getattr(pl, name)
    assert name not in dir(pl)


def test_there_is_no_platform_client_module():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("pardesline.cloud")


def test_cli_has_no_platform_commands(capsys):
    from pardesline.cli import main

    with pytest.raises(SystemExit):
        main(["login"])
    assert "invalid choice" in capsys.readouterr().err


def test_shipped_files_name_no_platform_address():
    folders = ["src/pardesline", "skills", "plugins", "docs/guides"]
    files = [ROOT / "README.md", ROOT / "PRIVACY.md", ROOT / "pyproject.toml", ROOT / "server.json"]
    for folder in folders:
        files += [p for p in (ROOT / folder).rglob("*") if p.suffix in {".py", ".md", ".json", ".toml"}]
    for path in files:
        text = path.read_text(encoding="utf-8")
        hit = PLATFORM.search(text)
        assert not hit, f"{path.relative_to(ROOT)}: {hit.group(0)}"
