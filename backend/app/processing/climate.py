"""Climate processing: POWER daily values -> contract TimeSeries + season aggregates (DATA_ARCHITECTURE §5.5).

Only plain temporal aggregations defined in §5.5 are computed (sum / mean with the >= 90 %-days completeness
rule). Every other climate/water/soil-moisture indicator is emitted with value null and an explicit reason:
NOT_COMPUTED (methodology pending Phase 4) or NO_DATA_SOURCE (dataset not integrated).
All POWER-derived values are support class R (regional context), never field observations.
"""

from __future__ import annotations

import math
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
RENO_PRECIP_NORMAL_MM = 760.5  # NOAA NCEI 1991-2020 normal (Hutchinson 10 SW, KS)

# Crop-specific thermal thresholds (T_base, T_cap) in °C (McMaster & Wilhelm 1997; Barger 1969)
CROP_GDD_THRESHOLDS: dict[int | None, tuple[float, float]] = {
    1: (10.0, 30.0),    # Corn (Maize) - Barger (1969); Gilmore & Rogers (1958)
    24: (0.0, 25.0),    # Winter Wheat - McMaster & Wilhelm (1997)
    4: (10.0, 35.0),    # Grain Sorghum - Vanderlip & Reeves (1972)
    5: (10.0, 30.0),    # Soybeans - Fehr & Caviness (1977)
    36: (5.0, 30.0),   # Alfalfa - Fick et al. (1988)
    None: (10.0, 30.0), # Fallback standard warm-season baseline
}

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
METHOD_MODIFIED_GDD = MethodRef(
    method_id="modified_gdd_mcmaster1997", name="Modified Growing Degree Days (Method 2)", version="1",
    description="Modified GDD parameterized by crop-specific base and ceiling temperatures "
                "(McMaster & Wilhelm 1997; Barger 1969). When crop identity is unspecified, standard "
                "warm-season baseline thresholds (10/30 °C) are applied over the calendar year.",
)
METHOD_PRECIP_ANOMALY = MethodRef(
    method_id="precip_anomaly_noaa_normals", name="Precipitation anomaly vs 1991–2020 normal", version="1",
    description="Percentage departure of season precipitation from NOAA NCEI 1991–2020 climate normal "
                "(760.5 mm at Hutchinson 10 SW, Reno County, KS). Note: Station rain-gauge normal serves as a "
                "regional benchmark and differs in spatial support from MERRA-2 gridded areal precipitation.",
)
METHOD_HEAT_STRESS = MethodRef(
    method_id="heat_stress_days_count", name="Heat-stress days count", version="1",
    description="Count of days where Tmax >= 35.0 degC (or 30.0 degC for winter wheat) across the analyzed "
                "calendar window. Because satellite phenology is unavailable, this metric reflects calendar-year thermal "
                "extremity rather than crop reproductive-stage-specific exposure (Schlenker & Roberts 2009).",
)
METHOD_FROST_FREE = MethodRef(
    method_id="frost_free_days_count", name="Frost-free days count (Tmin > 0 °C)", version="1",
    description="Count of individual days in the season window where daily minimum temperature Tmin > 0.0 degC. "
                "This represents total non-freezing days across the calendar year, distinct from the continuous "
                "freeze-free period between the last spring frost and first fall frost.",
)
METHOD_FAO56_ET0 = MethodRef(
    method_id="fao56_penman_monteith", name="FAO-56 Penman-Monteith Reference Evapotranspiration", version="1",
    description="Daily grass reference evapotranspiration ET0 calculated using the FAO-56 Penman-Monteith equation "
                "(Allen et al. 1998) with engineering approximations: assumed neutral wind speed u2 = 2.0 m/s "
                "(FAO-56 standard default), regional elevation (470 m), and clear-sky radiation ratio approximation "
                "for net longwave radiation.",
)
METHOD_WATER_BALANCE = MethodRef(
    method_id="climatic_water_balance", name="Climatic Water Balance (P - ET0)", version="1",
    description="Climatic water balance calculated as cumulative precipitation minus grass reference evapotranspiration "
                "(P - ET0). Measures net meteorological moisture surplus or deficit; this is NOT crop water demand, "
                "actual evapotranspiration (ETa), crop irrigation requirement, or root-zone soil water balance, "
                "which require crop coefficients (Kc), phenology, soil water storage, and effective precipitation.",
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

# key -> (label, category, unit, kind)
CLIMATE_INDICATORS: list[tuple[str, str, str, str, tuple]] = [
    ("precip_total_season", "Season precipitation total", "climate", "mm", ("sum", "PRECTOTCORR")),
    ("solar_total_season", "Season solar radiation total", "climate", "MJ_m-2", ("sum", "ALLSKY_SFC_SW_DWN")),
    ("rh_mean_season", "Season mean relative humidity", "climate", "percent", ("mean", "RH2M")),
    ("precip_anomaly_pct", "Precipitation anomaly vs 1991–2020", "climate", "percent", ("precip_anomaly",)),
    ("gdd_season", "Growing degree days", "climate", "degC_day", ("gdd",)),
    ("heat_stress_days", "Heat-stress days", "climate", "day", ("heat_stress",)),
    ("frost_free_days", "Frost-free days", "climate", "day", ("frost_free",)),
    ("et0_total_season", "Reference ET₀ total", "water", "mm", ("et0",)),
    ("water_balance_season", "Climatic water balance (P − ET₀)", "water", "mm", ("water_balance",)),
    ("et_actual_season", "Actual ET (OpenET)", "water", "mm", ("no_source", "openet")),
    ("sm_rootzone_mean_season", "Root-zone soil moisture (season mean)", "soil_moisture", "m3_m-3",
     ("no_source", "nasa_smap_spl4smgp")),
    ("sm_rootzone_percentile", "Root-zone soil moisture percentile", "soil_moisture", "percentile",
     ("no_source", "nasa_smap_spl4smgp")),
    ("sm_rootzone_dry_days", "Root-zone dry days", "soil_moisture", "day", ("no_source", "nasa_smap_spl4smgp")),
]

# Physical plausibility checks (INTEGRATION_GUIDE §1.2 W-2). Violations are FLAGGED, never dropped or altered.
RANGE_CHECKS = {"RH2M": (0.0, 100.0), "PRECTOTCORR": (0.0, None), "ALLSKY_SFC_SW_DWN": (0.0, None)}


def compute_daily_gdd(t_max: float, t_min: float, t_base: float, t_cap: float) -> float:
    """Modified Growing Degree Day (Method 2, McMaster & Wilhelm 1997; Barger 1969)."""
    t_max_star = min(max(t_max, t_base), t_cap)
    t_min_star = min(max(t_min, t_base), t_cap)
    return max(0.0, (t_max_star + t_min_star) / 2.0 - t_base)


def compute_fao56_et0_daily(
    t_mean: float, t_max: float, t_min: float, rh_mean: float, solar_mj: float,
    elevation_m: float = 470.0, u2: float = 2.0,
) -> float:
    """FAO-56 Penman-Monteith daily reference evapotranspiration ET0 (Allen et al. 1998)."""
    p_atm = 101.3 * math.pow((293.0 - 0.0065 * elevation_m) / 293.0, 5.26)
    gamma = 0.000665 * p_atm
    t = t_mean
    delta = 4098.0 * (0.6108 * math.exp(17.27 * t / (t + 237.3))) / math.pow(t + 237.3, 2)
    e0_max = 0.6108 * math.exp(17.27 * t_max / (t_max + 237.3))
    e0_min = 0.6108 * math.exp(17.27 * t_min / (t_min + 237.3))
    es = (e0_max + e0_min) / 2.0
    ea = es * (max(0.0, min(100.0, rh_mean)) / 100.0)
    rns = (1.0 - 0.23) * max(0.0, solar_mj)
    sigma = 4.903e-9
    t_k_max4 = math.pow(t_max + 273.16, 4)
    t_k_min4 = math.pow(t_min + 273.16, 4)
    cloudiness = 0.8  # typical Kansas growing-season ratio Rs / Rso ~ 0.7 - 0.9
    rnl = sigma * ((t_k_max4 + t_k_min4) / 2.0) * (0.34 - 0.14 * math.sqrt(max(0.0, ea))) * cloudiness
    rn = max(0.0, rns - rnl)
    num = 0.408 * delta * rn + gamma * (900.0 / (t + 273.0)) * u2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2)
    return max(0.0, num / den)


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

    # Derived daily climate calculations (GDD cumulative time series & ET0)
    tmax_list = per_param_values.get("T2M_MAX", [])
    tmin_list = per_param_values.get("T2M_MIN", [])
    t2m_list = per_param_values.get("T2M", [])
    precip_list = per_param_values.get("PRECTOTCORR", [])
    rh_list = per_param_values.get("RH2M", [])
    solar_list = per_param_values.get("ALLSKY_SFC_SW_DWN", [])

    daily_gdd_vals: list[float | None] = []
    gdd_points: list[TimeSeriesPoint] = []
    cum_gdd = 0.0
    tbase, tcap = CROP_GDD_THRESHOLDS.get(crop_code, CROP_GDD_THRESHOLDS[None])
    for i, d in enumerate(days):
        tmax = tmax_list[i] if i < len(tmax_list) else None
        tmin = tmin_list[i] if i < len(tmin_list) else None
        if tmax is not None and tmin is not None:
            gdd_val = compute_daily_gdd(tmax, tmin, tbase, tcap)
            daily_gdd_vals.append(gdd_val)
            cum_gdd += gdd_val
            gdd_points.append(TimeSeriesPoint(t=d.isoformat(), value=round(cum_gdd, 1), quality_status="valid"))
        else:
            daily_gdd_vals.append(None)
            gdd_points.append(TimeSeriesPoint(t=d.isoformat(), value=None, quality_status="missing",
                                              missing_reason="FILL_VALUE"))

    if daily is not None:
        series.append(TimeSeries(
            series_id=f"{field_id}:derived:gdd_cumulative:{year}",
            variable="gdd_cumulative",
            label="Cumulative growing degree days",
            unit="degC_day",
            nature="derived",
            spatial=power_spatial("T2M"),
            temporal=TemporalSupport(
                resolution="P1D", period_start=season.start, period_end=season.end,
                aggregation="none", time_standard="LST",
            ),
            sources=[power_source(daily)],
            points=gdd_points,
            reference=None,
        ))

    daily_et0_vals: list[float | None] = []
    for i in range(len(days)):
        t_mean = t2m_list[i] if i < len(t2m_list) else None
        t_max = tmax_list[i] if i < len(tmax_list) else None
        t_min = tmin_list[i] if i < len(tmin_list) else None
        rh_mean = rh_list[i] if i < len(rh_list) else None
        solar_mj = solar_list[i] if i < len(solar_list) else None
        if (t_mean is not None and t_max is not None and t_min is not None and
                rh_mean is not None and solar_mj is not None):
            daily_et0_vals.append(compute_fao56_et0_daily(t_mean, t_max, t_min, rh_mean, solar_mj))
        else:
            daily_et0_vals.append(None)

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
        elif kind[0] == "gdd":
            spatial = power_spatial("T2M")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_MODIFIED_GDD, []))
                continue
            present = [v for v in daily_gdd_vals if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                q = Quantity(value=round(sum(present), 1), unit=unit)
                gdd_flags: list[QualityFlag] = []
                if crop_code is None:
                    gdd_flags.append(QualityFlag(
                        code="GDD_DEFAULT_PARAMETERS", severity="info",
                        message="Crop identity unspecified; standard warm-season baseline thresholds (Tbase=10°C, "
                                "Tcap=30°C) applied across the full calendar year.",
                    ))
                if completeness < 1.0:
                    gdd_flags.append(QualityFlag(
                        code="MISSING_DAYS_OMITTED", severity="info",
                        message=f"GDD sum computed over {len(present)} available days ({completeness:.0%} completeness); "
                                "missing days are omitted and not filled or scaled.",
                    ))
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4),
                                      flags=gdd_flags)
            inputs = [period_ids[p] for p in ("T2M_MAX", "T2M_MIN") if p in period_ids]
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_MODIFIED_GDD, inputs))
        elif kind[0] == "precip_anomaly":
            spatial = power_spatial("PRECTOTCORR")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_PRECIP_ANOMALY, []))
                continue
            present = [v for v in precip_list if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                p_sum = sum(present)
                anom = ((p_sum - RENO_PRECIP_NORMAL_MM) / RENO_PRECIP_NORMAL_MM) * 100.0
                q = Quantity(value=round(anom, 2), unit=unit)
                anom_flags = [
                    QualityFlag(
                        code="POINT_STATION_BASELINE", severity="info",
                        message="Precipitation anomaly referenced to NOAA NCEI 1991–2020 normal for Hutchinson 10 SW, "
                                "KS (760.5 mm). Station rain-gauge normals provide a regional benchmark and differ in "
                                "spatial support from MERRA-2 gridded precipitation.",
                    )
                ]
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4),
                                      flags=anom_flags)
            inputs = [period_ids["PRECTOTCORR"]] if "PRECTOTCORR" in period_ids else []
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_PRECIP_ANOMALY, inputs))
        elif kind[0] == "heat_stress":
            spatial = power_spatial("T2M_MAX")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_HEAT_STRESS, []))
                continue
            t_crit = 30.0 if crop_code == 24 else 35.0
            present = [v for v in tmax_list if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                cnt = sum(1 for v in present if v >= t_crit)
                q = Quantity(value=float(cnt), unit=unit)
                heat_flags = [
                    QualityFlag(
                        code="PHENOLOGY_UNAVAILABLE", severity="info",
                        message="Satellite phenology stages (flowering/grain-fill) are unavailable; heat-stress days "
                                "reflect calendar window exceedances, not reproductive-stage-specific stress.",
                    )
                ]
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4),
                                      flags=heat_flags)
            inputs = [period_ids["T2M_MAX"]] if "T2M_MAX" in period_ids else []
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_HEAT_STRESS, inputs))
        elif kind[0] == "frost_free":
            spatial = power_spatial("T2M_MIN")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_FROST_FREE, []))
                continue
            present = [v for v in tmin_list if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                cnt = sum(1 for v in present if v > 0.0)
                q = Quantity(value=float(cnt), unit=unit)
                frost_flags = [
                    QualityFlag(
                        code="CALENDAR_DAYS_COUNT", severity="info",
                        message="Total count of non-freezing days across the calendar window; distinct from continuous "
                                "freeze-free growing season length between last spring frost and first fall frost.",
                    )
                ]
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4),
                                      flags=frost_flags)
            inputs = [period_ids["T2M_MIN"]] if "T2M_MIN" in period_ids else []
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_FROST_FREE, inputs))
        elif kind[0] == "et0":
            spatial = power_spatial("T2M")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_FAO56_ET0, []))
                continue
            present = [v for v in daily_et0_vals if v is not None]
            completeness = len(present) / len(days)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                sum_et0 = sum(present)
                q = Quantity(value=round(sum_et0, 1), unit=unit)
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4))
            inputs = [period_ids[p] for p in ("T2M", "T2M_MAX", "T2M_MIN", "RH2M", "ALLSKY_SFC_SW_DWN") if p in period_ids]
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_FAO56_ET0, inputs))
        elif kind[0] == "water_balance":
            spatial = power_spatial("PRECTOTCORR")
            if daily is None:
                reason = failure_reason or "UPSTREAM_ERROR"
                indicators.append(_indicator(ind_id, key, label, category, _missing(unit, reason), "derived", spatial,
                                             temporal, QualityInfo(status="missing", missing_reason=reason),
                                             [], METHOD_WATER_BALANCE, []))
                continue
            present_p = [v for v in precip_list if v is not None]
            present_et0 = [v for v in daily_et0_vals if v is not None]
            comp_p = len(present_p) / len(days)
            comp_et0 = len(present_et0) / len(days)
            completeness = min(comp_p, comp_et0)
            if completeness < COMPLETENESS_MIN:
                q = _missing(unit, "INSUFFICIENT_COVERAGE")
                quality = QualityInfo(status="missing", completeness=round(completeness, 4),
                                      missing_reason="INSUFFICIENT_COVERAGE",
                                      flags=[QualityFlag(code="BELOW_COMPLETENESS", severity="warning",
                                                         message=f"Only {completeness:.0%} of days present (90% "
                                                                 "required).")])
            else:
                wb = sum(present_p) - sum(present_et0)
                q = Quantity(value=round(wb, 1), unit=unit)
                quality = QualityInfo(status="valid" if completeness == 1 else "partial",
                                      completeness=round(completeness, 4))
            inputs = [period_ids[p] for p in ("PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "ALLSKY_SFC_SW_DWN")
                      if p in period_ids]
            indicators.append(_indicator(ind_id, key, label, category, q, "derived", spatial, temporal, quality,
                                         [power_source(daily)], METHOD_WATER_BALANCE, inputs))
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
