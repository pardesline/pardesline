"""pl.o3d / pl.pv / pl.sitk — faithful, server-side mirrors of open3d, pyvista
and SimpleITK.

You write the SAME code as with the real library, but nothing heavy runs
locally: each expression is recorded into a lazy op-graph and only sent to the
platform when you materialize it (``.value()``, ``.numpy()``, ``.to_file()``,
``.view()``). The whole graph then runs start-to-finish, server-side, on the
real library, and returns a value or a PardesLine file.

    import pardesline as pl
    f    = pl.upload("scan.ply")                     # a PardesLine file
    pcd  = pl.o3d.io.read_point_cloud(f)             # runs on the server
    down = pcd.voxel_down_sample(0.05)               # still server-side
    down.view()                                      # -> fast 3D viewer URL

This is the `pl.o3d` world (the libraries, faithful). The `pl.*` world is the
PardesLine-specific value-add (transfer, sharing, the curated algorithms).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    from .client import Client


class _Graph:
    def __init__(self) -> None:
        self.nodes: List[dict] = []

    def add(self, node: dict) -> int:
        node["id"] = len(self.nodes)
        self.nodes.append(node)
        return node["id"]


def _is_remote(x) -> bool:
    return isinstance(x, (RemoteValue, _Bound))


def _rv(x):
    """Coerce a _Bound (unrealised attribute) to a RemoteValue node."""
    return x._as_value() if isinstance(x, _Bound) else x


def _collect(objs) -> List[RemoteValue]:
    out: List[RemoteValue] = []

    def walk(v):
        if isinstance(v, _Bound):
            out.append(_rv(v))
        elif isinstance(v, RemoteValue):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            for e in v:
                walk(e)
        elif isinstance(v, dict):
            for e in v.values():
                walk(e)

    walk(objs)
    return out


def _merge(rvs: List[RemoteValue]) -> Tuple[_Graph, Dict[Tuple[int, int], int]]:
    """Merge the graphs of several remote values into one, remapping ids."""
    g = _Graph()
    remap: Dict[Tuple[int, int], int] = {}
    done = set()
    for rv in rvs:
        key = id(rv._g)
        if key in done:
            continue
        for node in rv._g.nodes:
            nn = dict(node)
            if "target" in nn:
                nn["target"] = remap[(key, nn["target"])]
            nn["args"] = _remap(nn.get("args", []), key, remap)
            nn["kwargs"] = _remap(nn.get("kwargs", {}), key, remap)
            if "key" in nn:
                nn["key"] = _remap(nn["key"], key, remap)
            if "value" in nn:
                nn["value"] = _remap(nn["value"], key, remap)
            old = nn.pop("id")
            remap[(key, old)] = g.add(nn)
        done.add(key)
    return g, remap


def _remap(v, key, remap):
    if isinstance(v, dict):
        if "$ref" in v:
            return {"$ref": remap[(key, v["$ref"])]}
        return {k: _remap(e, key, remap) for k, e in v.items()}
    if isinstance(v, list):
        return [_remap(e, key, remap) for e in v]
    return v


def _encode(v, remap):
    """JSON-encode an argument, turning remote values / files / arrays into refs."""
    if isinstance(v, _Bound):
        v = _rv(v)
    if isinstance(v, RemoteValue):
        return {"$ref": remap[(id(v._g), v._id)]}
    from .objects import RemoteObject
    if isinstance(v, RemoteObject):
        return {"$file": v.id}
    if type(v).__module__ == "numpy":  # ndarray or numpy scalar
        try:
            import numpy as np
            if isinstance(v, np.ndarray):
                return {"$np": {"data": v.tolist(), "dtype": str(v.dtype)}}
            return v.item()
        except Exception:
            pass
    if isinstance(v, (list, tuple)):
        return [_encode(e, remap) for e in v]
    if isinstance(v, dict):
        return {k: _encode(e, remap) for k, e in v.items()}
    return v


def _coerce(v):
    """Turn every _Bound (an unrealised attribute) into a RemoteValue node ONCE,
    so _collect (merge) and _encode operate on the same graph nodes."""
    if isinstance(v, _Bound):
        return v._as_value()
    if isinstance(v, (list, tuple)):
        return [_coerce(e) for e in v]
    if isinstance(v, dict):
        return {k: _coerce(e) for k, e in v.items()}
    return v


def _build(client, target, add_node, args=(), kwargs=None) -> RemoteValue:
    """Merge the graphs of the target + all remote args, append `add_node`
    (a callable given (graph, remapped_target_id, encoded_args, encoded_kwargs)),
    and return the resulting RemoteValue."""
    kwargs = {k: _coerce(v) for k, v in (kwargs or {}).items()}
    args = [_coerce(a) for a in args]
    rvs = _collect([target, args, kwargs]) if target is not None else _collect([args, kwargs])
    g, remap = _merge(rvs)
    tid = remap[(id(target._g), target._id)] if target is not None else None
    enc_args = [_encode(a, remap) for a in args]
    enc_kwargs = {k: _encode(v, remap) for k, v in kwargs.items()}
    nid = add_node(g, tid, enc_args, enc_kwargs)
    return RemoteValue(client, g, nid)


class RemoteValue:
    """A node in the lazy op-graph. Extend it with attribute/method/index
    access; realise it with .value()/.numpy()/.to_file()/.view()."""

    def __init__(self, client: Client, graph: _Graph, node_id: int):
        self._c = client
        self._g = graph
        self._id = node_id

    # ── graph extension ───────────────────────────────────────
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return _Bound(self._c, self, name)

    def __getitem__(self, key):
        return _build(self._c, self, lambda g, t, a, k: g.add(
            {"op": "getitem", "target": t, "key": a[0]}), args=(key,))

    def _as_value(self):
        return self

    # ── materialisation ───────────────────────────────────────
    def _eval(self, mode: str, output_name=None):
        body = {"nodes": self._g.nodes, "return": self._id, "mode": mode}
        if output_name is not None:
            body["output_name"] = output_name
        return self._c._http.request("POST", "/api/v1/rpc/eval", json=body, timeout=600)

    def value(self):
        """Run the graph and return the plain value (number / list / string)."""
        return self._eval("value")["result"]

    def numpy(self):
        import numpy as np
        return np.array(self.value())

    def to_file(self, name: str | None = None):
        """Run the graph and register the resulting object (point cloud / mesh /
        volume / ndarray) as a PardesLine file. Returns a RemoteObject."""
        data = self._eval("file", output_name=name)
        from .models import FileInfo
        from .objects import wrap_file
        return wrap_file(self._c, FileInfo.model_validate(data))

    def download(self, path=None, **kw):
        return self.to_file().download(path, **kw)

    def view(self) -> str:
        """Fast, login-free 3D viewer URL for the result."""
        return self.to_file().view()

    def share_link(self) -> str:
        """Public, revocable viewer link for the result."""
        return self.to_file().share_link()

    def __float__(self):
        return float(self.value())

    def __int__(self):
        return int(self.value())

    def __bool__(self):
        return bool(self.value())

    def __repr__(self):
        return f"<pl.remote node#{self._id} ({len(self._g.nodes)} ops)>"


class _Bound:
    """Result of attribute access on a remote value: call it (a method) or
    materialise/extend it (an attribute)."""

    def __init__(self, client, target: RemoteValue, name: str):
        self._c = client
        self._target = target
        self._name = name

    def __call__(self, *args, **kwargs):
        return _build(self._c, self._target, lambda g, t, a, k: g.add(
            {"op": "method", "target": t, "name": self._name, "args": a, "kwargs": k}),
            args, kwargs)

    def _as_value(self) -> RemoteValue:
        return _build(self._c, self._target, lambda g, t, a, k: g.add(
            {"op": "getattr", "target": t, "name": self._name}))

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return _Bound(self._c, self._as_value(), name)

    def __getitem__(self, key):
        return self._as_value()[key]

    def value(self):
        return self._as_value().value()

    def numpy(self):
        return self._as_value().numpy()

    def to_file(self, name=None):
        return self._as_value().to_file(name)

    def view(self):
        return self._as_value().view()

    def share_link(self):
        return self._as_value().share_link()

    def __float__(self):
        return float(self._as_value())

    def __int__(self):
        return int(self._as_value())

    def __repr__(self):
        return f"<pl.remote attr '{self._name}'>"


class _Namespace:
    """A path inside a mirrored library, e.g. pl.o3d.io.read_point_cloud."""

    def __init__(self, client: Client, lib: str, path: Tuple[str, ...] = ()):
        self._c = client
        self._lib = lib
        self._path = path

    def __getattr__(self, name: str) -> _Namespace:
        if name.startswith("_"):
            raise AttributeError(name)
        return _Namespace(self._c, self._lib, self._path + (name,))

    def __call__(self, *args, **kwargs) -> RemoteValue:
        return _build(self._c, None, lambda g, t, a, k: g.add(
            {"op": "call", "lib": self._lib, "path": list(self._path), "args": a, "kwargs": k}),
            args, kwargs)

    def __repr__(self):
        return f"<pl.{self._lib}{'.' + '.'.join(self._path) if self._path else ''}>"


def namespace(client: Client, lib: str) -> _Namespace:
    return _Namespace(client, lib)
