"""Typed errors raised by the PardesLine client.

Every error carries the platform's structured detail (`code`, `message`, and
for quota errors the usage numbers + upgrade link) so callers can branch on
`err.code` instead of parsing prose.
"""

from __future__ import annotations

from typing import Any, Optional


class PardesLineError(Exception):
    """Base class for every SDK error."""

    def __init__(self, message: str, *, code: Optional[str] = None, status: Optional[int] = None,
                 detail: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.detail = detail or {}


class AuthError(PardesLineError):
    """Not authenticated / invalid or revoked key (401). Run pl.login()."""


class Forbidden(PardesLineError):
    """Authenticated but not allowed (403) — e.g. not your file to share."""


class NotFound(PardesLineError):
    """No such file / not shared with you (404)."""


class Conflict(PardesLineError):
    """State conflict (409) — e.g. completing an upload with no bytes yet."""


class QuotaExceeded(PardesLineError):
    """A plan quota was reached (402). Carries the numbers + the upgrade link."""

    @property
    def quota(self) -> Optional[str]:
        return self.detail.get("quota")

    @property
    def used(self) -> Optional[int]:
        return self.detail.get("used")

    @property
    def limit(self) -> Optional[int]:
        return self.detail.get("limit")

    @property
    def resets_at(self) -> Optional[str]:
        return self.detail.get("resets_at")

    @property
    def upgrade_url(self) -> Optional[str]:
        return self.detail.get("upgrade_url")


class GpuAddonRequired(PardesLineError):
    """A GPU capability was requested without the GPU add-on (402/403)."""


class TooLarge(PardesLineError):
    """File exceeds the per-file transfer limit (413)."""


class RateLimited(PardesLineError):
    """Too many requests (429)."""


class PlatformLocked(PardesLineError):
    """The platform is temporarily locked by the administrator (503)."""


class TransferError(PardesLineError):
    """The bytes could not be moved to/from storage (network / storage error)."""


_BY_CODE = {
    "unauthenticated": AuthError,
    "forbidden": Forbidden,
    "not_found": NotFound,
    "conflict": Conflict,
    "quota_exceeded": QuotaExceeded,
    "gpu_addon_required": GpuAddonRequired,
    "too_large": TooLarge,
    "rate_limited": RateLimited,
    "platform_locked": PlatformLocked,
}

_BY_STATUS = {
    401: AuthError, 402: QuotaExceeded, 403: Forbidden, 404: NotFound,
    409: Conflict, 413: TooLarge, 429: RateLimited, 503: PlatformLocked,
}


def from_response(status: int, body: Any) -> PardesLineError:
    """Build the right exception from an HTTP error response body."""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        code = detail.get("code")
        message = detail.get("message") or code or f"HTTP {status}"
        cls = _BY_CODE.get(code) or _BY_STATUS.get(status, PardesLineError)
        return cls(message, code=code, status=status, detail=detail)
    message = (detail if isinstance(detail, str) else None) or f"HTTP {status}"
    cls = _BY_STATUS.get(status, PardesLineError)
    return cls(message, status=status)
