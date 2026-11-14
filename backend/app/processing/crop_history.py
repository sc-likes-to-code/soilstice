"""CDL zonal processing -> CropHistory (DATA_ARCHITECTURE §5.2–5.3; INTEGRATION_GUIDE §3).

- Field polygon reprojected to the raster CRS (EPSG:5070); 15 m inward buffer, skipped (flag INWARD_BUFFER_SKIPPED)
  if < 50 % of the area would remain.
- Pixel inclusion: pixel centre inside the polygon (rasterio geometry_mask, all_touched=False). This is the
  documented fallback to fractional-coverage zonal stats (exactextract is not used) and is edge-biased on small fields.
- Value 0 (background / outside county) is excluded and reported, never counted as a crop.
- purity = majority area fraction; low_purity = purity < 0.6 (contract).
- Rotation metrics are NOT computed here (methodology pending Phase 4): emitted with NOT_COMPUTED.
"""

from __future__ import annotations

import math
from collections import Counter
from uuid import UUID

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry.base import BaseGeometry

from app.catalog import SPATIAL, source_ref
from app.contracts import (
    CropHistory,
    CropRef,
    CropShare,
    CropYear,
    EnvironmentalIndicator,
    MethodRef,
    QualityFlag,
    QualityInfo,
    Quantity,
    TemporalSupport,
    YearPeriod,
)
from app.providers.cdl import CdlCountyRaster
from app.providers.http import ProviderError

from .geometry import inward_buffer_5070, reproject

INWARD_BUFFER_M = 15.0
LOW_PURITY = 0.6

# Non-agricultural land cover classes (USGS NLCD / CDL)
NON_AG_LANDCOVER_CODES = {
    0, 63, 64, 65, 81, 82, 83, 87, 88, 111, 112, 121, 122, 123, 124, 131, 141, 142, 143, 152, 190, 195,
}

# Agricultural land-use or non-crop cover classes (excluded from crop species diversity)
AG_NON_CROP_CODES = {
    61,   # Fallow/Idle Cropland (management state, not a crop species)
    176,  # Grassland/Pasture (perennial forage/cover, not a cultivated annual crop)
}

# Combined set of classes excluded from crop species rotation metrics
NON_CROP_SPECIES_CODES = NON_AG_LANDCOVER_CODES | AG_NON_CROP_CODES
NON_AG_CODES = NON_CROP_SPECIES_CODES  # backwards-compatibility alias

METHOD_DISTINCT_CROPS = MethodRef(
    method_id="cdl_distinct_crops_count", name="Distinct agricultural crop species count", version="1",
    description="Count of distinct agricultural crop species in the CDL 20-year history, excluding non-agricultural "
                "cover classes and non-crop agricultural land use (fallow, idle, pasture).",
)
METHOD_MAX_MONOCULTURE = MethodRef(
    method_id="cdl_max_monoculture_run", name="Longest same-crop monoculture run", version="1",
    description="Maximum number of consecutive calendar years with the identical cultivated crop species in the CDL "
                "sequence. Intervening fallow, pasture, non-crop cover, or missing years interrupt the run.",
)
METHOD_ROTATION_SHANNON = MethodRef(
    method_id="cdl_rotation_shannon_index", name="Shannon rotation diversity index", version="1",
    description="Shannon diversity index H' = -sum(p_i * ln(p_i)) calculated over the sequence of cultivated crop "
                "species years.",
)
METHOD_PENDING_ROTATION = METHOD_ROTATION_SHANNON


def zonal_histogram(raster_path, geom_5070: BaseGeometry) -> tuple[Counter, int, int, float]:
    """Returns (class counts excluding 0, total pixels in polygon, background pixels, native resolution m)."""
    with rasterio.open(raster_path) as src:
        geom = geom_5070
        if src.crs is not None and src.crs.to_epsg() != 5070:
            geom = reproject(geom_5070, "EPSG:5070", src.crs.to_string())
        minx, miny, maxx, maxy = geom.bounds
        pad = abs(src.res[0])
        win = from_bounds(minx - pad, miny - pad, maxx + pad, maxy + pad, transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win, boundless=True, fill_value=0)
        tr = src.window_transform(win)
        inside = geometry_mask([geom], out_shape=arr.shape, transform=tr, invert=True, all_touched=False)
        vals = arr[inside]
        total = int(vals.size)
        background = int(np.count_nonzero(vals == 0))
        counts = Counter(int(v) for v in vals[vals != 0])
        return counts, total, background, float(abs(src.res[0]))


