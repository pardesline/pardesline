"""Unit tests for the transfer flow with respx (no network).

They pin the exact call sequence the SDK makes — begin → PUT bytes to the
returned address → complete → resolve/download-url → GET bytes — plus the
error mapping, so a change to the client contract is caught here.
"""

import os

import httpx
import pytest
import respx

from pardesline.cloud import Client
from pardesline.cloud.errors import NotFound, QuotaExceeded

BASE = "https://api.test"
KEY = "pl_" + "a" * 32
DATA = b"\x93NUMPY" + os.urandom(2048)


@pytest.fixture
def client():
    return Client(token=KEY, base_url=BASE)


@respx.mock
def test_upload_begin_put_complete(tmp_path, client):
    src = tmp_path / "weights.npy"
    src.write_bytes(DATA)
    fid = "file-123"
    put_url = "https://bucket.example/signed-put"

    begin = respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": fid, "mode": "direct", "upload_url": put_url,
        "headers": {"Content-Type": "application/octet-stream"}, "complete_url": f"/api/v1/files/{fid}/complete",
        "max_bytes": 5_000_000_000,
    }))
    put = respx.put(put_url).mock(return_value=httpx.Response(200))
    complete = respx.post(f"{BASE}/api/v1/files/{fid}/complete").mock(return_value=httpx.Response(200, json={
        "id": fid, "name": "weights.npy", "extension": ".npy", "size_bytes": len(DATA),
        "geometry_type": None, "owner_email": "a@x.io", "download_url": f"/api/v1/files/{fid}/download",
    }))

    obj = client.upload(src)
    assert obj.id == fid and obj.name == "weights.npy" and obj.size_bytes == len(DATA)
    # the declared size sent to begin is the real file size
    assert begin.calls.last.request.read() and b'"size_bytes"' in begin.calls.last.request.content
    # the bytes went to the SIGNED bucket url, with NO API key header
    assert put.called and put.calls.last.request.headers.get("x-api-key") in (None, "")
    assert put.calls.last.request.content == DATA
    assert complete.called


@respx.mock
def test_upload_api_fallback_mode(tmp_path, client):
    """mode=api (local/dev): PUT goes to the API content route with the key."""
    src = tmp_path / "a.json"
    src.write_bytes(b'{"x":1}')
    fid = "file-api"
    respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": fid, "mode": "api", "upload_url": f"/api/v1/files/{fid}/content",
        "headers": {"Content-Type": "application/octet-stream"}, "complete_url": f"/api/v1/files/{fid}/complete",
    }))
    put = respx.put(f"{BASE}/api/v1/files/{fid}/content").mock(return_value=httpx.Response(200, json={"received_bytes": 7}))
    respx.post(f"{BASE}/api/v1/files/{fid}/complete").mock(return_value=httpx.Response(200, json={
        "id": fid, "name": "a.json", "extension": ".json", "size_bytes": 7}))
    obj = client.upload(src)
    assert obj.id == fid
    assert put.calls.last.request.headers.get("x-api-key") == KEY  # API route DOES get the key


@respx.mock
def test_read_and_download(tmp_path, client):
    fid = "file-shared"
    get_url = "https://bucket.example/signed-get"
    respx.get(f"{BASE}/api/v1/files/resolve").mock(return_value=httpx.Response(200, json={
        "id": fid, "name": "scan.ply", "extension": ".ply", "size_bytes": len(DATA),
        "shared_by": "alice@lab.org", "download_url": f"/api/v1/files/{fid}/download"}))
    respx.get(f"{BASE}/api/v1/files/{fid}/download-url").mock(return_value=httpx.Response(200, json={
        "file_id": fid, "mode": "direct", "url": get_url, "filename": "scan.ply", "size_bytes": len(DATA)}))
    respx.get(get_url).mock(return_value=httpx.Response(200, content=DATA))

    obj = client.read("alice@lab.org/scan.ply")
    assert obj.shared_by == "alice@lab.org"
    dest = obj.download(tmp_path / "out.ply")
    assert dest.read_bytes() == DATA


@respx.mock
def test_send_is_upload_plus_share(tmp_path, client):
    src = tmp_path / "m.stl"; src.write_bytes(DATA)
    fid = "file-send"
    respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": fid, "mode": "direct", "upload_url": "https://bucket/x", "headers": {},
        "complete_url": f"/api/v1/files/{fid}/complete"}))
    respx.put("https://bucket/x").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/api/v1/files/{fid}/complete").mock(return_value=httpx.Response(200, json={
        "id": fid, "name": "m.stl", "extension": ".stl", "size_bytes": len(DATA)}))
    share = respx.post(f"{BASE}/api/v1/files/{fid}/share").mock(return_value=httpx.Response(201, json={
        "id": "sh1", "file_id": fid, "to": "bob@lab.org", "permission": "read", "status": "active"}))
    obj = client.send(src, to="bob@lab.org")
    assert obj.id == fid and share.called
    assert b"bob@lab.org" in share.calls.last.request.content


@respx.mock
def test_folder_is_zipped(tmp_path, client):
    d = tmp_path / "dicom"; d.mkdir()
    (d / "s0.dcm").write_bytes(b"a"); (d / "s1.dcm").write_bytes(b"b")
    fid = "file-zip"
    begin = respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(201, json={
        "file_id": fid, "mode": "direct", "upload_url": "https://bucket/z", "headers": {},
        "complete_url": f"/api/v1/files/{fid}/complete"}))
    respx.put("https://bucket/z").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/api/v1/files/{fid}/complete").mock(return_value=httpx.Response(200, json={
        "id": fid, "name": "dicom.zip", "extension": ".zip", "size_bytes": 200, "geometry_type": "archive"}))
    obj = client.upload(d)
    assert obj.name == "dicom.zip"
    assert b'"dicom.zip"' in begin.calls.last.request.content


@respx.mock
def test_error_mapping(client):
    respx.get(f"{BASE}/api/v1/files/resolve").mock(return_value=httpx.Response(404, json={
        "detail": {"code": "not_found", "message": "Nothing shared by x matches 'y'."}}))
    with pytest.raises(NotFound) as ei:
        client.read("x@y.io/y")
    assert ei.value.code == "not_found"

    respx.post(f"{BASE}/api/v1/files/uploads").mock(return_value=httpx.Response(402, json={
        "detail": {"code": "quota_exceeded", "message": "Free plan storage quota reached (1 GB / 1 GB).",
                   "quota": "storage_bytes", "used": 1073741824, "limit": 1073741824,
                   "upgrade_url": "https://appbeta.pardesline.com/?checkout=1"}}))
    with pytest.raises(QuotaExceeded) as ei:
        client.upload_bytes(b"x", "big.npy")
    assert ei.value.quota == "storage_bytes" and ei.value.upgrade_url.endswith("checkout=1")


def test_token_resolution(monkeypatch, tmp_path):
    from pardesline.cloud import _auth
    monkeypatch.setenv("PARDESLINE_TOKEN_PATH", str(tmp_path / "token"))
    monkeypatch.delenv("PARDESLINE_API_KEY", raising=False)
    assert _auth.resolve_token() is None
    _auth.save_token("pl_saved")
    assert _auth.resolve_token() == "pl_saved"
    monkeypatch.setenv("PARDESLINE_API_KEY", "pl_env")
    assert _auth.resolve_token() == "pl_env"                 # env beats file
    assert _auth.resolve_token("pl_explicit") == "pl_explicit"  # explicit beats all
    _auth.clear_saved_token()
    monkeypatch.delenv("PARDESLINE_API_KEY")
    assert _auth.resolve_token() is None
