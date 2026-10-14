"""``pl.load``: one call for a file, a folder, a bundled dataset or a hub repo.

pl.load("scan.ply")                      -> Object
pl.load("scan.bin", layout={...})        -> PointCloud read through its layout
pl.load("rire_brain")                    -> Dataset (bundled manifest, files fetched on access)
pl.load("sample://popi_lung_4dct")       -> same
pl.load("hf://org/name")                 -> Dataset from the bundled manifest of that repo,
                                            or a draft with questions (like a private folder)
pl.load("hf://org/name/sub/folder")      -> same, listing only that folder of the repo
pl.load("s3://openneuro.org/ds000228")   -> a public bucket prefix, same flow
pl.load("tcia://Pancreas-CT")            -> a public TCIA collection (DICOM series), same flow
pl.load("my_dataset.manifest.json")      -> Dataset from your own manifest
pl.load("/data/study_A")                 -> Dataset after pl.scan; raises NeedsConfirmation
                                           until licence/units/labels are answered
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from loguru import logger

from ..errors import FetchError, ManifestError, NeedsConfirmation
from ..object import Object, wrap
from .cache import cache_dir, set_cache_dir
from .dataset import Dataset, Sample
from .manifest import Layout, LicenseSpec, Manifest, Role, SourceSpec
from .scan import DRAFT_NAME, scan_listing
from .scan import scan as scan_folder
from .sources import open_source

__all__ = [
    "DRAFT_NAME",
    "Dataset",
    "Layout",
    "Manifest",
    "Object",
    "Role",
    "Sample",
    "cache_dir",
    "datasets",
    "load",
    "load_manifest",
    "parse_hf_ref",
    "scan",
    "scan_uri",
    "set_cache_dir",
]

_KIND_ALIASES = {
    "points": "pointcloud",
    "pointcloud": "pointcloud",
    "point_cloud": "pointcloud",
    "splat": "pointcloud",
    "mesh": "mesh",
    "volume": "volume",
    "labels": "labels",
    "labelmap": "labels",
    "image": "image",
    "transform": "transform",
}

# Hub card licence ids -> SPDX-style ids used in manifests.
_HF_LICENSES = {
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-3.0": "CC-BY-3.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-sa-3.0": "CC-BY-SA-3.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc-by-nc-sa-4.0": "CC-BY-NC-SA-4.0",
    "cc-by-nc-sa-3.0": "CC-BY-NC-SA-3.0",
    "cc-by-nc-nd-4.0": "CC-BY-NC-ND-4.0",
    "cc0-1.0": "CC0-1.0",
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "bsd-3-clause": "BSD-3-Clause",
    "odc-by": "ODC-By-1.0",
    "odbl": "ODbL-1.0",
    "gpl-3.0": "GPL-3.0-only",
    "lgpl-3.0": "LGPL-3.0-only",
}


@lru_cache(maxsize=1)
def _bundled() -> dict[str, Manifest]:
    out: dict[str, Manifest] = {}
    folder = resources.files("pardesline.data") / "manifests"
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            m = Manifest.from_json(entry.read_text(encoding="utf-8"), where=f"bundled:{entry.name}")
            out[m.name] = m
    return out


def datasets(*, tag: str | None = None, scheme: str | None = None) -> list[Manifest]:
    """The manifests bundled with the package (``pl.load(name)`` works on
    each). ``tag="medical"`` or ``scheme="hf"`` filter the list."""
    out = list(_bundled().values())
    if tag:
        out = [m for m in out if tag in m.tags]
    if scheme:
        out = [m for m in out if m.source.scheme == scheme]
    return out


def parse_hf_ref(text: str) -> tuple[str, str | None]:
    """``hf://org/name/sub/folder`` -> ``("org/name", "sub/folder")``."""
    body = text[len("hf://") :].strip("/")
    if body.startswith("datasets/"):
        body = body[len("datasets/") :]
    parts = body.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ManifestError(f"{text!r}: a Hub reference is hf://<org>/<name>[/<sub/folder>]")
    repo = "/".join(parts[:2])
    sub = "/".join(parts[2:]) or None
    return repo, sub


