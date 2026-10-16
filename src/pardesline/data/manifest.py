"""The manifest: what ``pl.load`` reads instead of knowing the dataset.

A manifest says where the files come from (source), what the data may be
used for (licence), how files group into samples, and for each role what
the file does not say by itself: frame, units, label meanings, array layout.
Public datasets ship a manifest written once; private folders get one from
``pl.scan`` that the owner confirms.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..errors import ManifestError
from ..object.arrays import ARRAY_EXTS

__all__ = [
    "ARRAY_EXTS",
    "FileSpec",
    "Layout",
    "LicenseSpec",
    "Manifest",
    "Question",
    "Role",
    "SampleSpec",
    "SourceSpec",
]

ROLE_TYPES = (
    "volume",
    "labels",
    "mesh",
    "points",
    "image",
    "transform",
    "splat",
    "attribute",
    "calibration",
    "file",
)
SCHEMES = ("local", "https", "hf", "open3d", "archive", "s3", "tcia", "urllist")
TCIA_API = "https://services.cancerimagingarchive.net/nbia-api/services/v1"

# Hash-addressed mirrors used by the SimpleITK notebooks data; ``{sha512}`` is substituted.
DEFAULT_MIRRORS = (
    "https://s3.amazonaws.com/simpleitk/public/notebooks/SHA512/{sha512}",
    "https://data.kitware.com/api/v1/file/hashsum/sha512/{sha512}/download",
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FileSpec(_Model):
    """One downloadable file of an ``https`` source. ``sha512`` is preferred;
    ``md5`` is accepted when that is what the upstream publishes."""

    sha512: str | None = Field(default=None, min_length=128, max_length=128, pattern=r"^[0-9a-f]+$")
    md5: str | None = Field(default=None, min_length=32, max_length=32, pattern=r"^[0-9a-f]+$")
    url: str | None = None
    archive: bool = False  # the download is a tar/zip whose content lands in the file's folder
    archive_root: str | None = None  # ... or in this folder relative to the dataset cache ("." = root)
    size_mb: float | None = None

    @model_validator(mode="after")
    def _one_hash(self) -> FileSpec:
        if self.sha512 is None and self.md5 is None:
            raise ValueError("a file needs a sha512 (preferred) or an md5 checksum")
        return self


class SourceSpec(_Model):
    """Where the files come from.

    - ``local``: ``root`` folder (absolute, or relative to the manifest file).
    - ``https``: ``files`` with checksums, optional ``mirrors``.
    - ``hf``: ``repo_id`` on the Hugging Face Hub; ``paths`` restricts the
      listing to sub-folders (a 100k-file repo is never listed whole);
      ``max_files`` caps what one listing may return.
    - ``open3d``: a class of ``open3d.data``.
    - ``archive``: one remote ``url`` (or several ``urls`` that form one
      dataset) of zip or uncompressed tar read with HTTP Range requests: the
      index costs a few KB, a member costs its own size, the archive is never
      downloaded whole when the server supports ranges. ``prefix`` restricts
      the listing to members under it.
    - ``s3``: a public bucket listed with ListObjectsV2 (``bucket``,
      ``endpoint``, ``prefix``); relative paths are the keys under ``prefix``.
    - ``tcia``: a public collection of The Cancer Imaging Archive through the
      NBIA REST API (``collection``, optional ``modalities``); one entry per
      DICOM series as ``<PatientID>/<Modality>/<SeriesInstanceUID>/``.
    """

    scheme: Literal["local", "https", "hf", "open3d", "archive", "s3", "tcia", "urllist"]
    # local
    root: str | None = None
    # https
    files: dict[str, FileSpec] | None = None
    mirrors: list[str] | None = None
    # hf
    repo_id: str | None = None
    revision: str = "main"
    repo_type: str = "dataset"
    paths: list[str] | None = None
    max_files: int = Field(default=20000, ge=1)
    # open3d
    dataset: str | None = None
    # archive
    url: str | None = None
    urls: list[str] | None = None  # several archives forming one dataset (LUNA16 subsets, IXI modalities)
    format: Literal["zip", "tar"] | None = None  # inferred from the url when absent
    prefix: str | None = None
    sha512: str | None = Field(default=None, min_length=128, max_length=128, pattern=r"^[0-9a-f]+$")
    md5: str | None = Field(default=None, min_length=32, max_length=32, pattern=r"^[0-9a-f]+$")
    # s3 (public bucket)
    bucket: str | None = None
    endpoint: str = "https://s3.amazonaws.com"
    # tcia
    collection: str | None = None
    modalities: list[str] | None = None
    api: str = TCIA_API
    # urllist: a text index with one download URL per line
    index_url: str | None = None
    strip_prefix: str | None = None

    @model_validator(mode="after")
    def _check(self) -> SourceSpec:
        need = {
            "local": ["root"],
            "https": ["files"],
            "hf": ["repo_id"],
            "open3d": ["dataset"],
            "archive": [],
            "s3": ["bucket"],
            "tcia": ["collection"],
            "urllist": ["index_url"],
        }[self.scheme]
        for field in need:
            if getattr(self, field) in (None, {}, ""):
                raise ValueError(f"source.{field} is required for scheme {self.scheme!r}")
        if self.scheme == "archive":
            if not self.url and not self.urls:
                raise ValueError("source.url or source.urls is required for scheme 'archive'")
            if self.url and self.urls:
                raise ValueError("give source.url or source.urls, not both")
        if self.scheme == "https" and self.files:
            for rel, spec in self.files.items():
                if spec.url is None and not (self.mirrors or DEFAULT_MIRRORS):
                    raise ValueError(f"source.files[{rel!r}] needs a url or mirrors")
        if self.scheme == "archive" and self.format is None:
            low = (self.url or (self.urls or [""])[0]).lower().split("?")[0]
            if low.endswith(".zip"):
                self.format = "zip"
            elif low.endswith(".tar"):
                self.format = "tar"
            else:
                raise ValueError(
                    "source.format must be 'zip' or 'tar' when the url does not end with .zip/.tar "
                    "(compressed tars cannot be read by range)"
                )
        return self

    @property
    def archive_format(self) -> str:
        return self.format or ""

    @property
    def archive_urls(self) -> list[str]:
        return list(self.urls) if self.urls else ([self.url] if self.url else [])

    def key(self) -> str:
        """What identifies this source for ``pl.load`` lookups: the Hub repo,
        the bucket and prefix, the TCIA collection, the archive url(s)."""
        if self.scheme == "hf":
            return f"hf://{self.repo_id}"
        if self.scheme == "s3":
            return f"s3://{self.bucket}/{(self.prefix or '').strip('/')}".rstrip("/")
        if self.scheme == "tcia":
            return f"tcia://{self.collection}"
        if self.scheme == "archive":
            return ",".join(self.archive_urls)
        if self.scheme == "urllist":
            return f"urllist://{self.index_url}"
        return self.scheme


class Layout(_Model):
    """How to read a raw array file (``.npy``, ``.npz``, ``.bin``) as data.

    Points: ``shape="(N,4)"`` with ``columns=["x","y","z","reflectance"]``.
    Grids: ``shape="(L,W,H)"`` (voxel values) with optional ``spacing`` and
    ``origin`` in the role's units. ``dtype`` is required for headerless
    ``.bin`` / ``.raw`` files; ``key`` picks an array in an ``.npz``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    dtype: str | None = None
    shape: str | None = None  # "(N,3)", "(N,4)", "(200,200,16)"
    columns: list[str] | None = None
    key: str | None = None
    order: Literal["C", "F"] = "C"
    spacing: list[float] | None = None
    origin: list[float] | None = None
    scale: float | None = None  # multiply colours/intensities, e.g. 1/255
    note: str | None = None

    @field_validator("shape")
    @classmethod
    def _shape_syntax(cls, v):
        if v is None:
            return None
        s = v.replace(" ", "")
        if not re.fullmatch(r"\((?:[A-Za-z0-9]+)(?:,[A-Za-z0-9]+)*,?\)", s):
            raise ValueError(f"layout.shape {v!r} must look like '(N,3)' or '(200,200,16)'")
        return s

    def dims(self) -> list[int | None]:
        """``"(N,4)"`` -> ``[None, 4]``; letters mean 'whatever the file holds'."""
        if not self.shape:
            return []
        inner = self.shape.strip("()").rstrip(",")
        return [int(t) if t.isdigit() else None for t in inner.split(",") if t]


