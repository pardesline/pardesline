"""Credential resolution and the terminal login flow.

Precedence (highest first):
  1. an explicit token passed to Client(token=...) / login(token=...)
  2. the PARDESLINE_API_KEY environment variable (CI, notebooks)
  3. the key saved at ~/.pardesline/token (mode 0600) by a previous login()

login() with no argument is the Hugging-Face-style terminal flow: email →
6-digit code → the SDK mints a long-lived pl_ key with that short session and
stores it; the session token is discarded.
"""

from __future__ import annotations

import os
import socket
import stat
from pathlib import Path
from typing import Optional

ENV_VAR = "PARDESLINE_API_KEY"
ENV_BASE_URL = "PARDESLINE_BASE_URL"
DEFAULT_BASE_URL = "https://appbeta.pardesline.com"


def token_path() -> Path:
    override = os.environ.get("PARDESLINE_TOKEN_PATH")
    if override:
        return Path(override)
    return Path.home() / ".pardesline" / "token"


def load_saved_token() -> Optional[str]:
    p = token_path()
    try:
        if p.exists():
            tok = p.read_text(encoding="utf-8").strip()
            return tok or None
    except OSError:
        pass
    return None


def save_token(token: str) -> Path:
    p = token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(token.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)  # 0600 (best-effort on Windows)
    except OSError:
        pass
    return p


def clear_saved_token() -> None:
    try:
        token_path().unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:  # Python 3.7/3.8 have no missing_ok
        try:
            token_path().unlink()
        except OSError:
            pass
    except OSError:
        pass


def resolve_token(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit.strip()
    env = os.environ.get(ENV_VAR)
    if env:
        return env.strip()
    return load_saved_token()


def resolve_base_url(explicit: Optional[str] = None) -> str:
    return (explicit or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")


def default_key_name() -> str:
    try:
        host = socket.gethostname() or "device"
    except Exception:
        host = "device"
    return f"{host} (pardesline-python)"


def prompt(msg: str) -> str:
    return input(msg).strip()