def _bundled_for_key(key: str) -> Manifest | None:
    """The bundled manifest whose source key (``s3://bucket/prefix``,
    ``tcia://Collection``) is ``key``, or whose prefix contains it."""
    exact = [m for m in _bundled().values() if m.source.key() == key]
    if exact:
        return exact[0]
    return None


def _bundled_for_repo(repo: str, sub: str | None) -> Manifest | None:
    """The bundled manifest of a Hub repo; with a sub-folder, the one that
    already lists it, else the first for the repo re-scoped to that folder."""
    candidates = [m for m in _bundled().values() if m.source.scheme == "hf" and m.source.repo_id == repo]
    if not candidates:
        return None
    if sub:
        for m in candidates:
            if m.source.paths and any(sub == p or sub.startswith(p + "/") for p in m.source.paths):
                return m
        m = candidates[0]
        return m.model_copy(update={"source": m.source.model_copy(update={"paths": [sub]})})
    return candidates[0]


def load_manifest(ref: str | os.PathLike) -> tuple[Manifest, Path | None]:
    """Resolve a bundled name, ``sample://name``, ``hf://repo`` or a manifest
    file. Returns (manifest, folder of the manifest file or None)."""
    text = str(ref)
    if text.startswith("sample://"):
        text = text[len("sample://") :]
    if text.startswith("hf://"):
        repo, sub = parse_hf_ref(text)
        m = _bundled_for_repo(repo, sub)
        if m is not None:
            return m, None
        raise ManifestError(
            f"No bundled manifest for hf://{repo}. pl.load('hf://{repo}') drafts one from the repo listing "
            "and asks what it cannot establish (licence, units, array layouts); or write one and pass it: "
            "pl.load('hf://...', manifest='path.json')."
        )
    p = Path(text).expanduser()
    if p.is_file() and p.suffix.lower() == ".json":
        return Manifest.load(p), p.parent
    if text in _bundled():
        return _bundled()[text], None
    raise ManifestError(
        f"{text!r} is neither a bundled dataset ({', '.join(_bundled())}) nor a manifest file."
    )


def _per_role(m: Manifest, key: str, val: Any) -> dict[str, Any]:
    """``units="mm"`` applies to every role; ``units={"mesh": "mm"}`` to one.
    For labels, ``{1: "liver"}`` is global and ``{"mask": {1: "liver"}}`` per role."""
    if isinstance(val, dict):
        keys = list(val)
        if key == "labels" and keys and all(isinstance(k, int) or str(k).isdigit() for k in keys):
            return {r: val for r, spec in m.roles.items() if spec.type in ("labels", "volume")}
        if key in ("layout", "types") and keys and all(k in m.roles for k in keys):
            return dict(val)
        unknown = [k for k in keys if k not in m.roles]
        if unknown:
            raise ManifestError(f"{key}: unknown role(s) {unknown}; roles: {list(m.roles)}")
        return dict(val)
    if key in ("layout", "types"):
        raise ManifestError(f"{key} must be given per role: {key}={{'role': ...}}")
    return dict.fromkeys(m.roles, val)


