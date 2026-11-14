"""Climate processing: POWER daily values -> contract TimeSeries + season aggregates (DATA_ARCHITECTURE §5.5).

Only plain temporal aggregations defined in §5.5 are computed (sum / mean with the >= 90 %-days completeness
rule). Every other climate/water/soil-moisture indicator is emitted with value null and an explicit reason:
NOT_COMPUTED (methodology pending Phase 4) or NO_DATA_SOURCE (dataset not integrated).
All POWER-derived values are support class R (regional context), never field observations.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.catalog import POWER_MET_RES_M, POWER_SOLAR_RES_M, source_ref
from app.contracts import (
    AuthoritativeClimateSource,
    ClimateProfile,
    EnvironmentalIndicator,
    MethodRef,
    QualityFlag,
    QualityInfo,
    Quantity,
    Season,
    SourceRef,
    SpatialSupport,
    TemporalSupport,
    TimeSeries,
    TimeSeriesPoint,
)
from app.providers.power import PARAMETERS, SOLAR_PARAMETERS, PowerDaily

COMPLETENESS_MIN = 0.9  # §5.5: >= 90 % of days present, else null + completeness

METHOD_SUM = MethodRef(
    method_id="season_daily_sum", name="Season sum of daily values", version="1",
    description="Sum of daily values over the season window; null with INSUFFICIENT_COVERAGE unless at least 90% "
                "of days are present (DATA_ARCHITECTURE §5.5). Missing days are not filled.",
)
METHOD_MEAN = MethodRef(
    method_id="season_daily_mean", name="Season mean of daily values", version="1",
    description="Arithmetic mean of daily values over the season window; null with INSUFFICIENT_COVERAGE unless at "
                "least 90% of days are present (DATA_ARCHITECTURE §5.5).",
)
METHOD_PENDING = MethodRef(
    method_id="pending_phase4", name="Not computed: methodology pending", version="0",
    description="This indicator requires methodology or thresholds that are set and cited in Phase 4 "
                "(e.g. crop-specific GDD base, FAO-56 ET0, 1991-2020 normals). No value is produced until then.",
)
METHOD_NO_SOURCE = MethodRef(
    method_id="no_data_source", name="Not available: dataset not integrated", version="0",
    description="The dataset that provides this indicator is planned but not yet integrated.",
)

# key -> (label, category, unit, kind) ; kind: ("sum"|"mean", POWER param) | ("pending",) | ("no_source", dataset)
CLIMATE_INDICATORS: list[tuple[str, str, str, str, tuple]] = [
    ("precip_total_season", "Season precipitation total", "climate", "mm", ("sum", "PRECTOTCORR")),
    ("solar_total_season", "Season solar radiation total", "climate", "MJ_m-2", ("sum", "ALLSKY_SFC_SW_DWN")),
    ("rh_mean_season", "Season mean relative humidity", "climate", "percent", ("mean", "RH2M")),
    ("precip_anomaly_pct", "Precipitation anomaly vs 1991–2020", "climate", "percent", ("pending",)),
    ("gdd_season", "Growing degree days", "climate", "degC_day", ("pending",)),
    ("heat_stress_days", "Heat-stress days", "climate", "day", ("pending",)),
    ("frost_free_days", "Frost-free days", "climate", "day", ("pending",)),
    ("et0_total_season", "Reference ET₀ total", "water", "mm", ("pending",)),
    ("water_balance_season", "Water balance (P − ET₀)", "water", "mm", ("pending",)),
    ("et_actual_season", "Actual ET (OpenET)", "water", "mm", ("no_source", "openet")),
    ("sm_rootzone_mean_season", "Root-zone soil moisture (season mean)", "soil_moisture", "m3_m-3",
     ("no_source", "nasa_smap_spl4smgp")),
    ("sm_rootzone_percentile", "Root-zone soil moisture percentile", "soil_moisture", "percentile",
     ("no_source", "nasa_smap_spl4smgp")),
    ("sm_rootzone_dry_days", "Root-zone dry days", "soil_moisture", "day", ("no_source", "nasa_smap_spl4smgp")),
]

# Physical plausibility checks (INTEGRATION_GUIDE §1.2 W-2). Violations are FLAGGED, never dropped or altered.
RANGE_CHECKS = {"RH2M": (0.0, 100.0), "PRECTOTCORR": (0.0, None), "ALLSKY_SFC_SW_DWN": (0.0, None)}


def season_for_year(year: int, crop_code: int | None) -> Season:
    return Season(
        label=f"Calendar year {year} (crop season window pending crop knowledge base)",
        start=date(year, 1, 1), end=date(year, 12, 31), crop_code=crop_code,
    )


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def power_spatial(param: str) -> SpatialSupport:
    return SpatialSupport(
        support_class="R",
        native_resolution_m=POWER_SOLAR_RES_M if param in SOLAR_PARAMETERS else POWER_MET_RES_M,
        extraction_method="api_point_query", crs="EPSG:4326",
    )


def power_source(daily: PowerDaily) -> SourceRef:
    srcs = ", ".join(daily.sources) if daily.sources else "unspecified"
    return source_ref(
        "nasa_power_daily_ag", product=f"POWER Daily API (community=AG; sources: {srcs})",
        version=daily.api_version, acquisition_id=daily.acquisition.acquisition_id,
        retrieved_at=daily.acquisition.retrieved_at,
    )


def _missing(unit: str, reason: str) -> Quantity:
    return Quantity(value=None, unit=unit, missing_reason=reason)


def build_climate_profile(
    field_id: UUID, year: int, crop_code: int | None, daily: PowerDaily | None, *,
    failure_reason: str | None = None, failure_message: str | None = None,
    smap_rootzone: dict[date, float | None] | None = None,
    smap_surface: dict[date, float | None] | None = None,
) -> ClimateProfile:
    season = season_for_year(year, crop_code)
    days = _days(season.start, season.end)
    flags: list[QualityFlag] = []
    if crop_code is not None:
        flags.append(QualityFlag(code="SEASON_WINDOW_UNAVAILABLE", severity="info",
                                 message="Crop-specific season windows come from the crop knowledge base, which is not "
                                         "yet available; the calendar year is used."))
    flags.append(QualityFlag(code="REGIONAL_CONTEXT", severity="info",
                             message="NASA POWER values describe a ~50 km (meteorology) / ~110 km (solar) grid cell "
                                     "queried at the field centroid. They are regional context, not field measurements."))
    flags.append(QualityFlag(code="SMAP_REGIONAL_CONTEXT", severity="info",
                             message="SMAP L4 soil moisture is an assimilated ~9 km EASE-Grid estimate. "
                                     "Regional context, not a field measurement."))

    series: list[TimeSeries] = []
    per_param_values: dict[str, list[float | None]] = {}
    period_ids: dict[str, str] = {}
    if daily is not None:
        src = power_source(daily)
        for param, (variable, label, exp_unit, unit) in PARAMETERS.items():
            got_unit = daily.units.get(param)
            if param not in daily.values:
                flags.append(QualityFlag(code="PARAMETER_MISSING", severity="warning",
                                         message=f"POWER did not return {param}."))
                continue
            if got_unit is not None and got_unit != exp_unit:
                flags.append(QualityFlag(code="UNIT_MISMATCH", severity="critical",
                                         message=f"POWER returned {param} in '{got_unit}', expected '{exp_unit}'. "
                                                 "Series withheld rather than converted on an assumption."))
                continue
            vals = daily.values[param]
            lo_hi = RANGE_CHECKS.get(param)
            points: list[TimeSeriesPoint] = []
            out_vals: list[float | None] = []
            n_flagged = 0
            for d in days:
                if d > daily.end:
                    points.append(TimeSeriesPoint(t=d.isoformat(), value=None, quality_status="missing",
                                                  missing_reason="NOT_YET_PUBLISHED"))
                    out_vals.append(None)
                elif d not in vals:
                    points.append(TimeSeriesPoint(t=d.isoformat(), value=None, quality_status="missing",
                                                  missing_reason="UPSTREAM_ERROR"))
                    out_vals.append(None)
                elif vals[d] is None:
                    points.append(TimeSeriesPoint(t=d.isoformat(), value=None, quality_status="missing",
                                                  missing_reason="FILL_VALUE"))
                    out_vals.append(None)
                else:
                    v = vals[d]
                    bad = lo_hi is not None and ((lo_hi[0] is not None and v < lo_hi[0]) or
                                                 (lo_hi[1] is not None and v > lo_hi[1]))
                    if param == "T2M" and not bad:
                        tmin, tmax = daily.values.get("T2M_MIN", {}).get(d), daily.values.get("T2M_MAX", {}).get(d)
                        bad = tmin is not None and tmax is not None and not (tmin - 0.05 <= v <= tmax + 0.05)
                    n_flagged += bad
                    points.append(TimeSeriesPoint(t=d.isoformat(), value=v,
                                                  quality_status="flagged" if bad else "valid"))
                    out_vals.append(v)
            if n_flagged:
                flags.append(QualityFlag(code="PLAUSIBILITY_CHECK", severity="warning",
                                         message=f"{n_flagged} day(s) of {param} failed a range check and are "
                                                 "flagged (values kept as delivered)."))
            sid = f"{field_id}:power:{variable}:{year}"
            period_ids[param] = sid
            per_param_values[param] = out_vals
            series.append(TimeSeries(
                series_id=sid, variable=variable, label=label, unit=unit, nature="model",
                spatial=power_spatial(param),
                temporal=TemporalSupport(resolution="P1D", period_start=season.start, period_end=season.end,
                                         aggregation="none", time_standard="LST"),
                sources=[src], points=points, reference=None,
            ))

    # SMAP L4 Root-zone soil moisture series (SPL4SMGP v008) when retrieved
    if smap_rootzone is not None:
        smap_src = SourceRef(
            dataset_id="nasa_smap_spl4smgp",
            product="SPL4SMGP",
            product_version="008",
            doi="10.5067/0P5494498G02",
            documentation_url="https://nsidc.org/data/spl4smgp",
        )
        smap_spatial = SpatialSupport(
            support_class="R",
            native_resolution_m=9000.0,
            extraction_method="containing_cell",
            crs="EPSG:6933",
        )
        smap_points: list[TimeSeriesPoint] = []
        smap_start = date(2015, 3, 31)
        for d in days:
            if d in smap_rootzone:
                v = smap_rootzone[d]
                if v is not None:
                    smap_points.append(TimeSeriesPoint(t=d.isoformat(), value=v, quality_status="valid"))
                else:
                    smap_points.append(
                        TimeSeriesPoint(t=d.isoformat(), value=None, quality_status="missing", missing_reason="FILL_VALUE")
                    )
            elif d < smap_start:
                smap_points.append(
                    TimeSeriesPoint(
                        t=d.isoformat(), value=None, quality_status="missing", missing_reason="OUT_OF_TEMPORAL_RANGE"
                    )
                )
            else:
                smap_points.append(
                    TimeSeriesPoint(
                        t=d.isoformat(), value=None, quality_status="missing", missing_reason="NO_DATA_SOURCE"
                    )
                )

        series.append(TimeSeries(
            series_id=f"{field_id}:smap:sm_rootzone:{year}",
            variable="sm_rootzone",
            label="Root-zone soil moisture (0–100 cm)",
            unit="m3_m-3",
            nature="model",
            spatial=smap_spatial,
            temporal=TemporalSupport(
                resolution="P1D",
                period_start=season.start,
                period_end=season.end,
                aggregation="none",
                time_standard="UTC",
            ),
            sources=[smap_src],
            points=smap_points,
            reference=None,
        ))

    indicators: list[EnvironmentalIndicator] = []
    for key, label, category, unit, kind in CLIMATE_INDICATORS:
        ind_id = f"{field_id}:{key}:{season.start.isoformat()}"
        temporal = TemporalSupport(resolution="season", period_start=season.start, period_end=season.end,
                                   aggregation="sum" if kind[0] == "sum" else "mean" if kind[0] == "mean" else "none",
                                   time_standard="LST")
        if kind[0] in ("sum", "mean"):
            param = kind[1]
            spatial = power_spatial(param)
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "model", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_SUM if kind[0] == "sum" else METHOD_MEAN, []))
                continue
            vals = per_param_values.get(param)
            if vals is None:
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, "UPSTREAM_ERROR"), "model",
                                             spatial, temporal, QualityInfo(status="missing",
                                                                            missing_reason="UPSTREAM_ERROR"),
                                             [power_source(daily)], METHOD_SUM, []))
                continue
            present = [v for v in vals if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                value = sum(present) if kind[0] == "sum" else sum(present) / len(present)
                q = Quantity(value=round(value, 3), unit=unit)
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4))
            indicators.append(_indicator(ind_id, key, label, category, q, "model", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_SUM if kind[0] == "sum" else METHOD_MEAN,
                                         [period_ids[param]]))
        elif kind[0] == "pending":
            spatial = power_spatial("T2M")
            indicators.append(_indicator(ind_id, key, label, category, _missing(unit, "NOT_COMPUTED"), "derived",
                                         spatial, temporal, QualityInfo(status="missing", missing_reason="NOT_COMPUTED"),
                                         [], METHOD_PENDING, []))
        else:
            ds = kind[1]
            spatial = (SpatialSupport(support_class="R", native_resolution_m=9000, extraction_method="containing_cell",
                                      crs="EPSG:6933") if ds == "nasa_smap_spl4smgp" else
                       SpatialSupport(support_class="F", native_resolution_m=30, extraction_method="zonal_polygon"))
            indicators.append(_indicator(ind_id, key, label, category, _missing(unit, "NO_DATA_SOURCE"), "model",
                                         spatial, temporal, QualityInfo(status="missing",
                                                                        missing_reason="NO_DATA_SOURCE"),
                                         [], METHOD_NO_SOURCE, []))

    if daily is None:
        quality = QualityInfo(status="missing", missing_reason=failure_reason or "UPSTREAM_ERROR",
                              flags=flags + ([QualityFlag(code="POWER_UNAVAILABLE", severity="critical",
                                                          message=failure_message)] if failure_message else []))
    else:
        n_total = len(days) * max(len(series), 1)
        n_present = sum(1 for s in series for p in s.points if p.value is not None)
        completeness = n_present / n_total if series else 0.0
        status = "valid" if series and completeness == 1 and not any(f.severity != "info" for f in flags) else \
            "partial" if series else "missing"
        quality = QualityInfo(status=status, flags=flags, completeness=round(completeness, 4),
                              missing_reason=None if series else "UPSTREAM_ERROR")
    return ClimateProfile(
        field_id=field_id, season=season,
        authoritative_source=AuthoritativeClimateSource(precipitation="nasa_power_daily_ag",
                                                        temperature="nasa_power_daily_ag"),
        indicators=indicators, series=series, quality=quality,
    )


def _indicator(ind_id, key, label, category, value, nature, spatial, temporal, quality, sources, method, input_ids):
    return EnvironmentalIndicator(
        indicator_id=ind_id, key=key, label=label, category=category, value=value, nature=nature, spatial=spatial,
        temporal=temporal, quality=quality, sources=sources, method=method, input_ids=input_ids, reference_value=None,
    )
