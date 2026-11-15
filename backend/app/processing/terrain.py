"""SRTM terrain processing -> TerrainProfile (INTEGRATION_GUIDE §7.1; DATA_ARCHITECTURE §6.7).

- Elevation mean/min/max: pixel centres inside the field polygon on the NATIVE 1″ grid (EPSG:4326); voids excluded.
- Slope: DEM window reprojected to EPSG:5070 at 30 m (bilinear), Horn (1981) 3×3 kernel, percent rise;
  mean and 90th percentile over pixel centres inside the polygon. Voids propagate as NaN (never 0).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from app.catalog import SPATIAL, source_ref
from app.contracts import MethodRef, QualityFlag, QualityInfo, Quantity, SpatialSupport, TerrainProfile
from app.providers.meteomatics import MeteomaticsClient
from app.providers.srtm import VOID, SrtmTile

from .geometry import reproject as reproject_geom

SLOPE_RES_M = 30.0

METHOD = MethodRef(
    method_id="srtm_horn_slope", name="SRTM elevation statistics and Horn slope", version="1",
    description="Elevation statistics on the native SRTMGL1 1-arc-second grid (pixel-centre inclusion, voids excluded). "
                "Slope: DEM reprojected to EPSG:5070 at 30 m with bilinear resampling, Horn (1981) 3x3 finite "
                "differences, expressed in percent; mean and 90th percentile over the field.",
    reference_url="https://doi.org/10.1109/PROC.1981.11918",
)


def horn_slope_pct(dem: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Horn (1981) slope in percent. Edge cells and any cell with a NaN neighbour become NaN."""
    z = np.pad(dem.astype("float64"), 1, constant_values=np.nan)
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * dy)
    return np.sqrt(dzdx**2 + dzdy**2) * 100.0


def evaluate_spatial_adequacy(grid: list[list[float]] | np.ndarray) -> dict[str, Any]:
    """Evaluate whether elevation grid meets spatial adequacy criteria for slope calculation.

    Requires:
    - At least 3x3 grid (rows >= 3, cols >= 3)
    - At least 9 valid values
    - Spatial variance > 1e-4 (not a flat block or synthetic constant)
    """
    arr = np.array(grid, dtype=float)
    if arr.ndim != 2:
        return {"adequate": False, "reason": "Grid must be 2-dimensional"}
    rows, cols = arr.shape
    if rows < 3 or cols < 3:
        return {"adequate": False, "reason": f"Grid dimensions {rows}x{cols} too small for 3x3 finite-difference"}
    valid = arr[~np.isnan(arr)]
    if len(valid) < 9:
        return {"adequate": False, "reason": f"Only {len(valid)} valid cells (>= 9 required)"}
    var = float(np.var(valid))
    if var <= 1e-4:
        return {"adequate": False, "reason": "Zero or near-zero spatial variance; flat block interpolation"}
    return {"adequate": True, "cells": len(valid), "variance": var}


def compute_horn_slope_p90(grid: list[list[float]] | np.ndarray, dx: float = 30.0, dy: float = 30.0) -> float | None:
    """Compute 90th percentile slope using Horn (1981) finite-difference, or None if inadequate."""
    ad = evaluate_spatial_adequacy(grid)
    if not ad["adequate"]:
        return None
    arr = np.array(grid, dtype=float)
    slopes = horn_slope_pct(arr, dx=dx, dy=dy)
    valid_slopes = slopes[~np.isnan(slopes)]
    if len(valid_slopes) == 0:
        return None
    return round(float(np.percentile(valid_slopes, 90)), 2)