def _apply_answers(m: Manifest, answers: dict[str, Any]) -> Manifest:
    """Fill a draft from keyword answers: license=, units=, frame=, labels=,
    pairing=, types=, layout=."""
    data = m.model_dump(mode="json", exclude_none=True)
    answered: set[str] = set()
    if (lic := answers.get("license")) is not None:
        data["license"] = (
            {"spdx": lic}
            if isinstance(lic, str) and "-" in lic and " " not in lic
            else (lic if isinstance(lic, dict) else {"note": str(lic)})
        )
        answered.add("license")
    if (pairing := answers.get("pairing")) is not None:
        data["pairing"] = pairing
        answered.add("pairing")
    for key in ("types", "layout", "units", "frame", "labels"):
        val = answers.get(key)
        if val is None:
            continue
        per_role = _per_role(m, key, val)
        for role, v in per_role.items():
            if key == "labels":
                if v is None:
                    data["roles"][role]["type"] = (
                        "volume" if data["roles"][role]["type"] == "labels" else data["roles"][role]["type"]
                    )
                    data["roles"][role].pop("labels", None)
                else:
                    data["roles"][role]["labels"] = {str(k): str(n) for k, n in v.items()}
                    if data["roles"][role]["type"] == "volume":
                        data["roles"][role]["type"] = "labels"
            elif key == "types":
                data["roles"][role]["type"] = str(v)
            elif key == "layout":
                data["roles"][role]["layout"] = (
                    v.model_dump(exclude_none=True) if isinstance(v, Layout) else dict(v)
                )
            else:
                data["roles"][role][key] = v
            answered.add(f"roles.{role}.{key}")
    if "labels" in answers and answers["labels"] is None:
        answered |= {q.field for q in m.questions if q.field.endswith(".labels")}
    data["questions"] = [
        q.model_dump(mode="json", exclude_none=True) for q in m.questions if q.field not in answered
    ]
    return Manifest.from_dict(data, where="answers")


def _ask_interactively(m: Manifest) -> Manifest:
    answers: dict[str, Any] = {}
    print(f"\n{m.name}: {len(m.questions)} question(s) before loading.")
    for q in m.questions:
        default = f" [{q.suggestion}]" if q.suggestion is not None else ""
        reply = input(f"  {q.field}: {q.message}{default}\n  > ").strip()
        if not reply and q.suggestion is None:
            continue
        reply = reply or str(q.suggestion)
        if q.field == "license":
            answers["license"] = reply
        elif q.field == "pairing":
            answers["pairing"] = reply
        else:
            _, role, key = q.field.split(".")
            if key == "labels":
                if reply.lower() in ("none", "no", "n"):
                    val: Any = None
                else:
                    val = {}
                    for part in reply.replace(";", ",").split(","):
                        if ":" in part or "=" in part:
                            k, v = re.split(r"[:=]", part, maxsplit=1)
                            val[int(k.strip())] = v.strip().strip("'\"")
                answers.setdefault("labels", {})[role] = val
            elif key == "layout":
                print("  (layouts are easier to give in code: layout={'role': {...}}; skipped)")
            else:
                answers.setdefault(key, {})[role] = reply
    return _apply_answers(m, answers)


def _finish_draft(
    m: Manifest,
    *,
    draft_path: Path | None,
    answers: dict[str, Any],
    interactive: bool,
    assume: bool,
    save_draft: bool,
    manifest_dir: Path | None,
) -> Dataset:
    """The four asking modes, shared by private folders and un-manifested hub repos."""
    if answers:
        m = _apply_answers(m, answers)
    if m.is_draft and interactive:
        m = _ask_interactively(m)
    if m.is_draft and not assume:
        saved = None
        if save_draft and draft_path is not None:
            try:
                saved = m.save(draft_path)
            except OSError as exc:
                logger.debug("could not save the draft: {}", exc)
        raise NeedsConfirmation(m, saved)
    if m.is_draft:
        for q in m.questions:
            logger.warning("{}: assumed unknown - {}", q.field, q.message)
    return Dataset(m, open_source(m.source, m, manifest_dir=manifest_dir))


def _hf_card_license(repo: str) -> LicenseSpec:
    """The licence the Hub card declares (one API call); unknown when absent."""
    try:
        from huggingface_hub import HfApi

        info = HfApi().dataset_info(repo)
        card = info.card_data.to_dict() if info.card_data else {}
        lic = card.get("license")
        if isinstance(lic, list):
            lic = lic[0] if lic else None
    except Exception as exc:  # the listing is what matters; the card is a hint
        logger.debug("hf://{}: card not read ({})", repo, exc)
        return LicenseSpec(source_url=f"https://huggingface.co/datasets/{repo}")
    if not lic or str(lic).lower() in ("other", "unknown", "none"):
        return LicenseSpec(
            source_url=f"https://huggingface.co/datasets/{repo}",
            note=(
                "the Hub card declares no usable licence id; "
                "the terms come from the upstream source [TO CONFIRM]"
            ),
        )
    low = str(lic).lower()
    spdx = _HF_LICENSES.get(low, str(lic))
    return LicenseSpec(
        spdx=spdx,
        commercial=None if "nc" not in low.split("-") else False,
        source_url=f"https://huggingface.co/datasets/{repo}",
        note="as declared on the Hub card; the upstream terms prevail [TO CONFIRM]",
    )


