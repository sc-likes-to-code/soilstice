"""Contract-valid 'not available' profiles. Every quantity is null with an explicit reason (never 0)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.catalog import SPATIAL, source_ref
from app.contracts import (
    ClassValue,
    MethodRef,
    Phenology,
    QualityFlag,
    QualityInfo,
    Quantity,
    SoilLayer,
    SoilMoistureDepthMetric,
    SoilMoistureProfile,
    SoilProfile,
    SpatialSupport,
    TemporalSupport,
    TerrainProfile,
    TimeSeries,
    VegetationProfile,
)

from .soil import INTERVALS
from .soil import METHOD as SOIL_METHOD
from .terrain import METHOD as TERRAIN_METHOD


def _q(unit: str, reason: str) -> Quantity:
    return Quantity(value=None, unit=unit, missing_reason=reason)


def _quality(reason: str, message: str | None) -> QualityInfo:
    flags = [QualityFlag(code="NOT_AVAILABLE", severity="warning", message=message)] if message else []
    return QualityInfo(status="missing", flags=flags, completeness=0.0, missing_reason=reason)


def missing_soil(field_id: UUID, reason: str, message: str | None = None) -> SoilProfile:
    cv = ClassValue(value=None, weight_share=None, missing_reason=reason)
    return SoilProfile(
        field_id=field_id,
        layers=[SoilLayer(top_cm=t, bottom_cm=b, sand_pct=_q("percent", reason), silt_pct=_q("percent", reason),
                          clay_pct=_q("percent", reason), texture_class=None, ph_h2o=_q("pH", reason),
                          om_pct=_q("percent", reason), awc=_q("cm_cm-1", reason)) for t, b in INTERVALS],
        aws_0_100=_q("cm", reason), aws_0_150=_q("cm", reason), drainage_class=cv, hydrologic_group=cv,
        slope_pct_ssurgo=_q("percent", reason), map_units=[], survey=[], method=SOIL_METHOD,
        null_weight_fraction=None, spatial=SPATIAL["usda_nrcs_ssurgo_sda"], sources=[], quality=_quality(reason, message),
    )


def missing_terrain(field_id: UUID, reason: str, message: str | None = None) -> TerrainProfile:
    return TerrainProfile(
        field_id=field_id, elevation_mean=_q("m", reason), elevation_min=_q("m", reason), elevation_max=_q("m", reason),
        slope_mean_pct=_q("percent", reason), slope_p90_pct=_q("percent", reason), method=TERRAIN_METHOD,
        spatial=SPATIAL["nasa_srtm_gl1"], sources=[], quality=_quality(reason, message),
    )


def missing_vegetation(field_id: UUID, year: int, index: str) -> VegetationProfile:
    reason = "NO_DATA_SOURCE"
    spatial = SpatialSupport(support_class="F", native_resolution_m=30, extraction_method="zonal_polygon_inward_buffer")
    method = MethodRef(method_id="no_data_source", name="Not available: HLS-VI not integrated", version="0",
                       description="HLS / HLS-VI vegetation indices are planned (P0) but not yet integrated.")
    return VegetationProfile(
        field_id=field_id, year=year, index=index, scenes=[],
        series=TimeSeries(series_id=f"{field_id}:hls:{index.lower()}:{year}", variable=index.lower(),
                          label=f"{index} (HLS, not integrated)", unit="unitless", nature="derived", spatial=spatial,
                          temporal=TemporalSupport(resolution="irregular", period_start=date(year, 1, 1),
                                                   period_end=date(year, 12, 31), aggregation="median",
                                                   time_standard="UTC"),
                          sources=[source_ref("nasa_hls_vi")], points=[], reference=None),
        phenology=Phenology(peak_value=_q("unitless", reason), method=method, gap_filled=False, missing_reason=reason),
        spatial=spatial, sources=[], quality=_quality(reason, "HLS-VI is not yet integrated; no scenes are available."),
    )


def missing_soil_moisture(field_id: UUID, year: int, reason: str, message: str | None = None) -> SoilMoistureProfile:
    def _d_metric(label: str, cm: float, param: str) -> SoilMoistureDepthMetric:
        return SoilMoistureDepthMetric(
            depth_label=label,
            depth_cm=cm,
            parameter=param,
            mean=_q("m3_m-3", reason),
            variability_cv=None,
            min=_q("m3_m-3", reason),
            max=_q("m3_m-3", reason),
            valid_observations=0,
            missing_observations=0,
        )

    return SoilMoistureProfile(
        field_id=field_id,
        season_year=year,
        as_of=date.today(),
        surface_sm=_d_metric("surface", -5.0, "volumetric_soil_water_-5cm:m3m3"),
        shallow_sm=_d_metric("shallow", -15.0, "volumetric_soil_water_-15cm:m3m3"),
        middepth_sm=_d_metric("middepth", -50.0, "volumetric_soil_water_-50cm:m3m3"),
        deep_sm=_d_metric("deep", -150.0, "volumetric_soil_water_-150cm:m3m3"),
        rootzone_sm_composite=_q("m3_m-3", reason),
        rootzone_dry_days=_q("day", reason),
        series=[],
        metrics=[],
        spatial=SpatialSupport(
            support_class="R",
            native_resolution_m=None,
            extraction_method="api_point_query",
            crs="EPSG:4326",
        ),
        sources=[source_ref("meteomatics", product="Meteomatics Mix Model", version="v3.0")],
        quality=_quality(reason, message),
    )
