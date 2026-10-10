"""Unit tests (respx) for parameter discovery + validation — every algorithm
knob is fillable, typo-checked, and self-documenting from the live catalog."""

import httpx
import pytest
import respx

from pardesline.cloud import Client
from pardesline.cloud.models import FileInfo
from pardesline.cloud.objects import wrap_file

BASE = "https://api.test"
KEY = "pl_" + "d" * 32

MODULES = [
    {"id": "point_cloud_processing", "name": "PCP", "input_formats": [".ply", ".pcd"], "dual_input": False,
     "methods": [
         {"id": "voxel_downsample", "name": "Voxel downsample", "dual_input": False, "parameters": [
             {"name": "voxel_size", "type": "float", "default": 0.02, "min": 0.001, "max": 1.0,
              "description": "Voxel edge length."}]},
         {"id": "statistical_outlier_removal", "name": "SOR", "dual_input": False, "parameters": [
             {"name": "nb_neighbors", "type": "int", "default": 20, "min": 1, "max": 200},
             {"name": "std_ratio", "type": "float", "default": 2.0, "min": 0.1, "max": 10.0}]},
         {"id": "mesh_to_pointcloud", "name": "M2P", "dual_input": False, "parameters": []}]},
]


@pytest.fixture
def client():
    return Client(token=KEY, base_url=BASE)


@pytest.fixture(autouse=True)
def _clear_catalog():
    import pardesline.cloud._catalog as c
    c._cache.clear()
    yield
    c._cache.clear()


def _mock_catalog():
    respx.get(f"{BASE}/api/v1/modules").mock(return_value=httpx.Response(200, json=MODULES))


def _obj(client):
    return wrap_file(client, FileInfo.model_validate({
        "id": "f1", "name": "s.ply", "geometry_type": "pointcloud", "extension": ".ply",
        "size_bytes": 100, "download_url": "/api/v1/files/f1/download"}))


@respx.mock
def test_params_and_describe_via_alias_and_method_id(client):
    _mock_catalog()
    obj = _obj(client)
    # method id
    ps = obj.params("voxel_downsample")
    assert [p["name"] for p in ps] == ["voxel_size"] and ps[0]["default"] == 0.02
    # curated alias resolves to the same schema
    assert obj.params("downsample")[0]["name"] == "voxel_size"
    text = obj.describe("statistical_outlier_removal")
    assert "nb_neighbors" in text and "std_ratio" in text and "2.0" in text
    # module-level discovery
    assert client.modules.params("point_cloud_processing", "voxel_downsample")[0]["name"] == "voxel_size"


@respx.mock
def test_unknown_param_is_rejected_with_hint(client):
    _mock_catalog()
    obj = _obj(client)
    with pytest.raises(ValueError) as ei:
        obj.voxel_downsample(voxel_sixe=0.1)  # typo
    msg = str(ei.value)
    assert "unknown parameter" in msg and "voxel_size" in msg


@respx.mock
def test_no_param_method_rejects_any(client):
    _mock_catalog()
    obj = _obj(client)
    with pytest.raises(ValueError) as ei:
        obj.mesh_to_pointcloud(foo=1)
    assert "no parameters" in str(ei.value)


@respx.mock
def test_generated_method_has_param_doc(client):
    _mock_catalog()
    obj = _obj(client)
    assert "voxel_size" in (obj.voxel_downsample.__doc__ or "")


@respx.mock
def test_known_params_pass_through(client):
    _mock_catalog()
    obj = _obj(client)
    respx.post(f"{BASE}/api/v1/jobs").mock(return_value=httpx.Response(202, json={
        "id": "j1", "kind": "module", "status": "running", "progress": 0}))
    respx.get(f"{BASE}/api/v1/jobs/j1").mock(return_value=httpx.Response(200, json={
        "id": "j1", "kind": "module", "status": "completed", "progress": 100, "output_file_id": "j1"}))
    respx.get(f"{BASE}/api/v1/jobs/j1/result").mock(return_value=httpx.Response(200, json={
        "job": {"id": "j1", "status": "completed"},
        "output": {"id": "j1", "name": "o.ply", "geometry_type": "pointcloud", "extension": ".ply",
                   "size_bytes": 1, "download_url": "/api/v1/files/j1/download"}}))
    out = obj.statistical_outlier_removal(nb_neighbors=30, std_ratio=1.5)
    assert out.id == "j1"
    body = respx.calls[-3].request.content
    assert b'"nb_neighbors"' in body and b'"std_ratio"' in body