def scan_hf(ref: str, *, max_files: int = 20000) -> Manifest:
    """Draft a manifest for a Hub repo (or one of its folders) from its file
    listing: ``pl.scan("hf://org/name/sub/folder")``. Needs ``[hf]``."""
    repo, sub = parse_hf_ref(ref)
    source = SourceSpec(scheme="hf", repo_id=repo, paths=[sub] if sub else None, max_files=max_files)
    listing = open_source(source, Manifest.model_construct(name="draft")).list()
    if listing is None:
        raise FetchError(f"hf://{repo} cannot be listed")
    name = re.sub(r"[^a-z0-9_]+", "_", f"hf_{repo}".lower()).strip("_")
    return scan_listing(
        listing,
        name=name,
        source=source,
        title=f"hf://{repo}" + (f"/{sub}" if sub else ""),
        description=f"Drafted by pl.scan from the file listing of https://huggingface.co/datasets/{repo}",
        license=_hf_card_license(repo),
    )


def _source_for_uri(text: str) -> tuple[SourceSpec, str, LicenseSpec, str]:
    """``s3://bucket/prefix`` or ``tcia://Collection[/MOD,MOD]`` ->
    (source, draft name, licence hint, title)."""
    if text.startswith("s3://"):
        body = text[len("s3://") :].strip("/")
        bucket, _, prefix = body.partition("/")
        if not bucket:
            raise ManifestError(f"{text!r}: a bucket reference is s3://<bucket>/<prefix>")
        source = SourceSpec(scheme="s3", bucket=bucket, prefix=prefix or None)
        lic = LicenseSpec(source_url=f"https://{bucket}" if "." in bucket else None)
        if bucket == "openneuro.org":
            lic = LicenseSpec(
                spdx="CC0-1.0",
                commercial=True,
                redistribution="allowed",
                source_url=f"https://openneuro.org/datasets/{prefix.split('/')[0]}"
                if prefix
                else "https://openneuro.org",
                note=(
                    "OpenNeuro publishes under CC0 since 2018; older datasets may state PDDL in "
                    "dataset_description.json [TO CONFIRM]"
                ),
            )
        name = re.sub(r"[^a-z0-9_]+", "_", f"s3_{bucket}_{prefix}".lower()).strip("_")
        return source, name, lic, text
    if text.startswith("tcia://"):
        body = text[len("tcia://") :].strip("/")
        collection, _, mods = body.partition("/")
        if not collection:
            raise ManifestError(f"{text!r}: a TCIA reference is tcia://<Collection>[/<MODALITY,MODALITY>]")
        modalities = [m.strip().upper() for m in mods.split(",") if m.strip()] or None
        source = SourceSpec(scheme="tcia", collection=collection, modalities=modalities)
        lic = LicenseSpec(
            spdx="CC-BY-3.0",
            commercial=True,
            source_url=f"https://www.cancerimagingarchive.net/collection/{collection.lower()}/",
            note=(
                "TCIA's default licence is CC BY 3.0 but collections may differ (CC BY 4.0, NC); "
                "check the collection page and cite the collection and TCIA [TO CONFIRM]"
            ),
        )
        name = re.sub(r"[^a-z0-9_]+", "_", f"tcia_{collection}".lower()).strip("_")
        return source, name, lic, text
    raise ManifestError(f"{text!r}: unsupported reference")


