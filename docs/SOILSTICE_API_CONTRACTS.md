# SOILSTICE: API Contracts (frozen at Phase 0 exit)

**Status:** Implementation-ready specification. **Contract version `v1.0.0-phase0`.**
**Date:** 2026-11-14
**Consumers:**
- Phase 1 frontend: TypeScript types plus mock services.
- Phase 2 backend: Pydantic models plus FastAPI routes.

**Related:** [SOILSTICE_UI_ARCHITECTURE.md](SOILSTICE_UI_ARCHITECTURE.md) · [SOILSTICE_DATA_ARCHITECTURE.md](SOILSTICE_DATA_ARCHITECTURE.md) §5–6

> This document contains **type definitions only**: no application code and no data values. Any number appearing in an example is a placeholder, and every example is marked `"_example": true`.

---

## 1. Contract rules

| # | Rule |
|---|---|
| R1 | **Wire format is JSON with `snake_case` keys.** TypeScript types mirror `snake_case` exactly. No camelCase mapping layer. |
| R2 | **Canonical units are metric** (§2.2). The API never converts to imperial. The UI may convert for *display only*. |
| R3 | **Every measured or derived number travels as a `Quantity`**: value + unit + uncertainty + missing reason. Bare numbers are allowed only for identifiers, counts of records, geometry and scores that carry a `ScoreBand`. |
| R4 | **Every observation, indicator, series and profile carries** `sources: SourceRef[]`, `spatial: SpatialSupport` and `temporal: TemporalSupport` (or `quality` where noted). Source carries product version; spatial carries resolution and support class. |
| R5 | **Missing is `value: null` + `missing_reason`.** Never 0, never omitted. |
| R6 | **Synthetic data is self-identifying.** Every response has `meta.data_mode` (`"synthetic"` \| `"live"`). Every mock `SourceRef` uses `dataset_id: "synthetic"`. The UI badges both. |
| R7 | All responses use the envelope `ApiResponse<T>`. Errors use `ApiErrorResponse` with a stable `code`. |
| R8 | IDs are UUID v4 strings, except `dataset_id`, `indicator key` and `crop_code`, which are controlled vocabularies (§2). |
| R9 | **Additive-only evolution after freeze.** New optional fields are allowed. Renames and removals need a contract version bump and an entry in §9. |
| R10 | **The frontend talks only to FastAPI.** It never reads Supabase directly, so there is one contract surface. |

**Source-of-truth flow:**
1. This document is the source of truth.
2. Phase 1 hand-writes `types/contracts.ts` from it.
3. Phase 2 writes Pydantic models from it.
4. From Phase 2 on, FastAPI's OpenAPI schema is exported and TS types are generated with `openapi-typescript` (dev-only). The generated types are diffed against the hand-written ones in CI. Any difference is a contract violation.

---

## 2. Controlled vocabularies

### 2.1 TypeScript

```ts
// ---- primitives ----
export type UUID = string;            // RFC 4122 v4
export type ISODate = string;         // "YYYY-MM-DD"
export type ISODateTime = string;     // RFC 3339, UTC "Z"

export type DataMode = "synthetic" | "live";
export type SupportClass = "F" | "S" | "R";     // field-resolved | sub-regional | regional context
export type DataNature = "observation" | "model" | "derived" | "classification" | "proxy_statistic";
export type QualityStatus = "valid" | "partial" | "flagged" | "missing";
export type ScoreBand = "low" | "moderate" | "high" | "unknown";
export type Confidence = "low" | "medium" | "high";
export type Severity = "info" | "warning" | "critical";

export type MissingReason =
  | "NO_DATA_SOURCE" | "FILL_VALUE" | "QA_MASKED_CLOUD" | "QA_MASKED_SHADOW" | "QA_MASKED_SNOW"
  | "QA_LOW_QUALITY_RETRIEVAL" | "INSUFFICIENT_COVERAGE" | "OUT_OF_TEMPORAL_RANGE"
  | "UPSTREAM_ERROR" | "NOT_YET_PUBLISHED" | "NOT_COMPUTED" | "OUTSIDE_AOI" | "PENDING_PROCESSING";

export type DatasetId =
  | "nasa_power_daily_ag" | "usda_nrcs_ssurgo_sda" | "usda_nass_cdl" | "usda_nass_csb"
  | "nasa_hls" | "nasa_hls_vi" | "nasa_smap_spl4smgp" | "nasa_srtm_gl1"
  | "prism_daily" | "openet" | "usda_nass_quickstats" | "nasa_smap_spl3smp_e"
  | "nasa_gpm_imerg" | "fao_gaez_v5"
  | "soilstice_derived" | "user_input" | "synthetic";

export type ExtractionMethod =
  | "zonal_polygon" | "zonal_polygon_inward_buffer" | "containing_cell" | "api_point_query"
  | "vector_intersection" | "attribute_join" | "not_applicable";

export type TemporalResolution = "PT3H" | "P1D" | "P1M" | "season" | "P1Y" | "static" | "irregular";
export type Aggregation =
  | "none" | "mean" | "sum" | "median" | "min" | "max" | "majority" | "weighted_mean" | "percentile" | "count";
export type TimeStandard = "UTC" | "LST" | "not_applicable";

export type Unit =
  | "mm" | "degC" | "degC_day" | "percent" | "MJ_m-2_day-1" | "MJ_m-2" | "m3_m-3" | "wetness_0_1"
  | "cm" | "cm_cm-1" | "m" | "degree" | "pH" | "ha" | "day" | "year" | "count"
  | "percentile" | "unitless" | "score_0_100";

export type IndicatorCategory = "climate" | "soil_moisture" | "vegetation" | "water" | "soil" | "terrain" | "rotation";

export type IndicatorKey =
  // climate (support R from POWER; S once PRISM is integrated)
  | "precip_total_season" | "precip_anomaly_pct" | "gdd_season" | "heat_stress_days"
  | "frost_free_days" | "solar_total_season" | "rh_mean_season"
  // water
  | "et0_total_season" | "water_balance_season" | "et_actual_season"          // et_actual = OpenET (P1)
  // soil moisture (support R)
  | "sm_rootzone_mean_season" | "sm_rootzone_percentile" | "sm_rootzone_dry_days"
  // vegetation (support F)
  | "ndvi_peak" | "ndvi_peak_doy" | "ndvi_peak_cv" | "ndmi_peak_season"
  // soil (support F)
  | "aws_0_150" | "ph_0_30" | "om_0_30" | "clay_0_30"
  // terrain (support F)
  | "slope_mean_pct" | "slope_p90_pct" | "elevation_mean"
  // rotation (support F)
  | "distinct_crops" | "max_monoculture_run" | "rotation_shannon";

export type CropCode = number;   // USDA CDL category code (e.g., 1, 4, 5, 24, 26, 36, 61). The KB defines the allowed set.
```

### 2.2 Indicator key → canonical unit (normative)

