"""Environmental analytical engine — indicator assembly (layer 3).

Reads ONLY stored profiles (PHASE_0 D7: "P4 reads only stored observations, never upstream APIs").
Soil and terrain indicators are direct reads of profile values (no new methodology). Climate indicators come from
ClimateProfile (see processing/climate.py). Vegetation indicators are NO_DATA_SOURCE until HLS is integrated.
"""

from __future__ import annotations

from uuid import UUID

from app.catalog import SPATIAL
from app.contracts import (
    ClimateProfile,
    CropHistory,
    EnvironmentalIndicator,
    MethodRef,
    QualityInfo,
    Quantity,
    SoilProfile,
    SpatialSupport,
    TemporalSupport,
    TerrainProfile,
)

METHOD_READ = MethodRef(
    method_id="profile_value_read", name="Read from field profile", version="1",
    description="Indicator value copied unchanged from the stored field profile (no additional computation).",
)
METHOD_NO_SOURCE = MethodRef(
    method_id="no_data_source", name="Not available: dataset not integrated", version="0",
    description="The dataset that provides this indicator (HLS-VI) is planned but not yet integrated.",
)

STATIC = TemporalSupport(resolution="static", aggregation="none", time_standard="not_applicable")
NOT_PROCESSED = "PENDING_PROCESSING"


def _ind(field_id, key, label, category, value, nature, spatial, quality, sources, method, inputs, period="static"):
    return EnvironmentalIndicator(
        indicator_id=f"{field_id}:{key}:{period}", key=key, label=label, category=category, value=value,
        nature=nature, spatial=spatial, temporal=STATIC, quality=quality, sources=sources, method=method,
        input_ids=inputs,
    )


def soil_indicators(field_id: UUID, soil: SoilProfile | None, reason: str = NOT_PROCESSED):
    specs = [("aws_0_150", "Available water storage 0–150 cm", "cm"), ("ph_0_30", "Soil pH 0–30 cm", "pH"),
             ("om_0_30", "Organic matter 0–30 cm", "percent"), ("clay_0_30", "Clay 0–30 cm", "percent")]
    out = []
    for key, label, unit in specs:
        if soil is None:
            out.append(_ind(field_id, key, label, "soil", Quantity(value=None, unit=unit, missing_reason=reason),
                            "observation", SPATIAL["usda_nrcs_ssurgo_sda"],
                            QualityInfo(status="missing", missing_reason=reason), [], METHOD_READ, []))
            continue
        top = next((layer for layer in soil.layers if layer.top_cm == 0), None)
        q = {"aws_0_150": soil.aws_0_150, "ph_0_30": top.ph_h2o if top else None,
             "om_0_30": top.om_pct if top else None, "clay_0_30": top.clay_pct if top else None}[key]
        q = q or Quantity(value=None, unit=unit, missing_reason="INSUFFICIENT_COVERAGE")
        out.append(_ind(field_id, key, label, "soil", q, "observation", soil.spatial,
                        QualityInfo(status="missing" if q.value is None else soil.quality.status,
                                    flags=soil.quality.flags, completeness=soil.quality.completeness,
                                    missing_reason=q.missing_reason),
                        soil.sources, METHOD_READ, [f"soil:{field_id}"]))
    return out


def terrain_indicators(field_id: UUID, terrain: TerrainProfile | None, reason: str = NOT_PROCESSED):
    specs = [("slope_mean_pct", "Mean slope", "percent", "slope_mean_pct"),
             ("slope_p90_pct", "90th percentile slope", "percent", "slope_p90_pct"),
             ("elevation_mean", "Mean elevation", "m", "elevation_mean")]
    out = []
    for key, label, unit, attr in specs:
        if terrain is None:
            out.append(_ind(field_id, key, label, "terrain", Quantity(value=None, unit=unit, missing_reason=reason),
                            "derived", SPATIAL["nasa_srtm_gl1"], QualityInfo(status="missing", missing_reason=reason),
                            [], METHOD_READ, []))
            continue
        q: Quantity = getattr(terrain, attr)
        out.append(_ind(field_id, key, label, "terrain", q, "observation" if key == "elevation_mean" else "derived",
                        terrain.spatial, QualityInfo(status="missing" if q.value is None else terrain.quality.status,
                                                     flags=terrain.quality.flags,
                                                     completeness=terrain.quality.completeness,
                                                     missing_reason=q.missing_reason),
                        terrain.sources, METHOD_READ, [f"terrain:{field_id}"]))
    return out


def vegetation_indicators(field_id: UUID, year: int):
    hls = SpatialSupport(support_class="F", native_resolution_m=30, extraction_method="zonal_polygon_inward_buffer")
    specs = [("ndvi_peak", "Peak NDVI", "unitless"), ("ndvi_peak_doy", "Peak NDVI day of year", "day"),
             ("ndvi_peak_cv", "Peak NDVI interannual CV", "unitless"), ("ndmi_peak_season", "Season peak NDMI",
                                                                         "unitless")]
    return [
        EnvironmentalIndicator(
            indicator_id=f"{field_id}:{key}:{year}-01-01", key=key, label=label, category="vegetation",
            value=Quantity(value=None, unit=unit, missing_reason="NO_DATA_SOURCE"), nature="derived", spatial=hls,
            temporal=TemporalSupport(resolution="season", period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                                     aggregation="max", time_standard="UTC"),
            quality=QualityInfo(status="missing", missing_reason="NO_DATA_SOURCE"), sources=[],
            method=METHOD_NO_SOURCE, input_ids=[],
        )
        for key, label, unit in specs
    ]


def all_indicators(field_id: UUID, *, soil: SoilProfile | None, terrain: TerrainProfile | None,
                   climate: ClimateProfile | None, crop_history: CropHistory | None, year: int,
                   soil_reason: str = NOT_PROCESSED, terrain_reason: str = NOT_PROCESSED) -> list[EnvironmentalIndicator]:
    out: list[EnvironmentalIndicator] = []
    out += climate.indicators if climate else []
    out += soil_indicators(field_id, soil, soil_reason)
    out += terrain_indicators(field_id, terrain, terrain_reason)
    out += vegetation_indicators(field_id, year)
    out += crop_history.metrics if crop_history else []
    return out
