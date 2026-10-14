"""The s3, tcia and urllist sources against mocked HTTP (respx), plus the
archive source over several archives with DICOM folders, repeated
placeholders and MetaImage siblings."""

from __future__ import annotations

import io
import threading
import zipfile
from functools import partial
from http.server import ThreadingHTTPServer

import pytest
import respx
from httpx import Response
from test_source_archive import _RangeHandler

import pardesline as pl
from pardesline.data.dataset import _pattern_regex
from pardesline.data.manifest import Manifest

S3 = "https://s3.amazonaws.com/openneuro.org"


def _s3_page(keys, truncated=False, token=None):
    body = "".join(f"<Contents><Key>{k}</Key><Size>10</Size></Contents>" for k in keys)
    tok = f"<NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    flag = "true" if truncated else "false"
    return f"<ListBucketResult><IsTruncated>{flag}</IsTruncated>{tok}{body}</ListBucketResult>"


@respx.mock
def test_s3_listing_paginates_and_fetches(tmp_path):
    pl.set_cache_dir(tmp_path / "cache")
    try:
        route = respx.get(f"{S3}/")
        route.side_effect = [
            Response(
                200, text=_s3_page(["ds000228/sub-pixar001/anat/sub-pixar001_T1w.nii.gz"], True, "tok1")
            ),
            Response(
                200, text=_s3_page(["ds000228/sub-pixar002/anat/sub-pixar002_T1w.nii.gz", "ds000228/README"])
            ),
        ]
        respx.get(f"{S3}/ds000228/sub-pixar002/anat/sub-pixar002_T1w.nii.gz").mock(
            return_value=Response(200, content=b"\0" * 32)
        )
        m = Manifest.from_dict(
            {
                "name": "pixar",
                "source": {"scheme": "s3", "bucket": "openneuro.org", "prefix": "ds000228"},
                "license": {"spdx": "CC0-1.0"},
                "roles": {
                    "t1w": {"type": "volume", "pattern": "{id}/anat/{id}_T1w.nii.gz", "modality": "MR"}
                },
            }
        )
        ds = pl.load(m.save(tmp_path / "pixar.json"))
        assert ds.ids == ["sub-pixar001", "sub-pixar002"]  # repeated {id} matched the same text
        p = ds["sub-pixar002"].path("t1w")
        assert p.read_bytes() == b"\0" * 32 and route.call_count == 2
        ds2 = pl.load(m.save(tmp_path / "pixar.json"))  # listing served from the disk cache
        assert ds2.ids == ds.ids and route.call_count == 2
        # ds000228 has a bundled manifest -> that one is used, no listing call
        assert pl.load("s3://openneuro.org/ds000228").name == "openneuro_ds000228"
        # another prefix: nothing to ask (NIfTI frame known, OpenNeuro licence known) -> loads directly
        route.side_effect = [Response(200, text=_s3_page(["ds000001/sub-01/anat/sub-01_T1w.nii.gz"]))]
        drafted = pl.load("s3://openneuro.org/ds000001")
        assert (
            drafted.license.spdx == "CC0-1.0" and drafted.manifest.source.scheme == "s3" and len(drafted) == 1
        )
        assert drafted.manifest.roles and all(r.type == "volume" for r in drafted.manifest.roles.values())
    finally:
        pl.set_cache_dir(None)


@respx.mock
def test_s3_forbidden_listing_is_explained(tmp_path):
    pl.set_cache_dir(tmp_path / "cache")
    try:
        respx.get("https://s3.amazonaws.com/private-bucket/").mock(return_value=Response(403))
        with pytest.raises(pl.FetchError, match="anonymous listing"):
            pl.scan("s3://private-bucket/data")
    finally:
        pl.set_cache_dir(None)


def _dicom_zip(n=3):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(n):
            zf.writestr(f"PANCREAS_0001/1.2.3/{i:06d}.dcm", b"DICM" + bytes([i]) * 16)
    return buf.getvalue()


@respx.mock
def test_tcia_series_become_dicom_folders(tmp_path):
    pl.set_cache_dir(tmp_path / "cache")
    api = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
    try:
        respx.get(f"{api}/getSeries").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "PatientID": "PANCREAS_0001",
                        "Modality": "CT",
                        "SeriesInstanceUID": "1.2.3",
                        "ImageCount": 3,
                        "FileSize": 100,
                    },
                    {
                        "PatientID": "PANCREAS_0002",
                        "Modality": "CT",
                        "SeriesInstanceUID": "1.2.4",
                        "ImageCount": 3,
                        "FileSize": 100,
                    },
                    {
                        "PatientID": "PANCREAS_0002",
                        "Modality": "SEG",
                        "SeriesInstanceUID": "1.2.5",
                        "ImageCount": 1,
                        "FileSize": 10,
                    },
                ],
            )
        )
        respx.get(f"{api}/getImage").mock(return_value=Response(200, content=_dicom_zip()))
        with pytest.raises(pl.NeedsConfirmation) as exc:
            pl.load("tcia://Pancreas-Fictional/CT")
        draft = exc.value.manifest
        assert draft.source.scheme == "tcia" and draft.source.modalities == ["CT"]
        assert all(r.type == "volume" for r in draft.roles.values()) and len(draft.samples) == 2
        m = Manifest.from_dict(
            {
                "name": "pancreas",
                "source": {"scheme": "tcia", "collection": "Pancreas-CT"},
                "license": {"spdx": "CC-BY-3.0"},
                "roles": {
                    "ct": {"type": "volume", "pattern": "{id}/CT/{series}", "modality": "CT"},
                    "seg": {"type": "labels", "pattern": "{id}/SEG/{series}"},
                },
            }
        )
        ds = pl.load(m.save(tmp_path / "p.json"))
        assert ds.ids == ["PANCREAS_0001", "PANCREAS_0002"] and ds["PANCREAS_0002"].roles == ["ct", "seg"]
        folder = ds["PANCREAS_0001"].path("ct")
        assert folder.is_dir() and len(list(folder.glob("*.dcm"))) == 3
        vol = ds["PANCREAS_0001"].ct
        assert vol.kind == "volume" and vol.path.is_dir()  # fake DICOM bytes: no header to read here
        assert ds["PANCREAS_0001"].path("ct") == folder  # cached, no second download
    finally:
        pl.set_cache_dir(None)


