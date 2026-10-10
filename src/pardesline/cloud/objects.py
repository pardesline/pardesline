"""RemoteObject — a handle on a file living in PardesLine storage.

Returned by pl.upload() / pl.read() / pl.inbox(). Carries the file metadata and
the actions a user wants on a transferred file: download it, share it, delete
it. Compute methods (icp, register, …) are added in a later release.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from .models import FileInfo

if TYPE_CHECKING:
    from .client import Client


class RemoteObject:
    def __init__(self, client: Client, info: FileInfo):
        self._client = client
        self._info = info

    # ── identity ──────────────────────────────────────────────
    @property
    def id(self) -> str:
        return self._info.id

    @property
    def name(self) -> str:
        return self._info.name

    @property
    def size_bytes(self) -> int:
        return self._info.size_bytes

    @property
    def geometry_type(self) -> Optional[str]:
        return self._info.geometry_type

    @property
    def owner(self) -> Optional[str]:
        return self._info.owner_email

    @property
    def shared_by(self) -> Optional[str]:
        return self._info.shared_by

    @property
    def info(self) -> FileInfo:
        return self._info

    def refresh(self) -> RemoteObject:
        self._info = self._client._get_file(self.id)
        return self

    # ── actions ───────────────────────────────────────────────
    def download(self, path: Union[str, os.PathLike, None] = None, *, extract: bool = False):
        """Download the bytes to `path` (default: the file's own name in the
        cwd). If the file is a zipped folder, extract=True unpacks it and
        returns the destination directory."""
        dest = Path(path) if path is not None else Path(self.name)
        self._client._download_to(self.id, dest)
        if extract and zipfile.is_zipfile(dest):
            out_dir = dest.with_suffix("") if dest.suffix == ".zip" else Path(str(dest) + "_extracted")
            out_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(out_dir)
            return out_dir
        return dest

    def read_bytes(self) -> bytes:
        return self._client._read_bytes(self.id)

    def download_url(self, ttl: int = 3600) -> str:
        """A time-limited URL anyone can GET the bytes from (share by link)."""
        return self._client._download_url(self.id, ttl=ttl).url

    def share(self, to: str, *, message: Optional[str] = None):
        return self._client.share(self, to=to, message=message)

    def delete(self) -> None:
        self._client.delete(self.id)

    # ── compute ───────────────────────────────────────────────
    def run(self, module_id: str, method_id: str, *, moving=None, wait: bool = True, **params):
        """Run a module method on this object. Returns the resulting RemoteObject
        (waits by default), or the Job handle when wait=False."""
        job = self._client.jobs.submit(module_id, method_id, self, moving=moving, params=params or None)
        if wait:
            job.wait()
            return job.result(wait=False)
        return job

    def methods(self) -> list:
        """Method ids that apply to this object's geometry."""
        from ._catalog import get_catalog
        return get_catalog(self._client).methods_for(self._info.extension)

    def _resolve_method(self, name: str):
        """(module_id, method_id) for a curated alias or a catalog method_id
        applicable to this object's extension. Raises AttributeError otherwise."""
        from ._catalog import ALIASES, get_catalog
        if name in ALIASES:
            return ALIASES[name]
        resolved = get_catalog(self._client).resolve(name, self._info.extension)
        if resolved is None:
            raise AttributeError(
                f"{type(self).__name__} has no method {name!r}. "
                f"See obj.methods() or use obj.run(module_id, method_id, ...).")
        return resolved[0], name

    def params(self, method: str) -> list:
        """The full parameter schema (name/type/default/min/max/description) for
        one of this object's methods — every knob, all optional."""
        from ._catalog import get_catalog
        module_id, method_id = self._resolve_method(method)
        return get_catalog(self._client).params(module_id, method_id)

    def describe(self, method: str) -> str:
        """Pretty-print every tunable parameter of a method (name, default,
        range, description). e.g. print(obj.describe('icp'))."""
        from ._catalog import get_catalog
        module_id, method_id = self._resolve_method(method)
        return get_catalog(self._client).describe(module_id, method_id)

    # ── visualization ─────────────────────────────────────────
    def view(self) -> str:
        """A fast, login-free URL that opens this file in the standalone 3D
        viewer (point cloud or mesh). The link carries a short-lived signed
        token, so it opens without signing in and without booting the app."""
        return self._client._view_url(self.id)

    def share_link(self) -> str:
        """A public, revocable viewer link. Anyone you send it to can open the
        object in the 3D viewer with NO account and NO access to yours. Revoke
        by making the file private again."""
        return self._client._http.request("POST", f"/api/v1/files/{self.id}/share-link")["url"]

    def __getattr__(self, name: str):
        # Catalog-driven method resolution: obj.voxel_downsample(...) or a
        # curated alias obj.downsample(...). Only consulted for names Python
        # did not find as real attributes (so it never shadows the API above).
        if name.startswith("_"):
            raise AttributeError(name)
        from ._catalog import get_catalog
        module_id, method_id = self._resolve_method(name)
        cat = get_catalog(self._client)

        def _call(*args, wait: bool = True, **params):
            moving = args[0] if args else params.pop("moving", None)
            cat.validate_params(module_id, method_id, params)
            return self.run(module_id, method_id, moving=moving, wait=wait, **params)

        _call.__name__ = name
        _call.__doc__ = cat.describe(module_id, method_id)
        return _call

    def __repr__(self) -> str:
        owner = f" from {self.shared_by}" if self.shared_by else ""
        mb = self.size_bytes / 1e6
        geo = f" {self.geometry_type}" if self.geometry_type else ""
        return f"<{type(self).__name__}{geo} {self.name!r} ({mb:.1f} MB){owner} id={self.id[:8]}>"


class PointCloud(RemoteObject):
    pass


class Mesh(RemoteObject):
    pass


class Volume(RemoteObject):
    def info(self) -> dict:
        """Volume geometry: dimensions, spacing (mm), origin, scalar range."""
        return self._client._volume_info(self.id)

    def view(self, moving=None, *, method: str = "rigid") -> str:
        """Open this volume (optionally with a `moving` volume) in the 4-panel
        DICOM / registration slicer studio. Returns a URL."""
        mv = moving.id if isinstance(moving, RemoteObject) else moving
        return self._client._registration_url(self.id, mv, method)


class Transform(RemoteObject):
    pass


class Image(RemoteObject):
    pass


class Archive(RemoteObject):
    pass


_BY_GEOMETRY = {
    "pointcloud": PointCloud, "mesh": Mesh, "volume": Volume,
    "transform": Transform, "image": Image, "archive": Archive,
}

_BY_EXT = {
    ".ply": PointCloud, ".pcd": PointCloud, ".xyz": PointCloud, ".pts": PointCloud, ".las": PointCloud,
    ".stl": Mesh, ".obj": Mesh, ".glb": Mesh, ".vtp": Mesh,
    ".vti": Volume, ".vtu": Volume, ".vtk": Volume, ".mha": Volume, ".nrrd": Volume, ".nii": Volume, ".dcm": Volume,
    ".tfm": Transform, ".hdf5": Transform, ".h5": Transform,
    ".png": Image, ".jpg": Image, ".jpeg": Image,
    ".zip": Archive,
}


def wrap_file(client, info: FileInfo) -> RemoteObject:
    """Pick the RemoteObject subclass from the file's geometry/extension."""
    cls = _BY_GEOMETRY.get((info.geometry_type or "").lower())
    if cls is None:
        cls = _BY_EXT.get((info.extension or "").lower(), RemoteObject)
    return cls(client, info)
