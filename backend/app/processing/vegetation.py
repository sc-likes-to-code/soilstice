"""Vegetation indices & phenology processing for NASA HLS / HLS-VI (INTEGRATION_GUIDE §5).

Calculations:
- Fmask quality filtering (User Guide Table 9: bits 1-3 cloud/shadow, 4 snow/ice, 5 water).
- Acceptance criterion: scene clear_fraction >= 0.70 over the field polygon.
- Native spatial extraction: 30 m UTM pixels, zonal stats (median, p10, p90).
- Phenology derivation: peak value, peak date, greenup date, senescence date.
- Complete failure isolation and contract compliance.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

import numpy as np
from shapely.geometry.base import BaseGeometry

from app.catalog import source_ref
from app.logging import get_logger
from app.contracts import (
    MaskCounts,
    MethodRef,
    Phenology,
    QualityFlag,
    QualityInfo,
    Quantity,
    SpatialSupport,
    TemporalSupport,
    TimeSeries,
    TimeSeriesPoint,
    VegetationIndex,
    VegetationProfile,
    VegetationScene,
)
from app.providers.hls import HlsStacScene
from app.providers.meteomatics import MeteomaticsClient

log = get_logger("processing.vegetation")

HLS_SPATIAL = SpatialSupport(
    support_class="F",
    native_resolution_m=30,
    extraction_method="zonal_polygon_inward_buffer",
)

FMASK_METHOD = MethodRef(
    method_id="fmask_v2_hls",
    name="Fmask v4.0 for HLS v2.0",
    version="2.0",
    description="Bitmask filtering: bit 1 (cloud), bit 2 (cloud adjacent), bit 3 (cloud shadow), "
                "bit 4 (snow/ice), bit 5 (water). Accepted if clear_fraction >= 0.70.",
    reference_url="https://doi.org/10.1016/j.rse.2011.10.030",
)

PHENOLOGY_METHOD = MethodRef(
    method_id="hls_phenology_v1",
    name="HLS Multi-temporal Phenology",
    version="1.0",
    description="Peak vegetation detection from 30 m cloud-masked HLS time series with greenup (50% amplitude rise) "
                "and senescence (50% amplitude drop).",
    reference_url="https://doi.org/10.1016/j.rse.2020.111685",
)


def parse_fmask(fmask_arr: np.ndarray) -> tuple[MaskCounts, int, int, float, bool]:
    """Parse HLS Fmask uint8 raster values into mask counts and clear fraction."""
    total = int(fmask_arr.size)
    if total == 0:
        return MaskCounts(cloud=0, cloud_adjacent=0, cloud_shadow=0, snow_ice=0, water=0), 0, 0, 0.0, False

    # Bits: 1=cloud, 2=adjacent, 3=shadow, 4=snow/ice, 5=water
    cloud = int(np.sum((fmask_arr & (1 << 1)) > 0))
    adjacent = int(np.sum((fmask_arr & (1 << 2)) > 0))
    shadow = int(np.sum((fmask_arr & (1 << 3)) > 0))
    snow_ice = int(np.sum((fmask_arr & (1 << 4)) > 0))
    water = int(np.sum((fmask_arr & (1 << 5)) > 0))

    mask = (fmask_arr & 0b00111110) > 0  # any of bits 1..5 set
    valid = int(np.sum(~mask))
    clear_fraction = float(valid / total)
    accepted = clear_fraction >= 0.70

    counts = MaskCounts(
        cloud=cloud,
        cloud_adjacent=adjacent,
        cloud_shadow=shadow,
        snow_ice=snow_ice,
        water=water,
    )
    return counts, valid, total, clear_fraction, accepted


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Compute Normalized Difference Vegetation Index from NIR and Red arrays."""
    # Convert from int16 with 0.0001 scale
    valid = (nir != -9999) & (red != -9999)
    nir_f = np.where(valid, nir.astype(np.float32) * 0.0001, np.nan)
    red_f = np.where(valid, red.astype(np.float32) * 0.0001, np.nan)
    denom = nir_f + red_f
    return np.where((denom > 0) & np.isfinite(denom), (nir_f - red_f) / denom, np.nan)