def crop_year_from_raster(year: int, raster: CdlCountyRaster, geom_5070: BaseGeometry) -> tuple[CropYear, list[str]]:
    notes: list[str] = []
    counts, total, background, res = zonal_histogram(raster.path, geom_5070)
    src = source_ref("usda_nass_cdl", product=f"CDL county GeoTIFF (fips {raster.fips})", version=str(year),
                     acquisition_id=raster.acquisition.acquisition_id, retrieved_at=raster.acquisition.retrieved_at)
    valid = sum(counts.values())
    if total == 0 or valid == 0:
        reason = "INSUFFICIENT_COVERAGE" if total == 0 else "OUTSIDE_AOI"
        return CropYear(year=year, majority=CropRef(), purity=None, histogram=[], low_purity=False,
                        native_resolution_m=res, missing_reason=reason, source=src), notes
    if background:
        notes.append(f"{year}: {background} of {total} pixels are outside the county raster (value 0) and excluded.")
    name = lambda c: raster.legend.get(c, f"CDL class {c}")  # noqa: E731
    hist = [CropShare(crop_code=c, crop_name=name(c), area_fraction=round(n / valid, 6))
            for c, n in counts.most_common()]
    major_code, major_n = counts.most_common(1)[0]
    purity = major_n / valid
    return CropYear(
        year=year, majority=CropRef(crop_code=major_code, crop_name=name(major_code)), purity=round(purity, 6),
        histogram=hist, low_purity=purity < LOW_PURITY, class_accuracy=None, csb_crop_code=None,
        agrees_with_csb=None, native_resolution_m=res, missing_reason=None, source=src,
    ), notes


