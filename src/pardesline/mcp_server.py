"""``pardesline mcp``: the package as a Model Context Protocol server.

Any MCP client - Claude Desktop and Claude Code, Cursor, Gemini CLI, Codex,
a LangChain or OpenAI Agents tool loop - gets the 43 bundled datasets, any
``hf://`` / ``s3://`` / ``tcia://`` source, private folders through
``pl.scan``, the typed object model and the 73 catalog algorithms, on the
user's machine, without a PardesLine account. Nothing leaves the machine
except the downloads the user asks for.

Run it with ``pardesline mcp`` (stdio, the default every client speaks) or
``pardesline mcp --transport streamable-http --port 8765``. Needs
``pip install "pardesline[mcp]"``.

Design rules for tools:
- every result is plain JSON (paths as strings), small enough for a context
  window (lists are paged with ``limit`` / ``offset``);
- blocking work (downloads, algorithms) runs in a worker thread so the
  server keeps answering;
- the package's own rules hold: nothing is guessed, a question is returned
  as data for the agent to relay to the human (``scan_dataset`` ->
  ``confirm_dataset``), gated sources explain what the human must do.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from ._version import __version__
from .errors import MissingDependency, NeedsConfirmation, PardesLineError

__all__ = ["build_server", "main"]

INSTRUCTIONS = f"""pardesline {__version__}: 3D vision and medical imaging on this machine.

