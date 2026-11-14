"""Shared test fixtures.

EVERYTHING HERE IS SYNTHETIC TEST DATA. Fake providers return hand-made payloads in the real upstream formats so
that parsing and processing are exercised without network access. None of these values are observations and none
are ever written outside the test's temporary directories.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

from app.analytics.resilience import PendingResilienceEngine
from app.config import Settings
from app.main import create_app
from app.processing.geometry import reproject
from app.providers.cdl import CdlCountyRaster
from app.providers.http import ProviderError, ProviderNotConfigured
from app.providers.power import PowerDaily
from app.providers.srtm import SrtmTile, hgt_to_geotiff
from app.providers.ssurgo import SsurgoRaw
from app.repositories import Repositories, SqliteDocumentStore
from app.repositories.records import AcquisitionRecord
from app.rotation.engine import PendingRotationEngine
from app.rotation.kb import load_kb
from app.services.container import Container, Providers

# A ~97 ha square near the Reno County test point (KS-RENO-PT), EPSG:4326.
RENO_SQUARE = [[[[-98.055, 37.945], [-98.045, 37.945], [-98.045, 37.955], [-98.055, 37.955], [-98.055, 37.945]]]]


def acq(dataset_id: str) -> AcquisitionRecord:
    return AcquisitionRecord(acquisition_id=uuid.uuid4(), dataset_id=dataset_id, request_url="https://synthetic.test/",
                             http_status=200, sha256="0" * 64, bytes=0, retrieved_at=datetime.now(UTC))


def synthetic_ssurgo_raw() -> SsurgoRaw:
    """Two map units, three major components. Horizons cover 0–150 cm."""
    def hz(top, bottom, sand, silt, clay, om, ph, awc):
        h = {"top": top, "bottom": bottom}
        for p, v in [("sandtotal", sand), ("silttotal", silt), ("claytotal", clay), ("om", om), ("ph1to1h2o", ph),
                     ("awc", awc)]:
            h[f"{p}_l"], h[f"{p}_r"], h[f"{p}_h"] = v * 0.9, v, v * 1.1
        return h

    return SsurgoRaw(
        mapunit_area_m2={"100": 750_000.0, "200": 250_000.0},
        mapunit_names={"100": "Synthetic loam", "200": "Synthetic clay complex"},
        components=[
            {"mukey": "100", "cokey": "c1", "compname": "SynA", "comppct_r": 80.0, "drainagecl": "Well drained",
             "hydgrp": "B"},
            {"mukey": "200", "cokey": "c2", "compname": "SynB", "comppct_r": 60.0, "drainagecl": "Poorly drained",
             "hydgrp": "D"},
            {"mukey": "200", "cokey": "c3", "compname": "SynC", "comppct_r": 30.0, "drainagecl": "Well drained",
             "hydgrp": "C"},
        ],
        horizons={
            "c1": [hz(0, 20, 40, 40, 20, 2.0, 6.5, 0.18), hz(20, 150, 30, 40, 30, 1.0, 7.0, 0.15)],
            "c2": [hz(0, 150, 10, 40, 50, 3.0, 7.5, 0.12)],
            "c3": [hz(0, 150, 60, 25, 15, 1.0, 6.0, 0.10)],
        },
        muaggatt={"100": {"aws0100wta": 16.0, "aws0150wta": 22.0, "slopegradwta": 1.0},
                  "200": {"aws0100wta": 12.0, "aws0150wta": 18.0, "slopegradwta": 3.0}},
        surveys=[("KS155", date(2026, 8, 27))],
        acquisitions=[acq("usda_nrcs_ssurgo_sda")],
    )


def synthetic_power_daily(year: int, *, fill_days: int = 0, end: date | None = None) -> PowerDaily:
    start = date(year, 1, 1)
    end = end or date(year, 12, 31)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    vals = {
        "PRECTOTCORR": {d: 2.0 for d in days}, "T2M": {d: 12.0 for d in days}, "T2M_MAX": {d: 18.0 for d in days},
        "T2M_MIN": {d: 6.0 for d in days}, "RH2M": {d: 65.0 for d in days}, "ALLSKY_SFC_SW_DWN": {d: 15.0 for d in days},
    }
    fills = {k: set() for k in vals}
    for d in days[:fill_days]:
        for k in vals:
            vals[k][d] = None
            fills[k].add(d)
    return PowerDaily(longitude=-98.05, latitude=37.95, start=start, end=end, api_version="v2.10.3",
                      sources=["MERRA2", "SYN1DEG"], time_standard="LST",
                      units={"PRECTOTCORR": "mm/day", "T2M": "C", "T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%",
                             "ALLSKY_SFC_SW_DWN": "MJ/m^2/day"},
                      values=vals, fill_dates=fills, acquisition=acq("nasa_power_daily_ag"))


def write_cdl_raster(path: Path, geom_4326, code_by_column) -> Path:
    """Synthetic EPSG:5070 uint8 raster covering the geometry (+300 m). Columns are assigned classes."""
    g = reproject(geom_4326, "EPSG:4326", "EPSG:5070")
    minx, miny, maxx, maxy = g.bounds
    minx, miny, maxx, maxy = minx - 300, miny - 300, maxx + 300, maxy + 300
    w, h = int((maxx - minx) // 30) + 1, int((maxy - miny) // 30) + 1
    arr = np.zeros((h, w), dtype="uint8")
    for col in range(w):
        arr[:, col] = code_by_column(col, w)
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype="uint8", crs="EPSG:5070",
                       transform=from_origin(minx, maxy, 30, 30)) as dst:
        dst.write(arr, 1)
    return path


class FakeSsurgo:
    dataset_id = "usda_nrcs_ssurgo_sda"

    def __init__(self, fail: ProviderError | None = None):
        self.fail = fail

    def fetch_for_polygon(self, geom):
        if self.fail:
            raise self.fail
        return synthetic_ssurgo_raw()


class FakePower:
    dataset_id = "nasa_power_daily_ag"

    def __init__(self, fail: ProviderError | None = None):
        self.fail = fail

    def daily(self, lon, lat, start, end, cache=True):
        if self.fail:
            raise self.fail
        return synthetic_power_daily(start.year, end=end)


class FakeCdl:
    dataset_id = "usda_nass_cdl"

    def __init__(self, tmp: Path, fail: ProviderError | None = None):
        self.tmp, self.fail = tmp, fail

    def county_raster(self, year, fips):
        if self.fail:
            raise self.fail
        if year == 2006:
            raise ProviderError("not available", "OUT_OF_TEMPORAL_RANGE")
        from shapely.geometry import shape

        geom = shape({"type": "MultiPolygon", "coordinates": RENO_SQUARE})
        code = 24 if year % 2 else 1
        p = write_cdl_raster(self.tmp / f"cdl_{year}.tif", geom, lambda c, w: code if c < w * 0.6 else 5)
        return CdlCountyRaster(year=year, fips=fips, path=p, url="https://synthetic.test/cdl.tif",
                               acquisition=acq("usda_nass_cdl"), legend={1: "Corn", 5: "Soybeans", 24: "Winter Wheat"})


class FakeSrtm:
    dataset_id = "nasa_srtm_gl1"

    def __init__(self, tmp: Path, configured: bool = True):
        self.tmp, self.configured = tmp, configured

    def tiles_for_bounds(self, bounds):
        if not self.configured:
            raise ProviderNotConfigured("NASA Earthdata credentials are not configured.")
        # Synthetic tile N37W099: elevation rises 1 m per pixel row towards the south (a gentle plane).
        rows = np.arange(3601, dtype="float64")[:, None]
        arr = (400 + rows * 1.0 + np.zeros((1, 3601))).astype("int16")  # ~1 m per ~30.9 m => ~3.2 % slope
        p = hgt_to_geotiff(arr, "N37W099", self.tmp / "N37W099.tif")
        return [SrtmTile(name="N37W099", path=p, acquisition=acq("nasa_srtm_gl1"))]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(environment="test", db_path=":memory:", cache_dir=tmp_path / "cache", job_execution="inline",
                    http_retries=0, http_backoff_base_s=0.0, cdl_first_year=2006, cdl_last_year=2010,
                    climate_default_season_year=2024, rate_limit_writes_per_minute=0, log_level="WARNING",
                    _env_file=None)


def make_container(settings: Settings, providers: Providers) -> Container:
    return Container(settings=settings, repos=Repositories.create(SqliteDocumentStore(":memory:")),
                     providers=providers, kb=load_kb(None), resilience=PendingResilienceEngine(),
                     rotation=PendingRotationEngine(), executor=None)


@pytest.fixture
def fake_providers(tmp_path) -> Providers:
    return Providers(power=FakePower(), ssurgo=FakeSsurgo(), cdl=FakeCdl(tmp_path), srtm=FakeSrtm(tmp_path))


@pytest.fixture
def client_factory(settings):
    def factory(providers: Providers, **overrides):
        s = settings.model_copy(update=overrides) if overrides else settings
        container = make_container(s, providers)
        app = create_app(s, container)
        return TestClient(app), container
    return factory


@pytest.fixture
def client(client_factory, fake_providers):
    c, container = client_factory(fake_providers)
    with c:
        yield c


def reno_farm_id(client) -> str:
    farms = client.get("/api/v1/farms").json()["data"]
    return next(f["farm_id"] for f in farms if f["aoi"]["aoi_id"] == "ks_reno")


def create_reno_field(client, name="Test field", coords=None):
    return client.post(f"/api/v1/farms/{reno_farm_id(client)}/fields",
                       json={"name": name, "geometry": {"type": "MultiPolygon", "coordinates": coords or RENO_SQUARE}})
