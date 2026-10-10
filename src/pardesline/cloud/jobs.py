"""Job — a handle on a running computation. Poll it, wait for it, get its output."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, List, Optional

from .errors import PardesLineError
from .models import Job as JobModel

if TYPE_CHECKING:
    from .client import Client
    from .objects import RemoteObject

_TERMINAL = ("completed", "failed")


class JobFailed(PardesLineError):
    """A computation finished with status 'failed'."""


class Job:
    def __init__(self, client: Client, data: JobModel):
        self._client = client
        self._data = data

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def status(self) -> str:
        return self._data.status

    @property
    def kind(self) -> str:
        return self._data.kind

    @property
    def progress(self) -> int:
        return self._data.progress

    @property
    def error(self) -> Optional[str]:
        return self._data.error

    @property
    def done(self) -> bool:
        return self._data.status in _TERMINAL

    def refresh(self) -> Job:
        self._data = self._client._get_job(self.id)
        return self

    def logs(self, offset: int = 0) -> List[str]:
        return self._client._job_logs(self.id, offset)

    def wait(self, *, timeout: float = 600.0, poll: float = 1.5, raise_on_fail: bool = True) -> Job:
        """Block until the job finishes (or `timeout`), refreshing as it runs.
        Raises JobFailed on a failed job unless raise_on_fail=False."""
        start = time.time()
        interval = poll
        while not self.done:
            if time.time() - start > timeout:
                raise PardesLineError(f"Job {self.id} did not finish within {timeout}s (status {self.status}).")
            time.sleep(interval)
            interval = min(interval * 1.3, 5.0)
            self.refresh()
        if self.status == "failed" and raise_on_fail:
            raise JobFailed(self.error or "Job failed", code="job_failed")
        return self

    def result(self, *, wait: bool = True, timeout: float = 600.0) -> Optional[RemoteObject]:
        """The output file as a RemoteObject (waits for completion by default)."""
        if wait and not self.done:
            self.wait(timeout=timeout)
        return self._client._job_output(self.id)

    def __repr__(self) -> str:
        return f"<Job {self.kind} {self.status} progress={self.progress}% id={self.id[:8]}>"