| Key | Unit | Support | Phase computed |
|---|---|---|---|
| precip_total_season, et0_total_season, water_balance_season, et_actual_season | mm | R (S with PRISM; F with OpenET) | 4 |
| precip_anomaly_pct | percent | R/S | 4 |
| gdd_season | degC_day | R/S | 4 |
| heat_stress_days, frost_free_days, sm_rootzone_dry_days | day | R/S | 4 |
| solar_total_season | MJ_m-2 | R | 4 |
| rh_mean_season | percent | R | 4 |
| sm_rootzone_mean_season | m3_m-3 | R | 4 |
| sm_rootzone_percentile | percentile | R | 4 |
| ndvi_peak, ndvi_peak_cv, ndmi_peak_season | unitless | F | 4 |
| ndvi_peak_doy | day | F | 4 |
| aws_0_150 | cm | F | 3 |
| ph_0_30 | pH | F | 3 |
| om_0_30, clay_0_30 | percent | F | 3 |
| slope_mean_pct, slope_p90_pct | percent | F | 3 |
| elevation_mean | m | F | 3 |
| distinct_crops, max_monoculture_run | count / year | F | 4 |
| rotation_shannon | unitless | F | 4 |

### 2.3 Pydantic (v2)

```python
from typing import Literal, Optional, Generic, TypeVar
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field as PField

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

DataMode = Literal["synthetic", "live"]
SupportClass = Literal["F", "S", "R"]
DataNature = Literal["observation", "model", "derived", "classification", "proxy_statistic"]
QualityStatus = Literal["valid", "partial", "flagged", "missing"]
ScoreBand = Literal["low", "moderate", "high", "unknown"]
Confidence = Literal["low", "medium", "high"]
Severity = Literal["info", "warning", "critical"]
MissingReason = Literal[
    "NO_DATA_SOURCE", "FILL_VALUE", "QA_MASKED_CLOUD", "QA_MASKED_SHADOW", "QA_MASKED_SNOW",
    "QA_LOW_QUALITY_RETRIEVAL", "INSUFFICIENT_COVERAGE", "OUT_OF_TEMPORAL_RANGE",
    "UPSTREAM_ERROR", "NOT_YET_PUBLISHED", "NOT_COMPUTED", "OUTSIDE_AOI", "PENDING_PROCESSING"]
DatasetId = Literal[
    "nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "usda_nass_csb",
    "nasa_hls", "nasa_hls_vi", "nasa_smap_spl4smgp", "nasa_srtm_gl1",
    "prism_daily", "openet", "usda_nass_quickstats", "nasa_smap_spl3smp_e",
    "nasa_gpm_imerg", "fao_gaez_v5", "soilstice_derived", "user_input", "synthetic"]
ExtractionMethod = Literal[
    "zonal_polygon", "zonal_polygon_inward_buffer", "containing_cell", "api_point_query",
    "vector_intersection", "attribute_join", "not_applicable"]
TemporalResolution = Literal["PT3H", "P1D", "P1M", "season", "P1Y", "static", "irregular"]
Aggregation = Literal["none", "mean", "sum", "median", "min", "max", "majority",
                      "weighted_mean", "percentile", "count"]
TimeStandard = Literal["UTC", "LST", "not_applicable"]
Unit = Literal["mm", "degC", "degC_day", "percent", "MJ_m-2_day-1", "MJ_m-2", "m3_m-3", "wetness_0_1",
               "cm", "cm_cm-1", "m", "degree", "pH", "ha", "day", "year", "count",
               "percentile", "unitless", "score_0_100"]
IndicatorCategory = Literal["climate", "soil_moisture", "vegetation", "water", "soil", "terrain", "rotation"]
IndicatorKey = Literal[
    "precip_total_season", "precip_anomaly_pct", "gdd_season", "heat_stress_days", "frost_free_days",
    "solar_total_season", "rh_mean_season", "et0_total_season", "water_balance_season", "et_actual_season",
    "sm_rootzone_mean_season", "sm_rootzone_percentile", "sm_rootzone_dry_days",
    "ndvi_peak", "ndvi_peak_doy", "ndvi_peak_cv", "ndmi_peak_season",
    "aws_0_150", "ph_0_30", "om_0_30", "clay_0_30",
    "slope_mean_pct", "slope_p90_pct", "elevation_mean",
    "distinct_crops", "max_monoculture_run", "rotation_shannon"]
CropCode = int
```

---

## 3. Shared building blocks

### 3.1 TypeScript

```ts
export interface Uncertainty {
  kind: "range" | "std" | "ci95" | "classification_accuracy" | "none_provided";
  low: number | null;          // for "range" / "ci95"
  high: number | null;
  value: number | null;        // for "std" / "classification_accuracy" (0–1)
  note: string | null;
}

export interface Quantity {
  value: number | null;
  unit: Unit;
  uncertainty: Uncertainty | null;
  missing_reason: MissingReason | null;     // non-null iff value === null
}

export interface SourceRef {
  dataset_id: DatasetId;
  product: string;                 // e.g. "SPL4SMGP", "HLSS30_VI", "CDL", "POWER Daily API"
  product_version: string;         // e.g. "008", "2.0", "2025", "v2.10.3"
  acquisition_id: UUID | null;     // links to acquisition_log; null for synthetic
  doi: string | null;
  documentation_url: string | null;
  retrieved_at: ISODateTime | null;
}

export interface SpatialSupport {
  support_class: SupportClass;
  native_resolution_m: number | null;      // null for vector sources
  extraction_method: ExtractionMethod;
  field_fraction_of_cell: number | null;   // 0–1; only for "containing_cell"
  cell_id: string | null;
  crs: string | null;                      // native CRS, e.g. "EPSG:6933"
}

export interface TemporalSupport {
  resolution: TemporalResolution;
  period_start: ISODate | null;
  period_end: ISODate | null;
  aggregation: Aggregation;
  time_standard: TimeStandard;
}

export interface QualityFlag { code: string; severity: Severity; message: string; }

export interface QualityInfo {
  status: QualityStatus;
  flags: QualityFlag[];
  completeness: number | null;             // 0–1
  missing_reason: MissingReason | null;
}

export interface MethodRef {
  method_id: string;                       // e.g. "gdd_single_triangle" | "ssurgo_area_comppct_weighting"
  name: string;
  version: string;
  description: string;
  reference_url: string | null;
}

export interface TimeSeriesPoint {
  t: ISODate | ISODateTime;
  value: number | null;
  quality_status: QualityStatus;
  missing_reason: MissingReason | null;
}

export interface TimeSeries {
  series_id: string;
  variable: string;                        // e.g. "precipitation", "sm_rootzone", "ndvi"
  label: string;
  unit: Unit;
  nature: DataNature;
  spatial: SpatialSupport;
  temporal: TemporalSupport;
  sources: SourceRef[];
  points: TimeSeriesPoint[];
  reference: { label: string; period_start: ISODate; period_end: ISODate; points: TimeSeriesPoint[] } | null; // e.g. 1991–2020 normal
}

export interface GeoJSONMultiPolygon { type: "MultiPolygon"; coordinates: number[][][][]; } // EPSG:4326, [lon, lat]
```

