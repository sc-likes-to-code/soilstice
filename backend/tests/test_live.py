"""LIVE smoke tests against real upstream services. Deselected by default; run: pytest -m live.

Expected values come from the Phase 0/2 live checks at KS-RENO-PT (INTEGRATION_GUIDE §0.1).
"""

from __future__ import annotations

import os
from datetime import date

import pytest
from shapely.geometry import box

from app.processing.climate import build_climate_profile
from app.processing.soil import aggregate_soil
from app.providers.cdl import CdlClient
from app.providers.http import EarthdataAuth, HttpAcquirer
from app.providers.power import PowerClient
from app.providers.srtm import SrtmClient
from app.providers.ssurgo import SsurgoClient

pytestmark = pytest.mark.live
SQUARE = box(-98.055, 37.945, -98.045, 37.955)


@pytest.fixture
def http(tmp_path):
    return HttpAcquirer(tmp_path, retries=2, backoff_base_s=1.0)


def test_live_ssurgo(http):
    import uuid

    p = aggregate_soil(uuid.uuid4(), SsurgoClient(http).fetch_for_polygon(SQUARE))
    assert "1443836" in {m.mukey for m in p.map_units}
    assert 18 < p.aws_0_150.value < 25 and p.drainage_class.value == "Well drained"


def test_live_power(http):
    import uuid

    d = PowerClient(http).daily(-98.05, 37.95, date(2024, 1, 1), date(2024, 12, 31))
    prof = build_climate_profile(uuid.uuid4(), 2024, None, d)
    assert prof.quality.completeness == 1.0 and d.api_version.startswith("v2")


def test_live_cdl_county_file(http):
    r = CdlClient(http).county_raster(2025, "20155")
    assert r.path.exists() and r.legend.get(1) == "Corn"


@pytest.mark.skipif(not os.environ.get("SOILSTICE_EARTHDATA_TOKEN"), reason="needs SOILSTICE_EARTHDATA_TOKEN")
def test_live_srtm(http, tmp_path):
    c = SrtmClient(http, tmp_path, lambda: EarthdataAuth(token=os.environ["SOILSTICE_EARTHDATA_TOKEN"]))
    assert c.tiles_for_bounds(SQUARE.bounds)
