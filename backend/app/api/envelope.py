"""Response envelope helpers (API_CONTRACTS §4, rule R7)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.contracts import QualityFlag, ResponseMeta

# This backend serves only real acquisitions (handover H4); synthetic data exists only in the frontend mock
# mode and in backend tests.
DATA_MODE = "live"


def meta(request: Request, warnings: list[QualityFlag] | None = None) -> ResponseMeta:
    return ResponseMeta(request_id=getattr(request.state, "request_id", "unknown"), generated_at=datetime.now(UTC),
                        data_mode=DATA_MODE, warnings=warnings or [])


def ok(request: Request, data: Any, warnings: list[QualityFlag] | None = None) -> dict:
    """Envelope; FastAPI validates it against the route's `ApiResponse[T]` response_model."""
    return {"data": data, "meta": meta(request, warnings)}