### 3.2 Pydantic

```python
class Uncertainty(Contract):
    kind: Literal["range", "std", "ci95", "classification_accuracy", "none_provided"]
    low: Optional[float] = None
    high: Optional[float] = None
    value: Optional[float] = None
    note: Optional[str] = None

class Quantity(Contract):
    value: Optional[float]
    unit: Unit
    uncertainty: Optional[Uncertainty] = None
    missing_reason: Optional[MissingReason] = None
    # validator (Phase 2): (value is None) == (missing_reason is not None)

class SourceRef(Contract):
    dataset_id: DatasetId
    product: str
    product_version: str
    acquisition_id: Optional[UUID] = None
    doi: Optional[str] = None
    documentation_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None

class SpatialSupport(Contract):
    support_class: SupportClass
    native_resolution_m: Optional[float] = None
    extraction_method: ExtractionMethod
    field_fraction_of_cell: Optional[float] = PField(default=None, ge=0, le=1)
    cell_id: Optional[str] = None
    crs: Optional[str] = None

class TemporalSupport(Contract):
    resolution: TemporalResolution
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    aggregation: Aggregation
    time_standard: TimeStandard

class QualityFlag(Contract):
    code: str
    severity: Severity
    message: str

class QualityInfo(Contract):
    status: QualityStatus
    flags: list[QualityFlag] = []
    completeness: Optional[float] = PField(default=None, ge=0, le=1)
    missing_reason: Optional[MissingReason] = None

class MethodRef(Contract):
    method_id: str
    name: str
    version: str
    description: str
    reference_url: Optional[str] = None

class TimeSeriesPoint(Contract):
    t: str                        # ISO date or datetime
    value: Optional[float]
    quality_status: QualityStatus
    missing_reason: Optional[MissingReason] = None

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
    reference: Optional[TimeSeriesReference] = None

class GeoJSONMultiPolygon(Contract):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[list[float]]]]
```

---

## 4. Envelope, errors, jobs

### 4.1 TypeScript

```ts
export interface ResponseMeta {
  request_id: string;
  generated_at: ISODateTime;
  api_version: string;                 // "v1"
  contract_version: string;            // "1.0.0-phase0"
  data_mode: DataMode;
  warnings: QualityFlag[];
}
export interface ApiResponse<T> { data: T; meta: ResponseMeta; }

export type ApiErrorCode =
  | "NOT_FOUND" | "VALIDATION_ERROR" | "OUTSIDE_AOI" | "GEOMETRY_INVALID" | "FIELD_TOO_LARGE"
  | "NOT_EDITABLE" | "UPSTREAM_UNAVAILABLE" | "RATE_LIMITED" | "NOT_IMPLEMENTED" | "INTERNAL";
export interface ApiErrorResponse {
  error: { code: ApiErrorCode; message: string; details: Record<string, unknown> | null; request_id: string; retryable: boolean; };
}

export type JobStatus = "queued" | "running" | "succeeded" | "partial" | "failed";
export interface ProcessingJob {
  job_id: UUID;
  field_id: UUID;
  status: JobStatus;
  steps: { dataset_id: DatasetId; status: JobStatus; missing_reason: MissingReason | null; message: string | null }[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
```

### 4.2 Pydantic

```python
T = TypeVar("T")

class ResponseMeta(Contract):
    request_id: str
    generated_at: datetime
    api_version: str = "v1"
    contract_version: str = "1.0.0-phase0"
    data_mode: DataMode
    warnings: list[QualityFlag] = []

class ApiResponse(Contract, Generic[T]):
    data: T
    meta: ResponseMeta

ApiErrorCode = Literal["NOT_FOUND", "VALIDATION_ERROR", "OUTSIDE_AOI", "GEOMETRY_INVALID",
                       "FIELD_TOO_LARGE", "NOT_EDITABLE", "UPSTREAM_UNAVAILABLE", "RATE_LIMITED",
                       "NOT_IMPLEMENTED", "INTERNAL"]

class ApiErrorBody(Contract):
    code: ApiErrorCode
    message: str
    details: Optional[dict] = None
    request_id: str
    retryable: bool

class ApiErrorResponse(Contract):
    error: ApiErrorBody

JobStatus = Literal["queued", "running", "succeeded", "partial", "failed"]

class JobStep(Contract):
    dataset_id: DatasetId
    status: JobStatus
    missing_reason: Optional[MissingReason] = None
    message: Optional[str] = None

class ProcessingJob(Contract):
    job_id: UUID
    field_id: UUID
    status: JobStatus
    steps: list[JobStep]
    created_at: datetime
    updated_at: datetime
```

**HTTP mapping:**

| HTTP status | Error codes |
|---|---|
| 404 | `NOT_FOUND` |
| 422 | `VALIDATION_ERROR`, `GEOMETRY_INVALID`, `OUTSIDE_AOI`, `FIELD_TOO_LARGE` |
| 409 | `NOT_EDITABLE` |
| 503 | `UPSTREAM_UNAVAILABLE` (`retryable: true`) |
| 429 | `RATE_LIMITED` |
| 501 | `NOT_IMPLEMENTED` |
| 500 | `INTERNAL` |

---

## 5. Entity contracts

### 5.1 Farm

```ts
export interface Farm {
  farm_id: UUID;
  name: string;
  aoi: { aoi_id: "ks_reno" | "ks_finney"; label: string; county_fips: string[]; state: "KS" }; // AOIs fixed for MVP (PHASE_0_DECISIONS D2, T20)
  field_count: number;
  total_area: Quantity;                  // unit "ha"
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export interface FarmOverview {
  farm: Farm;
  fields: FieldSummary[];
  coverage_summary: { dataset_id: DatasetId; fields_available: number; fields_total: number }[];
  alerts: QualityFlag[];                 // e.g. "3 fields have no clear HLS scene in July"
  regional_context: EnvironmentalIndicator[];  // AOI-level, support "R"
}
```

```python
class AOI(Contract):
    aoi_id: Literal["ks_reno", "ks_finney"]
    label: str
    county_fips: list[str]
    state: Literal["KS"]

class Farm(Contract):
    farm_id: UUID
    name: str
    aoi: AOI
    field_count: int
    total_area: Quantity
    created_at: datetime
    updated_at: datetime

class CoverageCount(Contract):
    dataset_id: DatasetId
    fields_available: int
    fields_total: int

class FarmOverview(Contract):
    farm: Farm
    fields: list["FieldSummary"]
    coverage_summary: list[CoverageCount]
    alerts: list[QualityFlag]
    regional_context: list["EnvironmentalIndicator"]
```

### 5.2 Field and FieldSummary

