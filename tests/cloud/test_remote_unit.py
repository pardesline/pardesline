"""Unit tests for the pl.o3d / pl.pv / pl.sitk lazy op-graph (respx, no server).

They pin the graph the SDK records and the single /rpc/eval call it makes on
materialisation, including cross-chain merging (registration-style: two remote
inputs into one call)."""
import httpx
import pytest
import respx

from pardesline.cloud import Client
from pardesline.cloud.models import FileInfo
from pardesline.cloud.objects import Mesh, wrap_file

BASE = "https://api.test"
KEY = "pl_" + "e" * 32


@pytest.fixture
def client():
    return Client(token=KEY, base_url=BASE)


def _file(client, fid, ext=".ply", geo="pointcloud"):
    return wrap_file(client, FileInfo.model_validate({
        "id": fid, "name": f"{fid}{ext}", "geometry_type": geo, "extension": ext,
        "size_bytes": 10, "download_url": f"/api/v1/files/{fid}/download"}))


def test_graph_records_call_then_method(client):
    f = _file(client, "f1")
    pcd = client.o3d.io.read_point_cloud(f)          # a call on the open3d root
    down = pcd.voxel_down_sample(0.05)               # a method on the result
    nodes = down._g.nodes
    assert nodes[0] == {"op": "call", "lib": "open3d", "path": ["io", "read_point_cloud"],
                        "args": [{"$file": "f1"}], "kwargs": {}, "id": 0}
    assert nodes[1] == {"op": "method", "target": 0, "name": "voxel_down_sample",
                        "args": [0.05], "kwargs": {}, "id": 1}
    assert down._id == 1


@respx.mock
def test_to_file_posts_graph_and_wraps(client):
    f = _file(client, "f1")
    down = client.o3d.io.read_point_cloud(f).voxel_down_sample(0.05)
    route = respx.post(f"{BASE}/api/v1/rpc/eval").mock(return_value=httpx.Response(200, json={
        "id": "out1", "name": "down.ply", "geometry_type": "pointcloud", "extension": ".ply",
        "size_bytes": 200, "download_url": "/api/v1/files/out1/download"}))
    out = down.to_file("down.ply")
    assert isinstance(out, Mesh) or out.id == "out1"
    body = route.calls.last.request.content
    assert b'"mode":"file"' in body.replace(b" ", b"") and b'"return":1' in body.replace(b" ", b"")
    assert b'"read_point_cloud"' in body and b'"voxel_down_sample"' in body


@respx.mock
def test_value_materialisation(client):
    f = _file(client, "f1")
    n = client.np.asarray(client.o3d.io.read_point_cloud(f).points).shape[0]
    respx.post(f"{BASE}/api/v1/rpc/eval").mock(return_value=httpx.Response(200, json={"result": 795}))
    assert int(n) == 795


def test_cross_chain_merge_registration(client):
    src = client.o3d.io.read_point_cloud(_file(client, "s"))
    tgt = client.o3d.io.read_point_cloud(_file(client, "t"))
    # a call taking BOTH remote inputs -> their two graphs merge into one
    reg = client.o3d.pipelines.registration.registration_icp(src, tgt, 0.05)
    nodes = reg._g.nodes
    assert len(nodes) == 3  # read s, read t, registration_icp
    call = nodes[-1]
    assert call["op"] == "call" and call["path"][-1] == "registration_icp"
    refs = [a for a in call["args"] if isinstance(a, dict) and "$ref" in a]
    assert {r["$ref"] for r in refs} == {0, 1}  # both merged inputs referenced
