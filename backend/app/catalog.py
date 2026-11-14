"""Static catalog: dataset register, AOIs and dataset spatial supports.

Dataset descriptors are real metadata transcribed from docs/DATASET_SOURCE_REGISTER.md (the same values the
frontend's `src/services/mock/catalog.ts` uses). They describe datasets, not observations.
`integration_status` reflects THIS backend: only datasets with a working provider module are "integrated".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.contracts import (
    DatasetDescriptor,
    DatasetId,
    SourceRef,
    SpatialSupport,
    TemporalRange,
)

LAST_VERIFIED = date(2026, 11, 14)

# Datasets with a provider module in app/providers (Phase 2, first real-data increment).
INTEGRATED: frozenset[str] = frozenset(
    {"nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "nasa_srtm_gl1"}
)


def _d(dataset_id, title, publisher, product, version, priority, support, res, tres, start, end, url, doi, vstatus):
    return DatasetDescriptor(
        dataset_id=dataset_id,
        title=title,
        publisher=publisher,
        product=product,
        product_version=version,
        priority=priority,
        support_class=support,
        native_resolution_m=res,
        temporal_resolution=tres,
        temporal_coverage=TemporalRange(
            start=date.fromisoformat(start) if start else None, end=date.fromisoformat(end) if end else None
        ),
        documentation_url=url,
        doi=doi,
        verification_status=vstatus,
        last_verified=LAST_VERIFIED,
        integration_status="integrated" if dataset_id in INTEGRATED else "planned",
    )


DATASETS: list[DatasetDescriptor] = [
    _d("nasa_power_daily_ag", "NASA POWER Daily (AG community)", "NASA LaRC", "POWER Daily API", "v2.10.3", "P0", "R",
       55000, "P1D", "1981-01-01", None, "https://power.larc.nasa.gov/docs/services/api/temporal/daily/", None, "LIVE"),
    _d("usda_nrcs_ssurgo_sda", "SSURGO via Soil Data Access", "USDA NRCS", "SSURGO (SDA)", "live database", "P0", "F",
       None, "static", None, None, "https://sdmdataaccess.sc.egov.usda.gov/", None, "LIVE"),
    _d("usda_nass_cdl", "Cropland Data Layer (CropScape)", "USDA NASS", "CDL", "2006–2025 (KS)", "P0", "F", 30,
       "P1Y", "2006-01-01", "2025-12-31", "https://nassgeodata.gmu.edu/CropScape/devhelp/getexamples.html", None, "LIVE"),
    _d("usda_nass_csb", "Crop Sequence Boundaries", "USDA NASS", "CSB 2018–2025 rev23", "rev23", "P0", "F", None,
       "P1Y", "2018-01-01", "2025-12-31", "https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries",
       None, "DOC"),
    _d("nasa_hls_vi", "HLS Vegetation Indices (L30/S30)", "NASA LP DAAC", "HLSL30_VI / HLSS30_VI", "2.0", "P0", "F",
       30, "irregular", "2013-04-11", None, "https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-vi-2.0",
       "10.5067/HLS/HLSL30_VI.002", "LIVE"),
    _d("nasa_hls", "HLS Surface Reflectance (L30/S30)", "NASA LP DAAC", "HLSL30 / HLSS30", "2.0", "P0", "F", 30,
       "irregular", "2013-04-11", None, "https://www.earthdata.nasa.gov/data/projects/hls", None, "CMR"),
    _d("nasa_smap_spl4smgp", "SMAP L4 Surface & Root-Zone Soil Moisture", "NASA NSIDC DAAC", "SPL4SMGP", "008", "P0",
       "R", 9000, "PT3H", "2015-03-31", None, "https://nsidc.org/data/spl4smgp", None, "CMR"),
    _d("nasa_srtm_gl1", "SRTM Global 1 arc-second", "NASA LP DAAC", "SRTMGL1", "003", "P0", "F", 30, "static",
       "2000-02-11", "2000-02-21", "https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003",
       "10.5067/MEaSUREs/SRTM/SRTMGL1.003", "CMR"),
    _d("prism_daily", "PRISM daily climate", "PRISM Group, Oregon State University", "PRISM daily (4 km / 800 m)",
       "post-2025-10 COG", "P1", "S", 4000, "P1D", "1981-01-01", None, "https://prism.oregonstate.edu/", None, "LIVE"),
    _d("openet", "OpenET Ensemble ET", "OpenET consortium", "OpenET Collection", "2.1", "P1", "F", 30, "P1M",
       "2000-01-01", None, "https://openet.gitbook.io/docs", None, "DOC"),
    _d("usda_nass_quickstats", "NASS Quick Stats", "USDA NASS", "Quick Stats API", "api_GET", "P1", "R", None, "P1Y",
       None, None, "https://quickstats.nass.usda.gov/api", None, "LIVE"),
    _d("nasa_smap_spl3smp_e", "SMAP L3 Enhanced Soil Moisture", "NASA NSIDC DAAC", "SPL3SMP_E", "006", "P1", "R",
       9000, "P1D", "2015-03-31", None, "https://nsidc.org/data/SPL3SMP_E", None, "CMR"),
    _d("nasa_gpm_imerg", "GPM IMERG Final daily", "NASA GES DISC", "GPM_3IMERGDF", "07", "P2", "R", 11000, "P1D",
       "1998-01-01", "2025-09-30",
       "https://catalog.data.gov/dataset/gpm-imerg-final-precipitation-l3-1-day-0-1-degree-x-0-1-degree-v07-gpm-3imergdf-at-ges-dis-f1669",
       None, "CMR"),
    _d("fao_gaez_v5", "FAO GAEZ v5 crop suitability", "FAO + IIASA", "GAEZ v5", "v5", "P2", "R", 1000, "static",
       None, None, "https://www.fao.org/gaez/en/", None, "DOC"),
]

_BY_ID = {d.dataset_id: d for d in DATASETS}


def descriptor(dataset_id: DatasetId) -> DatasetDescriptor:
    return _BY_ID[dataset_id]


def source_ref(dataset_id: DatasetId, *, product: str | None = None, version: str | None = None,
               acquisition_id=None, retrieved_at=None) -> SourceRef:
    d = _BY_ID[dataset_id]
    return SourceRef(
        dataset_id=dataset_id,
        product=product or d.product,
        product_version=version or d.product_version,
        acquisition_id=acquisition_id,
        doi=d.doi,
        documentation_url=d.documentation_url,
        retrieved_at=retrieved_at,
    )


# Spatial support per dataset (DATA_ARCHITECTURE §5.4). POWER: api_point_query, no claim about interpolation.
POWER_MET_RES_M = 55000.0  # ~0.5° x 0.625° MERRA-2 grid
POWER_SOLAR_RES_M = 111000.0  # ~1° x 1° CERES SYN1deg grid

SPATIAL: dict[str, SpatialSupport] = {
    "nasa_power_daily_ag": SpatialSupport(support_class="R", native_resolution_m=POWER_MET_RES_M,
                                          extraction_method="api_point_query", crs="EPSG:4326"),
    "usda_nrcs_ssurgo_sda": SpatialSupport(support_class="F", native_resolution_m=None,
                                           extraction_method="vector_intersection", crs="EPSG:4326"),
    "usda_nass_cdl": SpatialSupport(support_class="F", native_resolution_m=30.0,
                                    extraction_method="zonal_polygon_inward_buffer", crs="EPSG:5070"),
    "nasa_srtm_gl1": SpatialSupport(support_class="F", native_resolution_m=30.0, extraction_method="zonal_polygon",
                                    crs="EPSG:4326"),
    "nasa_hls_vi": SpatialSupport(support_class="F", native_resolution_m=30.0,
                                  extraction_method="zonal_polygon_inward_buffer", crs="EPSG:32614"),
    "nasa_hls": SpatialSupport(support_class="F", native_resolution_m=30.0,
                               extraction_method="zonal_polygon_inward_buffer", crs="EPSG:32614"),
    "nasa_smap_spl4smgp": SpatialSupport(support_class="R", native_resolution_m=9000.0,
                                         extraction_method="containing_cell", crs="EPSG:6933"),
    "nasa_smap_spl3smp_e": SpatialSupport(support_class="R", native_resolution_m=9000.0,
                                          extraction_method="containing_cell", crs="EPSG:6933"),
    "usda_nass_csb": SpatialSupport(support_class="F", native_resolution_m=None,
                                    extraction_method="vector_intersection", crs="EPSG:5070"),
}


# ── AOIs (PHASE_0 D2, T20) ─────────────────────────────────────────────────


@dataclass(frozen=True)
class AoiDef:
    aoi_id: str
    label: str
    county_fips: str  # 5-digit
    farm_name: str
    # Approximate county extent [W, S, E, N] (same values as src/lib/aoi.ts). Authoritative-enough for MVP;
    # see handover D2: a TIGER county polygon would be exact.
    bbox: tuple[float, float, float, float]


AOIS: dict[str, AoiDef] = {
    "ks_reno": AoiDef("ks_reno", "Reno County, Kansas", "20155", "Reno Farm", (-98.472, 37.732, -97.698, 38.173)),
    "ks_finney": AoiDef("ks_finney", "Finney County, Kansas", "20055", "Finney Farm",
                        (-101.103, 37.732, -100.215, 38.264)),
}

MAX_FIELD_HA = 260.0

# ── Candidate crops (DATA_ARCHITECTURE §5.11) — CDL legend names, NOT a knowledge base ───────────────
# Served by E20 only while no cited crop KB is configured. Carries no agronomic thresholds.
CDL_CANDIDATE_CROPS: list[tuple[int, str, bool]] = [
    (24, "Winter Wheat", False),
    (1, "Corn", False),
    (4, "Sorghum", False),
    (5, "Soybeans", False),
    (36, "Alfalfa", False),
    (26, "Dbl Crop WinWht/Soybeans", True),
    (236, "Dbl Crop WinWht/Sorghum", True),
    (61, "Fallow/Idle Cropland", False),
]