def build_crop_history(
    field_id: UUID, geom_4326: BaseGeometry, first_year: int, last_year: int,
    rasters: dict[int, CdlCountyRaster | ProviderError],
) -> CropHistory:
    geom_5070, buffered = inward_buffer_5070(geom_4326, INWARD_BUFFER_M)
    flags: list[QualityFlag] = [
        QualityFlag(code="CDL_IS_CLASSIFICATION", severity="info",
                    message="CDL is a satellite-based classification, not ground truth; accuracy varies by crop."),
        QualityFlag(code="CLASS_ACCURACY_NOT_INGESTED", severity="info",
                    message="NASS state-level class accuracy is published on the CDL FAQ page and is not yet ingested; "
                            "class_accuracy is null."),
        QualityFlag(code="PIXEL_CENTRE_RULE", severity="info",
                    message="Pixels are included when their centre lies inside the polygon (no fractional coverage)."),
    ]
    if not buffered:
        flags.append(QualityFlag(code="INWARD_BUFFER_SKIPPED", severity="warning",
                                 message="The 15 m inward buffer would remove more than half of the field; the "
                                         "unbuffered polygon was used."))
    years: list[CropYear] = []
    for year in range(first_year, last_year + 1):
        r = rasters.get(year)
        if isinstance(r, CdlCountyRaster):
            try:
                cy, notes = crop_year_from_raster(year, r, geom_5070)
                for n in notes:
                    flags.append(QualityFlag(code="PIXELS_OUTSIDE_COUNTY", severity="warning", message=n))
            except Exception as exc:  # unreadable raster -> that year only
                cy = _missing_year(year, "UPSTREAM_ERROR")
                flags.append(QualityFlag(code="RASTER_READ_ERROR", severity="warning", message=f"{year}: {exc}"))
        else:
            reason = r.missing_reason if isinstance(r, ProviderError) else "PENDING_PROCESSING"
            cy = _missing_year(year, reason)
            if isinstance(r, ProviderError):
                flags.append(QualityFlag(code="YEAR_UNAVAILABLE", severity="warning", message=f"{year}: {r}"))
        years.append(cy)

    n_ok = sum(1 for y in years if y.missing_reason is None)
    n_low = sum(1 for y in years if y.low_purity)
    if n_low:
        flags.append(QualityFlag(code="LOW_PURITY_YEARS", severity="warning",
                                 message=f"{n_low} year(s) have majority-class purity below 0.6."))
    completeness = n_ok / len(years) if years else 0.0
    status = "valid" if n_ok == len(years) else ("partial" if n_ok else "missing")
    spatial = SPATIAL["usda_nass_cdl"]
    if not buffered:
        spatial = spatial.model_copy(update={"extraction_method": "zonal_polygon"})

    valid_years = [y for y in years if y.missing_reason is None and y.majority.crop_code is not None]
    ag_crop_years = [y for y in valid_years if y.majority.crop_code not in NON_CROP_SPECIES_CODES]
    ag_crops = [y.majority.crop_code for y in ag_crop_years]

    non_crop_years = [y.year for y in valid_years if y.majority.crop_code in AG_NON_CROP_CODES]
    if non_crop_years:
        flags.append(QualityFlag(
            code="NON_CROP_LAND_USE_OBSERVED", severity="info",
            message=f"{len(non_crop_years)} year(s) ({', '.join(str(y) for y in non_crop_years)}) classified as "
                    "agricultural non-crop land use (fallow/pasture); excluded from crop species diversity.",
        ))

    distinct_val: int | None = None
    max_run_val: int | None = None
    shannon_val: float | None = None

    if ag_crops:
        distinct_val = len(set(ag_crops))

        # Monoculture run: consecutive calendar years with identical cultivated crop species.
        # Intervening non-crop, pasture, fallow, or missing years interrupt the run.
        max_run = 0
        cur_run = 0
        prev_crop = None
        prev_year = None
        for y in years:
            if y.missing_reason is not None:
                cur_run = 0
                prev_crop = None
                prev_year = None
                continue
            c = y.majority.crop_code
            if c is None or c in NON_CROP_SPECIES_CODES:
                cur_run = 0
                prev_crop = None
                prev_year = y.year
                continue
            if c == prev_crop and prev_year is not None and y.year == prev_year + 1:
                cur_run += 1
            else:
                cur_run = 1
                prev_crop = c
            prev_year = y.year
            if cur_run > max_run:
                max_run = cur_run
        max_run_val = max_run

        counts = Counter(ag_crops)
        total_ag = len(ag_crops)
        shannon = -sum((cnt / total_ag) * math.log(cnt / total_ag) for cnt in counts.values())
        shannon_val = round(shannon, 3)

    metric_specs = [
        ("distinct_crops", "Distinct crops", "count", distinct_val, METHOD_DISTINCT_CROPS),
        ("max_monoculture_run", "Longest same-crop run", "year", max_run_val, METHOD_MAX_MONOCULTURE),
        ("rotation_shannon", "Rotation diversity (Shannon)", "unitless", shannon_val, METHOD_ROTATION_SHANNON),
    ]

    summary_src = source_ref(
        "usda_nass_cdl",
        product="CDL time series",
        version=f"{first_year}–{last_year}",
    )

    metrics = []
    for key, label, unit, val, method in metric_specs:
        if val is not None:
            q = Quantity(value=float(val) if unit == "unitless" else val, unit=unit)
            quality_info = QualityInfo(status="valid" if n_ok == len(years) else "partial",
                                       completeness=round(completeness, 4))
            srcs = [summary_src]
        else:
            reason = "INSUFFICIENT_COVERAGE" if n_ok > 0 else "UPSTREAM_ERROR"
            q = Quantity(value=None, unit=unit, missing_reason=reason)
            quality_info = QualityInfo(status="missing", completeness=round(completeness, 4), missing_reason=reason)
            srcs = []
        metrics.append(
            EnvironmentalIndicator(
                indicator_id=f"{field_id}:{key}:{first_year}-01-01", key=key, label=label, category="rotation",
                value=q, nature="derived", spatial=spatial,
                temporal=TemporalSupport(resolution="P1Y", period_start=f"{first_year}-01-01",
                                         period_end=f"{last_year}-12-31", aggregation="none",
                                         time_standard="not_applicable"),
                quality=quality_info, sources=srcs, method=method, input_ids=[],
            )
        )
    return CropHistory(
        field_id=field_id, period=YearPeriod(start_year=first_year, end_year=last_year), years=years, metrics=metrics,
        spatial=spatial,
        quality=QualityInfo(status=status, flags=flags, completeness=round(completeness, 4),
                            missing_reason=None if n_ok else "UPSTREAM_ERROR"),
    )


def _missing_year(year: int, reason: str) -> CropYear:
    return CropYear(year=year, majority=CropRef(), purity=None, histogram=[], low_purity=False,
                    native_resolution_m=None, missing_reason=reason,
                    source=source_ref("usda_nass_cdl", version=str(year)))