@respx.mock
def test_tcia_restricted_collection(tmp_path):
    pl.set_cache_dir(tmp_path / "cache")
    try:
        respx.get("https://services.cancerimagingarchive.net/nbia-api/services/v1/getSeries").mock(
            return_value=Response(401)
        )
        with pytest.raises(pl.FetchError, match="restricted"):
            pl.scan("tcia://Secret-Collection")
    finally:
        pl.set_cache_dir(None)


@respx.mock
def test_urllist_index(tmp_path):
    pl.set_cache_dir(tmp_path / "cache")
    try:
        index = "https://example.org/shapes.txt"
        respx.get(index).mock(
            return_value=Response(
                200,
                text=(
                    "https://files.example.org/dav/000000_liver.stl\n"
                    "https://files.example.org/dav/000001_liver.stl\n# comment\n"
                ),
            )
        )
        respx.get("https://files.example.org/dav/000001_liver.stl").mock(
            return_value=Response(200, content=b"solid x\nendsolid x\n")
        )
        m = Manifest.from_dict(
            {
                "name": "shapes",
                "source": {"scheme": "urllist", "index_url": index},
                "license": {"spdx": "CC-BY-4.0"},
                "roles": {"mesh": {"type": "mesh", "pattern": "{id}_{structure}.stl", "units": "mm"}},
            }
        )
        ds = pl.load(m.save(tmp_path / "s.json"))
        assert ds.ids == ["000000", "000001"] and ds[1].fields == {"structure": "liver"}
        mesh = ds[1].mesh
        assert isinstance(mesh, pl.Mesh) and mesh.path.read_bytes().startswith(b"solid")
    finally:
        pl.set_cache_dir(None)


def test_pattern_backreference_and_non_greedy_placeholders():
    rx, names = _pattern_regex("{id}/anat/{id}_T1w.nii.gz")
    assert names == ["id"]
    assert rx.match("sub-01/anat/sub-01_T1w.nii.gz")
    assert not rx.match("sub-01/anat/sub-02_T1w.nii.gz")
    rx, _ = _pattern_regex("3D_val_npz/{modality}_{id}.npz")
    m = rx.match("3D_val_npz/Microscopy_SELMA3D_patchvolume_cfos_009_0_0_0.npz")
    assert m and m.group("modality") == "Microscopy" and m.group("id") == "SELMA3D_patchvolume_cfos_009_0_0_0"
    rx, _ = _pattern_regex("{case}_{structure}.stl")
    m = rx.match("000000_tumoredbrain.stl")
    assert m and m.group("case") == "000000" and m.group("structure") == "tumoredbrain"


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_RangeHandler, directory=str(root)))
    httpd.ranges = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_archive_several_urls_dicom_folders_and_mhd_siblings(server, tmp_path):
    root, base = server
    a = io.BytesIO()
    with zipfile.ZipFile(a, "w") as zf:
        zf.writestr("subset0/scan1.mhd", b"ObjectType = Image\nElementDataFile = scan1.raw\n")
        zf.writestr("subset0/scan1.raw", b"\0" * 64)
        for i in range(2):
            zf.writestr(f"Train_Sets/CT/1/DICOM_anon/i{i:04d}.dcm", b"DICM" + b"\0" * 8)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zf:
        zf.writestr("subset1/scan2.mhd", b"ObjectType = Image\nElementDataFile = scan2.raw\n")
        zf.writestr("subset1/scan2.raw", b"\0" * 32)
    (root / "a.zip").write_bytes(a.getvalue())
    (root / "b.zip").write_bytes(b.getvalue())
    pl.set_cache_dir(tmp_path / "cache")
    try:
        m = Manifest.from_dict(
            {
                "name": "multi",
                "source": {"scheme": "archive", "urls": [f"{base}/a.zip", f"{base}/b.zip"], "format": "zip"},
                "license": {"spdx": "CC-BY-4.0"},
                "roles": {
                    "ct": {"type": "volume", "pattern": "subset{subset}/{id}.mhd"},
                    "dicom": {"type": "volume", "pattern": "Train_Sets/CT/{id}/DICOM_anon/*.dcm"},
                },
            }
        )
        ds = pl.load(m.save(tmp_path / "m.json"))
        assert set(ds.ids) == {"scan1", "scan2", "1"}
        p = ds["scan2"].path("ct")
        assert p.is_file() and p.with_suffix(".raw").is_file()  # the .raw sibling came along from archive b
        folder = ds["1"].path("dicom")
        assert folder.is_dir() and len(list(folder.glob("*.dcm"))) == 2
        assert "+1 more" in ds._source.describe()
    finally:
        pl.set_cache_dir(None)
