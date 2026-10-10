"""Unit tests (respx) for the viz + GPU surface of the SDK."""

import httpx
import pytest
import respx

from pardesline.cloud import Client
from pardesline.cloud.errors import GpuAddonRequired
from pardesline.cloud.models import FileInfo
from pardesline.cloud.objects import Volume, wrap_file

BASE = "https://api.test"
KEY = "pl_" + "c" * 32


@pytest.fixture
def client():
    return Client(token=KEY, base_url=BASE)


def _f(fid, name, geo, ext):
    return {"id": fid, "name": name, "geometry_type": geo, "extension": ext, "size_bytes": 10,
            "download_url": f"/api/v1/files/{fid}/download"}


@respx.mock
def test_obj_view_url(client):
    obj = wrap_file(client, FileInfo.model_validate(_f("p1", "s.ply", "pointcloud", ".ply")))
    respx.get(f"{BASE}/api/v1/files/p1/view-url").mock(return_value=httpx.Response(200, json={
        "url": f"{BASE}/?view=p1&type=pointcloud", "kind": "viewer", "file_ids": ["p1"]}))
    assert obj.view() == f"{BASE}/?view=p1&type=pointcloud"


@respx.mock
def test_view_many_and_registration(client):
    respx.post(f"{BASE}/api/v1/viz/view").mock(return_value=httpx.Response(200, json={
        "url": f"{BASE}/?view=a,b", "kind": "viewer", "file_ids": ["a", "b"]}))
    assert client.view("a", "b").endswith("view=a,b")
    respx.post(f"{BASE}/api/v1/viz/registration").mock(return_value=httpx.Response(200, json={
        "url": f"{BASE}/?reg=1&fixed=ct&moving=mr&method=rigid", "kind": "slicer", "file_ids": ["ct", "mr"]}))
    ct = wrap_file(client, FileInfo.model_validate(_f("ct", "ct.vti", "volume", ".vti")))
    mr = wrap_file(client, FileInfo.model_validate(_f("mr", "mr.vti", "volume", ".vti")))
    assert isinstance(ct, Volume)
    url = ct.view(mr, method="rigid")
    assert "reg=1" in url and "moving=mr" in url


@respx.mock
def test_volume_info(client):
    v = wrap_file(client, FileInfo.model_validate(_f("v1", "ct.vti", "volume", ".vti")))
    respx.get(f"{BASE}/api/v1/volumes/v1/info").mock(return_value=httpx.Response(200, json={
        "file_id": "v1", "dimensions": [256, 256, 130], "spacing": [1.0, 1.0, 1.0]}))
    info = v.info()
    assert info["dimensions"] == [256, 256, 130]


@respx.mock
def test_gpu_generate_3d_uploads_then_calls(client, tmp_path):
    img = tmp_path / "chair.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    # upload (transfer) the image
    respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": "img1", "mode": "direct", "upload_url": "https://bucket/x", "headers": {},
        "complete_url": "/api/v1/files/img1/complete"}))
    respx.put("https://bucket/x").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/api/v1/files/img1/complete").mock(return_value=httpx.Response(200, json=_f("img1", "chair.png", "image", ".png")))
    gen = respx.post(f"{BASE}/api/v1/gpu/generate-3d").mock(return_value=httpx.Response(200, json=_f("glb1", "trellis_3d.glb", "mesh", ".glb")))
    out = client.gpu.generate_3d(str(img))
    assert out.id == "glb1" and out.name == "trellis_3d.glb"
    assert b'"img1"' in gen.calls.last.request.content


@respx.mock
def test_gpu_addon_required_maps(client, tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": "img2", "mode": "api", "upload_url": "/api/v1/files/img2/content", "headers": {},
        "complete_url": "/api/v1/files/img2/complete"}))
    respx.put(f"{BASE}/api/v1/files/img2/content").mock(return_value=httpx.Response(200, json={"received_bytes": 6}))
    respx.post(f"{BASE}/api/v1/files/img2/complete").mock(return_value=httpx.Response(200, json=_f("img2", "x.png", "image", ".png")))
    respx.post(f"{BASE}/api/v1/gpu/generate-3d").mock(return_value=httpx.Response(402, json={
        "detail": {"code": "gpu_addon_required", "message": "needs GPU add-on", "upgrade_url": "https://x/checkout"}}))
    with pytest.raises(GpuAddonRequired) as ei:
        client.gpu.generate_3d(str(img))
    assert ei.value.detail.get("upgrade_url", "").endswith("checkout")


@respx.mock
def test_gpu_methods_lists(client):
    respx.get(f"{BASE}/api/v1/gpu/generate-3d/methods").mock(return_value=httpx.Response(200, json={"methods": ["trellis_generate"]}))
    respx.get(f"{BASE}/api/v1/gpu/image/methods").mock(return_value=httpx.Response(200, json={"methods": ["segment", "depth"]}))
    assert client.gpu.gen3d_methods() == ["trellis_generate"]
    assert "depth" in client.gpu.image_methods()
