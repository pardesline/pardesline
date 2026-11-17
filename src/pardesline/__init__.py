"""PardesLine — 3D vision and medical imaging, on your machine.

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

Everything executes on this machine. The package talks to no PardesLine service;
the only network traffic is the public dataset downloads you ask for.
"""

from __future__ import annotations

from typing import Any

from ._version import __version__
from .catalog import Catalog, Method, Module, Parameter, load_catalog
from .data import Dataset, Manifest, Sample, cache_dir, datasets, scan, set_cache_dir
from .data import load as load
from .data.manifest import Layout
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
from .object import Frame, Image, LabelMap, License, Mesh, Object, PointCloud, RawArray, Transform, Volume
from .runner import RunResult, output_dir, run, set_output_dir

__all__ = [
    "Catalog",
    "CatalogError",
    "Dataset",
    "FetchError",
    "Frame",
    "Image",
    "LabelMap",
    "Layout",
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
    "RawArray",
    "RunError",
    "RunResult",
    "Sample",
    "Transform",
    "Volume",
    "__version__",
    "cache_dir",
    "catalog",
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


# Names of the 0.1-0.5 platform client, removed in 0.6: the open-source package does not talk to
# any PardesLine service. Kept only to explain the AttributeError.
_REMOVED_PLATFORM_NAMES = frozenset(
    {
        "cloud",
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

# pl.o3d / pl.pv / pl.sitk / pl.np: the real library when it is installed.
_LIB_NAMES = {"o3d": "open3d", "pv": "pyvista", "sitk": "SimpleITK", "np": "numpy"}
_LIB_EXTRAS = {"o3d": "local", "pv": "local", "sitk": "medical", "np": "all"}


class _MissingLibrary:
    """Stands for a library that is not installed.

    Any use raises MissingDependency; attribute probes (hasattr, dir, introspection) still work, which
    an exception raised from the module ``__getattr__`` would break."""

    def __init__(self, name: str):
        self._name = name

    def _error(self) -> MissingDependency:
        return MissingDependency(_LIB_NAMES[self._name], _LIB_EXTRAS[self._name])

    def __getattr__(self, attr: str) -> Any:
        if attr.startswith("__"):
            raise AttributeError(attr)
        raise self._error()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise self._error()

    def __repr__(self) -> str:
        return f"<pl.{self._name}: {self._error()}>"


def __getattr__(name: str) -> Any:
    if name in _LIB_NAMES:
        import importlib

        try:
            return importlib.import_module(_LIB_NAMES[name])
        except ImportError:
            return _MissingLibrary(name)
    if name in _REMOVED_PLATFORM_NAMES:
        raise AttributeError(
            f"pl.{name} belonged to the PardesLine platform client, removed in pardesline 0.6: the "
            "open-source package runs entirely on your machine and talks to no PardesLine service."
        )
    raise AttributeError(f"module 'pardesline' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LIB_NAMES))
