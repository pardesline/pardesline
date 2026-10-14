"""The skills under skills/ stay grounded in the code: valid frontmatter, every
`module.method` they mention exists in the catalog, every dataset name they
cite is bundled, every public API name they cite exists, and the plugin
manifests agree with the package version."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import pardesline as pl

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
EXPECTED = {
    "using-pardesline",
    "catalog-and-run",
    "object-model",
    "datasets-and-manifests",
    "scanning-private-folders",
    "medical-volumes",
    "cloud-client",
    "contributing-algorithms",
    "mcp-server",
    # expert skills: theory, parameters, pitfalls and reference scripts per domain
    "3d-representations",
    "point-cloud-registration",
    "multimodal-rigid-registration",
    "atlas-label-transfer",
    "pointnet-segmentation",
    "dinov3-dense-features",
    "jepa-pretraining",
    "vae-anomaly-detection",
    "gaussian-splatting",
    "medical-segmentation-models",
    "evaluation-metrics-3d",
}
MODULE_IDS = set(pl.modules())


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n"), "frontmatter missing"
    head = text.split("\n---\n", 1)[0]
    name = re.search(r"^name:\s*(\S+)", head, re.M)
    desc = re.search(r"^description:\s*>-?\s*\n((?:\s{2}.*\n?)+)", head, re.M)
    assert name and desc, "name/description missing"
    return {"name": name.group(1), "description": " ".join(desc.group(1).split())}


def test_all_expected_skills_exist():
    assert {p.parent.name for p in SKILLS} == EXPECTED


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_frontmatter(path):
    fm = _frontmatter(path.read_text(encoding="utf-8"))
    assert fm["name"] == path.parent.name
    assert 200 <= len(fm["description"]) <= 1500, len(fm["description"])


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_module_method_references_exist(path):
    text = path.read_text(encoding="utf-8")
    cat = pl.catalog()
    for module, method in re.findall(r"\b([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\b", text):
        if module in MODULE_IDS:
            assert method in cat.module(module).methods, f"{path.parent.name}: {module}.{method}"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_bare_method_ids_in_tables_exist(path):
    """In the catalog table of catalog-and-run every listed id must exist."""
    if path.parent.name != "catalog-and-run":
        return
    text = path.read_text(encoding="utf-8")
    cat = pl.catalog()
    for line in text.splitlines():
        m = re.match(r"\| `([a-z_]+)`[^|]*\| ([^|]+) \|", line)
        if m and m.group(1) in MODULE_IDS:
            ids = [x.strip().split(" ")[0] for x in m.group(2).split(",")]
            for mid in ids:
                assert mid in cat.module(m.group(1)).methods, f"{m.group(1)}.{mid}"
            assert set(ids) == set(cat.module(m.group(1)).methods), m.group(1)


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_dataset_names_exist(path):
    text = path.read_text(encoding="utf-8")
    bundled = {m.name for m in pl.datasets()}
    for name in re.findall(r'pl\.load\("([a-z0-9_]+)"\)', text):
        assert name in bundled, f"{path.parent.name}: dataset {name}"
    for name in re.findall(r"`([a-z0-9_]+)`", text):
        if name.startswith(
            (
                "rire_",
                "popi_",
                "liver_",
                "visible_",
                "open3d_",
                "hf_",
                "msd_",
                "kitti_",
                "amos",
                "tcia_",
                "totalsegmentator_",
                "luna16",
                "ixi_",
                "verse19",
                "spider_",
                "chaos_",
                "openneuro_",
                "medshapenet",
                "c3vd_",
            )
        ):
            assert name in bundled, f"{path.parent.name}: dataset {name}"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_public_api_names_exist(path):
    text = path.read_text(encoding="utf-8")
    for name in set(re.findall(r"\bpl\.([A-Za-z_]+)\b", text)):
        if name in ("load", "scan", "run", "catalog", "describe", "datasets", "modules", "cloud"):
            continue
        assert hasattr(pl, name), f"{path.parent.name}: pl.{name} does not exist"


def test_cited_parameters_exist():
    cat = pl.catalog()
    cited = {
        ("point_cloud_processing", "voxel_downsample"): ["voxel_size"],
        ("point_cloud_processing", "statistical_outlier_removal"): ["nb_neighbors", "std_ratio"],
        ("point_cloud_reconstruction", "poisson"): ["depth", "density_quantile", "normal_radius"],
        ("pyvista_mesh_processing", "pv_decimate"): ["target_reduction"],
        ("pyvista_mesh_processing", "pv_smooth_laplacian"): ["n_iterations"],
        ("pyvista_mesh_processing", "pv_fill_holes"): ["hole_size"],
        ("mesh_processing", "mesh_to_pcd_poisson_disk"): ["num_points"],
        ("registration", "icp_refinement"): ["voxel_size", "max_iterations", "icp_estimation_method"],
        ("registration", "ransac_icp_pipeline"): ["voxel_size", "rotation_degrees"],
        ("point_cloud_segmentation", "dbscan_clustering"): ["eps", "min_points"],
        ("simpleitk_registration", "rigid"): [
            "num_iterations",
            "metric",
            "initializer",
            "sampling_percentage",
            "shrink_factors",
            "learning_rate",
        ],
        ("simpleitk_registration", "bspline"): ["grid_spacing"],
        ("simpleitk_registration", "demons"): ["num_iterations", "standard_deviations"],
        ("simpleitk_segmentation", "manual_threshold"): ["lower", "upper"],
        ("simpleitk_segmentation", "connected_components"): ["min_size"],
        ("simpleitk_segmentation", "watershed"): ["seed_radius"],
        ("pyvista_volume_processing", "pv_contour"): ["method"],
    }
    for (module, method), names in cited.items():
        known = cat.method(module, method).param_names
        for n in names:
            assert n in known, f"{module}.{method}: skills cite parameter {n!r}; accepted: {known}"


def test_plugin_manifests_match_version():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert plugin["version"] == pl.__version__ == market["plugins"][0]["version"]
    assert plugin["name"] == market["plugins"][0]["name"] == "pardesline"
    assert market["plugins"][0]["source"] == "./"
