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
    QualityFlag,
    QualityInfo,
    Quantity,
    SoilMoistureProfile,
    SoilProfile,
    SpatialSupport,
    TemporalSupport,
    TerrainProfile,
    VegetationProfile,
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
    specs = [
        ("slope_mean_pct", "Mean slope", "percent", "slope_mean_pct"),
        ("slope_p90_pct", "90th percentile slope", "percent", "slope_p90_pct"),
        ("elevation_mean", "Mean elevation", "m", "elevation_mean"),
    ]
    out = []
    for key, label, unit, attr in specs:
        if terrain is None:
            spatial_desc = SPATIAL.get("meteomatics", SPATIAL.get("nasa_srtm_gl1"))
            out.append(_ind(field_id, key, label, "terrain", Quantity(value=None, unit=unit, missing_reason=reason),
                            "derived", spatial_desc, QualityInfo(status="missing", missing_reason=reason),
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


def vegetation_indicators(field_id: UUID, year: int, veg: VegetationProfile | None = None):
    hls = SpatialSupport(support_class="F", native_resolution_m=30, extraction_method="zonal_polygon_inward_buffer")

    if veg and veg.phenology and veg.phenology.peak_value.value is not None:
        peak_q = veg.phenology.peak_value
        peak_doy = (
            Quantity(value=float(veg.phenology.peak_date.timetuple().tm_yday), unit="day")
            if veg.phenology.peak_date else Quantity(value=None, unit="day", missing_reason="INSUFFICIENT_COVERAGE")
        )
        return [
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:ndvi_peak:{year}-01-01", key="ndvi_peak", label="Peak NDVI",
                category="vegetation", value=peak_q, nature="derived", spatial=veg.spatial,
                temporal=TemporalSupport(resolution="season", period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                                         aggregation="max", time_standard="UTC"),
                quality=veg.quality, sources=veg.sources, method=veg.phenology.method, input_ids=[],
            ),
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:ndvi_peak_doy:{year}-01-01", key="ndvi_peak_doy", label="Peak NDVI day of year",
                category="vegetation", value=peak_doy, nature="derived", spatial=veg.spatial,
                temporal=TemporalSupport(resolution="season", period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                                         aggregation="max", time_standard="UTC"),
                quality=veg.quality, sources=veg.sources, method=veg.phenology.method, input_ids=[],
            ),
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:ndvi_peak_cv:{year}-01-01", key="ndvi_peak_cv", label="Peak NDVI interannual CV",
                category="vegetation", value=Quantity(value=None, unit="unitless", missing_reason="NO_DATA_SOURCE"),
                nature="derived", spatial=hls,
                temporal=TemporalSupport(resolution="season", period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                                         aggregation="max", time_standard="UTC"),
                quality=QualityInfo(status="missing", missing_reason="NO_DATA_SOURCE",
                                    flags=[QualityFlag(code="REGIONAL_NDVI_NOT_HLS", severity="info",
                                                       message="Canopy temporal stability model withheld: requires 30 m HLS; coarse regional NDVI cannot be substituted.")]),
                sources=[], method=METHOD_NO_SOURCE, input_ids=[],
            ),
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:ndmi_peak_season:{year}-01-01", key="ndmi_peak_season", label="Season peak NDMI",
                category="vegetation", value=Quantity(value=None, unit="unitless", missing_reason="NO_DATA_SOURCE"),
                nature="derived", spatial=hls,
                temporal=TemporalSupport(resolution="season", period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                                         aggregation="max", time_standard="UTC"),
                quality=QualityInfo(status="missing", missing_reason="NO_DATA_SOURCE"), sources=[],
                method=METHOD_NO_SOURCE, input_ids=[],
            ),
        ]

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
                   soil_moisture: SoilMoistureProfile | None = None,
                   vegetation: VegetationProfile | None = None,
                   soil_reason: str = NOT_PROCESSED, terrain_reason: str = NOT_PROCESSED) -> list[EnvironmentalIndicator]:
    out: list[EnvironmentalIndicator] = []

    # Process climate indicators, integrating soil moisture if provided
    if climate:
        clim_inds = list(climate.indicators)
        if soil_moisture:
            # Replace placeholder soil moisture indicators with actual Meteomatics values
            new_clim_inds: list[EnvironmentalIndicator] = []
            for ind in clim_inds:
                if ind.key == "sm_rootzone_mean_season":
                    new_clim_inds.append(
                        ind.model_copy(update={
                            "value": soil_moisture.rootzone_sm_composite,
                            "sources": soil_moisture.sources,
                            "spatial": soil_moisture.spatial,
                            "quality": soil_moisture.quality,
                        })
                    )
                elif ind.key == "sm_rootzone_dry_days":
                    new_clim_inds.append(
                        ind.model_copy(update={
                            "value": soil_moisture.rootzone_dry_days,
                            "sources": soil_moisture.sources,
                            "spatial": soil_moisture.spatial,
                            "quality": soil_moisture.quality,
                        })
                    )
                else:
                    new_clim_inds.append(ind)

            # Add depth-specific indicators
            for depth_m, key, lbl in [
                (soil_moisture.surface_sm, "sm_surface_mean_season", "Surface soil moisture (-5 cm mean)"),
                (soil_moisture.shallow_sm, "sm_shallow_mean_season", "Shallow soil moisture (-15 cm mean)"),
                (soil_moisture.middepth_sm, "sm_middepth_mean_season", "Mid-depth soil moisture (-50 cm mean)"),
                (soil_moisture.deep_sm, "sm_deep_mean_season", "Deep soil moisture (-150 cm mean)"),
            ]:
                new_clim_inds.append(
                    EnvironmentalIndicator(
                        indicator_id=f"{field_id}:{key}:{year}",
                        key=key,
                        label=lbl,
                        category="soil_moisture",
                        value=depth_m.mean,
                        nature="model",
                        spatial=soil_moisture.spatial,
                        temporal=TemporalSupport(
                            resolution="season",
                            period_start=f"{year}-01-01",
                            period_end=f"{year}-12-31",
                            aggregation="mean",
                            time_standard="UTC",
                        ),
                        quality=soil_moisture.quality,
                        sources=soil_moisture.sources,
                        method=METHOD_READ,
                        input_ids=[f"soil_moisture:{field_id}"],
                    )
                )
            out += new_clim_inds
        else:
            out += clim_inds

    out += soil_indicators(field_id, soil, soil_reason)
    out += terrain_indicators(field_id, terrain, terrain_reason)
    out += vegetation_indicators(field_id, year, veg=vegetation)
    out += crop_history.metrics if crop_history else []
    return [
        i for i in out
        if i.key not in {"et_actual_season", "sm_rootzone_percentile"}
        and "actual et" not in i.label.lower()
        and "openet" not in i.label.lower()
    ]
