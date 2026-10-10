"""Hugging Face Hub source: per-file lazy download through ``huggingface_hub``
(its own cache, resumable, token-aware). Needs ``pip install 'pardesline[hf]'``.

Gated or private repos use the user's own token (``huggingface-cli login`` or
``HF_TOKEN``); the package never scripts past a click-through.
"""

from __future__ import annotations

from pathlib import Path

from ...errors import FetchError, MissingDependency

__all__ = ["HfSource"]


class HfSource:
    def __init__(self, repo_id: str, *, revision: str = "main", repo_type: str = "dataset"):
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            raise MissingDependency("huggingface_hub", "hf") from None
        self.repo_id = repo_id
        self.revision = revision
        self.repo_type = repo_type
        self._listing: list[str] | None = None

    def list(self) -> list[str]:
        if self._listing is None:
            from huggingface_hub import HfApi
            from huggingface_hub.utils import HfHubHTTPError

            try:
                self._listing = sorted(
                    HfApi().list_repo_files(self.repo_id, repo_type=self.repo_type, revision=self.revision)
                )
            except HfHubHTTPError as exc:
                raise FetchError(f"cannot list hf://{self.repo_id}: {exc}") from None
        return self._listing

    def fetch(self, relpath: str) -> Path:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import HfHubHTTPError

        try:
            return Path(
                hf_hub_download(self.repo_id, relpath, repo_type=self.repo_type, revision=self.revision)
            )
        except HfHubHTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (401, 403):
                raise FetchError(
                    f"hf://{self.repo_id} is gated or private. Accept its terms on huggingface.co, then "
                    "`huggingface-cli login` (or set HF_TOKEN) and retry."
                ) from None
            raise FetchError(f"cannot fetch {relpath} from hf://{self.repo_id}: {exc}") from None

    def describe(self) -> str:
        return f"hf://{self.repo_id}@{self.revision}"