class LicenseSpec(_Model):
    spdx: str | None = None
    commercial: bool | None = None
    source_url: str | None = None
    note: str | None = None
    requires_agreement: bool = False
    redistribution: Literal["allowed", "forbidden", "unknown"] = "unknown"

    @property
    def confirmed(self) -> bool:
        return self.spdx is not None and "TO CONFIRM" not in (self.note or "")


class Role(_Model):
    type: Literal[
        "volume",
        "labels",
        "mesh",
        "points",
        "image",
        "transform",
        "splat",
        "attribute",
        "calibration",
        "file",
    ]
    description: str | None = None
    pattern: str | None = None  # "{id}/ct/*.dcm" - used when samples are not listed explicitly
    frame: str | None = None  # axis convention, e.g. "LPS", "sensor"
    units: str | None = None  # "mm", "m"
    labels: dict[int, str] | None = None
    layout: Layout | None = None  # for .npy/.npz/.bin: dtype, shape, columns - never guessed
    modality: str | None = None
    confidence: dict[str, float] | None = None  # from pl.scan: how sure each field is

    @field_validator("labels", mode="before")
    @classmethod
    def _int_keys(cls, v):
        if v is None:
            return None
        return {int(k): str(name) for k, name in v.items()}

    def needs_layout(self, relpath: str) -> bool:
        """True when ``relpath`` is a raw array and this role has no layout."""
        low = relpath.lower()
        return any(low.endswith(ext) for ext in ARRAY_EXTS) and self.layout is None


