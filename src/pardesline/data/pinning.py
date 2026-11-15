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

_PENDING_HF = (
    "hub source on the moving 'main' revision; pinning needs the current commit id, read from "
    "the Hub API (network) - pending the owner's go-ahead (2026-11)"
)
_PENDING_ARCHIVE = (
    "remote archive without checksum or size/ETag pin; reading them needs a HEAD request per "
    "URL (network) - pending the owner's go-ahead (2026-11)"
)

KNOWINGLY_UNPINNED: dict[str, str] = {
    # Hugging Face repos: commit ids not yet read
    **{
        name: _PENDING_HF
        for name in (
            "hf_3d_arena",
            "hf_abdomenatlas_mini",
            "hf_biomedsegfm_3d_val",
            "hf_ct_rate_valid",
            "hf_kits23",
            "hf_kitti360_gs_subset",
            "hf_nsclc_radiomics",
            "hf_objaverse_glb_shard",
            "hf_openmind",
            "hf_uniocc_carla_mini",
        )
    },
    # remote archives: sizes / ETags not yet read
    **{
        name: _PENDING_ARCHIVE
        for name in (
            "amos22",
            "c3vd_endoscopy_splats",
            "chaos_abdomen",
            "ixi_brain_mri",
            "kitti_raw_2011_09_26_drive_0001",
            "luna16",
            "msd_task01_braintumour",
            "msd_task02_heart",
            "msd_task03_liver",
            "msd_task04_hippocampus",
            "msd_task05_prostate",
            "msd_task06_lung",
            "msd_task07_pancreas",
            "msd_task08_hepaticvessel",
            "msd_task09_spleen",
            "msd_task10_colon",
            "spider_lumbar_mri",
            "totalsegmentator_ct",
            "totalsegmentator_mri",
            "verse19_spine",
        )
    },
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
