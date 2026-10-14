"""The MCP server: tools answer with JSON, questions come back as data, errors never kill it."""

from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest

import pardesline as pl

mcp = pytest.importorskip("mcp")
from pardesline.mcp_server import build_server  # noqa: E402


@pytest.fixture(scope="module")
def server():
    return build_server("pardesline-test")


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    # FastMCP returns (content, structured) or a list of content blocks depending on the version
    if isinstance(result, tuple):
        structured = result[1]
        if isinstance(structured, dict) and "result" in structured and len(structured) == 1:
            return structured["result"]
        return structured
    text = result[0].text
    return json.loads(text)


def test_tools_and_resources_are_registered(server):
    tools = {t.name for t in asyncio.run(server.list_tools())}
    assert {
        "list_datasets",
        "describe_dataset",
        "list_samples",
        "load_sample",
        "scan_dataset",
        "confirm_dataset",
        "export_dataset",
        "list_methods",
        "describe_method",
        "run_method",
        "describe_object",
        "to_mesh",
    } <= tools
    for t in asyncio.run(server.list_tools()):
        assert t.description and len(t.description) > 40, t.name
    resources = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert "pardesline://datasets" in resources and "pardesline://catalog" in resources
    templates = {t.uriTemplate for t in asyncio.run(server.list_resource_templates())}
    assert "pardesline://manifest/{name}" in templates
    prompts = {p.name for p in asyncio.run(server.list_prompts())}
    assert "start_here" in prompts


def test_list_and_describe_datasets(server):
    out = call(server, "list_datasets", medical_only=True)
    assert out["count"] >= 30 and any(d["name"] == "msd_task02_heart" for d in out["datasets"])
    out = call(server, "list_datasets", scheme="tcia")
    assert all(d["source"] == "tcia" for d in out["datasets"]) and out["count"] >= 4
    d = call(server, "describe_dataset", ref="msd_task02_heart")
    assert d["license"] == "CC-BY-SA-4.0" and d["roles"] == {"mri": "volume", "mask": "labels"}
    assert "left_atrium" in json.dumps(d["roles_detail"])
    err = call(server, "describe_dataset", ref="no_such_dataset")
    assert err["error"] in ("FileNotFoundError", "ManifestError")


def test_catalog_tools(server):
    out = call(server, "list_methods", extension=".mha")
    mods = {m["module"] for m in out["modules"]}
    assert "simpleitk_registration" in mods and "point_cloud_processing" not in mods
    d = call(server, "describe_method", method="point_cloud_reconstruction.poisson")
    assert "depth" in d["text"]
    err = call(server, "describe_method", method="nope.nothing")
    assert err["error"] == "CatalogError"


def test_scan_confirm_list_load_on_a_private_folder(server, tmp_path):
    root = tmp_path / "study"
    for pid in ("p01", "p02"):
        (root / pid).mkdir(parents=True)
        np.arange(16, dtype=np.float32).tofile(root / pid / "sweep.bin")
    scan = call(server, "scan_dataset", ref=str(root))
    fields = {q["field"] for q in scan["questions"]}
    assert scan["is_draft"] and "license" in fields and "roles.sweep.layout" in fields
    pending = call(server, "confirm_dataset", ref=str(root), answers={"license": "CC0-1.0"})
    assert pending["error"] == "NeedsConfirmation" and pending["questions"] and "how_to_answer" in pending
    done = call(
        server,
        "confirm_dataset",
        ref=str(root),
        answers={
            "license": "CC0-1.0",
            "types": {"sweep": "points"},
            "layout": {"sweep": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
            "units": {"sweep": "m"},
            "frame": {"sweep": "sensor"},
        },
    )
    assert done["sample_count"] == 2 and done["manifest_saved_to"].endswith("pardesline.manifest.json")
    listing = call(server, "list_samples", ref=str(root), limit=1)
    assert listing["total"] == 2 and listing["samples"][0]["id"] == "p01"
    rec = call(server, "load_sample", ref=str(root), sample="p02", role="sweep")
    assert rec["kind"] == "pointcloud" and rec["units"] == "m" and rec["standard_path"].endswith(".ply")
    assert rec["license"]["spdx"] == "CC0-1.0" and rec["layout"]["shape"] == "(N,4)"
    obj = call(server, "describe_object", path=rec["standard_path"])
    assert obj["kind"] == "pointcloud"
    exp = call(server, "export_dataset", ref=str(root), folder=str(tmp_path / "out"), take=1)
    assert exp["samples"] == 1 and (tmp_path / "out" / "p01" / "sweep.ply").is_file()


@pytest.mark.local
def test_run_method_through_the_server(server, tmp_path, out_dir):
    pts = np.random.default_rng(0).random((300, 3)) * 2
    f = tmp_path / "pts.bin"
    pts.astype(np.float32).tofile(f)
    rec = call(server, "describe_object", path=str(f), layout={"dtype": "float32", "shape": "(N,3)"})
    assert rec["kind"] == "pointcloud"
    cloud = pl.load(f, layout={"dtype": "float32", "shape": "(N,3)"})
    ply = cloud._op_input()
    res = call(
        server,
        "run_method",
        method="point_cloud_processing.voxel_downsample",
        input_path=str(ply),
        params={"voxel_size": 0.4},
    )
    assert res["output"].endswith(".ply") and res["duration_s"] > 0
    bad = call(
        server,
        "run_method",
        method="point_cloud_processing.voxel_downsample",
        input_path=str(ply),
        params={"voxel": 1},
    )
    assert bad["error"] == "ParameterError" and "voxel_size" in bad["message"]


@pytest.mark.slow
def test_stdio_roundtrip_with_a_real_client(tmp_path):
    """Spawn `python -m pardesline.mcp_server` as any MCP client would and talk to it over stdio."""
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def session():
        params = StdioServerParameters(command=sys.executable, args=["-m", "pardesline.mcp_server"])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
            init = await s.initialize()
            tools = await s.list_tools()
            res = await s.call_tool("describe_method", {"method": "point_cloud_processing.voxel_downsample"})
            prompt = await s.get_prompt("start_here")
            return init.serverInfo.name, {t.name for t in tools.tools}, res, prompt

    name, tools, res, prompt = asyncio.run(session())
    assert name == "pardesline" and "load_sample" in tools and "scan_dataset" in tools
    payload = res.structuredContent or json.loads(res.content[0].text)
    text = json.dumps(payload)
    assert "voxel_size" in text
    assert "list_datasets" in prompt.messages[0].content.text
