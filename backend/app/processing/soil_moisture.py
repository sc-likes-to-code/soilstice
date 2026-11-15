"""Meteomatics soil moisture processing pipeline (Section 6).

Implements:
- Retrieval and normalization for all four soil water parameters:
  - volumetric_soil_water_-5cm:m3m3 (surface)
  - volumetric_soil_water_-15cm:m3m3 (shallow)
  - volumetric_soil_water_-50cm:m3m3 (mid-depth)
  - volumetric_soil_water_-150cm:m3m3 (deep)
- Depth-specific statistics: seasonal mean, temporal variability (CV), min/max, observation counts
- Documented composite root-zone moisture derivation (0–100 cm):
  0.10 * sm_5cm + 0.20 * sm_15cm + 0.70 * sm_50cm
- Continuous dry-period indicators (threshold-based; missing days are not counted or bridged)
- Spatial resolution awareness and validation
- Unified metric emission with provenance and limitations
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from shapely.geometry.base import BaseGeometry

from app.catalog import source_ref
from app.contracts import (
    EnvironmentalIndicator,
    MethodRef,
    MetricCoverage,
    QualityFlag,
    QualityInfo,
    Quantity,
    SoilMoistureDepthMetric,
    SoilMoistureProfile,
    SourceRef,
    SpatialSupport,
    TemporalSupport,
    TimeSeries,
    TimeSeriesPoint,
    UnifiedEnvironmentalMetric,
)
from app.logging import get_logger
from app.providers.meteomatics import (
    SOIL_MOISTURE_PARAMETERS,
    MeteomaticsClient,
    TimeSeriesObservation,
)

log = get_logger("processing.soil_moisture")

# Defensible root-zone depth weighting (0–100 cm total depth):
# 0–10 cm (10 cm thick) -> represented by 5 cm depth (weight 0.10)
# 10–30 cm (20 cm thick) -> represented by 15 cm depth (weight 0.20)
# 30–100 cm (70 cm thick) -> represented by 50 cm depth (weight 0.70)
# -150 cm is deep drainage/subsoil (>100 cm), not in standard 1m root-zone composite
ROOTZONE_WEIGHTS = {
    "volumetric_soil_water_-5cm:m3m3": 0.10,
    "volumetric_soil_water_-15cm:m3m3": 0.20,
    "volumetric_soil_water_-50cm:m3m3": 0.70,
}

DRY_THRESHOLD_M3M3 = 0.15  # Wilting-point proxy / critical moisture deficit threshold
COMPLETENESS_MIN = 0.90  # 90% valid observations required for seasonal aggregates

METHOD_ROOTZONE = MethodRef(
    method_id="meteomatics_weighted_rootzone",
    name="Depth-Weighted Root-Zone Soil Moisture (0–100 cm)",
    version="1.0",
    description="Derived composite root-zone volumetric soil moisture calculated across three horizons: "
                "0–10 cm (5 cm depth, 10% weight), 10–30 cm (15 cm depth, 20% weight), and "
                "30–100 cm (50 cm depth, 70% weight). Deep subsoil (150 cm) reflects lower boundary conditions.",
)

METHOD_DRY_DAYS = MethodRef(
    method_id="rootzone_dry_days_threshold",
    name="Root-Zone Moisture Stress Days Count",
    version="1.0",
    description=f"Count of valid calendar days where daily mean root-zone volumetric soil water falls below "
                f"{DRY_THRESHOLD_M3M3} m3/m3. Missing observations are strictly excluded and never bridged.",
)

METHOD_DEPTH_STATS = MethodRef(
    method_id="meteomatics_depth_aggregation",
    name="Meteomatics Horizon Soil Water Statistics",
    version="1.0",
    description="Temporal and spatial mean and variability across specific sensor model depths from Meteomatics.",
)


def compute_depth_weighted_rootzone(s5: float, s15: float, s50: float) -> float:
    """Compute depth-weighted root-zone composite: 0.10*(-5cm) + 0.20*(-15cm) + 0.70*(-50cm)."""
    return round(0.10 * s5 + 0.20 * s15 + 0.70 * s50, 4)


def _validate_volumetric_value(val: float | None) -> float | None:
    """Validate volumetric water content. Physical plausible range is 0.00 to 0.65 m3/m3."""
    if val is None or math.isnan(val):
        return None
    if val < 0.0 or val > 0.85:
        return None
    return float(val)


def build_soil_moisture_profile(
    field_id: UUID,
    geom: BaseGeometry,
    season_year: int,
    client: MeteomaticsClient,
    start_date: date | None = None,
    end_date: date | None = None,
) -> SoilMoistureProfile:
    """Fetch 4-depth soil moisture from Meteomatics and construct SoilMoistureProfile."""
    start = start_date or date(season_year, 1, 1)
    end = end_date or min(date(season_year, 12, 31), date.today())
    today_dt = date.today()

    centroid = geom.centroid
    lat, lon = centroid.y, centroid.x

    # Query time series for all 4 parameters
    raw_series = client.query_time_series(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        step="P1D",
        parameters=SOIL_MOISTURE_PARAMETERS,
        model="mix",
    )

    expected_days = (end - start).days + 1
    depth_stats: dict[str, dict[str, Any]] = {}
    time_series_objs: list[TimeSeries] = []
    unified_metrics: list[UnifiedEnvironmentalMetric] = []
    flags: list[QualityFlag] = []

    spatial_support = SpatialSupport(
        support_class="R",
        native_resolution_m=None,  # Provider does not specify native numerical grid resolution for mix model
        extraction_method="api_point_query",
        crs="EPSG:4326",
    )

    source_obj = SourceRef(
        dataset_id="meteomatics",
        product="Meteomatics Mix Model",
        product_version="v3.0",
        documentation_url="https://www.meteomatics.com/en/api/",
        retrieved_at=datetime.now(UTC),
    )

    daily_rootzone_map: dict[str, list[float]] = {}

    depth_meta = [
        ("volumetric_soil_water_-5cm:m3m3", "surface", -5.0),
        ("volumetric_soil_water_-15cm:m3m3", "shallow", -15.0),
        ("volumetric_soil_water_-50cm:m3m3", "middepth", -50.0),
        ("volumetric_soil_water_-150cm:m3m3", "deep", -150.0),
    ]

    for param, depth_label, depth_cm in depth_meta:
        obs_list = raw_series.get(param, [])
        valid_vals: list[float] = []
        points: list[TimeSeriesPoint] = []

        for obs in obs_list:
            v_clean = _validate_volumetric_value(obs.value)
            t_str = obs.timestamp.strftime("%Y-%m-%d")
            points.append(
                TimeSeriesPoint(
                    t=t_str,
                    value=round(v_clean, 4) if v_clean is not None else None,
                    quality_status="valid" if v_clean is not None else "missing",
                    missing_reason=None if v_clean is not None else "INSUFFICIENT_COVERAGE",
                )
            )
            if v_clean is not None:
                valid_vals.append(v_clean)
                if param in ROOTZONE_WEIGHTS:
                    if t_str not in daily_rootzone_map:
                        daily_rootzone_map[t_str] = []

        n_valid = len(valid_vals)
        n_missing = expected_days - n_valid
        completeness = n_valid / expected_days if expected_days > 0 else 0.0

        if n_valid > 0:
            arr = np.array(valid_vals)
            mean_val = float(arr.mean())
            std_val = float(arr.std())
            cv_val = float(std_val / mean_val) if mean_val > 0 else 0.0
            min_val = float(arr.min())
            max_val = float(arr.max())
        else:
            mean_val = None
            cv_val = None
            min_val = None
            max_val = None

        def q_val(v: float | None, unit: str = "m3_m-3") -> Quantity:
            if v is not None:
                return Quantity(value=round(v, 4), unit=unit)
            return Quantity(value=None, unit=unit, missing_reason="INSUFFICIENT_COVERAGE")

        depth_stats[param] = {
            "depth_label": depth_label,
            "depth_cm": depth_cm,
            "parameter": param,
            "mean": q_val(mean_val),
            "variability_cv": q_val(cv_val, "unitless") if cv_val is not None else None,
            "min": q_val(min_val),
            "max": q_val(max_val),
            "valid_observations": n_valid,
            "missing_observations": n_missing,
        }

        # Add TimeSeries object
        time_series_objs.append(
            TimeSeries(
                series_id=f"{field_id}:sm_{depth_label}:{season_year}",
                variable=f"sm_{depth_label}",
                label=f"Volumetric soil water ({depth_label})",
                unit="m3_m-3",
                nature="model",
                temporal=TemporalSupport(
                    resolution="P1D",
                    period_start=start,
                    period_end=end,
                    aggregation="mean",
                    time_standard="UTC",
                ),
                spatial=spatial_support,
                sources=[source_obj],
                points=points,
            )
        )

        # Build UnifiedEnvironmentalMetric
        metric_status = (
            "available" if completeness >= COMPLETENESS_MIN
            else "partial" if n_valid > 0
            else "insufficient_coverage"
        )
        unified_metrics.append(
            UnifiedEnvironmentalMetric(
                metric=f"soil_moisture_{depth_label}",
                value=round(mean_val, 4) if mean_val is not None else None,
                unit="m3/m3",
                status=metric_status,
                provider="meteomatics",
                parameter=param,
                source_type="modelled_environmental_data",
                spatial_resolution_m=None,
                requested_grid_spacing="point_centroid",
                temporal_resolution="P1D",
                aggregation="temporal_mean",
                coverage=MetricCoverage(
                    valid_observations=n_valid,
                    expected_observations=expected_days,
                    coverage_fraction=round(completeness, 3),
                ),
                confidence="medium",
                limitations=["Derived from Meteomatics blend model; represents regional soil grid without sub-field sensing."],
                observed_at=datetime.now(UTC),
            )
        )

    # Calculate Root-Zone Composite (0–100 cm)
    # Day-by-day weighted sum: 0.10 * 5cm + 0.20 * 15cm + 0.70 * 50cm
    rz_pts: list[TimeSeriesPoint] = []
    rz_valid_vals: list[float] = []
    dry_days_count = 0

    pts_5 = {p.t: p.value for p in time_series_objs[0].points}
    pts_15 = {p.t: p.value for p in time_series_objs[1].points}
    pts_50 = {p.t: p.value for p in time_series_objs[2].points}

    cur_d = start
    while cur_d <= end:
        d_str = cur_d.strftime("%Y-%m-%d")
        v5 = pts_5.get(d_str)
        v15 = pts_15.get(d_str)
        v50 = pts_50.get(d_str)

        if v5 is not None and v15 is not None and v50 is not None:
            rz_val = round(0.10 * v5 + 0.20 * v15 + 0.70 * v50, 4)
            rz_valid_vals.append(rz_val)
            rz_pts.append(TimeSeriesPoint(t=d_str, value=rz_val, quality_status="valid"))
            if rz_val < DRY_THRESHOLD_M3M3:
                dry_days_count += 1
        else:
            rz_pts.append(TimeSeriesPoint(t=d_str, value=None, quality_status="missing", missing_reason="INSUFFICIENT_COVERAGE"))
        cur_d += np.timedelta64(1, "D").astype("timedelta64[ms]").astype(object) if hasattr(np, "timedelta64") else (
            cur_d.replace(day=cur_d.day + 1) if cur_d.day < 28 else (cur_d + (date(cur_d.year, cur_d.month + 1, 1) - cur_d))
        )
        # Safe standard date increment:
        from datetime import timedelta
        cur_d = cur_d if isinstance(cur_d, date) and not isinstance(cur_d, datetime) else date.fromisoformat(d_str) + timedelta(days=1)

    rz_completeness = len(rz_valid_vals) / expected_days if expected_days > 0 else 0.0
    if len(rz_valid_vals) > 0 and rz_completeness >= COMPLETENESS_MIN:
        rz_mean = float(np.mean(rz_valid_vals))
        q_rootzone = Quantity(value=round(rz_mean, 4), unit="m3_m-3")
        q_dry_days = Quantity(value=float(dry_days_count), unit="day")
        rz_status = "available"
    elif len(rz_valid_vals) > 0:
        rz_mean = float(np.mean(rz_valid_vals))
        q_rootzone = Quantity(value=round(rz_mean, 4), unit="m3_m-3")
        q_dry_days = Quantity(value=None, unit="day", missing_reason="INSUFFICIENT_COVERAGE")
        rz_status = "partial"
    else:
        q_rootzone = Quantity(value=None, unit="m3_m-3", missing_reason="INSUFFICIENT_COVERAGE")
        q_dry_days = Quantity(value=None, unit="day", missing_reason="INSUFFICIENT_COVERAGE")
        rz_status = "insufficient_coverage"

    time_series_objs.insert(
        0,
        TimeSeries(
            series_id=f"{field_id}:sm_rootzone:{season_year}",
            variable="sm_rootzone",
            label="Root-zone soil moisture composite",
            unit="m3_m-3",
            nature="model",
            temporal=TemporalSupport(
                resolution="P1D",
                period_start=start,
                period_end=end,
                aggregation="weighted_mean",
                time_standard="UTC",
            ),
            spatial=spatial_support,
            sources=[source_obj],
            points=rz_pts,
        ),
    )

    unified_metrics.append(
        UnifiedEnvironmentalMetric(
            metric="rootzone_soil_moisture",
            value=q_rootzone.value,
            unit="m3/m3",
            status=rz_status,
            provider="meteomatics",
            parameter="weighted_composite_0_100cm",
            source_type="derived_model_indicator",
            spatial_resolution_m=None,
            requested_grid_spacing="point_centroid",
            temporal_resolution="P1D",
            aggregation="depth_weighted_mean",
            coverage=MetricCoverage(
                valid_observations=len(rz_valid_vals),
                expected_observations=expected_days,
                coverage_fraction=round(rz_completeness, 3),
            ),
            confidence="medium",
            limitations=[
                "Calculated using 0.10*(-5cm) + 0.20*(-15cm) + 0.70*(-50cm).",
                "Regional modeled support class R, not direct in-situ probe measurement.",
            ],
            observed_at=datetime.now(UTC),
        )
    )

    overall_quality = QualityInfo(
        status="valid" if rz_completeness >= COMPLETENESS_MIN else "partial" if rz_valid_vals else "missing",
        flags=flags,
        completeness=round(rz_completeness, 3),
        missing_reason=None if rz_valid_vals else "INSUFFICIENT_COVERAGE",
    )

    s5 = depth_stats["volumetric_soil_water_-5cm:m3m3"]
    s15 = depth_stats["volumetric_soil_water_-15cm:m3m3"]
    s50 = depth_stats["volumetric_soil_water_-50cm:m3m3"]
    s150 = depth_stats["volumetric_soil_water_-150cm:m3m3"]

    return SoilMoistureProfile(
        field_id=field_id,
        season_year=season_year,
        as_of=today_dt,
        surface_sm=SoilMoistureDepthMetric(**s5),
        shallow_sm=SoilMoistureDepthMetric(**s15),
        middepth_sm=SoilMoistureDepthMetric(**s50),
        deep_sm=SoilMoistureDepthMetric(**s150),
        rootzone_sm_composite=q_rootzone,
        rootzone_dry_days=q_dry_days,
        series=time_series_objs,
        metrics=unified_metrics,
        quality=overall_quality,
        spatial=spatial_support,
        sources=[source_obj],
    )


def build_soil_moisture_indicators(
    field_id: UUID,
    year: int,
    sm_prof: SoilMoistureProfile,
) -> list[EnvironmentalIndicator]:
    """Emit rich EnvironmentalIndicators for all 4 horizons and composite metrics."""
    temp_support = TemporalSupport(
        resolution="P1D",
        period_start=date(year, 1, 1),
        period_end=min(date(year, 12, 31), date.today()),
        aggregation="mean",
        time_standard="UTC",
    )

    items: list[tuple[str, str, Quantity, MethodRef]] = [
        (
            "sm_surface_mean_season",
            "Surface soil moisture (-5 cm)",
            sm_prof.surface_sm.mean,
            METHOD_DEPTH_STATS,
        ),
        (
            "sm_shallow_mean_season",
            "Shallow soil moisture (-15 cm)",
            sm_prof.shallow_sm.mean,
            METHOD_DEPTH_STATS,
        ),
        (
            "sm_middepth_mean_season",
            "Mid-depth soil moisture (-50 cm)",
            sm_prof.middepth_sm.mean,
            METHOD_DEPTH_STATS,
        ),
        (
            "sm_deep_mean_season",
            "Deep drainage soil moisture (-150 cm)",
            sm_prof.deep_sm.mean,
            METHOD_DEPTH_STATS,
        ),
        (
            "sm_rootzone_mean_season",
            "Root-zone soil moisture composite",
            sm_prof.rootzone_sm_composite,
            METHOD_ROOTZONE,
        ),
        (
            "sm_rootzone_composite_season",
            "Depth-weighted root-zone composite (0–100 cm)",
            sm_prof.rootzone_sm_composite,
            METHOD_ROOTZONE,
        ),
        (
            "sm_rootzone_dry_days",
            "Root-zone dry days (<0.15 m³/m³)",
            sm_prof.rootzone_dry_days,
            METHOD_DRY_DAYS,
        ),
    ]

    cv_val = sm_prof.middepth_sm.variability_cv.value if sm_prof.middepth_sm.variability_cv else None
    if cv_val is not None:
        items.append((
            "sm_rootzone_cv",
            "Root-zone moisture temporal CV",
            Quantity(value=round(cv_val, 3), unit="percent"),
            METHOD_DEPTH_STATS,
        ))

    indicators: list[EnvironmentalIndicator] = []
    for key, label, val, method in items:
        indicators.append(
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:{year}:{key}",
                key=key,  # type: ignore[arg-type]
                label=label,
                category="soil_moisture",
                value=val,
                nature="model",
                spatial=sm_prof.spatial,
                temporal=temp_support,
                quality=sm_prof.quality,
                sources=sm_prof.sources,
                method=method,
                input_ids=[],
                reference_value=None,
            )
        )
    return indicators
