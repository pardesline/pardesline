"""Coordinate frames, units and licences carried by every object.

The rule of the package: a value that a file format does not carry is
*unknown*, never guessed. ``Frame.axes is None`` means "nobody said".
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

__all__ = ["AXES", "FORMAT_FRAMES", "UNITS", "Frame", "License"]

# Axis conventions we name. Anything else is kept verbatim as free text.
AXES = ("LPS", "RAS", "Y-up", "Z-up", "sensor", "world")
UNITS = ("mm", "cm", "m", "um", "px", "unitless")


@dataclass(frozen=True)
class Frame:
    """Where the coordinates of an object live.

    ``axes``: axis convention (``"LPS"`` for DICOM/ITK volumes, ``"RAS"`` for
    NIfTI headers, ``"Y-up"`` for glTF, ``"sensor"`` for a LiDAR sweep...).
    ``units``: length unit of one coordinate step. ``affine``: 4x4 row-major
    matrix from index/local space to the world frame, when the file has one
    (volumes). ``crs``: geographic reference for survey data. ``source``: who
    stated it - ``"file"`` (read from the header), ``"format"`` (fixed by the
    specification), ``"manifest"`` or ``"user"``.
    """

    axes: str | None = None
    units: str | None = None
    affine: tuple[tuple[float, float, float, float], ...] | None = None
    crs: str | None = None
    source: str | None = None

    @property
    def known(self) -> bool:
        return self.axes is not None and self.units is not None

    @property
    def unknown_fields(self) -> list[str]:
        out = []
        if self.axes is None:
            out.append("axes")
        if self.units is None:
            out.append("units")
        return out

    def merged(self, other: Frame | None) -> Frame:
        """``other`` fills what is unknown here; it never silently overrides a
        value the file itself stated."""
        if other is None:
            return self
        return Frame(
            axes=self.axes if self.axes is not None else other.axes,
            units=self.units if self.units is not None else other.units,
            affine=self.affine if self.affine is not None else other.affine,
            crs=self.crs if self.crs is not None else other.crs,
            source=self.source if self.source is not None else other.source,
        )

    def override(self, **changes: Any) -> Frame:
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Frame:
        if not d:
            return cls()
        affine = d.get("affine")
        if affine is not None:
            affine = tuple(tuple(float(x) for x in row) for row in affine)
        return cls(
            axes=d.get("axes"), units=d.get("units"), affine=affine, crs=d.get("crs"), source=d.get("source")
        )

    def describe(self) -> str:
        axes = self.axes or "unknown axes"
        units = self.units or "unknown units"
        src = f" ({self.source})" if self.source else ""
        crs = f", {self.crs}" if self.crs else ""
        return f"{axes}, {units}{crs}{src}"


# What a format fixes by specification. Everything absent here is unknown
# until a header (volumes) or a manifest says otherwise.
FORMAT_FRAMES: dict[str, Frame] = {
    ".glb": Frame(axes="Y-up", units="m", source="format"),
    ".gltf": Frame(axes="Y-up", units="m", source="format"),
}

# Formats SimpleITK reads into its own convention: once loaded, coordinates
# are LPS millimetres whatever the header said (NIfTI RAS is converted).
ITK_VOLUME_EXTS = frozenset({".mha", ".mhd", ".nrrd", ".nii", ".nii.gz", ".dcm", ".dicom", ".ima"})


@dataclass(frozen=True)
class License:
    """Terms attached to data. ``commercial=None`` means not established."""

    spdx: str | None = None
    commercial: bool | None = None
    source_url: str | None = None
    note: str | None = None
    requires_agreement: bool = False
    redistribution: str = "unknown"  # "allowed" | "forbidden" | "unknown"

    @property
    def known(self) -> bool:
        return self.spdx is not None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, "unknown", False)}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | str | None) -> License:
        if d is None:
            return cls()
        if isinstance(d, str):
            return cls(spdx=d)
        return cls(
            spdx=d.get("spdx"),
            commercial=d.get("commercial"),
            source_url=d.get("source_url"),
            note=d.get("note"),
            requires_agreement=bool(d.get("requires_agreement", False)),
            redistribution=d.get("redistribution", "unknown"),
        )

    def describe(self) -> str:
        if not self.known and not self.note:
            return "unknown licence"
        parts = [self.spdx or "no SPDX id"]
        if self.commercial is True:
            parts.append("commercial use allowed")
        elif self.commercial is False:
            parts.append("non-commercial")
        if self.requires_agreement:
            parts.append("requires accepting the source's terms")
        if self.note:
            parts.append(self.note)
        return "; ".join(parts)


License.UNKNOWN = License()  # type: ignore[attr-defined]
