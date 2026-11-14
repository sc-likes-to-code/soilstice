"""SRTM terrain processing -> TerrainProfile (INTEGRATION_GUIDE §7.1; DATA_ARCHITECTURE §6.7).

- Elevation mean/min/max: pixel centres inside the field polygon on the NATIVE 1″ grid (EPSG:4326); voids excluded.
- Slope: DEM window reprojected to EPSG:5070 at 30 m (bilinear), Horn (1981) 3×3 kernel, percent rise;
  mean and 90th percentile over pixel centres inside the polygon. Voids propagate as NaN (never 0).
"""

from __future__ import annotations

from uuid import UUID

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry.base import BaseGeometry

from app.catalog import SPATIAL, source_ref
from app.contracts import MethodRef, QualityFlag, QualityInfo, Quantity, TerrainProfile
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
