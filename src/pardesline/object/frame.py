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
        # commercial=False is a restriction and must survive a save: only values that state
        # nothing (None, redistribution "unknown", requires_agreement False) are left out.
        out: dict[str, Any] = {}
        for k, v in asdict(self).items():
            if (
                v is None
                or (k == "redistribution" and v == "unknown")
                or (k == "requires_agreement" and not v)
            ):
                continue
            out[k] = v
        return out

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


# Restrictiveness of the licences the package knows, by SPDX id: a higher rank allows less.
# This table is the only place licences are compared. A licence it does not list is treated
# as unknown, and an unknown licence is never upgraded to a known one.
#   0 public domain      no condition
#   1 attribution        credit the source; commercial use and derivatives allowed
#   2 share-alike        derivatives under the same terms
#   3 non-commercial     no commercial use
#   4 non-commercial, share-alike
#   5 no derivatives
#   6 non-commercial, no derivatives
LICENSE_ORDER: dict[str, int] = {
    "CC0-1.0": 0,
    "PDDL-1.0": 0,
    "Unlicense": 0,
    "CC-BY-3.0": 1,
    "CC-BY-4.0": 1,
    "ODC-By-1.0": 1,
    "MIT": 1,
    "BSD-2-Clause": 1,
    "BSD-3-Clause": 1,
    "Apache-2.0": 1,
    "ISC": 1,
    "CC-BY-SA-3.0": 2,
    "CC-BY-SA-4.0": 2,
    "ODbL-1.0": 2,
    "MPL-2.0": 2,
    "LGPL-3.0-only": 2,
    "GPL-3.0-only": 2,
    "GPL-3.0-or-later": 2,
    "CC-BY-NC-3.0": 3,
    "CC-BY-NC-4.0": 3,
    "CC-BY-NC-SA-2.0": 4,
    "CC-BY-NC-SA-3.0": 4,
    "CC-BY-NC-SA-4.0": 4,
    "CC-BY-ND-4.0": 5,
    "CC-BY-NC-ND-3.0": 6,
    "CC-BY-NC-ND-4.0": 6,
}

_REDISTRIBUTION_ORDER = {"allowed": 0, "unknown": 1, "forbidden": 2}


def combine_licenses(licenses: list[License], names: list[str] | None = None) -> License:
    """The licence of a result made from several inputs: the most restrictive wins.

    - any input whose licence is unknown, or not listed in :data:`LICENSE_ORDER`, makes the
      result unknown (``spdx=None``, ``commercial=None``);
    - otherwise ``spdx`` is the input of highest rank in :data:`LICENSE_ORDER`;
    - ``commercial`` is False if any input forbids it, True only if every input allows it,
      None otherwise; ``redistribution`` is the most restrictive of allowed < unknown <
      forbidden; ``requires_agreement`` is true if any input requires it;
    - ``note`` names every input licence, so the conditions of the others stay visible.
    """
    lics = list(licenses)
    if not lics:
        return License()
    if len(lics) == 1:
        return lics[0]
    labels = names or [f"input {i + 1}" for i in range(len(lics))]
    parts = [f"{n}: {lic.spdx or 'unknown'}" for n, lic in zip(labels, lics, strict=False)]
    note = "combined from " + "; ".join(parts) + " (most restrictive kept)"
    agreement = any(lic.requires_agreement for lic in lics)
    redistribution = max(
        (lic.redistribution or "unknown" for lic in lics), key=lambda r: _REDISTRIBUTION_ORDER.get(r, 1)
    )
    if redistribution not in _REDISTRIBUTION_ORDER:
        redistribution = "unknown"
    if any(lic.spdx is None or lic.spdx not in LICENSE_ORDER for lic in lics):
        return License(
            note=note + "; at least one is unknown, so the result is unknown",
            requires_agreement=agreement,
            redistribution=redistribution,
        )
    flags = [lic.commercial for lic in lics]
    commercial = False if False in flags else (True if all(f is True for f in flags) else None)
    top = max(lics, key=lambda lic: LICENSE_ORDER[lic.spdx])  # type: ignore[index]
    return License(
        spdx=top.spdx,
        commercial=commercial,
        source_url=top.source_url,
        note=note,
        requires_agreement=agreement,
        redistribution=redistribution,
    )
