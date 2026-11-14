"""Typed API errors (API_CONTRACTS §4). Each maps to a stable code and HTTP status."""

from __future__ import annotations

from typing import Any

from app.contracts.envelope import ApiErrorCode

HTTP_STATUS: dict[str, int] = {
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "GEOMETRY_INVALID": 422,
    "OUTSIDE_AOI": 422,
    "FIELD_TOO_LARGE": 422,
    "NOT_EDITABLE": 409,
    "UPSTREAM_UNAVAILABLE": 503,
    "RATE_LIMITED": 429,
    "NOT_IMPLEMENTED": 501,
    "INTERNAL": 500,
}
RETRYABLE = {"UPSTREAM_UNAVAILABLE", "RATE_LIMITED", "INTERNAL"}


class ApiException(Exception):
    code: ApiErrorCode = "INTERNAL"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None, code: ApiErrorCode | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.message = message
        self.details = details

    @property
    def status_code(self) -> int:
        return HTTP_STATUS[self.code]

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE


class NotFound(ApiException):
    code = "NOT_FOUND"


class ValidationFailed(ApiException):
    code = "VALIDATION_ERROR"


class GeometryInvalid(ApiException):
    code = "GEOMETRY_INVALID"


class OutsideAoi(ApiException):
    code = "OUTSIDE_AOI"


class FieldTooLarge(ApiException):
    code = "FIELD_TOO_LARGE"


class NotEditable(ApiException):
    code = "NOT_EDITABLE"


class UpstreamUnavailable(ApiException):
    code = "UPSTREAM_UNAVAILABLE"


class RateLimited(ApiException):
    code = "RATE_LIMITED"


class NotImplementedYet(ApiException):
    code = "NOT_IMPLEMENTED"
