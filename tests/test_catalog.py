"""The bundled catalog is complete, consistent with the scripts, and typed."""

from __future__ import annotations

import re

import pytest

import pardesline as pl
from pardesline.catalog import PARAM_TYPES, load_catalog

# Keyword names of pl.run / Object.run. (module, method, input are positional-only
# precisely so that a parameter called "method" stays usable as a keyword.)
RESERVED = {"output", "moving", "params", "timeout", "python", "on_log", "on_progress", "cwd"}

cat = load_catalog()


def test_counts_match_the_platform():
    assert len(cat) == 19
    assert len(cat.methods) == 73
    assert sum(len(m.parameters) for m in cat.methods) == 371


def test_ids_are_unique_and_well_formed():
    ids = [m.id for m in cat]
    assert len(ids) == len(set(ids))
    for mod in cat:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", mod.id), mod.id
        for m in mod.methods.values():
            assert re.fullmatch(r"[a-z][a-z0-9_]*", m.id), m.qualname
            names = [p.name for p in m.parameters]
            assert len(names) == len(set(names)), m.qualname


@pytest.mark.parametrize("method", cat.methods, ids=lambda m: m.qualname)
def test_script_exists_and_follows_the_contract(method):
    path = method.script_path()
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    assert '"--input"' in text and '"--output"' in text, method.qualname
    if method.dual_input:
        assert '"--moving"' in text, f"{method.qualname} is dual-input but has no --moving flag"
    declared = text
    if "add_common_reg_cli_args(" in text:  # shared registration flags live in the medical service
        declared += (path.parents[2] / "medical" / "_service.py").read_text(encoding="utf-8")
    for p in method.parameters:
        assert f'"--{p.name}"' in declared, (
            f"{method.qualname}: --{p.name} is in the catalog but not in the script"
        )
    assert "sys.path.insert" not in text, "scripts must not patch sys.path"
    assert "from services" not in text, "scripts must import pardesline.medical, not the platform"
    assert 'if __name__ == "__main__"' in text


@pytest.mark.parametrize("method", cat.methods, ids=lambda m: m.qualname)
def test_parameters_are_typed_and_defaults_valid(method):
    for p in method.parameters:
        assert p.type in PARAM_TYPES, (method.qualname, p.name, p.type)
        assert p.name not in RESERVED, f"{method.qualname}.{p.name} collides with a run() keyword"
        assert p.description, f"{method.qualname}.{p.name} has no description"
        if p.type == "enum":
            assert p.options and str(p.default) in p.options, (method.qualname, p.name)
        if p.type in ("int", "float") and p.default is not None:
            p.coerce(p.default)  # the default must pass its own validation
        if p.type == "bool":
            p.coerce(p.default)


def test_module_lookup_and_suggestions():
    assert cat.module("point_cloud_processing").name
    with pytest.raises(pl.CatalogError, match="Did you mean 'point_cloud_processing'"):
        cat.module("point_cloud_procesing")
    with pytest.raises(pl.CatalogError, match="Did you mean 'voxel_downsample'"):
        cat.method("point_cloud_processing", "voxel_downsampl")
    assert (
        cat.method("point_cloud_processing.voxel_downsample").qualname
        == "point_cloud_processing.voxel_downsample"
    )


def test_find_by_bare_id_and_extension():
    m = cat.find("voxel_downsample", ".ply")
    assert m.module_id == "point_cloud_processing"
    with pytest.raises(pl.CatalogError, match="does not accept"):
        cat.find("voxel_downsample", ".mha")
    with pytest.raises(pl.CatalogError, match="No method named"):
        cat.find("does_not_exist")


def test_methods_for_extension():
    assert cat.methods_for(".ply")
    assert all(cat.module(m.module_id).accepts(".mha") for m in cat.methods_for(".mha"))
    assert cat.methods_for(".docx") == []


def test_describe_is_readable():
    text = cat.describe("point_cloud_reconstruction.poisson")
    assert "point_cloud_reconstruction.poisson" in text
    assert "depth" in text
    assert "registration" in cat.describe("simpleitk_registration")
    assert pl.describe("sdf") == cat.describe("sdf")


def test_dual_input_flags():
    assert cat.method("simpleitk_registration", "rigid").dual_input
    assert cat.method("registration", "icp_refinement").dual_input
    assert not cat.method("point_cloud_processing", "voxel_downsample").dual_input


def test_top_level_helpers():
    assert pl.modules()[0] == "point_cloud_processing"
    assert pl.catalog() is cat
    assert pl.__version__


def test_accepts_nii_gz_wherever_nii_is_accepted():
    mod = pl.catalog().module("simpleitk_segmentation")
    assert ".nii" in mod.input_formats
    assert mod.accepts(".nii.gz") and mod.accepts(".NII.GZ") and mod.accepts(".nii")
    assert not mod.accepts(".gz") and not mod.accepts(".ply")
    assert not pl.catalog().module("point_cloud_processing").accepts(".nii.gz")
