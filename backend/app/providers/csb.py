"""USDA NASS Crop Sequence Boundaries (CSB) 2018–2025 provider (INTEGRATION_GUIDE §4).

Dataset: NationalCSB_2018-2025_rev23.zip (Public domain, released March 2026).
Attributes: CSBID, CSBACRES, CDL2018..CDL2025, STATEFIPS, CNTYFIPS, geometry.
CRS: NAD83 Albers Conical Equal Area (EPSG:5070).

Reliability filter (D5.1 / INTEGRATION_GUIDE §4.1):
- At least 6 of the 8 CDL2018–CDL2025 majority values must be true crop codes
  (not pasture/grass 176, forest 141-143, water 111, developed 121-124, wetlands 190/195).
- CSBACRES >= 10 (~4 ha).
- Area <= 260 ha (statutory section boundary limit).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

NON_CROP_CODES = {62, 63, 111, 121, 122, 123, 124, 141, 142, 143, 176, 190, 195}
ALBERS_TO_WGS84 = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)


@dataclass
class CsbRecord:
    csb_id: str
    state_fips: str
    county_fips: str
    acres: float
    area_ha: float
    crop_years: dict[int, int]  # year -> majority cdl crop code
    geometry_wgs84: dict[str, Any]
    is_reliable: bool
    rejection_reason: str | None = None


def validate_csb_record(raw: dict[str, Any]) -> CsbRecord:
    """Validate and transform a single CSB raw record from FileGDB or GeoJSON."""
    csb_id = str(raw.get("CSBID") or raw.get("csb_id") or "")
    state_fips = str(raw.get("STATEFIPS") or raw.get("state_fips") or "20").zfill(2)
    county_fips = str(raw.get("CNTYFIPS") or raw.get("county_fips") or "155").zfill(3)
    acres = float(raw.get("CSBACRES") or raw.get("acres") or 0.0)

    # Extract crop years 2018..2025
    crop_years: dict[int, int] = {}
    for y in range(2018, 2026):
        key = f"CDL{y}"
        if key in raw and raw[key] is not None:
            try:
                crop_years[y] = int(raw[key])
            except (ValueError, TypeError):
                pass

    # Geometry validation & reprojection
    raw_geom = raw.get("geometry")
    if isinstance(raw_geom, dict):
        poly = shape(raw_geom)
    elif hasattr(raw_geom, "__geo_interface__"):
        poly = shape(raw_geom.__geo_interface__)
    else:
        raise ValueError(f"Invalid geometry for CSB record {csb_id}")

    # Check if geometry is in EPSG:5070 coordinates (Albers x/y in hundreds of thousands/millions)
    bounds = poly.bounds
    if bounds[0] > 180 or bounds[0] < -180:
        # Reproject from EPSG:5070 to EPSG:4326
        poly_wgs84 = transform(ALBERS_TO_WGS84.transform, poly)
    else:
        poly_wgs84 = poly

    area_ha = round(acres * 0.404686, 2)

    # Reliability filter
    crop_year_count = sum(1 for c in crop_years.values() if c not in NON_CROP_CODES)
    is_reliable = True
    reason = None

    if len(crop_years) >= 8 and crop_year_count < 6:
        is_reliable = False
        reason = f"Only {crop_year_count} of 8 years had crop cultivation."
    elif acres < 10.0:
        is_reliable = False
        reason = f"Field size ({acres:.1f} ac) below 10-acre minimum threshold."
    elif area_ha > 260.0:
        is_reliable = False
        reason = f"Field size ({area_ha:.1f} ha) exceeds 260 ha demonstration bound."

    return CsbRecord(
        csb_id=csb_id,
        state_fips=state_fips,
        county_fips=county_fips,
        acres=acres,
        area_ha=area_ha,
        crop_years=crop_years,
        geometry_wgs84=mapping(poly_wgs84),
        is_reliable=is_reliable,
        rejection_reason=reason,
    )
