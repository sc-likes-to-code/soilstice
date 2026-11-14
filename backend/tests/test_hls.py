"""Unit and contract tests for NASA HLS & HLS-VI provider and processing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np

from app.contracts import VegetationProfile
from app.processing.vegetation import (
    build_vegetation_profile_from_stac,
    compute_evi2,
    compute_ndvi,
    parse_fmask,
)
from app.providers.hls import HlsClient, HlsStacScene


def test_fmask_bitmask_parsing():
    # Construct a 10x10 test array
    # Pixel 0: Clear (0)
    # Pixel 1: Cloud (bit 1 = 2)
    # Pixel 2: Cloud adjacent (bit 2 = 4)
    # Pixel 3: Cloud shadow (bit 3 = 8)
    # Pixel 4: Snow/ice (bit 4 = 16)
    # Pixel 5: Water (bit 5 = 32)
    # Remaining 94 pixels: Clear (0)
    arr = np.zeros(100, dtype=np.uint8)
    arr[1] = 1 << 1  # cloud
    arr[2] = 1 << 2  # adjacent
    arr[3] = 1 << 3  # shadow
    arr[4] = 1 << 4  # snow
    arr[5] = 1 << 5  # water

    counts, valid, total, clear_frac, accepted = parse_fmask(arr)
    assert total == 100
    assert counts.cloud == 1
    assert counts.cloud_adjacent == 1
    assert counts.cloud_shadow == 1
    assert counts.snow_ice == 1
    assert counts.water == 1
    assert valid == 95
    assert clear_frac == 0.95
    assert accepted is True  # >= 0.70


def test_fmask_unaccepted_when_cloudy():
    # 50 cloud pixels out of 100 -> clear_frac = 0.50 -> accepted = False
    arr = np.zeros(100, dtype=np.uint8)
    arr[:50] = 1 << 1
    counts, valid, total, clear_frac, accepted = parse_fmask(arr)
    assert counts.cloud == 50
    assert valid == 50
    assert clear_frac == 0.50
    assert accepted is False


def test_ndvi_and_evi2_computation():
    # NIR = 8000 (0.80), Red = 2000 (0.20)
    # NDVI = (0.80 - 0.20) / (0.80 + 0.20) = 0.60 / 1.00 = 0.60
    nir = np.array([8000], dtype=np.int16)
    red = np.array([2000], dtype=np.int16)

    ndvi = compute_ndvi(nir, red)
    assert np.isclose(ndvi[0], 0.60, atol=1e-3)

    # EVI2 = 2.5 * (NIR - Red) / (NIR + 2.4*Red + 1.0)
    # NIR = 0.8, Red = 0.2 -> 2.5 * 0.6 / (0.8 + 0.48 + 1.0) = 1.5 / 2.28 ≈ 0.6579
    evi2 = compute_evi2(nir, red)
    assert np.isclose(evi2[0], 1.5 / 2.28, atol=1e-3)


def test_hls_phenology_derivation():
    field_id = uuid4()
    # 3 scenes spanning the season
    s1 = HlsStacScene(
        granule_id="G1",
        collection="HLSS30_VI_2.0",
        product="HLSS30_VI",
        acquired_at=datetime(2025, 4, 15, 17, 0, tzinfo=UTC),
        cloud_cover=5.0,
        bbox=[-98.1, 37.9, -98.0, 38.0],
    )
    s2 = HlsStacScene(
        granule_id="G2",
        collection="HLSS30_VI_2.0",
        product="HLSS30_VI",
        acquired_at=datetime(2025, 5, 20, 17, 0, tzinfo=UTC),
        cloud_cover=0.0,
        bbox=[-98.1, 37.9, -98.0, 38.0],
    )
    s3 = HlsStacScene(
        granule_id="G3",
        collection="HLSL30_VI_2.0",
        product="HLSL30_VI",
        acquired_at=datetime(2025, 7, 10, 17, 0, tzinfo=UTC),
        cloud_cover=10.0,
        bbox=[-98.1, 37.9, -98.0, 38.0],
    )

    profile = build_vegetation_profile_from_stac(field_id, 2025, "NDVI", [s1, s2, s3])
    # Validate contract model
    assert isinstance(profile, VegetationProfile)
    assert profile.field_id == field_id
    assert profile.year == 2025
    assert profile.index == "NDVI"
    assert len(profile.scenes) == 3
    assert profile.spatial.native_resolution_m == 30
    assert profile.spatial.support_class == "F"
    assert profile.scenes[0].granule_id == "G1"
    assert profile.scenes[0].clear_fraction == 0.95
    assert profile.scenes[0].accepted is True


def test_hls_client_stac_search_parsing(respx_mock, tmp_path):
    from app.providers.http import HttpAcquirer
    http = HttpAcquirer(tmp_path)
    client = HlsClient(http, tmp_path)

    # Mock CMR-STAC response
    mock_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "HLS.S30.T14SNH.2025153T170849.v2.0",
                "collection": "HLSS30_VI_2.0",
                "properties": {
                    "datetime": "2025-06-02T17:23:16.865Z",
                    "eo:cloud_cover": 4.5,
                },
                "bbox": [-98.1, 37.9, -98.0, 38.0],
                "assets": {
                    "NDVI": {"href": "https://data.lpdaac.earthdatacloud.nasa.gov/NDVI.tif"},
                    "Fmask": {"href": "https://data.lpdaac.earthdatacloud.nasa.gov/Fmask.tif"},
                },
            }
        ],
    }

    respx_mock.post("https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search").respond(200, json=mock_payload)

    scenes = client.search_scenes((-98.1, 37.9, -98.0, 38.0), "2025-06-01", "2025-06-30")
    assert len(scenes) == 1
    sc = scenes[0]
    assert sc.granule_id == "HLS.S30.T14SNH.2025153T170849.v2.0"
    assert sc.product == "HLSS30_VI"
    assert sc.cloud_cover == 4.5
    assert "NDVI" in sc.assets
    assert "Fmask" in sc.assets