Before designing a pipeline, read the matching expert skill: list_skills() then get_skill(name)
(registration, segmentation, PointNet, DINOv3, JEPA, VAE anomaly detection, Gaussian splatting, metrics...).
Start with list_datasets (43 bundled: MSD, TotalSegmentator, LUNA16, TCIA, OpenNeuro, KITTI...),
or point at any source: "hf://org/name/folder", "s3://bucket/prefix", "tcia://Collection/CT",
a local folder. describe_dataset tells roles, licence and citation; list_samples pages the
samples; load_sample downloads ONE file (or DICOM series) and returns its local path with frame,
units, labels and licence. A private folder or an unknown source goes through scan_dataset:
relay its questions to the human, then call confirm_dataset with the answers - never guess a
licence, a unit or an array layout yourself. list_methods / describe_method / run_method expose
the 73 catalog algorithms on local files; to_mesh turns a label map into a surface. Quote
ds.license to the user before any redistribution or commercial use."""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json", exclude_none=True))
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    return value


def _error(exc: Exception) -> dict[str, Any]:
    out: dict[str, Any] = {"error": type(exc).__name__, "message": str(exc)}
    code = getattr(exc, "code", None)
    if code:
        out["code"] = code
    if isinstance(exc, NeedsConfirmation):
        out["questions"] = [q.model_dump(exclude_none=True) for q in exc.questions]
        out["draft_path"] = str(exc.draft_path) if exc.draft_path else None
        out["how_to_answer"] = (
            "Relay the questions to the human, then call confirm_dataset(ref, answers) with e.g. "
            "{'license': 'CC-BY-4.0', 'units': {'mesh': 'mm'}, 'labels': {'mask': {'1': 'liver'}}, "
            "'types': {'sweep': 'points'}, 'layout': {'sweep': {'dtype': 'float32', 'shape': '(N,4)', "
            "'columns': ['x','y','z','i']}}}"
        )
    return out


# ---------------------------------------------------------------------------
# tool implementations (synchronous; the server runs them in a worker thread)
# ---------------------------------------------------------------------------


def _manifest_summary(m) -> dict[str, Any]:
    return {
        "name": m.name,
        "title": m.title,
        "source": m.source.scheme,
        "source_key": m.source.key(),
        "license": m.license.spdx or "unknown",
        "commercial": m.license.commercial,
        "requires_agreement": m.license.requires_agreement,
        "size_mb": m.size_mb,
        "roles": {r: spec.type for r, spec in m.roles.items()},
        "tags": m.tags,
    }


def impl_list_datasets(tag: str | None = None, scheme: str | None = None, medical_only: bool = False) -> dict:
    """The bundled manifests as summaries.

    Filtered by ``tag``, source ``scheme`` or ``medical_only``.
    """

    import pardesline as pl

    rows = pl.datasets(tag=tag, scheme=scheme)
    if medical_only:
        rows = [m for m in rows if "medical" in m.tags]
    return {
        "count": len(rows),
        "datasets": [_manifest_summary(m) for m in rows],
        "also": "any hf://org/name[/folder], s3://bucket/prefix, tcia://Collection[/CT,MR] or local folder",
    }


def _open(ref: str, **answers: Any):
    import pardesline as pl

    return pl.load(ref, **answers)


def impl_describe_dataset(ref: str, count_samples: bool = False) -> dict:
    """Roles, frames, units, labels, licence and citation of a dataset reference.

    ``ref`` is a bundled name, an ``hf://`` / ``tcia://`` / ``s3://`` URI, a manifest
    path or a folder. ``count_samples`` lists the source to count samples, which may
    take a while on large archives.
    """

    import pardesline as pl

    for m in pl.datasets():
        if m.name == ref:
            out = _manifest_summary(m)
            out.update(
                {
                    "description": m.description,
                    "citation": m.citation,
                    "homepage": m.homepage,
                    "license_note": m.license.note,
                    "pairing": m.pairing,
                    "roles_detail": {r: spec.model_dump(exclude_none=True) for r, spec in m.roles.items()},
                    "text": m.describe(),
                }
            )
            if count_samples:
                ds = pl.load(ref)
                assert isinstance(ds, pl.Dataset)
                out["sample_count"] = len(ds)
                out["first_ids"] = ds.ids[:10]
            return out
    ds = _open(ref)
    m = ds.manifest
    out = _manifest_summary(m)
    out.update(
        {
            "description": m.description,
            "roles_detail": {r: spec.model_dump(exclude_none=True) for r, spec in m.roles.items()},
            "sample_count": len(ds),
            "first_ids": ds.ids[:10],
            "text": ds.describe(),
        }
    )
    return out


def impl_list_samples(
    ref: str, limit: int = 50, offset: int = 0, filters: dict[str, str] | None = None
) -> dict:
    """Sample ids and fields of a dataset, paged with ``limit`` / ``offset``.

    ``filters`` restricts to samples whose fields match.
    """

    ds = _open(ref)
    if filters:
        ds = ds.filter(**{k: str(v) for k, v in filters.items()})
    specs = ds._specs[offset : offset + max(1, min(limit, 500))]
    return {
        "dataset": ds.name,
        "total": len(ds),
        "offset": offset,
        "samples": [{"id": s.id, "roles": list(s.files), "fields": s.fields} for s in specs],
        "license": ds.license.describe(),
    }


def _object_record(obj) -> dict[str, Any]:
    info = {}
    try:
        info = {
            k: v for k, v in obj.info().items() if k in ("size", "spacing", "origin", "pixel_type", "shape")
        }
    except Exception as exc:  # header unreadable: say so, do not fail the call
        info = {"note": f"header not read: {exc}"}
    return {
        "path": str(obj.path),
        "kind": obj.kind,
        "role": obj.role,
        "frame": obj.frame.to_dict(),
        "frame_text": obj.frame.describe(),
        "units": obj.units,
        "labels": {str(k): v for k, v in (obj.labels or {}).items()} or None,
        "layout": obj.layout,
        "license": obj.license.to_dict(),
        "license_text": obj.license.describe(),
        "info": _json_safe(info),
        "provenance": _json_safe(obj.provenance),
        "methods": obj.methods()[:60],
    }


def impl_load_sample(ref: str, sample: str | int, role: str, standard: bool = True) -> dict:
    """Fetch one role of one sample and describe the resulting object.

    Returns the path, kind, frame, units, labels, licence, provenance, the catalog
    methods that accept the file and, when ``standard`` is true, ``standard_path``:
    a PLY / MetaImage rendition for raw arrays and DICOM folders.
    """

    ds = _open(ref)
    s = (
        ds[int(sample)]
        if isinstance(sample, int) or (isinstance(sample, str) and sample.isdigit() and sample not in ds.ids)
        else ds[sample]
    )
    obj = s.get(role)
    rec = _object_record(obj)
    rec["sample"] = s.id
    rec["dataset"] = ds.name
    if standard and (obj.is_raw_array or obj.path.is_dir()):
        rec["standard_path"] = str(obj._op_input())  # PLY / MetaImage the algorithms read
    return rec


def impl_scan_dataset(ref: str) -> dict:
    """Draft a manifest for a folder or a Hub repository and return its open questions."""

    import pardesline as pl

    m = pl.scan(ref)
    return {
        "name": m.name,
        "source": m.source.model_dump(exclude_none=True),
        "license": m.license.model_dump(exclude_none=True),
        "pairing": m.pairing,
        "roles": {r: spec.model_dump(exclude_none=True) for r, spec in m.roles.items()},
        "sample_count": len(m.samples or []),
        "first_samples": [s.model_dump(exclude_none=True) for s in (m.samples or [])[:5]],
        "questions": [q.model_dump(exclude_none=True) for q in m.questions],
        "is_draft": m.is_draft,
        "next_step": (
            "Relay the questions to the human and call confirm_dataset(ref, answers)."
            if m.is_draft
            else "Nothing to ask: load_sample / list_samples work on this ref directly."
        ),
    }


def impl_confirm_dataset(ref: str, answers: dict[str, Any] | None = None, save_to: str | None = None) -> dict:
    """Answer a draft's questions (``license``, ``units``, ``labels``...) and save the manifest."""

    ds = _open(ref, **(answers or {}))
    saved = None
    if save_to:
        saved = str(ds.manifest.save(save_to))
    elif ds.manifest.source.scheme == "local" and ds.manifest.source.root:
        from .data import DRAFT_NAME

        saved = str(ds.manifest.save(Path(ds.manifest.source.root) / DRAFT_NAME))
    return {
        "dataset": ds.name,
        "sample_count": len(ds),
        "roles": {r: spec.type for r, spec in ds.roles.items()},
        "license": ds.license.describe(),
        "manifest_saved_to": saved,
        "manifest": ds.manifest.model_dump(mode="json", exclude_none=True),
    }