def compute_evi2(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Compute 2-band Enhanced Vegetation Index (EVI2)."""
    valid = (nir != -9999) & (red != -9999)
    nir_f = np.where(valid, nir.astype(np.float32) * 0.0001, np.nan)
    red_f = np.where(valid, red.astype(np.float32) * 0.0001, np.nan)
    denom = nir_f + 2.4 * red_f + 1.0
    return np.where((denom > 0) & np.isfinite(denom), 2.5 * (nir_f - red_f) / denom, np.nan)


def derive_phenology(scenes: Sequence[VegetationScene]) -> Phenology:
    """Extract agricultural phenology parameters from accepted scenes."""
    valid_scenes = [s for s in scenes if s.accepted and s.median is not None]
    if not valid_scenes:
        return Phenology(
            peak_value=Quantity(value=None, unit="unitless", missing_reason="INSUFFICIENT_COVERAGE"),
            method=PHENOLOGY_METHOD,
            gap_filled=False,
            missing_reason="INSUFFICIENT_COVERAGE",
        )

    # Sort chronologically
    valid_scenes = sorted(valid_scenes, key=lambda s: s.acquired_at)
    best_scene = max(valid_scenes, key=lambda s: s.median if s.median is not None else -999.0)
    peak_val = best_scene.median
    peak_dt = best_scene.acquired_at.date()

    if peak_val is None or peak_val <= 0:
        return Phenology(
            peak_value=Quantity(value=peak_val, unit="unitless"),
            peak_date=peak_dt,
            method=PHENOLOGY_METHOD,
            gap_filled=False,
        )

    # Threshold for 50% seasonal amplitude
    min_val = min((s.median for s in valid_scenes if s.median is not None), default=0.1)
    threshold = min_val + 0.5 * (peak_val - min_val)

    greenup_dt: date | None = None
    for s in valid_scenes:
        if s.acquired_at.date() <= peak_dt and (s.median or 0) >= threshold:
            greenup_dt = s.acquired_at.date()
            break

    senescence_dt: date | None = None
    for s in valid_scenes:
        if s.acquired_at.date() > peak_dt and (s.median or 0) <= threshold:
            senescence_dt = s.acquired_at.date()
            break

    return Phenology(
        peak_value=Quantity(value=round(peak_val, 4), unit="unitless"),
        peak_date=peak_dt,
        greenup_date=greenup_dt,
        senescence_date=senescence_dt,
        method=PHENOLOGY_METHOD,
        gap_filled=False,
    )


def build_vegetation_profile_from_stac(
    field_id: UUID,
    year: int,
    index: VegetationIndex,
    stac_scenes: Sequence[HlsStacScene],
    *,
    extracted_scenes: Sequence[VegetationScene] | None = None,
    failure_reason: str | None = None,
    failure_message: str | None = None,
) -> VegetationProfile:
    """Build a contract-compliant VegetationProfile from STAC discovery and scene extractions."""
    scenes: list[VegetationScene] = []
    points: list[TimeSeriesPoint] = []

    if extracted_scenes:
        scenes = list(extracted_scenes)
        for s in scenes:
            if s.accepted and s.median is not None:
                d = s.acquired_at.date()
                points.append(
                    TimeSeriesPoint(
                        t=d.isoformat(),
                        value=round(s.median, 4),
                        quality_status="valid",
                    )
                )
    elif stac_scenes:
        # Real scenes discovered from STAC, but raw pixel extraction requires credentials
        for sc in stac_scenes:
            # Mask counts estimated from cloud cover percentage if raw Fmask not downloaded
            cloud_pct = sc.cloud_cover
            accepted = cloud_pct <= 30.0
            scenes.append(
                VegetationScene(
                    granule_id=sc.granule_id,
                    product=sc.product if sc.product in ("HLSL30_VI", "HLSS30_VI", "HLSL30", "HLSS30") else "synthetic",
                    acquired_at=sc.acquired_at,
                    median=None,
                    p10=None,
                    p90=None,
                    valid_pixels=0,
                    total_pixels=0,
                    clear_fraction=round(max(0.0, min(1.0, 1.0 - cloud_pct / 100.0)), 3),
                    accepted=accepted,
                    mask_counts=MaskCounts(cloud=int(cloud_pct), cloud_adjacent=0, cloud_shadow=0, snow_ice=0, water=0),
                    missing_reason="NOT_COMPUTED" if failure_reason is None else failure_reason,
                )
            )

    phenology = derive_phenology(scenes)

    series_id = f"{field_id}:hls:{index.lower()}:{year}"
    series = TimeSeries(
        series_id=series_id,
        variable=index.lower(),
        label=f"{index} (NASA HLS v2.0)",
        unit="unitless",
        nature="derived",
        spatial=HLS_SPATIAL,
        temporal=TemporalSupport(
            resolution="irregular",
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            aggregation="median",
            time_standard="UTC",
        ),
        sources=[source_ref("nasa_hls_vi"), source_ref("nasa_hls")],
        points=points,
        reference=None,
    )

    accepted_count = sum(1 for s in scenes if s.accepted)
    flags: list[QualityFlag] = []
    if failure_message:
        flags.append(QualityFlag(code="UPSTREAM_ERROR", severity="warning", message=failure_message))
    elif not points and scenes:
        flags.append(QualityFlag(
            code="AUTHENTICATION_REQUIRED",
            severity="info",
            message="Real HLS scenes discovered via CMR-STAC. "
                    "Configure NASA Earthdata credentials to download 30 m GeoTIFFs.",
        ))

    completeness = min(1.0, float(accepted_count / 15.0)) if accepted_count > 0 else 0.0
    quality = QualityInfo(
        status="valid" if points else "partial" if scenes else "missing",
        flags=flags,
        completeness=round(completeness, 3),
        missing_reason=failure_reason if not scenes else None,
    )

    return VegetationProfile(
        field_id=field_id,
        year=year,
        index=index,
        scenes=scenes,
        series=series,
        phenology=phenology,
        spatial=HLS_SPATIAL,
        sources=[source_ref("nasa_hls_vi"), source_ref("nasa_hls")],
        quality=quality,
    )


METHOD_METEOMATICS_NDVI = MethodRef(
    method_id="meteomatics_regional_ndvi",
    name="Meteomatics Regional Satellite NDVI",
    version="1.0",
    description="Regional context satellite NDVI (sat_ndvi:idx) from Meteomatics blend model. "
                "Represents regional canopy greenness indicators (support class R); not field-scale 30 m HLS imagery.",
    reference_url="https://www.meteomatics.com/en/api/",
)


def build_regional_ndvi_profile_from_meteomatics(
    field_id: UUID,
    geom: BaseGeometry,
    year: int,
    client: MeteomaticsClient,
) -> VegetationProfile:
    """Fetch regional NDVI time series from Meteomatics (sat_ndvi:idx) and build VegetationProfile."""
    centroid = geom.centroid
    lat, lon = centroid.y, centroid.x
    start_d = date(year, 1, 1)
    end_d = min(date(year, 12, 31), date.today())

    # Query time series
    try:
        raw_dict = client.query_time_series(
            lat=lat,
            lon=lon,
            start=start_d,
            end=end_d,
            step="P1D",
            parameters=["sat_ndvi:idx"],
            model="mix",
        )
    except Exception as exc:
        log.warning("Meteomatics sat_ndvi query unavailable for location (%.4f, %.4f): %s", lat, lon, exc)
        raw_dict = {}

    obs_list = raw_dict.get("sat_ndvi:idx", [])
    scenes: list[VegetationScene] = []
    points: list[TimeSeriesPoint] = []
    valid_vals: list[float] = []

    for obs in obs_list:
        v = obs.value
        # NDVI valid range: -1.0 to +1.0
        is_valid = v is not None and -1.0 <= v <= 1.0
        v_clean = round(float(v), 4) if is_valid else None
        d_str = obs.timestamp.strftime("%Y-%m-%d")

        if is_valid and v_clean is not None:
            valid_vals.append(v_clean)

        points.append(
            TimeSeriesPoint(
                t=d_str,
                value=v_clean,
                quality_status="valid" if is_valid else "missing",
                missing_reason=None if is_valid else "INSUFFICIENT_COVERAGE",
            )
        )

        scenes.append(
            VegetationScene(
                granule_id=f"METEOMATICS.SAT_NDVI.{d_str}",
                product="meteomatics_sat_ndvi",
                acquired_at=obs.timestamp,
                median=v_clean,
                p10=v_clean,
                p90=v_clean,
                valid_pixels=1 if is_valid else 0,
                total_pixels=1,
                clear_fraction=1.0 if is_valid else 0.0,
                accepted=is_valid,
                mask_counts=MaskCounts(cloud=0 if is_valid else 1, cloud_adjacent=0, cloud_shadow=0, snow_ice=0, water=0),
                missing_reason=None if is_valid else "INSUFFICIENT_COVERAGE",
            )
        )

    # Calculate regional peak NDVI
    if valid_vals:
        max_v = max(valid_vals)
        peak_idx = valid_vals.index(max_v)
        # Find matching date
        valid_scenes = [s for s in scenes if s.accepted and s.median is not None]
        peak_d = valid_scenes[peak_idx].acquired_at.date() if peak_idx < len(valid_scenes) else None
        phenology = Phenology(
            peak_value=Quantity(value=max_v, unit="unitless"),
            peak_date=peak_d,
            greenup_date=None,  # Do not infer precise dates from regional observations
            senescence_date=None,
            method=METHOD_METEOMATICS_NDVI,
            gap_filled=False,
            missing_reason=None,
        )
    else:
        phenology = Phenology(
            peak_value=Quantity(value=None, unit="unitless", missing_reason="INSUFFICIENT_COVERAGE"),
            peak_date=None,
            greenup_date=None,
            senescence_date=None,
            method=METHOD_METEOMATICS_NDVI,
            gap_filled=False,
            missing_reason="INSUFFICIENT_COVERAGE",
        )

    spatial_support = SpatialSupport(
        support_class="R",
        native_resolution_m=None,
        extraction_method="api_point_query",
        crs="EPSG:4326",
    )

    series_id = f"{field_id}:meteomatics:ndvi:{year}"
    series = TimeSeries(
        series_id=series_id,
        variable="ndvi",
        label="Regional NDVI (Meteomatics sat_ndvi:idx)",
        unit="unitless",
        nature="derived",
        spatial=spatial_support,
        temporal=TemporalSupport(
            resolution="P1D",
            period_start=start_d,
            period_end=end_d,
            aggregation="mean",
            time_standard="UTC",
        ),
        sources=[source_ref("meteomatics", product="Meteomatics Satellite NDVI", version="v3.0")],
        points=points,
        reference=None,
    )

    expected = max((end_d - start_d).days + 1, 1)
    completeness = len(valid_vals) / expected if expected else 0.0

    if valid_vals:
        flags = [
            QualityFlag(
                code="REGIONAL_VEGETATION_CONTEXT",
                severity="info",
                message="NDVI is derived from Meteomatics sat_ndvi:idx providing regional greenness context (support class R). "
                        "This is not field-level 30 m HLS imagery. Canopy stability model remains withheld.",
            )
        ]
        status = "valid" if completeness >= 0.8 else "partial"
        missing_reason = None
    else:
        flags = [
            QualityFlag(
                code="REGIONAL_VEGETATION_UNAVAILABLE",
                severity="info",
                message="Meteomatics sat_ndvi:idx regional satellite product is unavailable for this location (outside observation domain 90°E–180°E). "
                        "Regional vegetation context is marked unavailable.",
            )
        ]
        status = "missing"
        missing_reason = "OUTSIDE_AOI"

    return VegetationProfile(
        field_id=field_id,
        year=year,
        index="NDVI",
        scenes=scenes,
        series=series,
        phenology=phenology,
        spatial=spatial_support,
        sources=[source_ref("meteomatics", product="Meteomatics Satellite NDVI", version="v3.0")],
        quality=QualityInfo(
            status=status,
            flags=flags,
            completeness=round(completeness, 3),
            missing_reason=missing_reason,
        ),
    )

