"""Lightweight response models (Pydantic v2). Mirror the platform's /api/v1
schemas; only the fields the SDK uses are declared, extras are ignored."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Me(_Base):
    source: str = "api"
    access_state: str = "free"
    entitlements: dict = Field(default_factory=dict)
    quotas: dict = Field(default_factory=dict)
    period_resets_at: Optional[str] = None
    upgrade_url: Optional[str] = None
    user: dict = Field(default_factory=dict)

    @property
    def email(self) -> Optional[str]:
        return self.user.get("email")


class UploadSession(_Base):
    file_id: str
    mode: str
    upload_url: str
    method: str = "PUT"
    headers: dict = Field(default_factory=dict)
    expires_at: Optional[str] = None
    max_bytes: Optional[int] = None
    complete_url: str


class DownloadUrl(_Base):
    file_id: str
    mode: str
    url: str
    expires_at: Optional[str] = None
    filename: str = "download"
    size_bytes: int = 0


class Share(_Base):
    id: str
    file_id: str
    to: str
    permission: str = "read"
    status: str = "active"
    created_at: Optional[str] = None


class Job(_Base):
    id: str
    kind: str = "module"
    module_id: Optional[str] = None
    method_id: Optional[str] = None
    status: str = "pending"
    progress: int = 0
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_type: Optional[str] = None
    output_file_id: Optional[str] = None
    extra_output_file_ids: dict = Field(default_factory=dict)
    error: Optional[str] = None


class MethodInfo(_Base):
    id: str
    name: str = ""
    dual_input: bool = False
    parameters: List[dict] = Field(default_factory=list)


class ModuleInfo(_Base):
    id: str
    name: str = ""
    description: str = ""
    category: str = ""
    input_formats: List[str] = Field(default_factory=list)
    input_geometry: List[str] = Field(default_factory=list)
    dual_input: bool = False
    dual_input_label: str = ""
    methods: List[MethodInfo] = Field(default_factory=list)


class SampleInfo(_Base):
    id: str
    name: str = ""
    kind: str = ""
    geometry_type: Optional[str] = None
    extension: Optional[str] = None
    category: Optional[str] = None
    size_bytes: Optional[int] = None


class FileInfo(_Base):
    id: str
    name: str
    extension: str = ""
    geometry_type: Optional[str] = None
    size_bytes: int = 0
    file_type: str = "upload"
    owner_email: Optional[str] = None
    visibility: str = "private"
    created_at: Optional[str] = None
    project_id: Optional[str] = None
    workspace_id: Optional[str] = None
    job_id: Optional[str] = None
    permissions: List[str] = Field(default_factory=lambda: ["read"])
    shared_by: Optional[str] = None
    shared_at: Optional[str] = None
    share_id: Optional[str] = None