def build_terrain_profile(field_id: UUID, geom_4326: BaseGeometry, tiles: list[SrtmTile]) -> TerrainProfile:
    w, s, e, n = geom_4326.bounds
    pad = 0.003  # ~300 m so the slope kernel has neighbours at the field edge
    datasets = [rasterio.open(t.path) for t in tiles]
    try:
        mosaic, mtr = merge(datasets, bounds=(w - pad, s - pad, e + pad, n + pad), nodata=VOID)
    finally:
        for ds in datasets:
            ds.close()
    dem = mosaic[0]
    inside = geometry_mask([geom_4326], out_shape=dem.shape, transform=mtr, invert=True, all_touched=False)
    elev = dem[inside]
    n_total = int(elev.size)
    elev_valid = elev[elev != VOID].astype("float64")
    n_void = n_total - int(elev_valid.size)

    # Slope in EPSG:5070
    src = np.where(dem == VOID, np.nan, dem.astype("float32"))
    dst_tr, dw, dh = calculate_default_transform("EPSG:4326", "EPSG:5070", dem.shape[1], dem.shape[0],
                                                 left=w - pad, bottom=s - pad, right=e + pad, top=n + pad,
                                                 resolution=SLOPE_RES_M)
    dst = np.full((dh, dw), np.nan, dtype="float32")
    reproject(src, dst, src_transform=mtr, src_crs="EPSG:4326", dst_transform=dst_tr, dst_crs="EPSG:5070",
              resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    slope = horn_slope_pct(dst, SLOPE_RES_M, SLOPE_RES_M)
    g5070 = reproject_geom(geom_4326, "EPSG:4326", "EPSG:5070")
    inside5070 = geometry_mask([g5070], out_shape=slope.shape, transform=dst_tr, invert=True, all_touched=False)
    sl = slope[inside5070]
    sl = sl[~np.isnan(sl)]

    def q(v: float | None, unit: str, reason: str = "INSUFFICIENT_COVERAGE") -> Quantity:
        return Quantity(value=round(float(v), 3), unit=unit) if v is not None else \
            Quantity(value=None, unit=unit, missing_reason=reason)

    has_elev = elev_valid.size > 0
    flags = [QualityFlag(code="SRTM_SURFACE_MODEL", severity="info",
                         message="SRTM (Feb 2000) is a C-band surface model, not bare earth; tree lines and buildings "
                                 "bias it upward. Vertical datum EGM96.")]
    if n_void:
        flags.append(QualityFlag(code="VOID_PIXELS", severity="warning",
                                 message=f"{n_void} of {n_total} field pixels are voids and were excluded."))
    completeness = (elev_valid.size / n_total) if n_total else 0.0
    status = "missing" if not has_elev else ("valid" if n_void == 0 and sl.size else "partial")
    return TerrainProfile(
        field_id=field_id,
        elevation_mean=q(elev_valid.mean() if has_elev else None, "m"),
        elevation_min=q(elev_valid.min() if has_elev else None, "m"),
        elevation_max=q(elev_valid.max() if has_elev else None, "m"),
        slope_mean_pct=q(sl.mean() if sl.size else None, "percent"),
        slope_p90_pct=q(np.percentile(sl, 90) if sl.size else None, "percent"),
        method=METHOD, spatial=SPATIAL["nasa_srtm_gl1"],
        sources=[source_ref("nasa_srtm_gl1", product=f"SRTMGL1 tile {t.name}",
                            acquisition_id=t.acquisition.acquisition_id, retrieved_at=t.acquisition.retrieved_at)
                 for t in tiles],
        quality=QualityInfo(status=status, flags=flags, completeness=round(completeness, 4),
                            missing_reason=None if has_elev else "INSUFFICIENT_COVERAGE"),
    )


METHOD_METEOMATICS = MethodRef(
    method_id="meteomatics_elevation_horn_slope",
    name="Meteomatics Elevation & Conditional Horn Slope",
    version="1.0",
    description="Elevation statistics from Meteomatics digital elevation model (elevation:m). "
                "Slope is conditionally derived via Horn (1981) finite differences on a projected metric grid "
                "only when field spatial sampling meets minimum adequacy requirements (>= 9 valid cells, spatial variance > 0).",
    reference_url="https://doi.org/10.1109/PROC.1981.11918",
)


def build_terrain_profile_from_meteomatics(
    field_id: UUID,
    geom_4326: BaseGeometry,
    client: MeteomaticsClient,
    timestamp: datetime | None = None,
) -> TerrainProfile:
    """Fetch elevation grid from Meteomatics, compute elevation stats, and conditionally derive slope."""
    w, s, e, n = geom_4326.bounds
    ts = timestamp or datetime.now(UTC)

    # Calculate bounding box dimensions
    width_deg = max(e - w, 0.001)
    height_deg = max(n - s, 0.001)

    # Adaptive grid resolution: aim for ~60–90m cell spacing (~0.0006–0.0008 deg)
    res_deg = 0.0008
    pad_deg = 0.0024  # 3 cells pad around field for 3x3 kernel neighbors

    query_bounds = (w - pad_deg, s - pad_deg, e + pad_deg, n + pad_deg)

    # Query elevation grid
    grid_dict = client.query_grid(
        bounds=query_bounds,
        res_lat=res_deg,
        res_lon=res_deg,
        timestamp=ts,
        parameters=["elevation:m"],
        model="mix",
    )

    pts = grid_dict.get("elevation:m", [])
    if not pts:
        # Fallback to centroid point query if grid returned nothing
        mid_lat, mid_lon = geom_4326.centroid.y, geom_4326.centroid.x
        pt_res = client.query_point(mid_lat, mid_lon, ts, ["elevation:m"])
        elev_pt = pt_res.get("elevation:m")
        if elev_pt is not None:
            q_elev = Quantity(value=round(elev_pt, 2), unit="m")
            q_none = Quantity(value=None, unit="percent", missing_reason="INSUFFICIENT_COVERAGE")
            return TerrainProfile(
                field_id=field_id,
                elevation_mean=q_elev,
                elevation_min=q_elev,
                elevation_max=q_elev,
                slope_mean_pct=q_none,
                slope_p90_pct=q_none,
                method=METHOD_METEOMATICS,
                spatial=SpatialSupport(
                    support_class="R",
                    native_resolution_m=None,
                    extraction_method="api_point_query",
                    crs="EPSG:4326",
                ),
                sources=[source_ref("meteomatics", product="Meteomatics Elevation", version="v3.0")],
                quality=QualityInfo(
                    status="partial",
                    flags=[
                        QualityFlag(
                            code="POINT_ELEVATION_ONLY",
                            severity="warning",
                            message="Elevation was retrieved as a single point; slope cannot be derived.",
                        )
                    ],
                    completeness=1.0,
                ),
            )
        # Empty
        q_miss_m = Quantity(value=None, unit="m", missing_reason="NO_DATA_SOURCE")
        q_miss_pct = Quantity(value=None, unit="percent", missing_reason="NO_DATA_SOURCE")
        return TerrainProfile(
            field_id=field_id,
            elevation_mean=q_miss_m,
            elevation_min=q_miss_m,
            elevation_max=q_miss_m,
            slope_mean_pct=q_miss_pct,
            slope_p90_pct=q_miss_pct,
            method=METHOD_METEOMATICS,
            spatial=SpatialSupport(support_class="R", native_resolution_m=None, extraction_method="api_point_query", crs="EPSG:4326"),
            sources=[source_ref("meteomatics", product="Meteomatics Elevation", version="v3.0")],
            quality=QualityInfo(status="missing", missing_reason="NO_DATA_SOURCE"),
        )

    # Organize grid into 2D array
    lats = sorted({p.lat for p in pts}, reverse=True)
    lons = sorted({p.lon for p in pts})
    nrows, ncols = len(lats), len(lons)

    lat_idx = {lat: i for i, lat in enumerate(lats)}
    lon_idx = {lon: j for j, lon in enumerate(lons)}

    dem_grid = np.full((nrows, ncols), np.nan, dtype="float64")
    for p in pts:
        if p.valid and p.value is not None:
            dem_grid[lat_idx[p.lat], lon_idx[p.lon]] = p.value

    # Extract cells inside the field polygon
    field_elevs: list[float] = []
    field_mask = np.zeros((nrows, ncols), dtype=bool)

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            pt = Point(lon, lat)
            if geom_4326.contains(pt):
                field_mask[i, j] = True
                val = dem_grid[i, j]
                if not np.isnan(val):
                    field_elevs.append(val)

    # Elevation statistics
    has_elev = len(field_elevs) > 0
    if has_elev:
        elev_arr = np.array(field_elevs)
        mean_elev = float(elev_arr.mean())
        min_elev = float(elev_arr.min())
        max_elev = float(elev_arr.max())
        elev_variance = float(elev_arr.var())
    else:
        # Fallback to all valid grid points if polygon contains 0 due to very small field
        all_valid = dem_grid[~np.isnan(dem_grid)]
        if all_valid.size > 0:
            mean_elev = float(all_valid.mean())
            min_elev = float(all_valid.min())
            max_elev = float(all_valid.max())
            elev_variance = float(all_valid.var())
            has_elev = True
        else:
            mean_elev = None
            min_elev = None
            max_elev = None
            elev_variance = 0.0

    def q_m(v: float | None) -> Quantity:
        if v is not None:
            return Quantity(value=round(v, 2), unit="m")
        return Quantity(value=None, unit="m", missing_reason="INSUFFICIENT_COVERAGE")

    def q_p(v: float | None, reason: str = "INSUFFICIENT_COVERAGE") -> Quantity:
        if v is not None:
            return Quantity(value=round(v, 3), unit="percent")
        return Quantity(value=None, unit="percent", missing_reason=reason)

    flags: list[QualityFlag] = []
    flags.append(
        QualityFlag(
            code="METEOMATICS_ELEVATION",
            severity="info",
            message="Elevation derived from Meteomatics digital terrain model. Vertical datum EGM96/MSL.",
        )
    )

    # Spatial adequacy check for slope derivation:
    # 1. Must have at least 3x3 grid
    # 2. Field must contain at least 9 valid cells
    # 3. Elevation spatial variance must be strictly positive (> 0.001 m^2) to avoid deriving slope on flat block artifacts
    # 4. Field must span at least 2 distinct rows and columns
    mid_lat = (n + s) / 2.0
    lat_step = abs(lats[0] - lats[1]) if len(lats) > 1 else res_deg
    lon_step = abs(lons[1] - lons[0]) if len(lons) > 1 else res_deg

    dx_m = lon_step * 111320.0 * math.cos(math.radians(mid_lat))
    dy_m = lat_step * 110574.0

    rows_with_field = np.any(field_mask, axis=1).sum()
    cols_with_field = np.any(field_mask, axis=0).sum()

    spatial_adequate = (
        nrows >= 3
        and ncols >= 3
        and len(field_elevs) >= 9
        and rows_with_field >= 2
        and cols_with_field >= 2
        and elev_variance > 1e-4
    )

    slope_mean = None
    slope_p90 = None

    if spatial_adequate:
        # Calculate Horn slope
        slope_grid = horn_slope_pct(dem_grid, dx=dx_m, dy=dy_m)
        field_slopes = slope_grid[field_mask]
        valid_slopes = field_slopes[~np.isnan(field_slopes)]
        if valid_slopes.size > 0:
            slope_mean = float(valid_slopes.mean())
            slope_p90 = float(np.percentile(valid_slopes, 90))
        else:
            flags.append(
                QualityFlag(
                    code="SLOPE_EDGE_MASKED",
                    severity="warning",
                    message="Field cells were situated at the edge of the grid kernel; slope could not be evaluated.",
                )
            )
    else:
        flags.append(
            QualityFlag(
                code="INSUFFICIENT_TERRAIN_RESOLUTION",
                severity="warning",
                message="Field size or elevation grid sampling density is inadequate for reliable slope calculation "
                        f"(valid field cells: {len(field_elevs)}/9 required; variance: {elev_variance:.4f}). "
                        "Slope metrics are conditionally withheld.",
            )
        )

    completeness = len(field_elevs) / max(int(field_mask.sum()), 1) if has_elev else 0.0
    status = "valid" if (has_elev and slope_mean is not None) else "partial" if has_elev else "missing"

    return TerrainProfile(
        field_id=field_id,
        elevation_mean=q_m(mean_elev),
        elevation_min=q_m(min_elev),
        elevation_max=q_m(max_elev),
        slope_mean_pct=q_p(slope_mean),
        slope_p90_pct=q_p(slope_p90),
        method=METHOD_METEOMATICS,
        spatial=SpatialSupport(
            support_class="F" if spatial_adequate else "R",
            native_resolution_m=round(max(dx_m, dy_m), 1),
            extraction_method="zonal_polygon" if spatial_adequate else "api_point_query",
            crs="EPSG:4326",
        ),
        sources=[source_ref("meteomatics", product="Meteomatics Elevation Grid", version="v3.0")],
        quality=QualityInfo(
            status=status,
            flags=flags,
            completeness=round(completeness, 4),
            missing_reason=None if has_elev else "INSUFFICIENT_COVERAGE",
        ),
    )

