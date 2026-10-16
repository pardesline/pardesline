"""The typed catalog of modules, methods and parameters.

The catalog is generated from the same manifests that drive the PardesLine
platform (``catalog/data/<module>.json``). It is the single source of truth
for what an algorithm is called, which file types it accepts, which flags it
takes, their defaults and their ranges. Nothing here imports a native library.

    >>> import pardesline as pl
    >>> cat = pl.catalog()
    >>> m = cat.method("point_cloud_processing", "voxel_downsample")
    >>> m.validate({"voxel_size": 0.05})
    {'voxel_size': '0.05'}
"""

from __future__ import annotations

import builtins
import difflib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from ..errors import CatalogError, ParameterError

__all__ = ["Catalog", "Method", "Module", "Parameter", "load_catalog"]

PARAM_TYPES = ("float", "int", "bool", "enum", "string", "list")
_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f"}


@dataclass(frozen=True)
class Parameter:
    """One tunable flag of a method, as declared in the catalog."""

    name: str
    type: str
    default: Any
    description: str = ""
    min: float | None = None
    max: float | None = None
    options: tuple[str, ...] = ()
    advanced: bool = False
    rationale: str = ""  # why this default, and when to override it
    validated_on: str = ""  # the bundled data or test the method ran on with this default

    def coerce(self, value: Any, *, where: str = "") -> str:
        """Validate ``value`` against this parameter and return the string the
        script receives on its command line. Raises :class:`ParameterError`."""
        label = f"{where}{self.name}" if where else self.name
        try:
            if self.type == "float":
                out = self._number(value, float, label)
                self._check_range(out, label)
                return repr(out)
            if self.type == "int":
                out = self._number(value, int, label)
                self._check_range(out, label)
                return str(out)
            if self.type == "bool":
                return "true" if self._bool(value, label) else "false"
            if self.type == "enum":
                text = str(value)
                for opt in self.options:
                    if text.lower() == str(opt).lower():
                        return str(opt)
                raise ParameterError(f"{label}: {value!r} is not one of {list(self.options)}.")
            if self.type == "list":
                if isinstance(value, (list, tuple)):
                    return ",".join(str(v) for v in value)
                return str(value)
            if self.type == "string":
                if isinstance(value, (list, tuple, dict)):
                    raise ParameterError(f"{label}: expected text, got {type(value).__name__}.")
                return str(value)
        except ParameterError:
            raise
        except (TypeError, ValueError) as exc:
            raise ParameterError(f"{label}: {exc}") from None
        raise ParameterError(f"{label}: unsupported parameter type {self.type!r} in the catalog.")

    @staticmethod
    def _number(value: Any, kind: builtins.type[float] | builtins.type[int], label: str):
        if isinstance(value, bool):
            raise ParameterError(f"{label}: expected a {kind.__name__}, got a bool.")
        if isinstance(value, str):
            value = value.strip()
            try:
                value = float(value) if ("." in value or "e" in value.lower()) else int(value)
            except ValueError:
                raise ParameterError(f"{label}: expected a {kind.__name__}, got {value!r}.") from None
        if kind is int:
            if isinstance(value, float):
                if not value.is_integer():
                    raise ParameterError(f"{label}: expected an int, got {value!r}.")
                value = int(value)
            if not isinstance(value, int):
                raise ParameterError(f"{label}: expected an int, got {type(value).__name__}.")
            return value
        if not isinstance(value, (int, float)):
            raise ParameterError(f"{label}: expected a float, got {type(value).__name__}.")
        return float(value)

    @staticmethod
    def _bool(value: Any, label: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        text = str(value).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ParameterError(f"{label}: expected true/false, got {value!r}.")

    def _check_range(self, value: float, label: str) -> None:
        if self.min is not None and value < self.min:
            raise ParameterError(f"{label}: {value} is below the minimum {self.min}.")
        if self.max is not None and value > self.max:
            raise ParameterError(f"{label}: {value} is above the maximum {self.max}.")

    def describe(self) -> str:
        rng = ""
        if self.min is not None or self.max is not None:
            rng = f" [{self.min}..{self.max}]"
        opts = f" {{{', '.join(map(str, self.options))}}}" if self.options else ""
        adv = "  (advanced)" if self.advanced else ""
        why = f"\n      why: {self.rationale}" if self.rationale else ""
        head = f"{self.name}: {self.type} = {self.default!r}{rng}{opts}{adv}"
        return f"{head}\n      {self.description}{why}".rstrip()


@dataclass(frozen=True)
class Method:
    """One algorithm: a script with a typed parameter list."""

    id: str
    name: str
    module_id: str
    script: str
    output_extension: str
    dual_input: bool = False
    parameters: tuple[Parameter, ...] = ()
    validated_on: str = ""  # the bundled data or test this method's defaults were checked on

    @property
    def qualname(self) -> str:
        return f"{self.module_id}.{self.id}"

    @property
    def python_module(self) -> str:
        """Importable module name, runnable with ``python -m``."""
        return f"pardesline.ops.{self.module_id}.{Path(self.script).stem}"

    def script_path(self) -> Path:
        return Path(str(resources.files("pardesline.ops") / self.module_id / self.script))

    @property
    def param_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.parameters)

    def parameter(self, name: str) -> Parameter:
        for p in self.parameters:
            if p.name == name:
                return p
        raise ParameterError(self._unknown_message([name]))

    def validate(self, params: dict[str, Any] | None) -> dict[str, str]:
        """Check every supplied parameter and return the command-line strings.
        Unknown names, wrong types and out-of-range values raise
        :class:`ParameterError` with the accepted list."""
        params = dict(params or {})
        unknown = [k for k in params if k not in self.param_names]
        if unknown:
            raise ParameterError(self._unknown_message(unknown))
        out: dict[str, str] = {}
        for p in self.parameters:
            if p.name in params and params[p.name] is not None:
                out[p.name] = p.coerce(params[p.name], where=f"{self.qualname}: ")
        return out

    def _unknown_message(self, unknown: list[str]) -> str:
        names = ", ".join(unknown)
        if not self.parameters:
            return f"{self.qualname}: unknown parameter(s) {names}. This method takes no parameters."
        hints = []
        for u in unknown:
            close = difflib.get_close_matches(u, self.param_names, n=1)
            if close:
                hints.append(f"{u} -> {close[0]}?")
        hint = f" Did you mean: {'; '.join(hints)}." if hints else ""
        return (
            f"{self.qualname}: unknown parameter(s) {names}.{hint} Accepted: {', '.join(self.param_names)}."
        )

    def describe(self) -> str:
        head = f"{self.qualname}  -  {self.name}"
        if self.dual_input:
            head += "  (two inputs: input=fixed, moving=moving)"
        head += f"\n  output: {self.output_extension}"
        if self.validated_on:
            head += f"\n  defaults validated on: {self.validated_on}"
        if not self.parameters:
            return head + "\n  (no tunable parameters)"
        return head + "\n  parameters:\n" + "\n".join(f"    {p.describe()}" for p in self.parameters)


