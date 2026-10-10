"""The PardesLine client — the transfer core of the SDK.

    import pardesline as pl
    pl.login()                              # email + code, stores a pl_ key
    obj = pl.upload("scan.ply")             # bytes go straight to storage
    pl.share(obj, to="bob@lab.org")         # or pl.send("scan.ply", to="bob@lab.org")

    # on Bob's side
    obj = pl.read("alice@lab.org/scan.ply") # what Alice shared with me
    obj.download("scan.ply")

The API only ever hands out signed storage addresses; the file bytes travel
directly between this client and the cloud bucket (so multi-GB 3D files, DICOM
folders, npy, json, anything, move without passing through the backend).
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Union

from . import _auth
from ._http import Transport
from .errors import PardesLineError, TransferError
from .models import DownloadUrl, FileInfo, Me, Share, UploadSession
from .models import Job as JobModel
from .objects import RemoteObject, wrap_file
from .resources import (
    GpuResource,
    JobsResource,
    ModulesResource,
    PipelinesResource,
    ProjectsResource,
    SamplesResource,
)

PathLike = Union[str, os.PathLike]


class Client:
    """A connection to PardesLine. Reuse one across calls."""

    def __init__(self, token: Optional[str] = None, *, base_url: Optional[str] = None,
                 timeout: float = 60.0):
        self.base_url = _auth.resolve_base_url(base_url)
        self._token = _auth.resolve_token(token)
        self._http = Transport(self.base_url, self._token, timeout=timeout)
        # grouped API surfaces
        self.modules = ModulesResource(self)
        self.samples = SamplesResource(self)
        self.jobs = JobsResource(self)
        self.pipelines = PipelinesResource(self)
        self.projects = ProjectsResource(self)
        self.gpu = GpuResource(self)
        # Faithful server-side mirrors of the libraries (Sprint 3): write the
        # same code as open3d / pyvista / SimpleITK / numpy, it runs remotely.
        from .remote import namespace as _ns
        self.o3d = _ns(self, "open3d")
        self.pv = _ns(self, "pyvista")
        self.sitk = _ns(self, "SimpleITK")
        self.np = _ns(self, "numpy")

    # ── auth ──────────────────────────────────────────────────
    @property
    def token(self) -> Optional[str]:
        return self._token

    def _set_token(self, token: Optional[str]) -> None:
        self._token = token
        self._http.set_token(token)

    def login(self, token: Optional[str] = None, *, email: Optional[str] = None,
              save: bool = True) -> Client:
        """Authenticate. With `token` (a pl_ key copied from the website) it is
        stored and used. With no token, run the terminal flow: prompt for the
        email, send a 6-digit code, prompt for it, mint a long-lived key and
        store it at ~/.pardesline/token."""
        if token:
            self._set_token(token.strip())
            if save:
                _auth.save_token(self._token)
            self.me()  # validate
            return self

        email = email or _auth.prompt("PardesLine email: ")
        if not email:
            raise PardesLineError("An email is required to log in.")
        self._http.request("POST", "/api/auth/request-otp", json={"email": email}, auth=False)
        print(f"A 6-digit code was sent to {email}.")
        code = _auth.prompt("Enter the code: ")
        data = self._http.request("POST", "/api/auth/verify-otp",
                                  json={"email": email, "code": code}, auth=False)
        session_jwt = data["access_token"]
        # Mint a long-lived key with the short session token, then discard it.
        key = self._mint_key_with_jwt(session_jwt)
        self._set_token(key)
        if save:
            path = _auth.save_token(key)
            print(f"Logged in as {email}. Key saved to {path}.")
        return self

    def _mint_key_with_jwt(self, jwt: str) -> str:
        import httpx
        with httpx.Client(base_url=self.base_url, timeout=30.0) as c:
            r = c.post("/api/keys", json={"name": _auth.default_key_name()},
                       headers={"Authorization": f"Bearer {jwt}", "User-Agent": self._http._client.headers["User-Agent"]})
        if r.status_code >= 400:
            from .errors import from_response
            raise from_response(r.status_code, r.json() if r.content else {})
        return r.json()["key"]

    def logout(self) -> None:
        """Revoke the stored key on the server (best-effort) and delete it locally."""
        try:
            keys = self._http.request("GET", "/api/keys")
            for k in keys or []:
                if k.get("masked") and self._token and self._token.endswith(k["masked"][-4:]):
                    self._http.request("DELETE", f"/api/keys/{k['id']}")
        except PardesLineError:
            pass
        _auth.clear_saved_token()
        self._set_token(None)

    def me(self) -> Me:
        return Me.model_validate(self._http.request("GET", "/api/v1/me"))

    def whoami(self) -> Optional[str]:
        return self.me().email

    # ── transfer: upload ──────────────────────────────────────
    def upload(self, path: PathLike, *, name: Optional[str] = None, project: Optional[str] = None,
               workspace: Optional[str] = None) -> RemoteObject:
        """Upload a local file (or a folder, zipped) to your PardesLine
        storage. The bytes go straight to the bucket. Returns a RemoteObject."""
        src = Path(path)
        if not src.exists():
            raise FileNotFoundError(str(src))
        cleanup = None
        if src.is_dir():
            src, cleanup = self._zip_folder(src)
            name = name or (Path(path).name.rstrip("/\\") + ".zip")
        try:
            display = name or src.name
            size = src.stat().st_size
            session = self._begin_upload(display, size, project=project, workspace=workspace)
            with open(src, "rb") as f:
                self._http.put_bytes(session.upload_url, f, headers=session.headers)
            info = self._complete_upload(session.file_id)
            return wrap_file(self, info)
        finally:
            if cleanup:
                cleanup()

    def upload_bytes(self, data: bytes, name: str, *, project: Optional[str] = None) -> RemoteObject:
        session = self._begin_upload(name, len(data), project=project)
        self._http.put_bytes(session.upload_url, io.BytesIO(data), headers=session.headers)
        return wrap_file(self, self._complete_upload(session.file_id))

    def send(self, path: PathLike, to: str, *, name: Optional[str] = None,
             message: Optional[str] = None) -> RemoteObject:
        """upload + share in one call: hand a local file to another account."""
        obj = self.upload(path, name=name)
        self.share(obj, to=to, message=message)
        return obj

    def _begin_upload(self, name: str, size: int, *, project=None, workspace=None) -> UploadSession:
        body = {"name": name, "size_bytes": int(size)}
        if project:
            body["project_id"] = project
        if workspace:
            body["workspace_id"] = workspace
        return UploadSession.model_validate(self._http.request("POST", "/api/v1/files/uploads", json=body))

    def _complete_upload(self, file_id: str) -> FileInfo:
        return FileInfo.model_validate(self._http.request("POST", f"/api/v1/files/{file_id}/complete"))

    @staticmethod
    def _zip_folder(folder: Path):
        tmp = tempfile.NamedTemporaryFile(prefix="pardesline_", suffix=".zip", delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in folder.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(folder))
        return Path(tmp.name), lambda: os.unlink(tmp.name)

    # ── transfer: read / download ─────────────────────────────
    def read(self, ref: str) -> RemoteObject:
        """Resolve a file by id or by "owner@email/name" (something shared with
        you) into a RemoteObject."""
        data = self._http.request("GET", "/api/v1/files/resolve", params={"ref": ref})
        return wrap_file(self, FileInfo.model_validate(data))

    def get(self, file_id: str) -> RemoteObject:
        return wrap_file(self, self._get_file(file_id))

    def _get_file(self, file_id: str) -> FileInfo:
        return FileInfo.model_validate(self._http.request("GET", f"/api/v1/files/{file_id}"))

    def _download_url(self, file_id: str, *, ttl: int = 3600) -> DownloadUrl:
        return DownloadUrl.model_validate(
            self._http.request("GET", f"/api/v1/files/{file_id}/download-url", params={"ttl": ttl}))

    def _download_to(self, file_id: str, dest: Path) -> Path:
        d = self._download_url(file_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        n = self._http.stream_to_file(d.url, dest)
        if d.size_bytes and n != d.size_bytes:
            raise TransferError(f"Downloaded {n} bytes, expected {d.size_bytes}.")
        return dest

    def _read_bytes(self, file_id: str) -> bytes:
        return self._http.get_bytes(self._download_url(file_id).url)

    def download(self, ref: str, path: Optional[PathLike] = None, *, extract: bool = False):
        """Convenience: read(ref).download(path)."""
        return self.read(ref).download(path, extract=extract)

    # ── listing / sharing ─────────────────────────────────────
    def list(self, scope: str = "mine", *, limit: int = 50) -> list:
        data = self._http.request("GET", "/api/v1/files", params={"scope": scope, "limit": limit})
        return [wrap_file(self, FileInfo.model_validate(x)) for x in data.get("items", [])]

    def inbox(self, *, limit: int = 50) -> list:
        """Files other people shared with you."""
        data = self._http.request("GET", "/api/v1/inbox", params={"limit": limit})
        return [wrap_file(self, FileInfo.model_validate(x)) for x in data.get("items", [])]

    def share(self, obj: Union[RemoteObject, str], *, to: str, message: Optional[str] = None) -> Share:
        file_id = obj.id if isinstance(obj, RemoteObject) else obj
        body = {"to": to}
        if message:
            body["message"] = message
        return Share.model_validate(self._http.request("POST", f"/api/v1/files/{file_id}/share", json=body))

    def shares(self, obj: Union[RemoteObject, str]) -> list:
        file_id = obj.id if isinstance(obj, RemoteObject) else obj
        return [Share.model_validate(x) for x in self._http.request("GET", f"/api/v1/files/{file_id}/shares")]

    def unshare(self, obj: Union[RemoteObject, str], *, to: str) -> None:
        file_id = obj.id if isinstance(obj, RemoteObject) else obj
        self._http.request("DELETE", f"/api/v1/files/{file_id}/share", params={"to": to})

    def delete(self, obj: Union[RemoteObject, str]) -> None:
        file_id = obj.id if isinstance(obj, RemoteObject) else obj
        self._http.request("DELETE", f"/api/v1/files/{file_id}")

    # ── compute helpers (used by Job / resources / objects) ───
    def _get_job(self, job_id: str) -> JobModel:
        return JobModel.model_validate(self._http.request("GET", f"/api/v1/jobs/{job_id}"))

    def _job_logs(self, job_id: str, offset: int = 0):
        data = self._http.request("GET", f"/api/v1/jobs/{job_id}/logs", params={"offset": offset})
        return data.get("lines", [])

    def _job_output(self, job_id: str):
        data = self._http.request("GET", f"/api/v1/jobs/{job_id}/result")
        out = data.get("output")
        return wrap_file(self, FileInfo.model_validate(out)) if out else None

    def _volume_info(self, file_id: str) -> dict:
        return self._http.request("GET", f"/api/v1/volumes/{file_id}/info")

    def _wrap(self, data: dict):
        return wrap_file(self, FileInfo.model_validate(data))

    def _view_url(self, file_id: str) -> str:
        return self._http.request("GET", f"/api/v1/files/{file_id}/view-url")["url"]

    def _registration_url(self, fixed_id: str, moving_id=None, method: str = "rigid") -> str:
        body = {"fixed_file_id": fixed_id, "method": method}
        if moving_id:
            body["moving_file_id"] = moving_id
        return self._http.request("POST", "/api/v1/viz/registration", json=body)["url"]

    def view(self, *objs) -> str:
        """MeshLab-style viewer URL for one or several files/objects."""
        ids = [o.id if isinstance(o, RemoteObject) else o for o in objs]
        if len(ids) == 1:
            return self._view_url(ids[0])
        return self._http.request("POST", "/api/v1/viz/view", json={"file_ids": ids})["url"]

    def view_registration(self, fixed, moving=None, *, method: str = "rigid") -> str:
        """4-panel DICOM/registration slicer URL for one or two volumes."""
        fid = fixed.id if isinstance(fixed, RemoteObject) else fixed
        mid = moving.id if isinstance(moving, RemoteObject) else moving
        return self._registration_url(fid, mid, method)

    def run(self, module_id: str, method_id: str, input, *, moving=None, wait: bool = True, **params):
        """Run a module on a file id / RemoteObject. Returns the output object."""
        job = self.jobs.submit(module_id, method_id, input, moving=moving, params=params or None)
        if wait:
            job.wait()
            return job.result(wait=False)
        return job

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