class SampleSpec(_Model):
    id: str
    files: dict[str, str]  # role -> relative path inside the source
    fields: dict[str, str] = Field(default_factory=dict)  # patient_id, phase, split ...


class Question(_Model):
    """Something the scan could not establish and will not guess."""

    field: str  # "license" | "roles.mask.labels" | "roles.mesh.units" | "pairing"
    message: str
    suggestion: Any = None


class Manifest(_Model):
    schema_version: int = 1
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$")
    title: str | None = None
    description: str | None = None
    source: SourceSpec
    license: LicenseSpec = Field(default_factory=LicenseSpec)
    citation: str | None = None
    homepage: str | None = None
    pairing: str | None = None  # what groups files into a sample: "patient", "phase", "folder", "file"
    roles: dict[str, Role]
    samples: list[SampleSpec] | None = None
    size_mb: float | None = None
    tags: list[str] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)  # non-empty = draft, needs confirmation

    @field_validator("roles")
    @classmethod
    def _roles_not_empty(cls, v):
        if not v:
            raise ValueError("a manifest needs at least one role")
        for name in v:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                raise ValueError(f"role name {name!r} must be a python identifier in lower case")
        return v

    @model_validator(mode="after")
    def _samples_reference_roles(self) -> Manifest:
        if self.samples is not None:
            ids = [s.id for s in self.samples]
            if len(ids) != len(set(ids)):
                raise ValueError("sample ids must be unique")
            for s in self.samples:
                unknown = set(s.files) - set(self.roles)
                if unknown:
                    raise ValueError(f"sample {s.id!r} uses undeclared role(s) {sorted(unknown)}")
                for role, rel in s.files.items():
                    if not self.is_draft and self.roles[role].needs_layout(rel):
                        raise ValueError(
                            f"sample {s.id!r} role {role!r}: {rel} is a raw array; the role needs a "
                            "'layout' (dtype, shape, columns) - the package never guesses one"
                        )
        else:
            missing = [n for n, r in self.roles.items() if not r.pattern]
            if missing:
                raise ValueError(
                    f"without an explicit sample list every role needs a pattern; missing: {missing}"
                )
            for name, r in self.roles.items():
                if not self.is_draft and r.pattern and r.needs_layout(r.pattern):
                    raise ValueError(
                        f"role {name!r}: pattern {r.pattern} names raw arrays; the role needs a "
                        "'layout' (dtype, shape, columns) - the package never guesses one"
                    )
        return self

    # ---- convenience -----------------------------------------------------
    @property
    def is_draft(self) -> bool:
        return bool(self.questions)

    def role_type(self, role: str) -> str:
        return self.roles[role].type

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.model_dump(mode="json", exclude_none=True, exclude_defaults=False), indent=indent
        )

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        return p

    @classmethod
    def from_json(cls, text: str, *, where: str = "<string>") -> Manifest:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ManifestError(f"{where}: not valid JSON ({exc})") from None
        return cls.from_dict(data, where=where)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, where: str = "<dict>") -> Manifest:
        try:
            return cls.model_validate(data)
        except Exception as exc:  # pydantic.ValidationError - keep one error type for callers
            raise ManifestError(f"{where}: invalid manifest - {exc}") from None

    @classmethod
    def load(cls, path: str | Path) -> Manifest:
        p = Path(path)
        if not p.is_file():
            raise ManifestError(f"manifest not found: {p}")
        return cls.from_json(p.read_text(encoding="utf-8"), where=str(p))

    def describe(self) -> str:
        lines = [f"{self.name}" + (f"  -  {self.title}" if self.title else "")]
        if self.description:
            lines.append(f"  {self.description}")
        src: str = str(self.source.scheme)
        if self.source.repo_id:
            src += f" hf://{self.source.repo_id}"
            if self.source.paths:
                src += f" ({', '.join(self.source.paths)})"
        elif self.source.scheme == "archive":
            urls = self.source.archive_urls
            src += f" {urls[0]}" + (f" (+{len(urls) - 1} more)" if len(urls) > 1 else "")
        elif self.source.scheme == "s3":
            src += f" {self.source.key()}"
        elif self.source.scheme == "tcia":
            src += f" {self.source.collection}" + (
                f" ({', '.join(self.source.modalities)})" if self.source.modalities else ""
            )
        lines.append(f"  source:  {src}")
        lic = self.license.spdx or "unknown"
        if self.license.commercial is False:
            lic += ", non-commercial"
        if self.license.requires_agreement:
            lic += ", requires accepting the source's terms"
        if self.license.note:
            lic += f" ({self.license.note})"
        lines.append(f"  licence: {lic}")
        if self.citation:
            lines.append(f"  cite:    {self.citation}")
        n = len(self.samples) if self.samples is not None else "pattern-derived"
        lines.append(f"  samples: {n}" + (f", paired by {self.pairing}" if self.pairing else ""))
        lines.append("  roles:")
        for name, r in self.roles.items():
            extra = []
            if r.frame or r.units:
                extra.append(f"{r.frame or '?'} {r.units or '?'}")
            if r.labels:
                extra.append("labels " + ", ".join(f"{k}={v}" for k, v in sorted(r.labels.items())))
            if r.layout and r.layout.shape:
                extra.append(f"layout {r.layout.shape}" + (f" {r.layout.dtype}" if r.layout.dtype else ""))
            lines.append(
                f"    {name:<12} {r.type:<10} {r.description or ''}"
                + (f"  [{'; '.join(extra)}]" if extra else "")
            )
        if self.questions:
            lines.append("  open questions:")
            for q in self.questions:
                lines.append(f"    - {q.field}: {q.message}")
        return "\n".join(lines)
