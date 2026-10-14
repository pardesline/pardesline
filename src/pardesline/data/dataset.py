"""Dataset and Sample: lazy, typed access to the files a manifest describes."""

from __future__ import annotations

import random
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from loguru import logger

from ..errors import ManifestError
from ..object import Frame, License, Object, wrap
from .manifest import LicenseSpec, Manifest, Role, SampleSpec, SourceSpec
from .sources import Source, fetch_folder

__all__ = ["Dataset", "Sample", "derive_samples"]

_DICOM_EXTS = {".dcm", ".ima", ".dicom"}

_ROLE_KIND = {
    "volume": "volume",
    "labels": "labels",
    "mesh": "mesh",
    "points": "pointcloud",
    "image": "image",
    "transform": "transform",
    "splat": "pointcloud",
    "attribute": "file",
    "calibration": "file",
    "file": "file",
}


def _pattern_regex(pattern: str) -> tuple[re.Pattern[str], list[str]]:
    """``"{id}/ct/*.dcm"`` -> regex with named groups; ``*`` matches within a
    path segment, ``**`` across segments."""
    names: list[str] = []
    out = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "{":
            j = pattern.index("}", i)
            name = pattern[i + 1 : j].split(":")[0]
            if name in names:
                out += f"(?P={name})"  # a repeated placeholder must match the same text
            else:
                names.append(name)
                out += f"(?P<{name}>[^/]+?)"  # non-greedy: {modality}_{id} splits at the first "_"
            i = j + 1
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif c == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(c)
            i += 1
    return re.compile("^" + out + "$"), names


def derive_samples(manifest: Manifest, listing: list[str]) -> list[SampleSpec]:
    """Group a file listing into samples using the roles' patterns."""
    groups: dict[str, dict[str, Any]] = {}
    extra_matches: dict[str, set[str]] = {}
    for role_name, role in manifest.roles.items():
        if not role.pattern:
            continue
        rx, _names = _pattern_regex(role.pattern)
        for rel in listing:
            m = rx.match(rel.rstrip("/"))  # folder entries (a DICOM series) end with "/"
            if not m:
                continue
            fields = m.groupdict()
            # ``{id}`` names the sample; otherwise every placeholder, in order,
            # so ``{study}/{subject}`` stays unique across studies.
            sid = fields.get("id") or "/".join(fields[n] for n in _names) or Path(rel).stem
            g = groups.setdefault(sid, {"files": {}, "fields": {}})
            if role_name in g["files"]:
                if Path(rel).suffix.lower() in _DICOM_EXTS or not Path(rel).suffix:
                    # several files for one role in one sample (DICOM slices): keep the folder
                    g["files"][role_name] = str(Path(rel).parent.as_posix())
                else:
                    # a second match (e.g. a second run of the same modality): keep the first, say so
                    extra_matches.setdefault(role_name, set()).add(sid)
            else:
                g["files"][role_name] = rel
            g["fields"].update({k: v for k, v in fields.items() if k != "id"})
    if not groups:
        raise ManifestError(f"{manifest.name}: no file in the source matches the role patterns.")
    for role_name, sids in extra_matches.items():
        logger.warning(
            "{}: role {!r} matches more than one file in {} sample(s) (e.g. {}); the first match is used. "
            "Refine the pattern or add a placeholder to tell them apart.",
            manifest.name,
            role_name,
            len(sids),
            sorted(sids)[0],
        )
    return [SampleSpec(id=sid, files=g["files"], fields=g["fields"]) for sid, g in sorted(groups.items())]


class Sample:
    """One unit of the dataset (a patient, a scan, a frame). Roles are
    attributes: ``sample.ct``, ``sample.mask``. Files are fetched on access."""

    def __init__(self, dataset: Dataset, spec: SampleSpec):
        self._dataset = dataset
        self._spec = spec
        self._cache: dict[str, Object] = {}

    @property
    def id(self) -> str:
        return self._spec.id

    @property
    def roles(self) -> list[str]:
        return list(self._spec.files)

    @property
    def fields(self) -> dict[str, str]:
        return dict(self._spec.fields)

    @property
    def license(self) -> License:
        return self._dataset.license

    def path(self, role: str) -> Path:
        """Fetch (if needed) and return the local path of a role. A folder
        entry (DICOM series) fetches every file it holds; a MetaImage header
        brings its ``.raw`` / ``.zraw`` sibling along."""
        rel = self._spec.files[role]
        src = self._dataset._source
        if rel.endswith("/") or rel in self._dataset._folders:
            return fetch_folder(src, rel)
        p = src.fetch(rel)
        low = rel.lower()
        if low.endswith(".mhd"):
            listing = self._dataset._listing()
            for ext in (".raw", ".zraw"):
                sibling = rel[:-4] + ext
                if sibling in listing:
                    src.fetch(sibling)
        return p

    def get(self, role: str) -> Object:
        if role not in self._spec.files:
            raise KeyError(f"sample {self.id!r} has no role {role!r}; roles: {self.roles}")
        if role not in self._cache:
            self._cache[role] = self._dataset._make_object(self, role)
        return self._cache[role]

    def __getitem__(self, role: str) -> Object:
        return self.get(role)

    def __getattr__(self, role: str) -> Object:
        if role.startswith("_"):
            raise AttributeError(role)
        try:
            return self.get(role)
        except KeyError as exc:
            raise AttributeError(str(exc)) from None

    def __dir__(self) -> list[str]:
        return sorted(set(super().__dir__()) | set(self.roles))

    def __repr__(self) -> str:
        fields = " ".join(f"{k}={v}" for k, v in self._spec.fields.items())
        return f"<Sample {self.id!r} roles={self.roles}{(' ' + fields) if fields else ''}>"

    def describe(self) -> str:
        lines = [repr(self)]
        for role in self.roles:
            r = self._dataset.manifest.roles[role]
            lines.append(f"  {role:<12} {r.type:<10} {self._spec.files[role]}")
        return "\n".join(lines)


