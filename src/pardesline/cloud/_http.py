"""Thin httpx transport: auth header, retries with backoff, error mapping.

A single place that turns HTTP failures into the typed errors in errors.py and
retries idempotent calls on 429/5xx. Used by every resource.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from . import __version__
from .errors import PardesLineError, TransferError, from_response

USER_AGENT = f"pardesline-python/{__version__}"
_RETRY_STATUS = {429, 500, 502, 503, 504}


class Transport:
    def __init__(self, base_url: str, token: Optional[str], *, timeout: float = 60.0,
                 max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.max_retries = max_retries
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if token:
            headers["X-API-Key"] = token
        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout,
                                    follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def set_token(self, token: Optional[str]) -> None:
        self.token = token
        if token:
            self._client.headers["X-API-Key"] = token
        else:
            self._client.headers.pop("X-API-Key", None)

    def request(self, method: str, path: str, *, json: Any = None, params: Any = None,
                auth: bool = True, timeout: Optional[float] = None) -> Any:
        """Call an /api endpoint, return the parsed JSON, raise a typed error.
        `timeout` (seconds) overrides the default for this call (GPU calls need
        a long read timeout for cold starts)."""
        headers = {}
        if not auth:
            headers["X-API-Key"] = ""  # override the client default for public routes
        kwargs = {"json": json, "params": params, "headers": headers or None}
        if timeout is not None:
            kwargs["timeout"] = httpx.Timeout(connect=30.0, read=float(timeout), write=60.0, pool=30.0)
        # GPU calls are long single attempts — don't retry a partial compute.
        retries = 0 if timeout and timeout > 120 else self.max_retries
        for attempt in range(retries + 1):
            try:
                resp = self._client.request(method, path, **kwargs)
            except httpx.HTTPError as e:
                if attempt < retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise TransferError(f"Network error calling {path}: {e}") from e
            if resp.status_code in _RETRY_STATUS and attempt < retries:
                time.sleep(float(resp.headers.get("Retry-After", 0)) or 0.5 * (2 ** attempt))
                continue
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                except Exception:
                    body = {"detail": resp.text}
                raise from_response(resp.status_code, body)
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()
        raise PardesLineError("request failed after retries")

    # ── raw bytes to/from a storage/API URL (no auth header for signed URLs) ──

    def put_bytes(self, url: str, data, *, headers: Optional[dict] = None, timeout: float = 900.0) -> None:
        absolute = url if url.startswith("http") else f"{self.base_url}{url}"
        h = dict(headers or {})
        # A signed bucket URL must NOT receive our API key; the API fallback
        # route (relative path) needs it.
        if not url.startswith("http") and self.token:
            h["X-API-Key"] = self.token
        try:
            with httpx.Client(timeout=timeout) as c:
                resp = c.put(absolute, content=data, headers=h)
        except httpx.HTTPError as e:
            raise TransferError(f"Upload failed: {e}") from e
        if resp.status_code >= 400:
            raise TransferError(f"Upload rejected by storage ({resp.status_code}): {resp.text[:200]}")

    def get_bytes(self, url: str, *, timeout: float = 900.0):
        absolute = url if url.startswith("http") else f"{self.base_url}{url}"
        h = {}
        if not url.startswith("http") and self.token:
            h["X-API-Key"] = self.token
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as c:
                resp = c.get(absolute, headers=h)
        except httpx.HTTPError as e:
            raise TransferError(f"Download failed: {e}") from e
        if resp.status_code >= 400:
            raise TransferError(f"Download failed ({resp.status_code}): {resp.text[:200]}")
        return resp.content

    def stream_to_file(self, url: str, dest, *, timeout: float = 900.0) -> int:
        absolute = url if url.startswith("http") else f"{self.base_url}{url}"
        h = {}
        if not url.startswith("http") and self.token:
            h["X-API-Key"] = self.token
        total = 0
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as c:
                with c.stream("GET", absolute, headers=h) as resp:
                    if resp.status_code >= 400:
                        raise TransferError(f"Download failed ({resp.status_code})")
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            total += len(chunk)
        except httpx.HTTPError as e:
            raise TransferError(f"Download failed: {e}") from e
        return total
