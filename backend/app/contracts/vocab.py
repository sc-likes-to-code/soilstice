"""Controlled vocabularies — API_CONTRACTS §2 (contract v1.0.0-phase0). Mirrors src/types/contracts.ts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

CONTRACT_VERSION = "1.0.0-phase0"
API_VERSION = "v1"


class Contract(BaseModel):
    """Base for every wire model: no unknown keys (rejects `_example` payloads), immutable,
    and defaulted fields are *required* in the serialization JSON schema so that the exported
    OpenAPI matches the TypeScript interfaces exactly (fields are never omitted on the wire)."""

    model_config = ConfigDict(extra="forbid", frozen=True, json_schema_serialization_defaults_required=True)


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
    "UPSTREAM_ERROR", "NOT_YET_PUBLISHED", "NOT_COMPUTED", "OUTSIDE_AOI", "PENDING_PROCESSING",
]
DatasetId = Literal[
    "nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "usda_nass_csb",
    "nasa_hls", "nasa_hls_vi", "nasa_smap_spl4smgp", "nasa_srtm_gl1",
    "prism_daily", "openet", "usda_nass_quickstats", "nasa_smap_spl3smp_e",
    "nasa_gpm_imerg", "fao_gaez_v5", "soilstice_derived", "user_input", "synthetic",
]
ExtractionMethod = Literal[
    "zonal_polygon", "zonal_polygon_inward_buffer", "containing_cell", "api_point_query",
    "vector_intersection", "attribute_join", "not_applicable",
]
TemporalResolution = Literal["PT3H", "P1D", "P1M", "season", "P1Y", "static", "irregular"]
Aggregation = Literal["none", "mean", "sum", "median", "min", "max", "majority", "weighted_mean", "percentile", "count"]
TimeStandard = Literal["UTC", "LST", "not_applicable"]
Unit = Literal[
    "mm", "degC", "degC_day", "percent", "MJ_m-2_day-1", "MJ_m-2", "m3_m-3", "wetness_0_1",
    "cm", "cm_cm-1", "m", "degree", "pH", "ha", "day", "year", "count",
    "percentile", "unitless", "score_0_100",
]
IndicatorCategory = Literal["climate", "soil_moisture", "vegetation", "water", "soil", "terrain", "rotation"]
IndicatorKey = Literal[
    "precip_total_season", "precip_anomaly_pct", "gdd_season", "heat_stress_days", "frost_free_days",
    "solar_total_season", "rh_mean_season", "et0_total_season", "water_balance_season", "et_actual_season",
    "sm_rootzone_mean_season", "sm_rootzone_percentile", "sm_rootzone_dry_days",
    "ndvi_peak", "ndvi_peak_doy", "ndvi_peak_cv", "ndmi_peak_season",
    "aws_0_150", "ph_0_30", "om_0_30", "clay_0_30",
    "slope_mean_pct", "slope_p90_pct", "elevation_mean",
    "distinct_crops", "max_monoculture_run", "rotation_shannon",
]
CropCode = int