def scan_uri(text: str, *, max_files: int = 20000) -> Manifest:
    """Draft a manifest for an ``s3://`` prefix or a ``tcia://`` collection from its listing."""
    source, name, lic, title = _source_for_uri(text)
    if source.scheme == "s3":
        source = source.model_copy(update={"max_files": max_files})
    listing = open_source(source, Manifest.model_construct(name="draft")).list()
    if listing is None:
        raise FetchError(f"{text} cannot be listed")
    return scan_listing(
        listing,
        name=name,
        source=source,
        title=title,
        description=f"Drafted by pl.scan from the listing of {text}",
        license=lic,
    )


def scan(ref: str | os.PathLike, **kwargs: Any) -> Manifest:
    """Draft a manifest for a private folder, a Hub repo, a public bucket or
    a TCIA collection, and list the questions it will not answer by guessing."""
    text = str(ref)
    if text.startswith("hf://"):
        return scan_hf(text, **kwargs)
    if text.startswith(("s3://", "tcia://")):
        return scan_uri(text, **kwargs)
    return scan_folder(ref, **kwargs)


def _load_uri(
    text: str,
    *,
    manifest: str | os.PathLike | None,
    answers: dict[str, Any],
    interactive: bool,
    assume: bool,
    save_draft: bool,
) -> Dataset:
    """``s3://`` and ``tcia://``: bundled manifest when one matches, else the draft flow."""
    if manifest is not None:
        m, mdir = Manifest.load(manifest), Path(manifest).parent
        return Dataset(m, open_source(m.source, m, manifest_dir=mdir))
    source, name, _lic, _title = _source_for_uri(text)
    m = _bundled_for_key(source.key())
    if m is not None and not answers:
        return Dataset(m, open_source(m.source, m))
    folder = cache_dir() / "drafts"
    folder.mkdir(parents=True, exist_ok=True)
    draft_path = folder / f"{name}.manifest.json"
    if m is None:
        m = Manifest.load(draft_path) if draft_path.is_file() else scan_uri(text)
    return _finish_draft(
        m,
        draft_path=draft_path,
        answers=answers,
        interactive=interactive,
        assume=assume,
        save_draft=save_draft,
        manifest_dir=None,
    )


def _draft_path_for_hf(repo: str, sub: str | None) -> Path:
    folder = cache_dir() / "drafts"
    folder.mkdir(parents=True, exist_ok=True)
    tail = re.sub(r"[^A-Za-z0-9_.-]+", "_", repo + (f"_{sub}" if sub else ""))
    return folder / f"{tail}.manifest.json"


def _load_hf(
    text: str,
    *,
    manifest: str | os.PathLike | None,
    answers: dict[str, Any],
    interactive: bool,
    assume: bool,
    save_draft: bool,
) -> Dataset:
    repo, sub = parse_hf_ref(text)
    if manifest is not None:
        m, mdir = Manifest.load(manifest), Path(manifest).parent
        if m.source.scheme != "hf" or m.source.repo_id != repo:
            raise ManifestError(
                f"the manifest describes {m.source.scheme}://{m.source.repo_id}, not hf://{repo}"
            )
        if sub:
            m = m.model_copy(update={"source": m.source.model_copy(update={"paths": [sub]})})
        return Dataset(m, open_source(m.source, m, manifest_dir=mdir))
    m = _bundled_for_repo(repo, sub)
    if m is not None and not answers:
        try:
            return Dataset(m, open_source(m.source, m))
        except ManifestError as exc:
            if not sub or "matches the role patterns" not in str(exc):
                raise
            logger.info(
                "hf://{}/{}: the bundled manifest {} describes other folders; drafting one for this folder.",
                repo,
                sub,
                m.name,
            )
            m = None
    draft_path = _draft_path_for_hf(repo, sub)
    if m is None:
        m = Manifest.load(draft_path) if draft_path.is_file() else scan_hf(text)
    return _finish_draft(
        m,
        draft_path=draft_path,
        answers=answers,
        interactive=interactive,
        assume=assume,
        save_draft=save_draft,
        manifest_dir=None,
    )