```ts
export type FieldSource = "csb" | "user" | "synthetic";
export type FieldProcessingStatus = "ready" | "processing" | "partial" | "failed";

export interface Field {
  field_id: UUID;
  farm_id: UUID;
  name: string;
  geometry: GeoJSONMultiPolygon;
  centroid: [number, number];            // [lon, lat] EPSG:4326
  area: Quantity;                        // "ha", computed in EPSG:5070
  state_fips: string;
  county_fips: string;
  source: FieldSource;
  source_ref: SourceRef | null;          // CSB product/version, null for user fields
  csb_id: string | null;
  editable: boolean;                     // true only for source === "user"
  processing_status: FieldProcessingStatus;
  latest_job_id: UUID | null;
  created_at: ISODateTime;
}

export interface FieldSummary {
  field_id: UUID;
  name: string;
  centroid: [number, number];
  geometry: GeoJSONMultiPolygon;         // simplified for map display
  area: Quantity;
  source: FieldSource;
  processing_status: FieldProcessingStatus;
  latest_crop: { year: number; crop_code: CropCode | null; crop_name: string | null } | null;
  resilience_band: ScoreBand;            // "unknown" until computed
  coverage_completeness: number | null;  // 0–1, from DataCoverage
}

export interface CreateFieldRequest { name: string; geometry: GeoJSONMultiPolygon; } // must lie within farm AOI; ≤ 260 ha (FIELD_TOO_LARGE)
export interface CreateFieldResponse { field: Field; job: ProcessingJob; }            // HTTP 202
```

```python
FieldSource = Literal["csb", "user", "synthetic"]
FieldProcessingStatus = Literal["ready", "processing", "partial", "failed"]

class Field(Contract):
    field_id: UUID
    farm_id: UUID
    name: str
    geometry: GeoJSONMultiPolygon
    centroid: tuple[float, float]
    area: Quantity
    state_fips: str
    county_fips: str
    source: FieldSource
    source_ref: Optional[SourceRef] = None
    csb_id: Optional[str] = None
    editable: bool
    processing_status: FieldProcessingStatus
    latest_job_id: Optional[UUID] = None
    created_at: datetime

class LatestCrop(Contract):
    year: int
    crop_code: Optional[CropCode] = None
    crop_name: Optional[str] = None

class FieldSummary(Contract):
    field_id: UUID
    name: str
    centroid: tuple[float, float]
    geometry: GeoJSONMultiPolygon
    area: Quantity
    source: FieldSource
    processing_status: FieldProcessingStatus
    latest_crop: Optional[LatestCrop] = None
    resilience_band: ScoreBand
    coverage_completeness: Optional[float] = PField(default=None, ge=0, le=1)

class CreateFieldRequest(Contract):
    name: str = PField(min_length=1, max_length=80)
    geometry: GeoJSONMultiPolygon

class CreateFieldResponse(Contract):
    field: Field
    job: ProcessingJob
```

### 5.3 EnvironmentalIndicator

```ts
export interface EnvironmentalIndicator {
  indicator_id: string;                  // stable: `${field_id}:${key}:${period_start}`
  key: IndicatorKey;
  label: string;
  category: IndicatorCategory;
  value: Quantity;
  nature: DataNature;
  spatial: SpatialSupport;
  temporal: TemporalSupport;
  quality: QualityInfo;
  sources: SourceRef[];
  method: MethodRef;
  input_ids: string[];                   // indicator_ids / series_ids used (lineage)
  reference_value: Quantity | null;      // e.g. 1991–2020 normal, same unit
}
```

```python
class EnvironmentalIndicator(Contract):
    indicator_id: str
    key: IndicatorKey
    label: str
    category: IndicatorCategory
    value: Quantity
    nature: DataNature
    spatial: SpatialSupport
    temporal: TemporalSupport
    quality: QualityInfo
    sources: list[SourceRef]
    method: MethodRef
    input_ids: list[str] = []
    reference_value: Optional[Quantity] = None
```

### 5.4 ClimateProfile

```ts
export interface ClimateProfile {
  field_id: UUID;
  season: { label: string; start: ISODate; end: ISODate; crop_code: CropCode | null };  // window from crop KB, or calendar year if unknown
  authoritative_source: { precipitation: DatasetId; temperature: DatasetId };            // POWER until PRISM is integrated (T8)
  indicators: EnvironmentalIndicator[];   // climate + water + soil_moisture categories
  series: TimeSeries[];                   // precipitation (P1D/P1M), tmax/tmin, gdd_cumulative, sm_rootzone (SMAP, R), et0
  quality: QualityInfo;
}
```

```python
class Season(Contract):
    label: str
    start: date
    end: date
    crop_code: Optional[CropCode] = None

class AuthoritativeClimateSource(Contract):
    precipitation: DatasetId
    temperature: DatasetId

class ClimateProfile(Contract):
    field_id: UUID
    season: Season
    authoritative_source: AuthoritativeClimateSource
    indicators: list[EnvironmentalIndicator]
    series: list[TimeSeries]
    quality: QualityInfo
```

### 5.5 SoilProfile

```ts
export interface SoilLayer {
  top_cm: number;
  bottom_cm: number;
  sand_pct: Quantity; silt_pct: Quantity; clay_pct: Quantity;   // uncertainty kind "range" from SSURGO _l/_h
  texture_class: string | null;                                  // USDA class from aggregated sand/silt/clay
  ph_h2o: Quantity;
  om_pct: Quantity;
  awc: Quantity;                                                 // "cm_cm-1"
}
export interface SoilMapUnitShare {
  mukey: string;
  muname: string;
  area_fraction: number;                                         // 0–1 of field area
  major_components: { cokey: string; compname: string; comppct_r: number | null }[];
}
export interface SoilProfile {
  field_id: UUID;
  layers: SoilLayer[];                                           // fixed intervals: 0–30, 30–100, 100–150 cm
  aws_0_100: Quantity;                                           // "cm"
  aws_0_150: Quantity;                                           // "cm"
  drainage_class: { value: string | null; weight_share: number | null; missing_reason: MissingReason | null };
  hydrologic_group: { value: string | null; weight_share: number | null; missing_reason: MissingReason | null };
  slope_pct_ssurgo: Quantity;
  map_units: SoilMapUnitShare[];
  survey: { areasymbol: string; saverest: ISODate | null }[];
  method: MethodRef;                                             // "ssurgo_area_comppct_weighting" v1 (DATA_ARCHITECTURE §5.3.1)
  null_weight_fraction: number | null;
  spatial: SpatialSupport;                                       // F, vector_intersection
  sources: SourceRef[];
  quality: QualityInfo;
}
```