class Dataset:
    """A manifest bound to its source. Indexing is lazy: nothing is fetched
    until a role of a sample is accessed."""

    def __init__(self, manifest: Manifest, source: Source, *, samples: list[SampleSpec] | None = None):
        self.manifest = manifest
        self._source = source
        if samples is None:
            if manifest.samples is not None:
                samples = list(manifest.samples)
            else:
                listing = source.list()
                if listing is None:
                    raise ManifestError(
                        f"{manifest.name}: this source cannot be listed; list the samples explicitly."
                    )
                samples = derive_samples(manifest, listing)
        self._specs: list[SampleSpec] = samples
        self._samples: dict[str, Sample] = {}
        self._folders: set[str] = {
            rel
            for s in samples
            for rel in s.files.values()
            if not rel.endswith("/") and "." not in rel.rsplit("/", 1)[-1]
        }
        self._listing_cache: list[str] | None = None
        self.license = License.from_dict(manifest.license.model_dump(exclude_none=True))
        if not self.license.known:
            logger.warning("{}: licence unknown - check the terms before using this data.", manifest.name)

    def _listing(self) -> list[str]:
        if self._listing_cache is None:
            self._listing_cache = self._source.list() or []
        return self._listing_cache

    # ---- metadata --------------------------------------------------------
    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def citation(self) -> str | None:
        return self.manifest.citation

    @property
    def roles(self) -> dict[str, Role]:
        return self.manifest.roles

    @property
    def is_draft(self) -> bool:
        return self.manifest.is_draft

    def describe(self) -> str:
        head = self.manifest.describe()
        return head + f"\n  files:   {self._source.describe()}\n  samples: {len(self)}"

    def __repr__(self) -> str:
        return f"<Dataset {self.name!r} {len(self)} samples, roles={list(self.roles)}>"

    # ---- samples ---------------------------------------------------------
    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[Sample]:
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, key: int | str) -> Sample:
        if isinstance(key, str):
            for spec in self._specs:
                if spec.id == key:
                    return self._sample(spec)
            raise KeyError(f"no sample {key!r} in {self.name}; ids: {self.ids[:10]}")
        spec = self._specs[key]
        return self._sample(spec)

    def _sample(self, spec: SampleSpec) -> Sample:
        if spec.id not in self._samples:
            self._samples[spec.id] = Sample(self, spec)
        return self._samples[spec.id]

    @property
    def ids(self) -> list[str]:
        return [s.id for s in self._specs]

    def take(self, n: int) -> Dataset:
        return self._subset(self._specs[:n])

    def sample(self, n: int, seed: int = 0) -> Dataset:
        rng = random.Random(seed)
        return self._subset(rng.sample(self._specs, min(n, len(self._specs))))

    def filter(self, **fields: str) -> Dataset:
        """Samples whose fields match, e.g. ``ds.filter(phase="00")``."""
        keep = [s for s in self._specs if all(s.fields.get(k) == v for k, v in fields.items())]
        return self._subset(keep)

    def _subset(self, specs: list[SampleSpec]) -> Dataset:
        return Dataset(self.manifest, self._source, samples=specs)

    def split(
        self, by: str | None = None, fractions: tuple[float, ...] = (0.8, 0.2), seed: int = 0
    ) -> tuple[Dataset, ...]:
        """Leakage-free split: all samples sharing the same ``by`` field (default
        the manifest's pairing key, else the sample id) land in the same part."""
        key = by or self.manifest.pairing or "id"
        if abs(sum(fractions) - 1.0) > 1e-6:
            raise ValueError("fractions must sum to 1")
        groups: dict[str, list[SampleSpec]] = {}
        for s in self._specs:
            g = s.id if key == "id" else s.fields.get(key, s.id)
            groups.setdefault(g, []).append(s)
        keys = sorted(groups)
        random.Random(seed).shuffle(keys)
        parts: list[list[SampleSpec]] = [[] for _ in fractions]
        bounds = [sum(fractions[: i + 1]) for i in range(len(fractions))]
        for i, k in enumerate(keys):
            pos = (i + 0.5) / len(keys)
            idx = next(j for j, b in enumerate(bounds) if pos <= b)
            parts[idx].extend(groups[k])
        return tuple(self._subset(p) for p in parts)

    # ---- by role / by type ----------------------------------------------
    def role(self, name: str) -> Iterator[Object]:
        if name not in self.roles:
            raise KeyError(f"no role {name!r} in {self.name}; roles: {list(self.roles)}")
        for s in self:
            if name in s.roles:
                yield s.get(name)

    def _by_type(self, *types: str) -> Iterator[Object]:
        for s in self:
            for r in s.roles:
                if self.roles[r].type in types:
                    yield s.get(r)

    @property
    def volumes(self) -> Iterator[Object]:
        return self._by_type("volume", "labels")

    @property
    def meshes(self) -> Iterator[Object]:
        return self._by_type("mesh")

    @property
    def points(self) -> Iterator[Object]:
        return self._by_type("points", "splat")

    def fetch_all(self) -> int:
        """Download every file now. Returns the number of files."""
        n = 0
        for s in self._specs:
            for rel in s.files.values():
                self._source.fetch(rel)
                n += 1
        return n

    # ---- objects ----------------------------------------------------------
    def _make_object(self, sample: Sample, role_name: str) -> Object:
        role = self.roles[role_name]
        rel = sample._spec.files[role_name]
        if role.needs_layout(rel):
            raise ManifestError(
                f"{self.name}: role {role_name!r} ({rel}) is a raw array and the manifest gives no layout "
                "(dtype, shape, columns / key). Add one to the role; the package never guesses it."
            )
        path = sample.path(role_name)
        declared = (
            Frame(axes=role.frame, units=role.units, source="manifest")
            if (role.frame or role.units)
            else None
        )
        obj = wrap(
            path,
            kind=_ROLE_KIND[role.type],
            frame=declared,
            labels=role.labels,
            license=self.license,
            role=role_name,
            layout=role.layout,
            provenance=[
                {
                    "step": "load",
                    "dataset": self.name,
                    "sample": sample.id,
                    "role": role_name,
                    "source": self._source.describe(),
                    "path": str(path),
                }
            ],
            read_sidecar=False,
        )
        if role.modality:
            obj.meta["modality"] = role.modality
        return obj

    # ---- standardise ------------------------------------------------------
    def export(self, folder: str | Path, *, overwrite: bool = False) -> Manifest:
        """Write every sample of this (sub)dataset as standard files in
        ``folder`` - raw arrays become PLY or MetaImage through their layout,
        DICOM series become one ``.mha`` - each with its ``.pardesline.json``
        sidecar (frame, units, labels, licence, provenance), plus a local
        ``pardesline.manifest.json`` so ``pl.load(folder)`` reopens the copy
        without questions. Returns that manifest."""
        root = Path(folder).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        roles_out: dict[str, Role] = {}
        samples_out: list[SampleSpec] = []
        for spec in self._specs:
            s = self[spec.id]
            files: dict[str, str] = {}
            for role_name in s.roles:
                obj = s.get(role_name)
                ext = _standard_extension(obj)
                rel = f"{spec.id}/{role_name}{ext}"
                dest = root / rel
                if dest.exists() and not overwrite:
                    raise FileExistsError(f"{dest} exists; pass overwrite=True to replace it")
                obj.save(dest)
                files[role_name] = rel
                src_role = self.roles[role_name]
                roles_out.setdefault(
                    role_name,
                    Role(
                        type=src_role.type,
                        description=src_role.description,
                        frame=obj.frame.axes,
                        units=obj.frame.units,
                        labels=src_role.labels,
                        modality=src_role.modality,
                    ),
                )
            samples_out.append(SampleSpec(id=spec.id, files=files, fields=dict(spec.fields)))
        lic = self.manifest.license
        out = Manifest(
            name=self.manifest.name,
            title=self.manifest.title,
            description=(
                f"Standard copy of {self.name} exported by pardesline from {self._source.describe()}. "
                + (self.manifest.description or "")
            ).strip(),
            source=SourceSpec(scheme="local", root="."),
            license=LicenseSpec(**lic.model_dump(exclude_none=True)),
            citation=self.manifest.citation,
            homepage=self.manifest.homepage,
            pairing=self.manifest.pairing,
            roles=roles_out,
            samples=samples_out,
            tags=list(self.manifest.tags),
        )
        from .scan import DRAFT_NAME

        out.save(root / DRAFT_NAME)
        logger.info("{}: {} samples exported to {}", self.name, len(samples_out), root)
        return out


def _standard_extension(obj: Object) -> str:
    """The file type an exported object takes: standard formats as they are,
    raw arrays and DICOM folders materialised."""
    if obj.is_raw_array:
        return ".mha" if obj.kind in ("volume", "labels") else ".ply"
    if obj.path.is_dir():
        return ".mha"
    ext = obj.extension
    return ext if ext else ".bin"