def impl_export_dataset(ref: str, folder: str, take: int | None = None, overwrite: bool = False) -> dict:
    """Write a dataset (or its first ``take`` samples) as standard files.

    PLY / MetaImage with sidecars and a manifest for the folder.
    """

    ds = _open(ref)
    if take:
        ds = ds.take(take)
    m = ds.export(folder, overwrite=overwrite)
    return {
        "dataset": ds.name,
        "folder": str(Path(folder).resolve()),
        "samples": len(m.samples or []),
        "manifest": "pardesline.manifest.json",
    }


def impl_list_methods(extension: str | None = None, category: str | None = None) -> dict:
    """The catalog methods, optionally those accepting a file ``extension`` or in a ``category``."""

    import pardesline as pl

    cat = pl.catalog()
    out = []
    for mod in cat:
        if category and mod.category != category:
            continue
        if extension and not mod.accepts(extension if extension.startswith(".") else "." + extension):
            continue
        out.append(
            {
                "module": mod.id,
                "category": mod.category,
                "inputs": list(mod.input_formats),
                "methods": [
                    {"id": m.id, "name": m.name, "two_inputs": m.dual_input, "params": list(m.param_names)}
                    for m in mod.methods.values()
                ],
            }
        )
    return {"modules": out, "aliases": sorted(pl.object.ALIASES)}


def impl_describe_method(method: str) -> dict:
    """One method with every parameter.

    Type, default, range, description, rationale and validation regime.
    """

    import pardesline as pl

    return {"method": method, "text": pl.catalog().describe(method)}


def impl_run_method(
    method: str,
    input_path: str,
    moving_path: str | None = None,
    params: dict[str, Any] | None = None,
    output_path: str | None = None,
    timeout: float = 600,
) -> dict:
    """Run a catalog method on a file with validated parameters.

    Returns the output path and the recorded provenance step.
    """

    import pardesline as pl

    res = pl.run(method, input_path, output_path, moving=moving_path, params=params or {}, timeout=timeout)
    return {
        "output": str(res.output),
        "sidecar": str(res.sidecar) if res.sidecar else None,
        "duration_s": round(res.duration_s, 3),
        "method": res.method.qualname,
        "params": res.params,
        "log_tail": "\n".join(res.log.strip().splitlines()[-15:]),
    }