```python
class SoilLayer(Contract):
    top_cm: float
    bottom_cm: float
    sand_pct: Quantity
    silt_pct: Quantity
    clay_pct: Quantity
    texture_class: Optional[str] = None
    ph_h2o: Quantity
    om_pct: Quantity
    awc: Quantity

class SoilComponentRef(Contract):
    cokey: str
    compname: str
    comppct_r: Optional[float] = None

class SoilMapUnitShare(Contract):
    mukey: str
    muname: str
    area_fraction: float = PField(ge=0, le=1)
    major_components: list[SoilComponentRef]

class ClassValue(Contract):
    value: Optional[str] = None
    weight_share: Optional[float] = PField(default=None, ge=0, le=1)
    missing_reason: Optional[MissingReason] = None

class SurveyRef(Contract):
    areasymbol: str
    saverest: Optional[date] = None

class SoilProfile(Contract):
    field_id: UUID
    layers: list[SoilLayer]
    aws_0_100: Quantity
    aws_0_150: Quantity
    drainage_class: ClassValue
    hydrologic_group: ClassValue
    slope_pct_ssurgo: Quantity
    map_units: list[SoilMapUnitShare]
    survey: list[SurveyRef]
    method: MethodRef
    null_weight_fraction: Optional[float] = None
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo
```

### 5.6 TerrainProfile

TerrainProfile is not on the requested entity list. It is added because terrain is a P0 dataset and a resilience component.

```ts
export interface TerrainProfile {
  field_id: UUID;
  elevation_mean: Quantity; elevation_min: Quantity; elevation_max: Quantity;   // "m", EGM96
  slope_mean_pct: Quantity; slope_p90_pct: Quantity;
  method: MethodRef;                     // Horn slope in EPSG:5070
  spatial: SpatialSupport;
  sources: SourceRef[];
  quality: QualityInfo;
}
```

```python
class TerrainProfile(Contract):
    field_id: UUID
    elevation_mean: Quantity
    elevation_min: Quantity
    elevation_max: Quantity
    slope_mean_pct: Quantity
    slope_p90_pct: Quantity
    method: MethodRef
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo
```

### 5.7 VegetationProfile

```ts
export type VegetationIndex = "NDVI" | "EVI" | "NDMI" | "SAVI" | "MSAVI" | "NDWI" | "NBR" | "NBR2" | "TVI";
export interface VegetationScene {
  granule_id: string;
  product: "HLSL30_VI" | "HLSS30_VI" | "HLSL30" | "HLSS30" | "synthetic";
  acquired_at: ISODateTime;
  median: number | null; p10: number | null; p90: number | null;
  valid_pixels: number; total_pixels: number;
  clear_fraction: number;                    // 0–1
  accepted: boolean;                         // clear_fraction ≥ 0.70
  mask_counts: { cloud: number; cloud_adjacent: number; cloud_shadow: number; snow_ice: number; water: number };
  missing_reason: MissingReason | null;
}
export interface VegetationProfile {
  field_id: UUID;
  year: number;
  index: VegetationIndex;
  scenes: VegetationScene[];
  series: TimeSeries;                        // accepted scene medians (irregular)
  phenology: {
    peak_value: Quantity; peak_date: ISODate | null;
    greenup_date: ISODate | null; senescence_date: ISODate | null;
    method: MethodRef; gap_filled: boolean;
    missing_reason: MissingReason | null;    // INSUFFICIENT_COVERAGE if < 6 accepted scenes
  };
  spatial: SpatialSupport;                   // F, zonal_polygon_inward_buffer, 30 m
  sources: SourceRef[];
  quality: QualityInfo;
}
```

```python
VegetationIndex = Literal["NDVI", "EVI", "NDMI", "SAVI", "MSAVI", "NDWI", "NBR", "NBR2", "TVI"]

class MaskCounts(Contract):
    cloud: int
    cloud_adjacent: int
    cloud_shadow: int
    snow_ice: int
    water: int

class VegetationScene(Contract):
    granule_id: str
    product: Literal["HLSL30_VI", "HLSS30_VI", "HLSL30", "HLSS30", "synthetic"]
    acquired_at: datetime
    median: Optional[float] = None
    p10: Optional[float] = None
    p90: Optional[float] = None
    valid_pixels: int
    total_pixels: int
    clear_fraction: float = PField(ge=0, le=1)
    accepted: bool
    mask_counts: MaskCounts
    missing_reason: Optional[MissingReason] = None

class Phenology(Contract):
    peak_value: Quantity
    peak_date: Optional[date] = None
    greenup_date: Optional[date] = None
    senescence_date: Optional[date] = None
    method: MethodRef
    gap_filled: bool
    missing_reason: Optional[MissingReason] = None

class VegetationProfile(Contract):
    field_id: UUID
    year: int
    index: VegetationIndex
    scenes: list[VegetationScene]
    series: TimeSeries
    phenology: Phenology
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo
```

### 5.8 CropHistory

```ts
export interface CropYear {
  year: number;
  majority: { crop_code: CropCode | null; crop_name: string | null };
  purity: number | null;                     // majority area fraction, 0–1
  histogram: { crop_code: CropCode; crop_name: string; area_fraction: number }[];
  low_purity: boolean;                       // purity < 0.6
  class_accuracy: Uncertainty | null;        // kind "classification_accuracy", from NASS state metadata
  csb_crop_code: CropCode | null;            // CSB CDL{year} attribute, 2018–2025 only
  agrees_with_csb: boolean | null;
  native_resolution_m: number | null;        // 30 (2006–2009 to be confirmed at ingest)
  missing_reason: MissingReason | null;
  source: SourceRef;
}
export interface CropHistory {
  field_id: UUID;
  period: { start_year: number; end_year: number };   // KS: 2006–2025
  years: CropYear[];
  metrics: EnvironmentalIndicator[];                  // distinct_crops, max_monoculture_run, rotation_shannon
  spatial: SpatialSupport;
  quality: QualityInfo;
}
```

```python
class CropRef(Contract):
    crop_code: Optional[CropCode] = None
    crop_name: Optional[str] = None

class CropShare(Contract):
    crop_code: CropCode
    crop_name: str
    area_fraction: float = PField(ge=0, le=1)

class CropYear(Contract):
    year: int
    majority: CropRef
    purity: Optional[float] = PField(default=None, ge=0, le=1)
    histogram: list[CropShare]
    low_purity: bool
    class_accuracy: Optional[Uncertainty] = None
    csb_crop_code: Optional[CropCode] = None
    agrees_with_csb: Optional[bool] = None
    native_resolution_m: Optional[float] = None
    missing_reason: Optional[MissingReason] = None
    source: SourceRef

class YearPeriod(Contract):
    start_year: int
    end_year: int

class CropHistory(Contract):
    field_id: UUID
    period: YearPeriod
    years: list[CropYear]
    metrics: list[EnvironmentalIndicator]
    spatial: SpatialSupport
    quality: QualityInfo
```

### 5.9 DataCoverage