def load(
    ref: str | os.PathLike,
    *,
    manifest: str | os.PathLike | None = None,
    assume: bool = False,
    interactive: bool = False,
    save_draft: bool = True,
    layout: Layout | dict[str, Any] | None = None,
    kind: str | None = None,
    **answers: Any,
) -> Object | Dataset:
    """Open a file as an :class:`Object` or a dataset as a :class:`Dataset`.

    A raw array file (``.npy``, ``.npz``, ``.bin``) needs ``layout=`` (dtype,
    shape, columns / key) and takes ``kind=`` ("points", "volume", "labels");
    with a layout and no kind, a ``(N,k)`` shape is points and a ``(a,b,c)``
    shape is a grid.

    For a folder without a confirmed manifest - or a Hub repo without a
    bundled one - ``pl.scan`` drafts a manifest. Then: strict (default)
    raises :class:`NeedsConfirmation` listing the open questions and saves
    the draft; ``assume=True`` loads with unknowns left unknown (and warns);
    ``interactive=True`` asks in the terminal; keyword answers
    (``license=, units=, frame=, labels=, pairing=, types=, layout=``) fill
    the draft directly.
    """
    text = str(ref)
    p = Path(text).expanduser() if "://" not in text else None
    if layout is not None and not (p is not None and p.is_file()):
        answers["layout"] = layout  # per-role answer for a dataset draft
    if text.startswith("hf://"):
        return _load_hf(
            text,
            manifest=manifest,
            answers=answers,
            interactive=interactive,
            assume=assume,
            save_draft=save_draft,
        )
    if text.startswith(("s3://", "tcia://")):
        return _load_uri(
            text,
            manifest=manifest,
            answers=answers,
            interactive=interactive,
            assume=assume,
            save_draft=save_draft,
        )
    if "://" in text or manifest is not None:
        if manifest is not None:
            m, mdir = Manifest.load(manifest), Path(manifest).parent
        else:
            m, mdir = load_manifest(text)
        return Dataset(m, open_source(m.source, m, manifest_dir=mdir))

    assert p is not None
    if p.is_file():
        if p.suffix.lower() == ".json" and not p.name.endswith(".pardesline.json"):
            try:
                m, mdir = Manifest.load(p), p.parent
            except ManifestError:
                raise ManifestError(
                    f"{p} is a JSON file but not a manifest; a 3D file was expected."
                ) from None
            return Dataset(m, open_source(m.source, m, manifest_dir=mdir))
        return _load_file(p, layout=layout, kind=kind)
    if p.is_dir():
        draft_path = p / DRAFT_NAME
        if draft_path.is_file():
            m = Manifest.load(draft_path)
            if m.source.scheme == "local" and m.source.root in (None, ".", str(p), str(p.resolve())):
                m = m.model_copy(update={"source": m.source.model_copy(update={"root": str(p.resolve())})})
        else:
            m = scan_folder(p)
        return _finish_draft(
            m,
            draft_path=draft_path,
            answers=answers,
            interactive=interactive,
            assume=assume,
            save_draft=save_draft,
            manifest_dir=p,
        )
    if text in _bundled():
        m = _bundled()[text]
        return Dataset(m, open_source(m.source, m))
    raise FileNotFoundError(
        f"pl.load({text!r}): no such file or folder, and no bundled dataset of that name "
        f"(bundled: {', '.join(_bundled()) or 'none'})."
    )


def _load_file(p: Path, *, layout: Layout | dict[str, Any] | None, kind: str | None) -> Object:
    if kind is not None:
        k = _KIND_ALIASES.get(kind.lower())
        if k is None:
            raise ManifestError(f"kind={kind!r}: expected one of {sorted(set(_KIND_ALIASES))}")
        kind = k
    if layout is not None:
        lay = layout if isinstance(layout, Layout) else Layout.model_validate(layout)
        if kind is None:
            dims = lay.dims()
            kind = "volume" if len(dims) == 3 and all(d is not None for d in dims) else "pointcloud"
        return wrap(p, kind=kind, layout=lay)
    return wrap(p, kind=kind)
