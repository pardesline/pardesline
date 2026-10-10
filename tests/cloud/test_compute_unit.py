"""Unit tests for the compute surface (respx): jobs, catalog-driven methods,
pipelines, projects — pinning the call sequence and the typed objects."""

import httpx
import pytest
import respx

from pardesline.cloud import Client
from pardesline.cloud.models import FileInfo
from pardesline.cloud.objects import PointCloud, Volume, wrap_file

BASE = "https://api.test"
KEY = "pl_" + "b" * 32

MODULES = [
    {"id": "point_cloud_processing", "name": "PCP", "input_formats": [".ply", ".pcd"], "dual_input": False,
     "methods": [{"id": "voxel_downsample", "name": "Voxel", "dual_input": False,
                  "parameters": [{"name": "voxel_size", "type": "float", "default": 0.02}]},
                 {"id": "statistical_outlier_removal", "name": "SOR", "dual_input": False,
                  "parameters": [{"name": "nb_neighbors", "type": "int", "default": 20},
                                 {"name": "std_ratio", "type": "float", "default": 2.0}]}]},
    {"id": "simpleitk_registration", "name": "Reg", "input_formats": [".vti", ".mha"], "dual_input": True,
     "methods": [{"id": "rigid", "name": "Rigid", "dual_input": True,
                  "parameters": [{"name": "learning_rate", "type": "float", "default": 1.0}]}]},
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


def _file(fid, name, geo, ext):
    return {"id": fid, "name": name, "geometry_type": geo, "extension": ext, "size_bytes": 100,
            "file_type": "sample", "download_url": f"/api/v1/files/{fid}/download"}


def _mock_catalog():
    respx.get(f"{BASE}/api/v1/modules").mock(return_value=httpx.Response(200, json=MODULES))


def _mock_job_lifecycle(input_id, out_id, module="point_cloud_processing", method="voxel_downsample"):
    jid = out_id
    respx.post(f"{BASE}/api/v1/jobs").mock(return_value=httpx.Response(202, json={
        "id": jid, "kind": "module", "module_id": module, "method_id": method, "status": "running", "progress": 10}))
    respx.get(f"{BASE}/api/v1/jobs/{jid}").mock(return_value=httpx.Response(200, json={
        "id": jid, "kind": "module", "status": "completed", "progress": 100, "output_file_id": jid}))
    respx.get(f"{BASE}/api/v1/jobs/{jid}/result").mock(return_value=httpx.Response(200, json={
        "job": {"id": jid, "status": "completed"}, "output": _file(jid, "out.ply", "pointcloud", ".ply"),
        "extra_outputs": []}))
    return jid


@respx.mock
def test_typed_objects_from_geometry():
    c = Client(token=KEY, base_url=BASE)
    assert isinstance(wrap_file(c, FileInfo.model_validate(_file("v", "ct.vti", "volume", ".vti"))), Volume)
    assert isinstance(wrap_file(c, FileInfo.model_validate(_file("p", "s.ply", None, ".ply"))), PointCloud)


@respx.mock
def test_run_module_returns_output_object(client):
    _mock_catalog()
    respx.post(f"{BASE}/api/v1/samples/sphere/use").mock(return_value=httpx.Response(201, json=_file("in1", "sphere.ply", "pointcloud", ".ply")))
    obj = client.samples.use("sphere")
    assert isinstance(obj, PointCloud)
    _mock_job_lifecycle("in1", "job1")
    out = obj.run("point_cloud_processing", "voxel_downsample", voxel_size=0.05)
    assert isinstance(out, PointCloud) and out.id == "job1"


@respx.mock
def test_catalog_method_and_alias(client):
    _mock_catalog()
    obj = wrap_file(client, FileInfo.model_validate(_file("in2", "s.ply", "pointcloud", ".ply")))
    # generated method name == method_id
    jid = _mock_job_lifecycle("in2", "job2")
    out = obj.voxel_downsample(voxel_size=0.1)
    assert out.id == jid
    body = respx.calls[-3].request.content  # the POST /jobs
    assert b'"voxel_downsample"' in body and b'"in2"' in body
    # curated alias 'downsample' -> voxel_downsample
    _mock_job_lifecycle("in2", "job3")
    assert obj.downsample(voxel_size=0.2).id == "job3"
    # a method that doesn't apply to a point cloud is not exposed
    with pytest.raises(AttributeError):
        obj.rigid  # volume-only


@respx.mock
def test_dual_input_registration(client):
    _mock_catalog()
    fixed = wrap_file(client, FileInfo.model_validate(_file("ct", "ct.vti", "volume", ".vti")))
    moving = wrap_file(client, FileInfo.model_validate(_file("mr", "mr.vti", "volume", ".vti")))
    _mock_job_lifecycle("ct", "regjob", module="simpleitk_registration", method="rigid")
    out = fixed.register(moving)                       # alias -> simpleitk_registration.rigid, moving positional
    assert out.id == "regjob"
    posted = respx.calls[-3].request.content
    assert b'"moving_file_id"' in posted and b'"mr"' in posted


@respx.mock
def test_pipeline(client):
    respx.post(f"{BASE}/api/v1/pipelines").mock(return_value=httpx.Response(202, json={
        "id": "pj", "kind": "pipeline", "status": "running", "progress": 0}))
    respx.get(f"{BASE}/api/v1/jobs/pj").mock(return_value=httpx.Response(200, json={
        "id": "pj", "kind": "pipeline", "status": "completed", "progress": 100, "output_file_id": "pj"}))
    respx.get(f"{BASE}/api/v1/jobs/pj/result").mock(return_value=httpx.Response(200, json={
        "job": {"id": "pj", "status": "completed"}, "output": _file("pj", "out.ply", "pointcloud", ".ply")}))
    out = client.pipelines.run([
        {"module_id": "point_cloud_processing", "method_id": "voxel_downsample"},
        {"module_id": "point_cloud_processing", "method_id": "statistical_outlier_removal"},
    ], "in3")
    assert out.id == "pj"


@respx.mock
def test_projects(client):
    respx.post(f"{BASE}/api/v1/projects").mock(return_value=httpx.Response(201, json={"id": "pr1", "name": "P"}))
    respx.put(f"{BASE}/api/v1/projects/pr1/workflow").mock(return_value=httpx.Response(200, json={"status": "saved", "blocks": 1}))
    respx.post(f"{BASE}/api/v1/projects/pr1/run").mock(return_value=httpx.Response(202, json={
        "id": "wj", "kind": "workflow", "status": "running", "progress": 0}))
    respx.get(f"{BASE}/api/v1/jobs/wj").mock(return_value=httpx.Response(200, json={
        "id": "wj", "kind": "workflow", "status": "completed", "progress": 100, "output_file_id": "wj"}))
    respx.get(f"{BASE}/api/v1/jobs/wj/result").mock(return_value=httpx.Response(200, json={
        "job": {"id": "wj", "status": "completed"}, "output": _file("wj", "o.ply", "pointcloud", ".ply")}))
    p = client.projects.create("P")
    p.save_workflow({"blocks": [{"id": "in", "type": "file-input"}], "edges": []})
    out = p.run("in4")
    assert out.id == "wj"


@respx.mock
def test_job_wait_raises_on_fail(client):
    respx.post(f"{BASE}/api/v1/jobs").mock(return_value=httpx.Response(202, json={
        "id": "fj", "kind": "module", "status": "running", "progress": 0}))
    respx.get(f"{BASE}/api/v1/jobs/fj").mock(return_value=httpx.Response(200, json={
        "id": "fj", "kind": "module", "status": "failed", "error": "script blew up"}))
    from pardesline.cloud.jobs import JobFailed
    job = client.jobs.submit("point_cloud_processing", "voxel_downsample", "in5")
    with pytest.raises(JobFailed) as ei:
        job.wait(poll=0.01)
    assert "blew up" in str(ei.value)
