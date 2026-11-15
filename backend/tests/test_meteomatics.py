"""Unit and integration tests for Meteomatics provider and environmental pipelines."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest
import respx
import httpx
from shapely.geometry import Polygon

from app.providers.http import HttpAcquirer, ProviderError
from app.providers.meteomatics import (
    BASE_URL,
    MeteomaticsClient,
    MeteomaticsError,
    SOIL_MOISTURE_PARAMETERS,
    format_iso,
    sanitize_value,
)
from app.processing.soil_moisture import (
    compute_depth_weighted_rootzone,
    build_soil_moisture_profile,
)
from app.processing.terrain import (
    evaluate_spatial_adequacy,
    compute_horn_slope_p90,
    build_terrain_profile_from_meteomatics,
)
from app.processing.vegetation import (
    build_regional_ndvi_profile_from_meteomatics,
)


# ───────────── Client Tests ─────────────

def test_format_iso():
    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
    assert format_iso(dt) == "2025-06-15T12:00:00Z"
    d = date(2025, 6, 15)
    assert format_iso(d) == "2025-06-15T00:00:00Z"
    s = "2025-06-15T12:00:00Z"
    assert format_iso(s) == s


def test_sanitize_value():
    assert sanitize_value(0.31) == 0.31
    assert sanitize_value("0.32") == 0.32
    assert sanitize_value(-999) is None
    assert sanitize_value(-9999.0) is None
    assert sanitize_value(None) is None
    assert sanitize_value(float("nan")) is None


def test_meteomatics_client_headers_and_auth(tmp_path):
    http = HttpAcquirer(tmp_path)
    client = MeteomaticsClient(http, lambda: ("test_user", "test_pass"))
    headers = client._get_auth_header()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")


@respx.mock
def test_meteomatics_point_query(tmp_path):
    http = HttpAcquirer(tmp_path)
    client = MeteomaticsClient(http, lambda: ("user", "pass"))

    fake_response = {
        "version": "3.0",
        "user": "user",
        "dateGenerated": "2025-06-15T12:00:00Z",
        "status": "OK",
        "data": [
            {
                "parameter": "volumetric_soil_water_-5cm:m3m3",
                "coordinates": [
                    {
                        "lat": 37.95,
                        "lon": -98.05,
                        "dates": [{"date": "2025-06-15T12:00:00Z", "value": 0.31}],
                    }
                ],
            },
            {
                "parameter": "elevation:m",
                "coordinates": [
                    {
                        "lat": 37.95,
                        "lon": -98.05,
                        "dates": [{"date": "2025-06-15T12:00:00Z", "value": 465.0}],
                    }
                ],
            },
        ],
    }

    respx.get(url__startswith=BASE_URL).respond(status_code=200, json=fake_response)

    res = client.query_point(
        lat=37.95,
        lon=-98.05,
        timestamp=datetime(2025, 6, 15, 12, 0, tzinfo=UTC),
        parameters=["volumetric_soil_water_-5cm:m3m3", "elevation:m"],
    )

    assert res["volumetric_soil_water_-5cm:m3m3"] == 0.31
    assert res["elevation:m"] == 465.0


@respx.mock
def test_meteomatics_error_categorization(tmp_path):
    http = HttpAcquirer(tmp_path)
    client = MeteomaticsClient(http, lambda: ("user", "wrong_pass"))

    respx.get(url__startswith=BASE_URL).respond(status_code=401, text="Unauthorized access")

    with pytest.raises(MeteomaticsError) as exc_info:
        client.query_point(
            lat=37.95,
            lon=-98.05,
            timestamp=datetime(2025, 6, 15, 12, 0, tzinfo=UTC),
            parameters=["elevation:m"],
        )

    err = exc_info.value
    assert err.category in ("auth_failure", "AUTHENTICATION_FAILURE")
    assert err.http_status == 401
    # Secret must never be in exception message
    assert "wrong_pass" not in str(err)


# ───────────── Soil Moisture Pipeline Tests ─────────────

def test_depth_weighted_rootzone_formula():
    # Defensible weights: 0.10 for 5cm, 0.20 for 15cm, 0.70 for 50cm
    val = compute_depth_weighted_rootzone(0.30, 0.35, 0.40)
    expected = round(0.10 * 0.30 + 0.20 * 0.35 + 0.70 * 0.40, 4)
    assert math.isclose(val, expected, rel_tol=1e-5)
    assert val == 0.38


def test_build_soil_moisture_profile_offline(fake_providers):
    geom = Polygon([[-98.055, 37.945], [-98.045, 37.945], [-98.045, 37.955], [-98.055, 37.955]])
    fid = uuid4()
    profile = build_soil_moisture_profile(
        field_id=fid,
        geom=geom,
        season_year=2025,
        client=fake_providers.meteomatics,
    )

    assert profile.field_id == fid
    assert profile.season_year == 2025
    assert profile.surface_sm.mean.value is not None and profile.surface_sm.mean.value > 0.0
    assert profile.shallow_sm.mean.value is not None and profile.shallow_sm.mean.value > 0.0
    assert profile.middepth_sm.mean.value is not None and profile.middepth_sm.mean.value > 0.0
    assert profile.deep_sm.mean.value is not None and profile.deep_sm.mean.value > 0.0
    assert profile.rootzone_sm_composite.value is not None and profile.rootzone_sm_composite.value > 0.0

    # Unified environmental metric checks
    assert len(profile.metrics) > 0
    rz_m = next(m for m in profile.metrics if m.metric == "rootzone_soil_moisture")
    assert rz_m.unit in ("m3/m3", "m3_m-3")
    assert rz_m.status == "available"
    assert rz_m.value is not None


# ───────────── Terrain & Spatial Adequacy Tests ─────────────

def test_spatial_adequacy_evaluation():
    # 3x3 adequate grid with variance
    grid_ok = [
        [460.0, 461.0, 462.0],
        [461.0, 463.0, 465.0],
        [463.0, 465.0, 468.0],
    ]
    res_ok = evaluate_spatial_adequacy(grid_ok)
    assert res_ok["adequate"] is True
    p90 = compute_horn_slope_p90(grid_ok)
    assert p90 is not None
    assert p90 > 0.0

    # Flat grid with zero variance -> should be withheld
    grid_flat = [
        [465.0, 465.0, 465.0],
        [465.0, 465.0, 465.0],
        [465.0, 465.0, 465.0],
    ]
    res_flat = evaluate_spatial_adequacy(grid_flat)
    assert res_flat["adequate"] is False
    assert compute_horn_slope_p90(grid_flat) is None

    # Too small grid (< 9 cells) -> withheld
    grid_small = [[460.0, 461.0], [462.0, 463.0]]
    res_small = evaluate_spatial_adequacy(grid_small)
    assert res_small["adequate"] is False
    assert compute_horn_slope_p90(grid_small) is None


def test_build_terrain_profile_from_meteomatics(fake_providers):
    geom = Polygon([[-98.055, 37.945], [-98.045, 37.945], [-98.045, 37.955], [-98.055, 37.955]])
    fid = uuid4()
    terrain = build_terrain_profile_from_meteomatics(
        field_id=fid,
        geom_4326=geom,
        client=fake_providers.meteomatics,
    )

    assert terrain.field_id == fid
    assert terrain.elevation_mean.value is not None
    assert terrain.elevation_mean.value > 400.0
    assert terrain.elevation_min.value <= terrain.elevation_max.value


# ───────────── Regional NDVI Tests ─────────────

def test_build_regional_ndvi_profile_from_meteomatics(fake_providers):
    geom = Polygon([[-98.055, 37.945], [-98.045, 37.945], [-98.045, 37.955], [-98.055, 37.955]])
    fid = uuid4()
    veg = build_regional_ndvi_profile_from_meteomatics(
        field_id=fid,
        geom=geom,
        year=2025,
        client=fake_providers.meteomatics,
    )

    assert veg.field_id == fid
    assert veg.year == 2025
    assert veg.index == "NDVI"
    assert veg.spatial.support_class == "R"
    assert len(veg.scenes) > 0
    # Canopy stability model is withheld for regional NDVI
    assert veg.phenology.greenup_date is None
    assert veg.phenology.senescence_date is None
    assert any(flag.code == "REGIONAL_VEGETATION_CONTEXT" for flag in veg.quality.flags)