```ts
export type CoverageStatus = "available" | "partial" | "missing" | "pending" | "not_applicable" | "not_integrated";
export interface DatasetCoverage {
  dataset_id: DatasetId;
  label: string;
  priority: "P0" | "P1" | "P2";
  status: CoverageStatus;                    // "not_integrated" = planned (P1/P2) but not built yet
  support_class: SupportClass;
  native_resolution_m: number | null;
  temporal_coverage: { start: ISODate | null; end: ISODate | null };
  product_version: string | null;
  last_updated: ISODateTime | null;
  missing_reason: MissingReason | null;
  note: string | null;
}
export interface DataCoverage {
  field_id: UUID;
  datasets: DatasetCoverage[];
  completeness: number;                      // share of P0 datasets with status available|partial
}
```

```python
CoverageStatus = Literal["available", "partial", "missing", "pending", "not_applicable", "not_integrated"]

class TemporalRange(Contract):
    start: Optional[date] = None
    end: Optional[date] = None

class DatasetCoverage(Contract):
    dataset_id: DatasetId
    label: str
    priority: Literal["P0", "P1", "P2"]
    status: CoverageStatus
    support_class: SupportClass
    native_resolution_m: Optional[float] = None
    temporal_coverage: TemporalRange
    product_version: Optional[str] = None
    last_updated: Optional[datetime] = None
    missing_reason: Optional[MissingReason] = None
    note: Optional[str] = None

class DataCoverage(Contract):
    field_id: UUID
    datasets: list[DatasetCoverage]
    completeness: float = PField(ge=0, le=1)
```

### 5.10 ResilienceProfile

Methodology: DATA_ARCHITECTURE §5.10.

```ts
export type ResilienceComponentKey =
  | "soil_water_buffer" | "terrain_erosion_risk" | "vegetation_stability"
  | "climate_exposure" | "rotation_diversity";
export interface ResilienceComponent {
  key: ResilienceComponentKey;
  label: string;
  score: Quantity;                           // unit "score_0_100"; null + reason if inputs missing
  band: ScoreBand;
  support_class: SupportClass;               // weakest support among inputs
  confidence: Confidence;
  input_indicator_ids: string[];
  explanation: string;                       // plain-language driver statement, generated from rules
  rule_ref: MethodRef;                       // breakpoint table id + version
}
export interface ResilienceProfile {
  profile_id: UUID;
  field_id: UUID;
  as_of: ISODate;
  model_version: string;                     // "soilstice-resilience-<semver>"
  status: "computed" | "insufficient_data" | "pending";
  composite: { score: Quantity; band: ScoreBand; confidence: Confidence; components_used: number; components_total: 5 };
  components: ResilienceComponent[];
  limitations: QualityFlag[];
  disclaimers: string[];
}
```

```python
ResilienceComponentKey = Literal["soil_water_buffer", "terrain_erosion_risk", "vegetation_stability",
                                 "climate_exposure", "rotation_diversity"]

class ResilienceComponent(Contract):
    key: ResilienceComponentKey
    label: str
    score: Quantity
    band: ScoreBand
    support_class: SupportClass
    confidence: Confidence
    input_indicator_ids: list[str]
    explanation: str
    rule_ref: MethodRef

class ResilienceComposite(Contract):
    score: Quantity
    band: ScoreBand
    confidence: Confidence
    components_used: int = PField(ge=0, le=5)
    components_total: Literal[5] = 5

class ResilienceProfile(Contract):
    profile_id: UUID
    field_id: UUID
    as_of: date
    model_version: str
    status: Literal["computed", "insufficient_data", "pending"]
    composite: ResilienceComposite
    components: list[ResilienceComponent]
    limitations: list[QualityFlag]
    disclaimers: list[str]
```

### 5.11 Crop catalog entry (for selectors)

The Rotation Lab needs this. It is a read-only view of the crop knowledge base (Phase 5).

```ts
export interface CropOption { crop_code: CropCode; name: string; family: string; is_double_crop: boolean; kb_version: string; }
```

```python
class CropOption(Contract):
    crop_code: CropCode
    name: str
    family: str
    is_double_crop: bool
    kb_version: str
```

### 5.12 RotationScenario

```ts
export type FitBand = "suitable" | "marginal" | "unsuitable" | "unknown";
export interface ScenarioYear { year: number; crop_code: CropCode; crop_name: string; }
export interface ScenarioEvaluation {
  engine_version: string;
  kb_version: string;
  overall: FitBand;
  dimensions: { key: "agronomic_fit" | "rotation_benefit" | "water_risk" | "diversity"; band: FitBand; explanation: string }[];
  year_findings: { year: number; band: FitBand; messages: QualityFlag[]; evidence_ids: UUID[] }[];
  warnings: QualityFlag[];
  evaluated_at: ISODateTime;
}
export interface RotationScenario {
  scenario_id: UUID;
  field_id: UUID;
  name: string;
  start_year: number;
  sequence: ScenarioYear[];                  // 2–8 years
  evaluation: ScenarioEvaluation | null;     // null until evaluated
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export interface UpsertScenarioRequest { name: string; start_year: number; sequence: { year: number; crop_code: CropCode }[]; }
```

```python
FitBand = Literal["suitable", "marginal", "unsuitable", "unknown"]

class ScenarioYear(Contract):
    year: int
    crop_code: CropCode
    crop_name: str

class EvaluationDimension(Contract):
    key: Literal["agronomic_fit", "rotation_benefit", "water_risk", "diversity"]
    band: FitBand
    explanation: str

class YearFinding(Contract):
    year: int
    band: FitBand
    messages: list[QualityFlag]
    evidence_ids: list[UUID]

class ScenarioEvaluation(Contract):
    engine_version: str
    kb_version: str
    overall: FitBand
    dimensions: list[EvaluationDimension]
    year_findings: list[YearFinding]
    warnings: list[QualityFlag]
    evaluated_at: datetime

class RotationScenario(Contract):
    scenario_id: UUID
    field_id: UUID
    name: str
    start_year: int
    sequence: list[ScenarioYear] = PField(min_length=2, max_length=8)
    evaluation: Optional[ScenarioEvaluation] = None
    created_at: datetime
    updated_at: datetime

class ScenarioYearInput(Contract):
    year: int
    crop_code: CropCode

class UpsertScenarioRequest(Contract):
    name: str = PField(min_length=1, max_length=80)
    start_year: int
    sequence: list[ScenarioYearInput] = PField(min_length=2, max_length=8)
```

### 5.13 RotationRecommendation

```ts
export interface FactorAssessment {
  factor: "ph" | "drainage" | "water_holding" | "gdd" | "slope" | "rotation_history" | "regional_climate";
  band: FitBand;
  observed: Quantity | null;
  requirement: string;                       // human-readable rule, e.g. "optimal pH range per KB entry"
  support_class: SupportClass;
  evidence_ids: UUID[];
}
export interface RecommendationCandidate {
  rank: number;
  crop_code: CropCode;
  crop_name: string;
  overall: FitBand;                          // limiting-factor result (worst factor)
  confidence: Confidence;
  factors: FactorAssessment[];
  rotation_effects: QualityFlag[];           // e.g. "breaks 3-year sorghum run"
  reasons: string[];                         // short plain-language bullets
}
export interface RotationRecommendation {
  recommendation_id: UUID;
  field_id: UUID;
  target_season: { label: string; start: ISODate; end: ISODate };
  engine_version: string;
  kb_version: string;
  status: "computed" | "insufficient_data" | "pending";
  candidates: RecommendationCandidate[];
  excluded: { crop_code: CropCode; crop_name: string; reason: string }[];
  disclaimers: string[];                     // must include "not a yield or profit forecast"
  generated_at: ISODateTime;
}
```

