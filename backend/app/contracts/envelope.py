"""Envelope, errors, jobs — API_CONTRACTS §4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from .common import QualityFlag
from .vocab import API_VERSION, CONTRACT_VERSION, Contract, DataMode, DatasetId, MissingReason

T = TypeVar("T")


class ResponseMeta(Contract):
    request_id: str
    generated_at: datetime
    api_version: str = API_VERSION
    contract_version: str = CONTRACT_VERSION
    data_mode: DataMode
    warnings: list[QualityFlag] = []


class ApiResponse(Contract, Generic[T]):
    data: T
    meta: ResponseMeta


ApiErrorCode = Literal[
    "NOT_FOUND", "VALIDATION_ERROR", "OUTSIDE_AOI", "GEOMETRY_INVALID", "FIELD_TOO_LARGE",
    "NOT_EDITABLE", "UPSTREAM_UNAVAILABLE", "RATE_LIMITED", "NOT_IMPLEMENTED", "INTERNAL",
]


class ApiErrorBody(Contract):
    code: ApiErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: str
    retryable: bool


class ApiErrorResponse(Contract):
    error: ApiErrorBody


JobStatus = Literal["queued", "running", "succeeded", "partial", "failed"]


class JobStep(Contract):
    dataset_id: DatasetId
    status: JobStatus
    missing_reason: MissingReason | None = None
    message: str | None = None


class ProcessingJob(Contract):
    job_id: UUID
    field_id: UUID
    status: JobStatus
    steps: list[JobStep]
    created_at: datetime
    updated_at: datetime