@dataclass(frozen=True)
class Module:
    """A family of methods sharing input formats."""

    id: str
    name: str
    description: str
    category: str
    order: int
    input_formats: tuple[str, ...]
    methods: dict[str, Method] = field(default_factory=dict)
    dual_input: bool = False
    dual_input_label: str = ""
    theory: dict[str, Any] = field(default_factory=dict)
    videos: tuple[dict[str, str], ...] = ()

    def accepts(self, extension: str | None) -> bool:
        """``True`` when the module reads files with this suffix. ``.nii.gz`` is
        accepted wherever ``.nii`` is: the readers (SimpleITK, VTK) handle the
        compression themselves."""
        ext = (extension or "").lower()
        if ext == ".nii.gz":
            return ".nii.gz" in self.input_formats or ".nii" in self.input_formats
        return bool(ext) and ext in self.input_formats

    def method(self, method_id: str) -> Method:
        try:
            return self.methods[method_id]
        except KeyError:
            close = difflib.get_close_matches(method_id, self.methods, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise CatalogError(
                f"Module {self.id!r} has no method {method_id!r}.{hint} Available: {', '.join(self.methods)}."
            ) from None

    def describe(self) -> str:
        lines = [f"{self.id}  -  {self.name}  [{self.category}]", f"  {self.description}"]
        lines.append(f"  input formats: {', '.join(self.input_formats)}")
        if self.dual_input:
            lines.append(f"  two inputs: fixed + moving ({self.dual_input_label or 'moving'})")
        lines.append("  methods:")
        for m in self.methods.values():
            lines.append(f"    {m.id:<32} {m.name}  ({len(m.parameters)} params)")
        return "\n".join(lines)


class Catalog:
    """All modules, ordered as on the platform."""

    def __init__(self, modules: list[Module]):
        self._modules: dict[str, Module] = {m.id: m for m in sorted(modules, key=lambda m: (m.order, m.id))}

    # ---- access ---------------------------------------------------------
    def __iter__(self) -> Iterator[Module]:
        return iter(self._modules.values())

    def __len__(self) -> int:
        return len(self._modules)

    def __contains__(self, module_id: object) -> bool:
        return module_id in self._modules

    @property
    def modules(self) -> list[Module]:
        return list(self._modules.values())

    @property
    def methods(self) -> list[Method]:
        return [m for mod in self._modules.values() for m in mod.methods.values()]

    def module(self, module_id: str) -> Module:
        try:
            return self._modules[module_id]
        except KeyError:
            close = difflib.get_close_matches(module_id, self._modules, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise CatalogError(
                f"Unknown module {module_id!r}.{hint} Available: {', '.join(self._modules)}."
            ) from None

    def method(self, module_id: str, method_id: str | None = None) -> Method:
        """``method("mod", "meth")`` or ``method("mod.meth")``."""
        if method_id is None:
            if "." not in module_id:
                raise CatalogError(f"Expected 'module.method', got {module_id!r}.")
            module_id, method_id = module_id.split(".", 1)
        return self.module(module_id).method(method_id)

    def find(self, method_id: str, extension: str | None = None) -> Method:
        """Resolve a bare method id (``"voxel_downsample"``) to its method.
        When several modules define the id, ``extension`` picks the one that
        accepts the file; an ambiguous lookup raises :class:`CatalogError`."""
        if "." in method_id:
            return self.method(method_id)
        candidates = [m for mod in self for m in mod.methods.values() if m.id == method_id]
        if not candidates:
            close = difflib.get_close_matches(method_id, {m.id for m in self.methods}, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise CatalogError(f"No method named {method_id!r} in the catalog.{hint}")
        if extension:
            accepting = [m for m in candidates if self.module(m.module_id).accepts(extension)]
            if len(accepting) == 1:
                return accepting[0]
            if not accepting:
                raise CatalogError(
                    f"{method_id!r} does not accept {extension!r} files. Modules defining it: "
                    + ", ".join(m.module_id for m in candidates)
                )
            candidates = accepting
        if len(candidates) > 1:
            raise CatalogError(
                f"{method_id!r} exists in several modules: "
                + ", ".join(m.qualname for m in candidates)
                + ". Use the qualified name."
            )
        return candidates[0]

    def methods_for(self, extension: str | None) -> list[Method]:
        """Every method whose module accepts files with this extension."""
        return [m for mod in self if mod.accepts(extension) for m in mod.methods.values()]

    def describe(self, module_id: str, method_id: str | None = None) -> str:
        if method_id is None and "." not in module_id:
            return self.module(module_id).describe()
        return self.method(module_id, method_id).describe()


# ---- loading -------------------------------------------------------------


def _parameter(raw: dict[str, Any], why: dict[str, str] | None = None, validated_on: str = "") -> Parameter:
    typ = raw.get("type", "string")
    if typ not in PARAM_TYPES:
        raise CatalogError(f"Parameter {raw.get('name')!r} has unsupported type {typ!r}.")
    return Parameter(
        name=raw["name"],
        type=typ,
        default=raw.get("default"),
        description=raw.get("description", ""),
        min=raw.get("min"),
        max=raw.get("max"),
        options=tuple(str(o) for o in raw.get("options", []) or []),
        advanced=bool(raw.get("advanced", False)),
        rationale=(why or {}).get(raw["name"], ""),
        validated_on=validated_on,
    )


def _module(raw: dict[str, Any], defaults: dict[str, Any] | None = None) -> Module:
    module_dual = bool(raw.get("dual_input", False))
    methods = {}
    for m in raw["methods"]:
        why = (defaults or {}).get(f"{raw['id']}.{m['id']}", {})
        methods[m["id"]] = Method(
            id=m["id"],
            name=m.get("name", m["id"]),
            module_id=raw["id"],
            script=m["script"],
            output_extension=m.get("output_extension", ".ply"),
            dual_input=bool(m.get("dual_input", module_dual)),
            parameters=tuple(
                _parameter(p, why.get("params"), why.get("validated_on", "")) for p in m.get("parameters", [])
            ),
            validated_on=why.get("validated_on", ""),
        )
    return Module(
        id=raw["id"],
        name=raw.get("name", raw["id"]),
        description=raw.get("description", ""),
        category=raw.get("category", ""),
        order=int(raw.get("order", 999)),
        input_formats=tuple(str(e).lower() for e in raw.get("input_formats", [])),
        methods=methods,
        dual_input=module_dual,
        dual_input_label=raw.get("dual_input_label", ""),
        theory=raw.get("theory", {}) or {},
        videos=tuple(raw.get("videos", []) or []),
    )


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    """Load the bundled catalog once per process."""
    data_dir = resources.files("pardesline.catalog") / "data"
    defaults_file = data_dir / "_defaults.json"
    defaults = json.loads(defaults_file.read_text(encoding="utf-8")) if defaults_file.is_file() else {}
    modules = []
    for entry in sorted(data_dir.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json") and not entry.name.startswith("_"):
            modules.append(_module(json.loads(entry.read_text(encoding="utf-8")), defaults))
    if not modules:
        raise CatalogError("The bundled catalog is empty - the package is broken, please reinstall.")
    return Catalog(modules)