```python
class FactorAssessment(Contract):
    factor: Literal["ph", "drainage", "water_holding", "gdd", "slope", "rotation_history", "regional_climate"]
    band: FitBand
    observed: Optional[Quantity] = None
    requirement: str
    support_class: SupportClass
    evidence_ids: list[UUID] = []

class RecommendationCandidate(Contract):
    rank: int = PField(ge=1)
    crop_code: CropCode
    crop_name: str
    overall: FitBand
    confidence: Confidence
    factors: list[FactorAssessment]
    rotation_effects: list[QualityFlag]
    reasons: list[str]

class TargetSeason(Contract):
    label: str
    start: date
    end: date

class ExcludedCrop(Contract):
    crop_code: CropCode
    crop_name: str
    reason: str

class RotationRecommendation(Contract):
    recommendation_id: UUID
    field_id: UUID
    target_season: TargetSeason
    engine_version: str
    kb_version: str
    status: Literal["computed", "insufficient_data", "pending"]
    candidates: list[RecommendationCandidate]
    excluded: list[ExcludedCrop]
    disclaimers: list[str]
    generated_at: datetime
```

### 5.14 EvidenceItem

```ts
export type EvidenceKind = "dataset" | "indicator" | "method" | "kb_rule" | "literature";
export type VerificationStatus = "LIVE" | "CMR" | "DOC" | "UNVERIFIED" | "SYNTHETIC";
export interface EvidenceItem {
  evidence_id: UUID;
  kind: EvidenceKind;
  title: string;
  summary: string;
  field_id: UUID | null;                     // null = global (dataset/method/KB rule)
  dataset_id: DatasetId | null;
  product_version: string | null;
  citation: string | null;                   // formatted reference
  url: string | null;
  doi: string | null;
  accessed_at: ISODate | null;
  verification_status: VerificationStatus;
  spatial: SpatialSupport | null;
  temporal: TemporalSupport | null;
  related_ids: string[];                     // indicator_ids, component keys, candidate crop codes
}
```

```python
EvidenceKind = Literal["dataset", "indicator", "method", "kb_rule", "literature"]
VerificationStatus = Literal["LIVE", "CMR", "DOC", "UNVERIFIED", "SYNTHETIC"]

class EvidenceItem(Contract):
    evidence_id: UUID
    kind: EvidenceKind
    title: str
    summary: str
    field_id: Optional[UUID] = None
    dataset_id: Optional[DatasetId] = None
    product_version: Optional[str] = None
    citation: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    accessed_at: Optional[date] = None
    verification_status: VerificationStatus
    spatial: Optional[SpatialSupport] = None
    temporal: Optional[TemporalSupport] = None
    related_ids: list[str] = []
```

### 5.15 FieldProfile (aggregate)

```ts
export interface FieldProfile {
  field: Field;
  coverage: DataCoverage;
  soil: SoilProfile | null;                  // null => see coverage for reason
  terrain: TerrainProfile | null;
  crop_history: CropHistory | null;
  climate_summary: EnvironmentalIndicator[]; // key season indicators only; full detail via /climate
  vegetation_summary: EnvironmentalIndicator[];
  resilience: ResilienceProfile | null;
}
```

```python
class FieldProfile(Contract):
    field: Field
    coverage: DataCoverage
    soil: Optional[SoilProfile] = None
    terrain: Optional[TerrainProfile] = None
    crop_history: Optional[CropHistory] = None
    climate_summary: list[EnvironmentalIndicator] = []
    vegetation_summary: list[EnvironmentalIndicator] = []
    resilience: Optional[ResilienceProfile] = None
```

### 5.16 DatasetDescriptor (registry)

```ts
export interface DatasetDescriptor {
  dataset_id: DatasetId; title: string; publisher: string; product: string; product_version: string;
  priority: "P0" | "P1" | "P2"; support_class: SupportClass; native_resolution_m: number | null;
  temporal_resolution: TemporalResolution; temporal_coverage: { start: ISODate | null; end: ISODate | null };
  documentation_url: string; doi: string | null; verification_status: VerificationStatus; last_verified: ISODate;
  integration_status: "integrated" | "planned";
}
```

```python
class DatasetDescriptor(Contract):
    dataset_id: DatasetId
    title: str
    publisher: str
    product: str
    product_version: str
    priority: Literal["P0", "P1", "P2"]
    support_class: SupportClass
    native_resolution_m: Optional[float] = None
    temporal_resolution: TemporalResolution
    temporal_coverage: TemporalRange
    documentation_url: str
    doi: Optional[str] = None
    verification_status: VerificationStatus
    last_verified: date
    integration_status: Literal["integrated", "planned"]
```

---

## 6. Endpoints (`/api/v1`)

All `GET`s are idempotent and cacheable. No authentication in the MVP (PHASE_0_DECISIONS D8). The "Mockable in Phase 1" column states whether the Phase 1 mock service can return a contract-valid synthetic response.

