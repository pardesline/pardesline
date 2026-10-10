"""Grouped API surfaces hung off the Client: modules, samples, jobs, pipelines,
projects. Thin wrappers returning models / RemoteObjects / Job handles."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from .models import ModuleInfo, SampleInfo

if TYPE_CHECKING:
    from .client import Client
    from .jobs import Job
    from .objects import RemoteObject


class ModulesResource:
    def __init__(self, client: Client):
        self._c = client

    def list(self) -> List[ModuleInfo]:
        return [ModuleInfo.model_validate(x) for x in self._c._http.request("GET", "/api/v1/modules", auth=False)]

    def get(self, module_id: str) -> ModuleInfo:
        return ModuleInfo.model_validate(self._c._http.request("GET", f"/api/v1/modules/{module_id}", auth=False))

    def params(self, module_id: str, method_id: str) -> List[dict]:
        """Full parameter schema (name/type/default/min/max/description) for a
        module method — every knob, all optional."""
        from ._catalog import get_catalog
        return get_catalog(self._c).params(module_id, method_id)

    def describe(self, module_id: str, method_id: str) -> str:
        """Human-readable listing of every tunable parameter of a module method."""
        from ._catalog import get_catalog
        return get_catalog(self._c).describe(module_id, method_id)


class SamplesResource:
    def __init__(self, client: Client):
        self._c = client

    def list(self, kind: Optional[str] = None) -> List[SampleInfo]:
        params = {"kind": kind} if kind else None
        return [SampleInfo.model_validate(x) for x in self._c._http.request("GET", "/api/v1/samples", params=params, auth=False)]

    def use(self, sample_id: str, *, project: Optional[str] = None) -> RemoteObject:
        from .models import FileInfo
        from .objects import wrap_file
        body = {"project_id": project} if project else {}
        data = self._c._http.request("POST", f"/api/v1/samples/{sample_id}/use", json=body)
        return wrap_file(self._c, FileInfo.model_validate(data))


class JobsResource:
    def __init__(self, client: Client):
        self._c = client

    def submit(self, module_id: str, method_id: str, input, *, moving=None, params: Optional[dict] = None,
               project: Optional[str] = None, wait: bool = False) -> Job:
        from .jobs import Job
        from .models import Job as JobModel
        from .objects import RemoteObject
        input_id = input.id if isinstance(input, RemoteObject) else input
        body = {"module_id": module_id, "method_id": method_id, "input_file_id": input_id, "params": params or {}}
        if moving is not None:
            body["moving_file_id"] = moving.id if isinstance(moving, RemoteObject) else moving
        if project:
            body["project_id"] = project
        job = Job(self._c, JobModel.model_validate(self._c._http.request("POST", "/api/v1/jobs", json=body)))
        return job.wait() if wait else job

    def get(self, job_id: str) -> Job:
        from .jobs import Job
        return Job(self._c, self._c._get_job(job_id))

    def list(self, *, status: Optional[str] = None, limit: int = 50) -> List[Job]:
        from .jobs import Job
        from .models import Job as JobModel
        params = {"limit": limit}
        if status:
            params["status"] = status
        rows = self._c._http.request("GET", "/api/v1/jobs", params=params)
        return [Job(self._c, JobModel.model_validate(x)) for x in rows]


class PipelinesResource:
    def __init__(self, client: Client):
        self._c = client

    def run(self, steps: List[dict], input, *, project: Optional[str] = None, wait: bool = True):
        from .jobs import Job
        from .models import Job as JobModel
        from .objects import RemoteObject
        input_id = input.id if isinstance(input, RemoteObject) else input
        body = {"steps": steps, "input_file_id": input_id}
        if project:
            body["project_id"] = project
        job = Job(self._c, JobModel.model_validate(self._c._http.request("POST", "/api/v1/pipelines", json=body)))
        if wait:
            job.wait()
            return job.result(wait=False)
        return job


class GpuResource:
    """GPU features: image → 3D (Trellis) and 2D AI image processing. Require
    the GPU add-on; raise GpuAddonRequired otherwise."""

    def __init__(self, client: Client):
        self._c = client

    def generate_3d(self, image, *, method: str = "trellis_generate", params: Optional[dict] = None,
                    timeout_s: int = 480):
        """Turn a 2D image (a local path or an uploaded object) into a 3D .glb.
        Returns the resulting Mesh (registered to you). Expect GPU cold starts."""
        from .objects import RemoteObject
        obj = image if isinstance(image, RemoteObject) else self._c.upload(image)
        body = {"input_file_id": obj.id, "method": method, "params": params or {}, "timeout_s": timeout_s}
        return self._c._wrap(self._c._http.request("POST", "/api/v1/gpu/generate-3d", json=body, timeout=timeout_s + 60))

    def process_image(self, image, method: str, *, params: Optional[dict] = None, second=None):
        """Run a 2D AI method (segmentation, depth, super-resolution, …) on one
        or two images. Returns the result file."""
        from .objects import RemoteObject
        obj = image if isinstance(image, RemoteObject) else self._c.upload(image)
        body = {"input_file_id": obj.id, "method": method, "params": params or {}}
        if second is not None:
            s = second if isinstance(second, RemoteObject) else self._c.upload(second)
            body["second_file_id"] = s.id
        return self._c._wrap(self._c._http.request("POST", "/api/v1/gpu/image", json=body, timeout=360))

    def gen3d_methods(self) -> list:
        """List image→3D methods (each a dict with id/name/params)."""
        return self._methods("generate-3d")

    def image_methods(self) -> list:
        """List 2D-AI image methods (each a dict with id/name/params)."""
        return self._methods("image")

    def _methods(self, kind: str) -> list:
        data = self._c._http.request("GET", f"/api/v1/gpu/{kind}/methods").get("methods", [])
        # tolerate a doubly-wrapped {"methods": {"methods": [...]}} from upstream.
        if isinstance(data, dict):
            data = data.get("methods", [])
        return data


class ProjectsResource:
    def __init__(self, client: Client):
        self._c = client

    def list(self, *, module: Optional[str] = None) -> List[Project]:
        params = {"module_id": module} if module else None
        return [Project(self._c, x) for x in self._c._http.request("GET", "/api/v1/projects", params=params)]

    def create(self, name: str, *, module: Optional[str] = None) -> Project:
        body = {"name": name}
        if module:
            body["module_id"] = module
        return Project(self._c, self._c._http.request("POST", "/api/v1/projects", json=body))

    def get(self, project_id: str) -> Project:
        return Project(self._c, self._c._http.request("GET", f"/api/v1/projects/{project_id}"))


class Project:
    def __init__(self, client: Client, data: dict):
        self._c = client
        self._d = data

    @property
    def id(self) -> str:
        return self._d["id"]

    @property
    def name(self) -> str:
        return self._d["name"]

    def workflow(self) -> dict:
        return self._c._http.request("GET", f"/api/v1/projects/{self.id}/workflow").get("workflow")

    def save_workflow(self, workflow: dict) -> dict:
        return self._c._http.request("PUT", f"/api/v1/projects/{self.id}/workflow", json=workflow)

    def run(self, input, *, wait: bool = True):
        from .jobs import Job
        from .models import Job as JobModel
        from .objects import RemoteObject
        input_id = input.id if isinstance(input, RemoteObject) else input
        job = Job(self._c, JobModel.model_validate(
            self._c._http.request("POST", f"/api/v1/projects/{self.id}/run", json={"input_file_id": input_id})))
        if wait:
            job.wait()
            return job.result(wait=False)
        return job

    def delete(self) -> None:
        self._c._http.request("DELETE", f"/api/v1/projects/{self.id}")

    def __repr__(self) -> str:
        return f"<Project {self.name!r} id={self.id[:8]}>"