def skills_dir() -> Path:
    """Where the expert skills live: inside the installed package, or the repo's skills/ folder."""
    here = Path(__file__).resolve().parent
    for candidate in (here / "skills", here.parent.parent / "skills"):
        if candidate.is_dir() and any(candidate.glob("*/SKILL.md")):
            return candidate
    raise PardesLineError("the skills folder was not found next to the package", code="skills_missing")


def _skill_frontmatter(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not text.startswith("---"):
        return out
    head = text[3:].split("\n---", 1)[0]
    key = None
    for line in head.splitlines():
        if line.startswith(("name:", "description:")):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().lstrip(">-").strip()
        elif key == "description" and line.startswith(" "):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def impl_list_skills() -> dict:
    """The expert skills shipped with the package: name, description and files."""

    root = skills_dir()
    skills = []
    for skill in sorted(root.glob("*/SKILL.md")):
        fm = _skill_frontmatter(skill.read_text(encoding="utf-8"))
        files = sorted(
            str(p.relative_to(skill.parent)).replace(os.sep, "/")
            for p in skill.parent.rglob("*")
            if p.is_file() and p.name != "SKILL.md" and "__pycache__" not in p.parts
        )
        skills.append({"name": skill.parent.name, "description": fm.get("description", ""), "files": files})
    return {
        "count": len(skills),
        "skills": skills,
        "how": "get_skill(name) returns SKILL.md; get_skill(name, file) one of its files",
    }


def impl_get_skill(name: str, file: str | None = None) -> dict:
    """The text of a skill's ``SKILL.md`` or of one of its files.

    Paths outside the skill folder are refused.
    """

    root = skills_dir()
    folder = (root / name).resolve()
    if not folder.is_dir() or root.resolve() not in folder.parents:
        raise PardesLineError(f"no skill {name!r}; list_skills() names them", code="skill_missing")
    target = (folder / (file or "SKILL.md")).resolve()
    if folder not in target.parents and target != folder:
        raise PardesLineError("file must be inside the skill folder", code="skill_missing")
    if not target.is_file():
        raise PardesLineError(f"skill {name!r} has no file {file!r}", code="skill_missing")
    text = target.read_text(encoding="utf-8", errors="replace")
    return {"skill": name, "file": file or "SKILL.md", "content": text, "chars": len(text)}


def impl_describe_object(path: str, layout: dict[str, Any] | None = None, kind: str | None = None) -> dict:
    """Kind, frame, units, labels, sidecar and accepted methods of any file.

    Raw arrays (``.npy``, ``.bin``) need a ``layout``.
    """

    import pardesline as pl

    obj = pl.load(path, layout=layout, kind=kind)
    if not isinstance(obj, pl.Object):
        raise PardesLineError(f"{path} is a dataset, not a file; use describe_dataset", code="not_a_file")
    return _object_record(obj)


def impl_to_mesh(
    path: str, label: int | None = None, isovalue: float | None = None, output_path: str | None = None
) -> dict:
    """A label map or volume to a surface.

    ``label`` gives the exact boundary of one label, ``isovalue`` a level set.
    """

    import pardesline as pl

    obj = pl.load(path)
    if not isinstance(obj, pl.Volume):
        raise PardesLineError(
            f"{path} is a {getattr(obj, 'kind', 'dataset')}, not a volume", code="not_a_volume"
        )
    if label is not None and not isinstance(obj, pl.LabelMap):
        obj = obj.as_labels()
    mesh = obj.to_mesh(label=label, isovalue=isovalue, output=output_path)
    rec = _object_record(mesh)
    rec["step"] = _json_safe(mesh.provenance[-1])
    return rec


# ---------------------------------------------------------------------------
# server
# ---------------------------------------------------------------------------


def build_server(name: str = "pardesline"):
    """The FastMCP server with every tool, resource and prompt registered."""
    try:
        import anyio
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise MissingDependency("mcp", "mcp") from None

    server = FastMCP(name, instructions=INSTRUCTIONS)

    async def _call(fn, *args, **kwargs):
        try:
            return _json_safe(await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs)))
        except NeedsConfirmation as exc:
            return _error(exc)
        except PardesLineError as exc:
            return _error(exc)
        except FileNotFoundError as exc:
            return {"error": "FileNotFoundError", "message": str(exc)}
        except Exception as exc:  # keep the server alive, tell the agent what broke
            logger.exception("tool {} failed", getattr(fn, "__name__", fn))
            return {"error": type(exc).__name__, "message": str(exc)}

    @server.tool()
    async def list_datasets(
        tag: str | None = None, scheme: str | None = None, medical_only: bool = False
    ) -> dict:
        """List the bundled dataset manifests (name, source, licence, roles). Filter by tag
        (medical, ct, mri, dicom, mesh, lidar...) or scheme (archive, hf, s3, tcia, https, urllist,
        open3d). Any other source works too: pass hf://org/name[/folder], s3://bucket/prefix,
        tcia://Collection[/CT,MR] or a local folder to describe_dataset / scan_dataset."""
        return await _call(impl_list_datasets, tag, scheme, medical_only)

    @server.tool()
    async def describe_dataset(ref: str, count_samples: bool = False) -> dict:
        """Roles, licence, citation and layout of a dataset: a bundled name (msd_task02_heart),
        hf://org/name[/folder], s3://bucket/prefix, tcia://Collection or a local folder with a
        confirmed manifest. count_samples=True lists the source (network) and returns the count."""
        return await _call(impl_describe_dataset, ref, count_samples)

    @server.tool()
    async def list_samples(
        ref: str, limit: int = 50, offset: int = 0, filters: dict[str, str] | None = None
    ) -> dict:
        """Page through the samples of a dataset: ids, roles and fields (split, patient...). Nothing
        is downloaded. filters match sample fields, e.g. {"split": "Tr"}."""
        return await _call(impl_list_samples, ref, limit, offset, filters)

    @server.tool()
    async def load_sample(ref: str, sample: str, role: str, standard: bool = True) -> dict:
        """Download ONE file (or DICOM series) of a dataset and return its local path with kind,
        frame, units, labels, licence, provenance and the methods that accept it. sample is an id
        or an index. standard=True also materialises raw arrays / DICOM folders as PLY / MetaImage
        (standard_path) so run_method can take them."""
        return await _call(impl_load_sample, ref, sample, role, standard)

    @server.tool()
    async def scan_dataset(ref: str) -> dict:
        """Draft a manifest for a private folder, hf://, s3:// or tcia:// source and return the
        questions the package will not answer by guessing (licence, units, frame, label meanings,
        array layouts). Relay them to the human, then call confirm_dataset."""
        return await _call(impl_scan_dataset, ref)

    @server.tool()
    async def confirm_dataset(
        ref: str, answers: dict[str, Any] | None = None, save_to: str | None = None
    ) -> dict:
        """Answer the scan's questions and load the dataset. answers keys: license (SPDX id or free
        text), pairing, units / frame (one value or per role), labels (per role {"1": "liver"}),
        types (per role: points, mesh, volume, labels, image), layout (per role: dtype, shape,
        columns, key). The confirmed manifest is saved next to a local folder, or to save_to."""
        return await _call(impl_confirm_dataset, ref, answers, save_to)

    @server.tool()
    async def export_dataset(ref: str, folder: str, take: int | None = None, overwrite: bool = False) -> dict:
        """Write a standard copy of a dataset (or its first `take` samples): PLY / MetaImage / NIfTI
        files, a .pardesline.json sidecar each (frame, units, labels, licence, provenance) and a
        local pardesline.manifest.json. Downloads everything it exports."""
        return await _call(impl_export_dataset, ref, folder, take, overwrite)

    @server.tool()
    async def list_methods(extension: str | None = None, category: str | None = None) -> dict:
        """The 73 catalog algorithms by module, with parameter names; filter by input extension
        (.ply, .mha...) or category. Aliases (downsample, poisson, segment...) are listed too."""
        return await _call(impl_list_methods, extension, category)

    @server.tool()
    async def describe_method(method: str) -> dict:
        """Every parameter of a method (type, default, range, choices, description):
        "module.method", e.g. simpleitk_registration.rigid, or a module name."""
        return await _call(impl_describe_method, method)

    @server.tool()
    async def run_method(
        method: str,
        input_path: str,
        moving_path: str | None = None,
        params: dict[str, Any] | None = None,
        output_path: str | None = None,
        timeout: float = 600,
    ) -> dict:
        """Run one catalog algorithm on a local file ("module.method" or an alias). Registration
        methods take the fixed image as input_path and the moving one as moving_path. Parameters are
        validated against the catalog before anything runs. Returns the output path and the log tail."""
        return await _call(impl_run_method, method, input_path, moving_path, params, output_path, timeout)

    @server.tool()
    async def describe_object(
        path: str, layout: dict[str, Any] | None = None, kind: str | None = None
    ) -> dict:
        """What a local 3D file knows about itself: kind, frame and units (from the header or
        unknown), labels, licence, header info, accepted methods. Raw .npy/.npz/.bin need a layout
        (dtype, shape, columns, key) and optionally a kind (points, volume, labels)."""
        return await _call(impl_describe_object, path, layout, kind)

    @server.tool()
    async def to_mesh(
        path: str, label: int | None = None, isovalue: float | None = None, output_path: str | None = None
    ) -> dict:
        """Surface from a volume in world coordinates: label=k for the exact boundary of a label
        map (LPS millimetres), isovalue=v for the level set of a grey-level volume. Exactly one of
        the two."""
        return await _call(impl_to_mesh, path, label, isovalue, output_path)

    @server.tool()
    async def list_skills() -> dict:
        """The expert skills shipped with pardesline (3D representations, point-cloud
        registration, multimodal rigid registration, atlas label transfer, PointNet
        segmentation, DINOv3 dense features, JEPA pretraining, VAE anomaly detection, Gaussian
        splatting, medical segmentation models, 3-D evaluation metrics, datasets, the object
        model...). Each has a SKILL.md and runnable scripts. Read one with get_skill before
        designing a pipeline in its domain."""
        return await _call(impl_list_skills)

    @server.tool()
    async def get_skill(name: str, file: str | None = None) -> dict:
        """Return a skill's SKILL.md (the expert guide: theory, parameters, pitfalls, pardesline
        calls) or one of its files (file="scripts/xxx.py"): the reference implementations are
        meant to be copied and adapted."""
        return await _call(impl_get_skill, name, file)

    @server.resource("pardesline://skills")
    def skills_resource() -> str:
        """The expert skills as a JSON index."""
        return json.dumps(_json_safe(impl_list_skills()), indent=1)

    @server.resource("pardesline://skill/{name}")
    def skill_resource(name: str) -> str:
        """One skill's SKILL.md."""
        try:
            return impl_get_skill(name)["content"]
        except PardesLineError as exc:
            return json.dumps(_error(exc))

    @server.resource("pardesline://datasets")
    def datasets_resource() -> str:
        """The bundled dataset manifests as JSON summaries."""
        return json.dumps(_json_safe(impl_list_datasets()), indent=1)

    @server.resource("pardesline://manifest/{name}")
    def manifest_resource(name: str) -> str:
        """One bundled manifest as JSON."""
        import pardesline as pl

        for m in pl.datasets():
            if m.name == name:
                return m.to_json()
        return json.dumps({"error": f"no bundled manifest {name!r}"})

    @server.resource("pardesline://catalog")
    def catalog_resource() -> str:
        """Modules, methods and parameter names of the 73 algorithms."""
        return json.dumps(_json_safe(impl_list_methods()), indent=1)

    @server.prompt()
    def start_here() -> str:
        """How to work with pardesline through this server."""
        return INSTRUCTIONS

    return server


def main(argv: list[str] | None = None) -> int:
    """Run the MCP server (``pardesline mcp``).

    stdio by default; ``--transport streamable-http --port N`` serves HTTP.
    """

    import argparse

    p = argparse.ArgumentParser(prog="pardesline mcp", description="Run the pardesline MCP server.")
    p.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default="stdio",
        help="stdio is what MCP clients spawn",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--name", default="pardesline")
    args = p.parse_args(argv)
    try:
        server = build_server(args.name)
    except MissingDependency as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.transport != "stdio":
        server.settings.host = args.host
        server.settings.port = args.port
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("PARDESLINE_LOG", "INFO"))  # stdout is the protocol channel
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
