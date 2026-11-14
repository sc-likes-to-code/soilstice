"""Shared building blocks — API_CONTRACTS §3."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field as PField
from pydantic import model_validator

from .vocab import (
    Aggregation,
    Contract,
    DataNature,
    DatasetId,
    ExtractionMethod,
    MissingReason,
    QualityStatus,
    Severity,
    SupportClass,
    TemporalResolution,
    TimeStandard,
    Unit,
)


class Uncertainty(Contract):
    kind: Literal["range", "std", "ci95", "classification_accuracy", "none_provided"]
    low: float | None = None
    high: float | None = None
    value: float | None = None
    note: str | None = None


class Quantity(Contract):
    value: float | None
    unit: Unit
    uncertainty: Uncertainty | None = None
    missing_reason: MissingReason | None = None

    @model_validator(mode="after")
    def _missing_iff_null(self) -> Quantity:
        # Rule R5: missing is value null + reason; never 0, never omitted.
        if (self.value is None) != (self.missing_reason is not None):
            raise ValueError("Quantity: missing_reason must be set if and only if value is null")
        return self


class SourceRef(Contract):
    dataset_id: DatasetId
    product: str
    product_version: str
    acquisition_id: UUID | None = None
    doi: str | None = None
    documentation_url: str | None = None
    retrieved_at: datetime | None = None


class SpatialSupport(Contract):
    support_class: SupportClass
    native_resolution_m: float | None = None
    extraction_method: ExtractionMethod
    field_fraction_of_cell: float | None = PField(default=None, ge=0, le=1)
    cell_id: str | None = None
    crs: str | None = None


class TemporalSupport(Contract):
    resolution: TemporalResolution
    period_start: date | None = None
    period_end: date | None = None
    aggregation: Aggregation
    time_standard: TimeStandard


class QualityFlag(Contract):
    code: str
    severity: Severity
    message: str


class QualityInfo(Contract):
    status: QualityStatus
    flags: list[QualityFlag] = []
    completeness: float | None = PField(default=None, ge=0, le=1)
    missing_reason: MissingReason | None = None


class MethodRef(Contract):
    method_id: str
    name: str
    version: str
    description: str
    reference_url: str | None = None


class TimeSeriesPoint(Contract):
    t: str
    value: float | None
    quality_status: QualityStatus
    missing_reason: MissingReason | None = None


class TimeSeriesReference(Contract):
    label: str
    period_start: date
    period_end: date
    points: list[TimeSeriesPoint]


class TimeSeries(Contract):
    series_id: str
    variable: str
    label: str
    unit: Unit
    nature: DataNature
    spatial: SpatialSupport
    temporal: TemporalSupport
    sources: list[SourceRef]
    points: list[TimeSeriesPoint]
    reference: TimeSeriesReference | None = None


class GeoJSONMultiPolygon(Contract):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[list[float]]]]
