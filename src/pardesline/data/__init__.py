"""``pl.load``: one call for a file, a folder, a bundled dataset or a hub repo.

pl.load("scan.ply")                      -> Object
pl.load("rire_brain")                    -> Dataset (bundled manifest, files fetched on access)
pl.load("sample://popi_lung_4dct")       -> same
pl.load("hf://org/name")                 -> Dataset, if a manifest for that repo is bundled or given
pl.load("my_dataset.manifest.json")      -> Dataset from your own manifest
pl.load("/data/study_A")                 -> Dataset after pl.scan; raises NeedsConfirmation
                                           until licence/units/labels are answered
"""

from __future__ import annotations

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from loguru import logger

from ..errors import ManifestError, NeedsConfirmation
from ..object import Object, wrap
from .cache import cache_dir, set_cache_dir
from .dataset import Dataset, Sample
from .manifest import Manifest, Role
from .scan import DRAFT_NAME, scan
from .sources import open_source

__all__ = [
    "DRAFT_NAME",
    "Dataset",
    "Manifest",
    "Object",
    "Role",
    "Sample",
    "cache_dir",
    "datasets",
    "load",
    "load_manifest",
    "scan",
    "set_cache_dir",
]


@lru_cache(maxsize=1)
def _bundled() -> dict[str, Manifest]:
    out: dict[str, Manifest] = {}
    folder = resources.files("pardesline.data") / "manifests"
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            m = Manifest.from_json(entry.read_text(encoding="utf-8"), where=f"bundled:{entry.name}")
            out[m.name] = m
    return out


def datasets() -> list[Manifest]:
    """The manifests bundled with the package (``pl.load(name)`` works on each)."""
    return list(_bundled().values())


def load_manifest(ref: str | os.PathLike) -> tuple[Manifest, Path | None]:
    """Resolve a bundled name, ``sample://name``, ``hf://repo`` or a manifest
    file. Returns (manifest, folder of the manifest file or None)."""
    text = str(ref)
    if text.startswith("sample://"):
        text = text[len("sample://") :]
    if text.startswith("hf://"):
        repo = text[len("hf://") :].strip("/")
        for m in _bundled().values():
            if m.source.scheme == "hf" and m.source.repo_id == repo:
                return m, None
        raise ManifestError(
            f"No manifest for hf://{repo} yet. pl.load needs one to know the roles, layout and licence. "
            "Write one (see docs/manifests.md) and pass it: pl.load('hf://...', manifest='path.json'), "
            "or contribute it to the repository."
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
        unknown = [k for k in keys if k not in m.roles]
        if unknown:
            raise ManifestError(f"{key}: unknown role(s) {unknown}; roles: {list(m.roles)}")
        return dict(val)
    return dict.fromkeys(m.roles, val)


def _apply_answers(m: Manifest, answers: dict[str, Any]) -> Manifest:
    """Fill a draft from keyword answers: license=, units=, frame=, labels=, pairing=."""
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
    for key in ("units", "frame", "labels"):
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
            else:
                answers.setdefault(key, {})[role] = reply
    return _apply_answers(m, answers)


def load(
    ref: str | os.PathLike,
    *,
    manifest: str | os.PathLike | None = None,
    assume: bool = False,
    interactive: bool = False,
    save_draft: bool = True,
    **answers: Any,
) -> Object | Dataset:
    """Open a file as an :class:`Object` or a dataset as a :class:`Dataset`.

    For a folder without a confirmed manifest, ``pl.scan`` drafts one. Then:
    strict (default) raises :class:`NeedsConfirmation` listing the open
    questions and saves the draft next to the data; ``assume=True`` loads
    with unknowns left unknown (and warns); ``interactive=True`` asks in the
    terminal; keyword answers (``license=..., units=..., frame=..., labels=...,
    pairing=...``) fill the draft directly.
    """
    text = str(ref)
    if "://" in text or manifest is not None:
        if manifest is not None:
            m, mdir = Manifest.load(manifest), Path(manifest).parent
            if text.startswith("hf://") and m.source.scheme == "hf":
                repo = text[len("hf://") :].strip("/")
                if m.source.repo_id != repo:
                    raise ManifestError(f"the manifest describes hf://{m.source.repo_id}, not hf://{repo}")
        else:
            m, mdir = load_manifest(text)
        return Dataset(m, open_source(m.source, m, manifest_dir=mdir))

    p = Path(text).expanduser()
    if p.is_file():
        if p.suffix.lower() == ".json" and not p.name.endswith(".pardesline.json"):
            try:
                m, mdir = Manifest.load(p), p.parent
            except ManifestError:
                raise ManifestError(
                    f"{p} is a JSON file but not a manifest; a 3D file was expected."
                ) from None
            return Dataset(m, open_source(m.source, m, manifest_dir=mdir))
        return wrap(p)
    if p.is_dir():
        draft_path = p / DRAFT_NAME
        if draft_path.is_file():
            m = Manifest.load(draft_path)
            if m.source.scheme == "local" and m.source.root in (None, ".", str(p), str(p.resolve())):
                m = m.model_copy(update={"source": m.source.model_copy(update={"root": str(p.resolve())})})
        else:
            m = scan(p)
        if answers:
            m = _apply_answers(m, answers)
        if m.is_draft and interactive:
            m = _ask_interactively(m)
        if m.is_draft and not assume:
            saved = None
            if save_draft:
                try:
                    saved = m.save(draft_path)
                except OSError as exc:
                    logger.debug("could not save the draft next to the data: {}", exc)
            raise NeedsConfirmation(m, saved)
        if m.is_draft:
            for q in m.questions:
                logger.warning("{}: assumed unknown - {}", q.field, q.message)
        return Dataset(m, open_source(m.source, m, manifest_dir=p))
    if text in _bundled():
        m = _bundled()[text]
        return Dataset(m, open_source(m.source, m))
    raise FileNotFoundError(
        f"pl.load({text!r}): no such file or folder, and no bundled dataset of that name "
        f"(bundled: {', '.join(_bundled()) or 'none'})."
    )


import re  # noqa: E402  (used by the interactive prompt parser)
