"""``pl.scan``: draft a manifest for a private folder, and say what it could
not establish instead of guessing.

The draft groups files into samples (one sub-folder per sample when the
folder is organised that way, otherwise by shared name prefix, otherwise one
file per sample), names roles after the containing folder or the file type,
reads volume headers, and lists *questions*: licence, units and frame of
formats that do not carry them, label meanings, uncertain pairing.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

from ..object import ITK_VOLUME_EXTS, extension_of, kind_of
from ..object.frame import FORMAT_FRAMES
from .manifest import LicenseSpec, Manifest, Question, Role, SampleSpec, SourceSpec

__all__ = ["DRAFT_NAME", "scan"]

DRAFT_NAME = "pardesline.manifest.json"
_LABEL_HINT = re.compile(r"(mask|seg|label|gt|ground|annot|roi)", re.I)
_DICOM_EXTS = {".dcm", ".ima", ".dicom"}
# Formats the scan will not classify on its own (declare them in the manifest by hand).
_AMBIGUOUS_EXTS = {".txt", ".gz", ".zip", ".tar"}
_KIND_TO_ROLE_TYPE = {
    "pointcloud": "points",
    "mesh": "mesh",
    "volume": "volume",
    "image": "image",
    "transform": "transform",
}
_ROLE_RENAMES = {
    "images": "image",
    "img": "image",
    "masks": "mask",
    "labels": "mask",
    "segmentations": "mask",
    "meshes": "mesh",
}


def _sanitize(name: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    if not s or not s[0].isalpha():
        s = "r_" + s
    return _ROLE_RENAMES.get(s, s)


def _data_entries(root: Path) -> list[tuple[str, str]]:
    """(relpath, kind) for every data file; a DICOM folder is one 'volume' entry."""
    entries: list[tuple[str, str]] = []
    dicom_dirs: set[Path] = set()
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if p.is_file():
            if p.suffix.lower() in _DICOM_EXTS:
                dicom_dirs.add(p.parent)
                continue
            if p.parent in dicom_dirs:
                continue
            k = kind_of(p)
            if k in _KIND_TO_ROLE_TYPE and extension_of(p) not in _AMBIGUOUS_EXTS:
                entries.append((rel.as_posix(), k))
    for d in sorted(dicom_dirs):
        entries.append((d.relative_to(root).as_posix() if d != root else ".", "volume"))
    return entries


def _group(entries: list[tuple[str, str]]) -> tuple[dict[str, list[tuple[str, str]]], str, float]:
    """-> {sample_id: entries}, pairing key, confidence."""
    by_top: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for rel, k in entries:
        top = rel.split("/")[0] if "/" in rel else ""
        by_top[top].append((rel, k))
    tops_with_dirs = [t for t in by_top if t]
    flat = by_top.get("", [])
    # 1. one sub-folder per sample
    if len(tops_with_dirs) >= 2 and len(flat) == 0:
        return {t: by_top[t] for t in sorted(tops_with_dirs)}, "folder", 0.9
    # 2. flat folder: shared prefix "<id>_<role>" / "<id>-<role>"
    if flat and len(flat) >= 2:
        parts = {}
        for rel, _k in flat:
            stem = Path(rel).name
            stem = (
                stem[: -len(extension_of(rel))]
                if extension_of(rel) and stem.lower().endswith(extension_of(rel))
                else stem
            )
            m = re.match(r"^(.+?)[-_](.+)$", stem)
            parts[rel] = (m.group(1), m.group(2)) if m else (stem, "")
        suffix_sets: dict[str, set[str]] = defaultdict(set)
        for pid, suf in parts.values():
            suffix_sets[pid].add(suf)
        common = Counter(s for sufs in suffix_sets.values() for s in sufs)
        repeated = {s for s, c in common.items() if c >= 2 and s}
        if repeated and len(suffix_sets) >= 2:
            groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
            for rel, k in flat:
                groups[parts[rel][0]].append((rel, k))
            for t in tops_with_dirs:
                groups[t].extend(by_top[t])
            return dict(sorted(groups.items())), "name_prefix", 0.6
    # 3. one file per sample
    groups = {}
    for rel, k in entries:
        sid = _sanitize(Path(rel).name.split(".")[0]) if rel != "." else "root"
        base, n = sid, 2
        while sid in groups:
            sid = f"{base}_{n}"
            n += 1
        groups[sid] = [(rel, k)]
    return groups, "file", 0.5 if len(entries) > 1 else 0.9


def _role_name(rel: str, kind: str, sample_id: str, pairing: str, used: set[str]) -> str:
    parts = rel.split("/")
    folder = None
    if (pairing == "folder" and len(parts) >= 3) or (pairing != "folder" and len(parts) >= 2):
        folder = parts[-2]
    if folder:
        name = _sanitize(folder)
    else:
        stem = Path(rel).name.split(".")[0]
        if pairing == "name_prefix":
            m = re.match(r"^(.+?)[-_](.+)$", stem)
            name = _sanitize(m.group(2)) if m else _KIND_TO_ROLE_TYPE[kind]
        elif pairing == "folder" and _sanitize(stem) != _sanitize(sample_id):
            name = _sanitize(stem)  # p01/surface.stl -> "surface"
        else:
            name = _KIND_TO_ROLE_TYPE[kind]
    if kind == "volume" and _LABEL_HINT.search(Path(rel).name) and name == "volume":
        name = "mask"
    base, n = name, 2
    while name in used:
        name = f"{base}_{n}"
        n += 1
    used.add(name)
    return name


def scan(folder: str | Path, *, name: str | None = None, read_headers: bool = True) -> Manifest:
    """Draft a manifest for ``folder``. The result carries ``questions`` for
    every field that needs a human; ``pl.load(folder, ...)`` consumes it."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"not a folder: {root}")
    entries = _data_entries(root)
    if not entries:
        raise FileNotFoundError(f"no 3D data found under {root} (point clouds, meshes, volumes, DICOM).")
    groups, pairing, pairing_conf = _group(entries)

    roles: dict[str, Role] = {}
    samples: list[SampleSpec] = []
    role_examples: dict[str, str] = {}
    for sid, items in groups.items():
        used: set[str] = set()
        files: dict[str, str] = {}
        for rel, kind in items:
            rname = _role_name(rel, kind, sid, pairing, used)
            files[rname] = rel
            if rname not in roles:
                is_label = kind == "volume" and bool(_LABEL_HINT.search(rel))
                rtype = "labels" if is_label else _KIND_TO_ROLE_TYPE[kind]
                ext = extension_of(root / rel) if rel != "." else ".dcm"
                role = Role(type=rtype, description=f"{kind} files like {rel}", confidence={})
                if ext in FORMAT_FRAMES:
                    role.frame, role.units = FORMAT_FRAMES[ext].axes, FORMAT_FRAMES[ext].units
                    role.confidence = {"frame": 1.0, "units": 1.0}
                elif ext in ITK_VOLUME_EXTS:
                    role.frame, role.units = "LPS", "mm"
                    role.confidence = {"frame": 1.0, "units": 1.0}
                roles[rname] = role
                role_examples[rname] = rel
        samples.append(SampleSpec(id=_sanitize(sid) if pairing != "file" else sid, files=files))

    questions: list[Question] = [
        Question(
            field="license",
            message=(
                "Who owns this data and under which terms may it be used? "
                "(e.g. 'internal, no redistribution', 'CC-BY-4.0')"
            ),
        )
    ]
    if pairing_conf < 0.8 and len(samples) > 1:
        questions.append(
            Question(
                field="pairing",
                message=f"Files were grouped into {len(samples)} samples by {pairing}. Is that right?",
                suggestion=pairing,
            )
        )
    for rname, role in roles.items():
        if role.type in ("points", "mesh", "volume", "labels") and not role.units:
            questions.append(
                Question(
                    field=f"roles.{rname}.units",
                    message=f"{role_examples[rname]}: the format carries no unit. mm, m, ...?",
                )
            )
        if role.type in ("points", "mesh") and not role.frame:
            questions.append(
                Question(
                    field=f"roles.{rname}.frame",
                    message=(
                        f"{role_examples[rname]}: which axis convention (Y-up, Z-up, LPS, sensor, world)?"
                    ),
                )
            )
        if role.type == "labels":
            questions.append(
                Question(
                    field=f"roles.{rname}.labels",
                    message=(
                        f"{role_examples[rname]} looks like a label map (name hint). "
                        "What does each value mean? e.g. {1: 'liver'}"
                    ),
                )
            )
        elif role.type == "volume" and read_headers:
            try:
                from ..object.convert import read_volume_header

                header = read_volume_header(root / role_examples[rname])
                if header["integer"] and header["components"] == 1:
                    questions.append(
                        Question(
                            field=f"roles.{rname}.labels",
                            message=f"{role_examples[rname]} has integer voxels ({header['pixel_type']}). "
                            "Is it a label map? If so, name the values; if not, answer labels=None.",
                        )
                    )
            except Exception as exc:  # no SimpleITK, unreadable file: no question, just a note
                logger.debug("header of {} not read: {}", role_examples[rname], exc)

    manifest = Manifest(
        name=name or _sanitize(root.name) or "dataset",
        title=root.name,
        description=f"Scanned from {root}",
        source=SourceSpec(scheme="local", root=str(root)),
        license=LicenseSpec(),
        pairing=pairing,
        roles=roles,
        samples=samples,
        questions=questions,
    )
    return manifest
