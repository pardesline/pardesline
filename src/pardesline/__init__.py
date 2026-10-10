"""PardesLine — 3D vision and medical imaging, locally or in the cloud.

    import pardesline as pl

    scan = pl.load("scan.ply")                       # a local point cloud (Object)
    surface = scan.downsample(voxel_size=0.01).poisson(depth=9)
    surface.save("surface.ply")                      # + surface.ply.pardesline.json (frame, licence…)

    ds = pl.load("rire_brain")                       # a dataset: manifest + fetched-on-access files
    s = ds[0]; s.roles                               # ['ct', 'mr_t1']
    moved = s.ct.align(s.mr_t1)                      # rigid registration, transform in moved.transform

    ds = pl.load("/data/study_A", license="internal", units={"mesh": "mm"})   # your own folder

    pl.run("simpleitk_registration", "rigid", "ct.mha", moving="mr.mha")
    pl.catalog().describe("point_cloud_reconstruction.poisson")

Everything under ``pl.run`` / ``pl.load`` executes on this machine. The cloud
client (``pl.login``, ``pl.upload``, ``pl.share``, hosted compute, viewers)
lives in ``pardesline.cloud`` and stays reachable from the top level.
"""

from __future__ import annotations

from typing import Any

from ._version import __version__
from .catalog import Catalog, Method, Module, Parameter, load_catalog
from .data import Dataset, Manifest, Sample, cache_dir, datasets, scan, set_cache_dir
from .data import load as load
from .errors import (
    CatalogError,
    FetchError,
    ManifestError,
    MissingDependency,
    NeedsConfirmation,
    ParameterError,
    PardesLineError,
    RunError,
)
from .object import Frame, Image, LabelMap, License, Mesh, Object, PointCloud, Transform, Volume
from .runner import RunResult, output_dir, run, set_output_dir

__all__ = [
    "Catalog",
    "CatalogError",
    "Dataset",
    "FetchError",
    "Frame",
    "Image",
    "LabelMap",
    "License",
    "Manifest",
    "ManifestError",
    "Mesh",
    "Method",
    "MissingDependency",
    "Module",
    "NeedsConfirmation",
    "Object",
    "Parameter",
    "ParameterError",
    "PardesLineError",
    "PointCloud",
    "RunError",
    "RunResult",
    "Sample",
    "Transform",
    "Volume",
    "__version__",
    "cache_dir",
    "catalog",
    "cloud",
    "datasets",
    "describe",
    "load",
    "modules",
    "output_dir",
    "run",
    "scan",
    "set_cache_dir",
    "set_output_dir",
]


def catalog() -> Catalog:
    """The bundled catalog of modules, methods and parameters."""
    return load_catalog()


def modules() -> list[str]:
    """Module ids, in platform order."""
    return [m.id for m in load_catalog()]


def describe(what: str) -> str:
    """``describe("module")``, ``describe("module.method")`` or a dataset name."""
    for m in datasets():
        if m.name == what:
            return m.describe()
    return load_catalog().describe(what)


# ---- cloud client, lazily -----------------------------------------------
# 0.1.x exposed the cloud helpers at the top level. They still work, without
# importing the HTTP client until first use.
_CLOUD_NAMES = frozenset(
    {
        "Client",
        "RemoteObject",
        "AuthError",
        "Conflict",
        "Forbidden",
        "GpuAddonRequired",
        "NotFound",
        "PlatformLocked",
        "QuotaExceeded",
        "RateLimited",
        "TooLarge",
        "TransferError",
        "login",
        "logout",
        "whoami",
        "me",
        "upload",
        "upload_bytes",
        "send",
        "read",
        "download",
        "share",
        "inbox",
        "list_files",
        "delete",
        "view",
        "view_registration",
        "gpu",
    }
)

# pl.o3d / pl.pv / pl.sitk / pl.np: the real library when it is installed,
# otherwise the cloud-executed mirror from 0.1.x.
_LIB_NAMES = {"o3d": "open3d", "pv": "pyvista", "sitk": "SimpleITK", "np": "numpy"}


def __getattr__(name: str) -> Any:
    if name == "cloud":
        from . import cloud

        return cloud
    if name in _CLOUD_NAMES:
        from . import cloud

        return getattr(cloud, name)
    if name in _LIB_NAMES:
        import importlib

        try:
            return importlib.import_module(_LIB_NAMES[name])
        except ImportError:
            from . import cloud

            return getattr(cloud, name)
    raise AttributeError(f"module 'pardesline' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | _CLOUD_NAMES | set(_LIB_NAMES))
