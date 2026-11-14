"""Internal storage records that are not wire contracts (they never leave the backend as-is)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.contracts import AoiId, DatasetId, MissingReason


class FarmRecord(BaseModel):
    farm_id: UUID
    name: str
    aoi_id: AoiId
    created_at: datetime
    updated_at: datetime


class AcquisitionRecord(BaseModel):
    """One upstream request (DATA_ARCHITECTURE §5.1 stage 1 `acquisition_log`). Secrets are never stored."""

    acquisition_id: UUID
    dataset_id: DatasetId
    request_url: str
    request_params_redacted: dict[str, Any] | None = None
    http_status: int | None = None
    sha256: str | None = None
    bytes: int | None = None
    retrieved_at: datetime
    object_uri: str | None = None
    error_class: str | None = None


StepState = str  # "available" | "partial" | "missing" | "pending"


class DatasetState(BaseModel):
    """Per-field, per-dataset processing outcome; drives DataCoverage."""

    field_id: UUID
    dataset_id: DatasetId
    state: StepState
    missing_reason: MissingReason | None = None
    message: str | None = None
    product_version: str | None = None
    temporal_start: str | None = None
    temporal_end: str | None = None
    updated_at: datetime
