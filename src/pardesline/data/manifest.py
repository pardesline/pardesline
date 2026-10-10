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

__all__ = ["FileSpec", "LicenseSpec", "Manifest", "Question", "Role", "SampleSpec", "SourceSpec"]

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
SCHEMES = ("local", "https", "hf", "open3d")

# Hash-addressed mirrors used by the SimpleITK notebooks data; ``{sha512}`` is substituted.
DEFAULT_MIRRORS = (
    "https://s3.amazonaws.com/simpleitk/public/notebooks/SHA512/{sha512}",
    "https://data.kitware.com/api/v1/file/hashsum/sha512/{sha512}/download",
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FileSpec(_Model):
    """One downloadable file of an ``https`` source."""

    sha512: str = Field(min_length=128, max_length=128, pattern=r"^[0-9a-f]+$")
    url: str | None = None
    archive: bool = False  # the download is a tar/zip whose content lands in the file's folder
    size_mb: float | None = None


class SourceSpec(_Model):
    scheme: Literal["local", "https", "hf", "open3d"]
    # local
    root: str | None = None
    # https
    files: dict[str, FileSpec] | None = None
    mirrors: list[str] | None = None
    # hf
    repo_id: str | None = None
    revision: str = "main"
    repo_type: str = "dataset"
    # open3d
    dataset: str | None = None

    @model_validator(mode="after")
    def _check(self) -> SourceSpec:
        need = {"local": ["root"], "https": ["files"], "hf": ["repo_id"], "open3d": ["dataset"]}[self.scheme]
        for field in need:
            if getattr(self, field) in (None, {}, ""):
                raise ValueError(f"source.{field} is required for scheme {self.scheme!r}")
        if self.scheme == "https" and self.files:
            for rel, spec in self.files.items():
                if spec.url is None and not (self.mirrors or DEFAULT_MIRRORS):
                    raise ValueError(f"source.files[{rel!r}] needs a url or mirrors")
        return self


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
    layout: dict[str, Any] | None = None  # for .npy/.bin: dtype, shape, columns - never guessed
    modality: str | None = None
    confidence: dict[str, float] | None = None  # from pl.scan: how sure each field is

    @field_validator("labels", mode="before")
    @classmethod
    def _int_keys(cls, v):
        if v is None:
            return None
        return {int(k): str(name) for k, name in v.items()}


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
        else:
            missing = [n for n, r in self.roles.items() if not r.pattern]
            if missing:
                raise ValueError(
                    f"without an explicit sample list every role needs a pattern; missing: {missing}"
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
        lines.append(
            f"  source:  {self.source.scheme}" + (f" {self.source.repo_id}" if self.source.repo_id else "")
        )
        lic = self.license.spdx or "unknown"
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
            lines.append(
                f"    {name:<12} {r.type:<10} {r.description or ''}"
                + (f"  [{'; '.join(extra)}]" if extra else "")
            )
        if self.questions:
            lines.append("  open questions:")
            for q in self.questions:
                lines.append(f"    - {q.field}: {q.message}")
        return "\n".join(lines)
