"""Does a manifest say exactly which data it loads?

A manifest is *pinned* when loading it on two different days cannot silently return different
data: a Hugging Face source names a commit, an archive source records a checksum or the size and
ETag of every archive URL (checked when the archive is opened), ``https`` files carry checksums
(the schema requires them), Open3D datasets are verified by Open3D against its own checksums,
and local folders are the caller's.

A manifest that is not pinned must be listed in :data:`KNOWINGLY_UNPINNED` with the reason;
``tests/test_manifest_pinning.py`` fails on any other.
"""

from __future__ import annotations

import re

from .manifest import Manifest

__all__ = ["KNOWINGLY_UNPINNED", "pin_status"]

_COMMIT = re.compile(r"^[0-9a-f]{40}$")

KNOWINGLY_UNPINNED: dict[str, str] = {
    # sources that cannot be pinned by the manifest format today
    "openneuro_ds000228": (
        "public S3 bucket listed with ListObjectsV2: objects can be added or replaced; "
        "OpenNeuro snapshots (versioned) are not yet a source scheme"
    ),
    "tcia_lidc_idri": (
        "TCIA collection listed through the NBIA API: series can be added to a collection; "
        "pinning would list SeriesInstanceUIDs in the manifest"
    ),
    "tcia_nsclc_radiomics_dicom": (
        "TCIA collection listed through the NBIA API: series can be added; pinning "
        "would list SeriesInstanceUIDs in the manifest"
    ),
    "tcia_pancreas_ct": (
        "TCIA collection listed through the NBIA API: series can be added; pinning would "
        "list SeriesInstanceUIDs in the manifest"
    ),
    "tcia_prostate_3t": (
        "TCIA collection listed through the NBIA API: series can be added; pinning would "
        "list SeriesInstanceUIDs in the manifest"
    ),
    "medshapenet": (
        "URL list read from a remote index file that can change; the index has no published checksum"
    ),
}


def pin_status(m: Manifest) -> tuple[bool, str]:
    """(pinned, how): whether the manifest fixes the data it loads, and by what."""
    s = m.source
    if s.scheme == "hf":
        if _COMMIT.match(s.revision or ""):
            return True, f"Hugging Face commit {s.revision}"
        return False, f"Hugging Face revision {s.revision!r} is a branch or tag, not a commit"
    if s.scheme == "https":
        return True, "every file carries a checksum"
    if s.scheme == "archive":
        if s.sha512 or s.md5:
            return True, "archive checksum"
        urls = s.archive_urls if isinstance(s.archive_urls, list) else [s.archive_urls]
        pinned = set(s.pins or {})
        missing = [u for u in urls if u not in pinned]
        if not missing:
            return True, "size and ETag of every archive URL"
        return False, f"{len(missing)} of {len(urls)} archive URLs carry no checksum or size/ETag pin"
    if s.scheme == "open3d":
        return True, "Open3D verifies its downloads against its own checksums"
    if s.scheme == "local":
        return True, "local files"
    return False, f"scheme {s.scheme!r} lists a remote collection that can change"
