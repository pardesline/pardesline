"""The Cancer Imaging Archive through the public NBIA REST API: the largest
open DICOM source (156 public collections in 2026-10, CT, MR, PET, RTSTRUCT,
SEG). No account is needed for public collections; restricted ones answer
401 and are out of scope here - the package never scripts past a data-use
agreement.

One dataset entry per DICOM series, named ``<PatientID>/<Modality>/
<SeriesInstanceUID>/`` so a manifest can route modalities to roles
(``{id}/CT/{series}``). Fetching a series downloads its zip from
``getImage`` and unpacks it in the cache; the folder is then a DICOM volume.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from ...errors import FetchError
from ..cache import dataset_cache_dir

__all__ = ["TciaSource"]

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(s: str) -> str:
    return _SAFE.sub("_", s)


class TciaSource:
    """A public collection of The Cancer Imaging Archive through the NBIA REST API.

    ``getSeries`` lists the series (PatientID, Modality, SeriesInstanceUID, counts);
    ``getImage`` returns one series as a zip of DICOM files, unpacked into a folder
    that opens as one volume. Restricted collections answer 401 and are not handled.
    """

    def __init__(
        self,
        name: str,
        collection: str,
        *,
        modalities: list[str] | None = None,
        api: str = "https://services.cancerimagingarchive.net/nbia-api/services/v1",
        cache: Path | None = None,
    ):
        self.name = name
        self.collection = collection
        self.modalities = [m.upper() for m in modalities] if modalities else None
        self.api = api.rstrip("/")
        self.cache = cache if cache is not None else dataset_cache_dir(name)
        self._series: dict[str, dict[str, Any]] | None = None  # relpath -> series record

    # ---- series index -------------------------------------------------------
    def _index_path(self) -> Path:
        return self.cache / ".tcia-series.json"

    def series(self) -> dict[str, dict[str, Any]]:
        if self._series is not None:
            return self._series
        idx = self._index_path()
        records: list[dict[str, Any]] | None = None
        if idx.is_file():
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
                if data.get("collection") == self.collection:
                    records = data["series"]
            except (OSError, ValueError, KeyError):
                records = None
        if records is None:
            try:
                r = httpx.get(
                    f"{self.api}/getSeries",
                    params={"Collection": self.collection},
                    timeout=120,
                    follow_redirects=True,
                )
            except httpx.HTTPError as exc:
                raise FetchError(f"cannot reach the TCIA API: {exc}") from None
            if r.status_code in (401, 403):
                raise FetchError(
                    f"TCIA collection {self.collection!r} is restricted: accept its data-use agreement on "
                    "cancerimagingarchive.net and download it with the NBIA Data Retriever; "
                    "the package does not script past it."
                )
            if r.status_code != 200:
                raise FetchError(f"TCIA getSeries for {self.collection!r}: HTTP {r.status_code}")
            try:
                records = r.json()
            except ValueError:
                raise FetchError(f"TCIA getSeries for {self.collection!r}: unreadable answer") from None
            if not records:
                raise FetchError(
                    f"TCIA collection {self.collection!r} is unknown or empty (check the exact name)."
                )
            try:
                idx.parent.mkdir(parents=True, exist_ok=True)
                idx.write_text(
                    json.dumps({"collection": self.collection, "series": records}), encoding="utf-8"
                )
            except OSError as exc:  # pragma: no cover
                logger.debug("series index not cached: {}", exc)
        out: dict[str, dict[str, Any]] = {}
        for s in records:
            mod = str(s.get("Modality") or "UNKNOWN").upper()
            if self.modalities and mod not in self.modalities:
                continue
            rel = f"{_safe(str(s.get('PatientID') or 'unknown'))}/{mod}/{s['SeriesInstanceUID']}/"
            out[rel] = s
        self._series = out
        return out

    # ---- Source protocol ----------------------------------------------------
    def list(self) -> list[str]:
        return sorted(self.series())

    def fetch(self, relpath: str) -> Path:
        return self.fetch_folder(relpath)

    def fetch_folder(self, relpath: str) -> Path:
        rel = relpath.rstrip("/") + "/"
        rec = self.series().get(rel)
        if rec is None:
            raise FetchError(f"{relpath!r} is not a series of TCIA collection {self.collection!r}")
        target = self.cache / rel.rstrip("/")
        marker = target / ".complete"
        if marker.is_file():
            return target
        uid = rec["SeriesInstanceUID"]
        logger.info(
            "{}: downloading series {} ({} images, {:.1f} MB) from TCIA",
            self.name,
            uid[-12:],
            rec.get("ImageCount"),
            (rec.get("FileSize") or 0) / 1e6,
        )
        buf = io.BytesIO()
        try:
            with httpx.stream(
                "GET",
                f"{self.api}/getImage",
                params={"SeriesInstanceUID": uid},
                timeout=600,
                follow_redirects=True,
            ) as r:
                if r.status_code != 200:
                    raise FetchError(f"TCIA getImage {uid}: HTTP {r.status_code}")
                for chunk in r.iter_bytes(1 << 20):
                    buf.write(chunk)
        except httpx.HTTPError as exc:
            raise FetchError(f"TCIA getImage {uid}: {exc}") from None
        buf.seek(0)
        if not zipfile.is_zipfile(buf):
            raise FetchError(f"TCIA getImage {uid}: the answer is not a zip archive")
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(buf) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name  # flatten: one series = one folder of files
                if not name or name.startswith("."):
                    continue
                (target / name).write_bytes(zf.read(info))
        marker.write_text(json.dumps(rec), encoding="utf-8")
        return target

    def series_info(self, relpath: str) -> dict[str, Any]:
        return dict(self.series().get(relpath.rstrip("/") + "/", {}))

    def describe(self) -> str:
        mods = f" [{', '.join(self.modalities)}]" if self.modalities else ""
        return f"TCIA collection {self.collection}{mods} via {self.api}, series cached in {self.cache}"
