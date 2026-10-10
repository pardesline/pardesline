"""Bind module methods onto the remote object classes from the live catalog.

The platform's /api/v1/modules lists every module, its methods and which input
geometry it accepts. We expose each method_id as a Python method on the object
type it applies to (a point-cloud method on PointCloud, a volume method on
Volume, …) plus a set of curated friendly aliases. Everything ultimately calls
obj.run(module_id, method_id, **params).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .client import Client

# Curated, human-friendly aliases → (module_id, method_id). Keep small and
# obvious; anything else is reachable via obj.run(...) or the generated names.
ALIASES: Dict[str, Tuple[str, str]] = {
    # point cloud
    "downsample": ("point_cloud_processing", "voxel_downsample"),
    "remove_outliers": ("point_cloud_processing", "statistical_outlier_removal"),
    "poisson": ("point_cloud_reconstruction", "poisson"),
    "ball_pivoting": ("point_cloud_reconstruction", "ball_pivoting"),
    "normals": ("features_extraction", "normal_estimation"),
    "icp": ("registration", "icp_refinement"),
    "ransac": ("registration", "ransac_global"),
    # mesh
    "decimate": ("pyvista_mesh_processing", "pv_decimate"),
    "smooth": ("pyvista_mesh_processing", "pv_smooth_laplacian"),
    "to_points": ("mesh_processing", "mesh_to_pcd_poisson_disk"),
    # volume / medical (dual-input handled positionally)
    "register": ("simpleitk_registration", "rigid"),
    "segment": ("simpleitk_segmentation", "otsu_threshold"),
}


class Catalog:
    """Loaded once per client from /api/v1/modules."""

    def __init__(self, modules: List[dict]):
        self.modules = modules
        # method_id -> list of (module_id, accepted_extensions, dual_input)
        # We gate by the file EXTENSION against the module's input_formats (like
        # the server), NOT by coarse geometry: a .ply may be a mesh or a point
        # cloud, and a module accepting .ply applies to both.
        self._by_method: Dict[str, List[Tuple[str, frozenset, bool]]] = {}
        # (module_id, method_id) -> [param schema dicts] and -> display name
        self._params: Dict[Tuple[str, str], List[dict]] = {}
        self._method_name: Dict[Tuple[str, str], str] = {}
        for m in modules:
            exts = frozenset((e or "").lower() for e in (m.get("input_formats") or []))
            for meth in m.get("methods", []):
                self._by_method.setdefault(meth["id"], []).append(
                    (m["id"], exts, bool(meth.get("dual_input") or m.get("dual_input"))))
                self._params[(m["id"], meth["id"])] = list(meth.get("parameters") or [])
                self._method_name[(m["id"], meth["id"])] = meth.get("name") or meth["id"]

    def params(self, module_id: str, method_id: str) -> List[dict]:
        """The parameter schema (name/type/default/min/max/description) for a
        method — every knob the algorithm accepts, all optional."""
        return self._params.get((module_id, method_id), [])

    def validate_params(self, module_id: str, method_id: str, params: dict) -> None:
        """Raise a helpful ValueError if a param name isn't accepted by this
        method. No-op when the method is unknown to the catalog (forward-compat)."""
        key = (module_id, method_id)
        if key not in self._params:
            return
        known = {p.get("name") for p in self._params[key]}
        unknown = [k for k in params if k not in known]
        if not unknown:
            return
        if known:
            hint = "Accepted: " + ", ".join(sorted(n for n in known if n)) + "."
        else:
            hint = "This method takes no parameters."
        raise ValueError(
            f"{module_id}.{method_id}: unknown parameter(s) {', '.join(unknown)}. {hint} "
            f"See obj.describe({method_id!r}).")

    def describe(self, module_id: str, method_id: str) -> str:
        """A human-readable listing of every parameter + default + range."""
        rows = self._params.get((module_id, method_id))
        title = f"{module_id}.{method_id}  ({self._method_name.get((module_id, method_id), method_id)})"
        if not rows:
            return f"{title}\n  (no tunable parameters)"
        lines = [title]
        for p in rows:
            name = p.get("name", "?")
            typ = p.get("type", "")
            dflt = p.get("default")
            rng = ""
            if p.get("min") is not None or p.get("max") is not None:
                rng = f" [{p.get('min')}..{p.get('max')}]"
            opts = f" {{{', '.join(map(str, p['options']))}}}" if p.get("options") else ""
            desc = p.get("description", "")
            lines.append(f"  {name}: {typ}={dflt!r}{rng}{opts}  {desc}".rstrip())
        return "\n".join(lines)

    def resolve(self, method_id: str, extension: Optional[str]) -> Optional[Tuple[str, bool]]:
        """(module_id, dual_input) for a method whose module accepts `extension`,
        else None."""
        candidates = self._by_method.get(method_id)
        if not candidates:
            return None
        ext = (extension or "").lower()
        if ext:
            for module_id, exts, dual in candidates:
                if not exts or ext in exts:
                    return module_id, dual
            return None
        module_id, _exts, dual = candidates[0]
        return module_id, dual

    def methods_for(self, extension: Optional[str]) -> List[str]:
        ext = (extension or "").lower()
        names = set()
        for method_id, entries in self._by_method.items():
            for _module_id, exts, _dual in entries:
                if not ext or not exts or ext in exts:
                    names.add(method_id)
                    break
        return sorted(names)


_cache: Dict[str, Catalog] = {}


def get_catalog(client: Client) -> Catalog:
    key = client.base_url
    cat = _cache.get(key)
    if cat is None:
        cat = Catalog([m.model_dump() if hasattr(m, "model_dump") else m for m in client.modules.list()])
        _cache[key] = cat
    return cat