| # | Method & path | Response `data` | Query / body | Errors | Mockable in Phase 1 |
|---|---|---|---|---|---|
| E1 | `GET /health` | `{status: "ok", contract_version}` | — | — | Yes |
| E2 | `GET /datasets` | `DatasetDescriptor[]` | — | — | Yes (static, from Source Register) |
| E3 | `GET /farms` | `Farm[]` | — | — | Yes |
| E4 | `GET /farms/{farm_id}` | `Farm` | — | 404 | Yes |
| E5 | `PATCH /farms/{farm_id}` | `Farm` | `{name}` | 404, 422 | Yes (in-memory) |
| E6 | `GET /farms/{farm_id}/overview` | `FarmOverview` | `season_year?` | 404 | Yes |
| E7 | `GET /farms/{farm_id}/fields` | `FieldSummary[]` | `source?`, `status?` | 404 | Yes |
| E8 | `POST /farms/{farm_id}/fields` | `CreateFieldResponse` (202) | `CreateFieldRequest` | 422 `GEOMETRY_INVALID`/`OUTSIDE_AOI`/`FIELD_TOO_LARGE` | Partly (validation only; job simulated) |
| E9 | `GET /fields/{field_id}` | `Field` | — | 404 | Yes |
| E10 | `DELETE /fields/{field_id}` | `{deleted: true}` | — | 404, 409 `NOT_EDITABLE` | Yes (in-memory) |
| E11 | `GET /fields/{field_id}/profile` | `FieldProfile` | `season_year?` | 404 | Yes |
| E12 | `GET /fields/{field_id}/coverage` | `DataCoverage` | — | 404 | Yes |
| E13 | `GET /fields/{field_id}/climate` | `ClimateProfile` | `season_year`, `crop_code?` | 404 | Yes |
| E14 | `GET /fields/{field_id}/soil` | `SoilProfile` | — | 404 | Yes |
| E15 | `GET /fields/{field_id}/terrain` | `TerrainProfile` | — | 404 | Yes |
| E16 | `GET /fields/{field_id}/vegetation` | `VegetationProfile` | `year`, `index=NDVI` | 404 | Yes |
| E17 | `GET /fields/{field_id}/crop-history` | `CropHistory` | — | 404 | Yes |
| E18 | `GET /fields/{field_id}/indicators` | `EnvironmentalIndicator[]` | `category?`, `season_year?` | 404 | Yes |
| E19 | `GET /fields/{field_id}/resilience` | `ResilienceProfile` | — | 404 | Yes (placeholder scores, synthetic) |
| E20 | `GET /crops` | `CropOption[]` | — | — | Yes |
| E21 | `GET /fields/{field_id}/recommendations` | `RotationRecommendation` | `season_year` | 404 | Yes (synthetic, labelled) |
| E22 | `GET /fields/{field_id}/scenarios` | `RotationScenario[]` | — | 404 | Yes |
| E23 | `POST /fields/{field_id}/scenarios` | `RotationScenario` (201, evaluated) | `UpsertScenarioRequest` | 422 (unknown crop code, bad years) | Yes (canned evaluation) |
| E24 | `PUT /scenarios/{scenario_id}` | `RotationScenario` (re-evaluated) | `UpsertScenarioRequest` | 404, 422 | Yes |
| E25 | `DELETE /scenarios/{scenario_id}` | `{deleted: true}` | — | 404 | Yes |
| E26 | `GET /fields/{field_id}/evidence` | `EvidenceItem[]` | `kind?`, `related_id?` | 404 | Yes |
| E27 | `GET /jobs/{job_id}` | `ProcessingJob` | — | 404 | Yes (simulated progression) |

Scenario evaluation runs synchronously inside E23/E24. This is rules-only, with no external calls, so it should take well under a second. There is no separate evaluate endpoint.

---

## 7. Frontend service interfaces (TypeScript)

These are the only things UI components import. Implementations: `mock/*` (Phase 1) and `http/*` (Phase 6), selected by `NEXT_PUBLIC_DATA_MODE=mock|api` in one factory module.

```ts
export interface FarmService {
  listFarms(): Promise<ApiResponse<Farm[]>>;
  getFarm(farmId: UUID): Promise<ApiResponse<Farm>>;
  updateFarm(farmId: UUID, patch: { name: string }): Promise<ApiResponse<Farm>>;
  getOverview(farmId: UUID, seasonYear?: number): Promise<ApiResponse<FarmOverview>>;
}
export interface FieldService {
  listFields(farmId: UUID, filter?: { source?: FieldSource; status?: FieldProcessingStatus }): Promise<ApiResponse<FieldSummary[]>>;
  getField(fieldId: UUID): Promise<ApiResponse<Field>>;
  createField(farmId: UUID, req: CreateFieldRequest): Promise<ApiResponse<CreateFieldResponse>>;
  deleteField(fieldId: UUID): Promise<ApiResponse<{ deleted: true }>>;
  getProfile(fieldId: UUID, seasonYear?: number): Promise<ApiResponse<FieldProfile>>;
  getCoverage(fieldId: UUID): Promise<ApiResponse<DataCoverage>>;
  getJob(jobId: UUID): Promise<ApiResponse<ProcessingJob>>;
}
export interface EnvironmentService {
  getClimate(fieldId: UUID, seasonYear: number, cropCode?: CropCode): Promise<ApiResponse<ClimateProfile>>;
  getSoil(fieldId: UUID): Promise<ApiResponse<SoilProfile>>;
  getTerrain(fieldId: UUID): Promise<ApiResponse<TerrainProfile>>;
  getVegetation(fieldId: UUID, year: number, index?: VegetationIndex): Promise<ApiResponse<VegetationProfile>>;
  getIndicators(fieldId: UUID, opts?: { category?: IndicatorCategory; seasonYear?: number }): Promise<ApiResponse<EnvironmentalIndicator[]>>;
}
export interface RotationService {
  listCrops(): Promise<ApiResponse<CropOption[]>>;
  getCropHistory(fieldId: UUID): Promise<ApiResponse<CropHistory>>;
  getRecommendation(fieldId: UUID, seasonYear: number): Promise<ApiResponse<RotationRecommendation>>;
  listScenarios(fieldId: UUID): Promise<ApiResponse<RotationScenario[]>>;
  createScenario(fieldId: UUID, req: UpsertScenarioRequest): Promise<ApiResponse<RotationScenario>>;
  updateScenario(scenarioId: UUID, req: UpsertScenarioRequest): Promise<ApiResponse<RotationScenario>>;
  deleteScenario(scenarioId: UUID): Promise<ApiResponse<{ deleted: true }>>;
}
export interface ResilienceService { getResilience(fieldId: UUID): Promise<ApiResponse<ResilienceProfile>>; }
export interface EvidenceService {
  listDatasets(): Promise<ApiResponse<DatasetDescriptor[]>>;
  listEvidence(fieldId: UUID, opts?: { kind?: EvidenceKind; relatedId?: string }): Promise<ApiResponse<EvidenceItem[]>>;
}
```

**Error contract for services:**
- Implementations **throw** a typed `ApiError` (`code`, `message`, `retryable`, `requestId`), built from `ApiErrorResponse`.
- Mock services must be able to simulate each `ApiErrorCode` and latency, so error and loading states can be built in Phase 1. A query string such as `?mock_error=UPSTREAM_UNAVAILABLE` or `?mock_latency=1500` is read only in mock mode.

---

## 8. Mock data rules (Phase 1)

1. Fixtures are **generated deterministically** by a seeded generator, not hand-typed tables of plausible numbers.
2. Every `SourceRef` uses `dataset_id: "synthetic"` and `product_version: "synthetic-0"`.
3. Every response has `meta.data_mode: "synthetic"`.
4. Field names are "Demo Field A…", with `source: "synthetic"`.
5. Geometry is synthetic: simple rectangles inside the Reno County bbox. It is **not** copied from CSB, so real geometry is never paired with fake attributes.
6. Fixtures must cover every state:
   - a fully covered field
   - a partially covered field (cloud-masked vegetation, `INSUFFICIENT_COVERAGE`)
   - a `processing` user field
   - a `failed` field
   - a field with `resilience.status = "insufficient_data"`
7. Fixtures must validate against the TS types (compile-time) and, from Phase 2, against the Pydantic models (a contract test runs fixtures through `Model.model_validate`).

---

## 9. Change log

| Version | Date | Change |
|---|---|---|
| 1.0.0-phase0 | 2026-11-14 | Initial frozen contract |
