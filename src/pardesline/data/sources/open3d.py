"""Open3D's bundled demo data (``open3d.data``), downloaded by Open3D itself
into its own cache. Needs ``pip install 'pardesline[local]'``."""

from __future__ import annotations

from pathlib import Path

from ...errors import FetchError, MissingDependency

__all__ = ["Open3DSource"]


class Open3DSource:
    """Demo data shipped by ``open3d.data`` (bunny, armadillo, ICP fragments), downloaded by Open3D itself."""

    def __init__(self, dataset: str):
        self.dataset = dataset
        self._paths: dict[str, Path] | None = None

    def _resolve(self) -> dict[str, Path]:
        if self._paths is None:
            try:
                import open3d as o3d
            except ImportError:
                raise MissingDependency("Open3D", "local") from None
            cls = getattr(o3d.data, self.dataset, None)
            if cls is None:
                raise FetchError(f"open3d.data has no dataset {self.dataset!r}")
            data = cls()  # downloads on first use
            paths = []
            if hasattr(data, "paths"):
                paths = [Path(p) for p in data.paths]
            elif hasattr(data, "path"):
                paths = [Path(data.path)]
            self._paths = {p.name: p for p in paths}
        return self._paths

    def list(self) -> list[str]:
        return sorted(self._resolve())

    def fetch(self, relpath: str) -> Path:
        paths = self._resolve()
        if relpath not in paths:
            raise FetchError(f"{relpath!r} is not a file of open3d.data.{self.dataset}; has {sorted(paths)}")
        return paths[relpath]

    def describe(self) -> str:
        return f"open3d.data.{self.dataset}"
