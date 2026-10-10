"""PardesLine — transfer files between accounts in a few lines.

    import pardesline as pl
    pl.login()
    obj = pl.upload("scan.ply")
    pl.share(obj, to="bob@lab.org")

    # bob:
    pl.read("alice@lab.org/scan.ply").download("scan.ply")

The module-level helpers use a default client built lazily from the stored
credentials (PARDESLINE_API_KEY or ~/.pardesline/token). For explicit control,
use the Client class.
"""

from __future__ import annotations

from typing import Optional

from .._version import __version__

from .client import Client
from .errors import (
    AuthError,
    Conflict,
    Forbidden,
    GpuAddonRequired,
    NotFound,
    PardesLineError,
    PlatformLocked,
    QuotaExceeded,
    RateLimited,
    TooLarge,
    TransferError,
)
from .objects import RemoteObject

__all__ = [
    "AuthError",
    "Client",
    "Conflict",
    "Forbidden",
    "GpuAddonRequired",
    "NotFound",
    "PardesLineError",
    "PlatformLocked",
    "QuotaExceeded",
    "RateLimited",
    "RemoteObject",
    "TooLarge",
    "TransferError",
    "delete",
    "download",
    "gpu",
    "inbox",
    "list_files",
    "login",
    "logout",
    "me",
    "np",
    "o3d",
    "pv",
    "read",
    "send",
    "share",
    "sitk",
    "upload",
    "upload_bytes",
    "view",
    "view_registration",
    "whoami",
]

_default: Optional[Client] = None


def _client() -> Client:
    global _default
    if _default is None:
        _default = Client()
    return _default


def login(token: Optional[str] = None, *, email: Optional[str] = None, save: bool = True) -> Client:
    """Log in (terminal email+code flow, or with a pl_ key). Returns the client."""
    global _default
    _default = Client(token=token) if token else Client()
    return _default.login(token=token, email=email, save=save)


def logout() -> None:
    _client().logout()


def whoami() -> Optional[str]:
    return _client().whoami()


def me():
    return _client().me()


def upload(path, *, name=None, project=None, workspace=None) -> RemoteObject:
    return _client().upload(path, name=name, project=project, workspace=workspace)


def upload_bytes(data: bytes, name: str, *, project=None) -> RemoteObject:
    return _client().upload_bytes(data, name, project=project)


def send(path, to: str, *, name=None, message=None) -> RemoteObject:
    """Upload a local file and hand it to another account in one call."""
    return _client().send(path, to=to, name=name, message=message)


def read(ref: str) -> RemoteObject:
    return _client().read(ref)


def download(ref: str, path=None, *, extract: bool = False):
    return _client().download(ref, path, extract=extract)


def share(obj, *, to: str, message: Optional[str] = None):
    return _client().share(obj, to=to, message=message)


def inbox(*, limit: int = 50):
    return _client().inbox(limit=limit)


def list_files(scope: str = "mine", *, limit: int = 50):
    return _client().list(scope, limit=limit)


def delete(obj) -> None:
    _client().delete(obj)


def view(*objs):
    return _client().view(*objs)


def view_registration(fixed, moving=None, *, method: str = "rigid"):
    return _client().view_registration(fixed, moving, method=method)


class _GpuProxy:
    def __getattr__(self, name):
        return getattr(_client().gpu, name)


gpu = _GpuProxy()


class _LibProxy:
    """Module-level pl.o3d / pl.pv / pl.sitk / pl.np — the faithful, server-side
    mirrors of open3d / pyvista / SimpleITK / numpy (bound to the default client)."""

    def __init__(self, attr: str):
        self._attr = attr

    def __getattr__(self, name: str):
        return getattr(getattr(_client(), self._attr), name)

    def __call__(self, *args, **kwargs):
        return getattr(_client(), self._attr)(*args, **kwargs)


o3d = _LibProxy("o3d")
pv = _LibProxy("pv")
sitk = _LibProxy("sitk")
np = _LibProxy("np")
