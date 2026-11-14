"""Unit tests for USDA NASS Crop Sequence Boundaries (CSB) provider."""

from __future__ import annotations

from app.providers.csb import validate_csb_record


def test_csb_reliable_crop_field_passes():
    # Polygon in WGS84 around Reno County KS
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [-98.05, 37.95],
                [-98.04, 37.95],
                [-98.04, 37.94],
                [-98.05, 37.94],
                [-98.05, 37.95],
            ]
        ],
    }
    # 8 years of crops (Wheat 24, Corn 1, Soybeans 5)
    raw = {
        "CSBID": "20182025201550001",
        "STATEFIPS": "20",
        "CNTYFIPS": "155",
        "CSBACRES": 75.5,
        "CDL2018": 24,
        "CDL2019": 5,
        "CDL2020": 24,
        "CDL2021": 1,
        "CDL2022": 24,
        "CDL2023": 5,
        "CDL2024": 24,
        "CDL2025": 1,
        "geometry": geom,
    }

    rec = validate_csb_record(raw)
    assert rec.csb_id == "20182025201550001"
    assert rec.state_fips == "20"
    assert rec.county_fips == "155"
    assert rec.acres == 75.5
    assert rec.area_ha == round(75.5 * 0.404686, 2)
    assert rec.is_reliable is True
    assert rec.rejection_reason is None
    assert len(rec.crop_years) == 8


def test_csb_unreliable_when_non_crop():
    # 5 out of 8 years are grass/pasture (176) or water (111) -> only 3 crop years -> unreliable
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [-98.05, 37.95],
                [-98.04, 37.95],
                [-98.04, 37.94],
                [-98.05, 37.94],
                [-98.05, 37.95],
            ]
        ],
    }
    raw = {
        "CSBID": "20182025201550002",
        "STATEFIPS": "20",
        "CNTYFIPS": "155",
        "CSBACRES": 50.0,
        "CDL2018": 176,
        "CDL2019": 176,
        "CDL2020": 176,
        "CDL2021": 176,
        "CDL2022": 176,
        "CDL2023": 24,
        "CDL2024": 5,
        "CDL2025": 24,
        "geometry": geom,
    }

    rec = validate_csb_record(raw)
    assert rec.is_reliable is False
    assert "crop cultivation" in (rec.rejection_reason or "")


def test_csb_sub_10_acres_rejected():
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [-98.05, 37.95],
                [-98.04, 37.95],
                [-98.04, 37.94],
                [-98.05, 37.94],
                [-98.05, 37.95],
            ]
        ],
    }
    raw = {
        "CSBID": "20182025201550003",
        "STATEFIPS": "20",
        "CNTYFIPS": "155",
        "CSBACRES": 5.2,  # < 10 acres
        "CDL2018": 24,
        "CDL2019": 5,
        "CDL2020": 24,
        "CDL2021": 1,
        "CDL2022": 24,
        "CDL2023": 5,
        "CDL2024": 24,
        "CDL2025": 1,
        "geometry": geom,
    }

    rec = validate_csb_record(raw)
    assert rec.is_reliable is False
    assert "below 10-acre minimum" in (rec.rejection_reason or "")
