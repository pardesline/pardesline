"""Hugging Face Hub source: listing and per-file lazy download through
``huggingface_hub`` (its own cache, resumable, token-aware). Needs
``pip install 'pardesline[hf]'``.

What the Hub taught us (2026-10): a repo like ``MIC-DKFZ/OpenMind`` holds
100 000+ files; listing it whole is 100+ paginated API calls and an
anonymous client is rate-limited (HTTP 429) long before the end. So a
manifest names the sub-folders it needs (``source.paths``), the listing is
done per folder with ``list_repo_tree`` and cached on disk for the repo
revision, and a cap (``source.max_files``) stops a runaway listing with an
explanation instead of a 429.

Gated or private repos use the user's own token (``huggingface-cli login``
or ``HF_TOKEN``); the package never scripts past a click-through.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import time
from pathlib import Path

from loguru import logger

from ...errors import FetchError, MissingDependency
from ..cache import cache_dir

__all__ = ["HfSource"]

_TOKEN_HINT = (
    "Set HF_TOKEN (or run `huggingface-cli login`) to raise the Hub's rate limit, and narrow the "
    "listing with source.paths / pl.load('hf://org/name/sub/folder')."
)
_warned_anonymous = False


def _status(exc: Exception) -> int | None:
    return getattr(getattr(exc, "response", None), "status_code", None)


class HfSource:
    """Files of a Hugging Face Hub repository, listed per ``paths`` and fetched with ``huggingface_hub``.

    The tree listing is cached on disk per commit sha; downloads go through the
    Hub cache (resumable, token-aware). Gated repositories need the user's own
    token after accepting the terms.
    """

    def __init__(
        self,
        repo_id: str,
        *,
        revision: str = "main",
        repo_type: str = "dataset",
        paths: list[str] | None = None,
        max_files: int = 20000,
    ):
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            raise MissingDependency("huggingface_hub", "hf") from None
        self.repo_id = repo_id
        self.revision = revision
        self.repo_type = repo_type
        self.paths = [p.strip("/") for p in paths] if paths else None
        self.max_files = max_files
        self._listing: list[str] | None = None
        self._sha: str | None = None

    # ---- helpers ----------------------------------------------------------
    def _api(self):
        from huggingface_hub import HfApi

        return HfApi()

    def _warn_if_anonymous(self) -> None:
        global _warned_anonymous
        if _warned_anonymous:
            return
        try:
            from huggingface_hub import get_token

            if get_token() is None:
                logger.info(
                    "hf://{}: anonymous requests to the Hub are rate-limited. {}", self.repo_id, _TOKEN_HINT
                )
        except Exception:  # pragma: no cover - only a hint
            pass
        _warned_anonymous = True

    def commit_sha(self) -> str:
        """The commit the revision points at (one API call, memoised)."""
        if self._sha is None:
            from huggingface_hub.utils import HfHubHTTPError

            try:
                info = self._api().repo_info(self.repo_id, repo_type=self.repo_type, revision=self.revision)
            except HfHubHTTPError as exc:
                raise self._translate(exc, f"cannot reach hf://{self.repo_id}") from None
            self._sha = str(getattr(info, "sha", None) or self.revision)
        return self._sha

    def _translate(self, exc: Exception, what: str) -> FetchError:
        status = _status(exc)
        if "Repository Not Found" in str(exc) or status == 404:
            return FetchError(f"{what}: not found on the Hub (repo, revision or path).")
        if status in (401, 403):
            return FetchError(
                f"hf://{self.repo_id} is gated or private. Accept its terms on huggingface.co, then "
                "`huggingface-cli login` (or set HF_TOKEN) and retry."
            )
        if status == 429:
            return FetchError(f"{what}: the Hub rate-limited this client (HTTP 429). {_TOKEN_HINT}")
        return FetchError(f"{what}: {exc}")

    def _listing_cache_path(self) -> Path:
        key = hashlib.sha1(
            json.dumps([self.repo_id, self.repo_type, self.commit_sha(), self.paths]).encode()
        ).hexdigest()[:16]
        folder = cache_dir() / "hf-listings"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{self.repo_id.replace('/', '__')}_{key}.json"

    # ---- Source protocol --------------------------------------------------
    def list(self) -> list[str]:
        if self._listing is not None:
            return self._listing
        self._warn_if_anonymous()
        cache_file = self._listing_cache_path()
        if cache_file.is_file():
            try:
                self._listing = json.loads(cache_file.read_text(encoding="utf-8"))["files"]
                return self._listing
            except (OSError, ValueError, KeyError):
                pass
        from huggingface_hub.utils import HfHubHTTPError

        api = self._api()
        files: list[str] = []
        t0 = time.perf_counter()
        try:
            folders: builtins.list[str | None] = list(self.paths) if self.paths else [None]
            for folder in folders:
                for entry in api.list_repo_tree(
                    self.repo_id,
                    path_in_repo=folder,
                    repo_type=self.repo_type,
                    revision=self.revision,
                    recursive=True,
                ):
                    if type(entry).__name__ == "RepoFolder" or getattr(entry, "size", None) is None:
                        continue  # a folder
                    files.append(entry.path)
                    if len(files) > self.max_files:
                        raise FetchError(
                            f"hf://{self.repo_id}: more than {self.max_files} files under "
                            f"{folder or 'the root'}. Name the sub-folders you need "
                            "(source.paths, or pl.load('hf://org/name/sub/folder')) "
                            "or raise source.max_files."
                        )
        except HfHubHTTPError as exc:
            raise self._translate(exc, f"cannot list hf://{self.repo_id}") from None
        files.sort()
        logger.debug(
            "hf://{}: {} files listed in {:.1f}s", self.repo_id, len(files), time.perf_counter() - t0
        )
        try:
            cache_file.write_text(
                json.dumps(
                    {"repo_id": self.repo_id, "sha": self.commit_sha(), "paths": self.paths, "files": files}
                ),
                encoding="utf-8",
            )
        except OSError as exc:  # pragma: no cover
            logger.debug("listing not cached: {}", exc)
        self._listing = files
        return files

    def fetch(self, relpath: str) -> Path:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import HfHubHTTPError

        try:
            return Path(
                hf_hub_download(self.repo_id, relpath, repo_type=self.repo_type, revision=self.revision)
            )
        except HfHubHTTPError as exc:
            raise self._translate(exc, f"cannot fetch {relpath} from hf://{self.repo_id}") from None

    def fetch_many(self, relpaths: builtins.list[str]) -> builtins.list[Path]:
        """Download several files in one ``snapshot_download`` (parallel, resumable)."""
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import HfHubHTTPError

        try:
            root = Path(
                snapshot_download(
                    self.repo_id,
                    repo_type=self.repo_type,
                    revision=self.revision,
                    allow_patterns=list(relpaths),
                )
            )
        except HfHubHTTPError as exc:
            raise self._translate(
                exc, f"cannot fetch {len(relpaths)} files from hf://{self.repo_id}"
            ) from None
        return [root / rel for rel in relpaths]

    def describe(self) -> str:
        scope = f" [{', '.join(self.paths)}]" if self.paths else ""
        return f"hf://{self.repo_id}@{self.revision}{scope}"
