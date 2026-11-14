"""Processing functions (pure). Inputs are SYNTHETIC."""

from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pytest
from shapely.geometry import box, shape

from app.processing.climate import build_climate_profile
from app.processing.crop_history import build_crop_history, zonal_histogram
from app.processing.geometry import area_ha, inward_buffer_5070, reproject
from app.processing.soil import aggregate_soil, interval_value
from app.processing.terrain import horn_slope_pct
from app.processing.texture import usda_texture_class
from app.providers.cdl import CdlCountyRaster
from app.providers.http import ProviderError

from .conftest import RENO_SQUARE, acq, synthetic_power_daily, synthetic_ssurgo_raw, write_cdl_raster

FID = uuid.uuid4()


@pytest.mark.parametrize("sand,silt,clay,expected", [
    (92, 4, 4, "Sand"), (82, 12, 6, "Loamy sand"), (65, 25, 10, "Sandy loam"), (40, 40, 20, "Loam"),
    (20, 65, 15, "Silt loam"), (5, 88, 7, "Silt"), (60, 15, 25, "Sandy clay loam"), (30, 35, 35, "Clay loam"),
    (10, 55, 35, "Silty clay loam"), (50, 5, 45, "Sandy clay"), (5, 45, 50, "Silty clay"), (20, 20, 60, "Clay"),
])
def test_usda_texture_triangle(sand, silt, clay, expected):
    assert usda_texture_class(sand, silt, clay) == expected


def test_texture_missing_input():
    assert usda_texture_class(None, 40, 20) is None


def test_interval_value_coverage_rule():
    hz = [{"top": 0, "bottom": 20, "c": 10.0}, {"top": 20, "bottom": 30, "c": None}]
    assert interval_value(hz, 0, 30, "c") is None  # 20/30 = 67 % < 80 %
    hz[1]["c"] = 40.0
    assert interval_value(hz, 0, 30, "c") == pytest.approx((20 * 10 + 10 * 40) / 30)


def test_soil_aggregation_weights_and_classes():
    p = aggregate_soil(FID, synthetic_ssurgo_raw())
    # weights: c1 = 0.75*0.8 = 0.6, c2 = 0.25*0.6 = 0.15, c3 = 0.25*0.3 = 0.075
    w = {"c1": 0.6, "c2": 0.15, "c3": 0.075}
    c1_clay_0_30 = (20 * 20 + 10 * 30) / 30
    expected = (w["c1"] * c1_clay_0_30 + w["c2"] * 50 + w["c3"] * 15) / sum(w.values())
    top = p.layers[0]
    assert top.clay_pct.value == pytest.approx(expected, abs=1e-3)
    assert top.clay_pct.uncertainty.kind == "range" and top.clay_pct.uncertainty.low < top.clay_pct.value
    assert p.drainage_class.value == "Well drained"
    assert p.drainage_class.weight_share == pytest.approx((0.6 + 0.075) / 0.825, abs=1e-3)
    assert p.hydrologic_group.value == "B"
    assert p.aws_0_150.value == pytest.approx(0.75 * 22 + 0.25 * 18)
    assert p.null_weight_fraction == 0 and p.quality.status == "valid"
    assert [m.mukey for m in p.map_units] == ["100", "200"] and p.map_units[0].area_fraction == 0.75
    assert p.survey[0].areasymbol == "KS155" and p.sources[0].dataset_id == "usda_nrcs_ssurgo_sda"
    assert "PROVISIONAL" in p.method.description


def test_soil_null_weight_thresholds():
    raw = synthetic_ssurgo_raw()
    raw.horizons.pop("c1")  # dominant component has no horizons -> 0.6 / 0.825 = 73 % null weight
    p = aggregate_soil(FID, raw)
    assert p.null_weight_fraction == pytest.approx(0.6 / 0.825, abs=1e-3)
    assert p.quality.status == "missing" and p.quality.missing_reason == "INSUFFICIENT_COVERAGE"
    assert all(layer.clay_pct.value is None and layer.clay_pct.missing_reason == "INSUFFICIENT_COVERAGE"
               for layer in p.layers)

    raw = synthetic_ssurgo_raw()
    raw.horizons.pop("c2")  # 0.15 / 0.825 = 18 % -> still valid; add null comppct to push above 20 %
    raw.components[2]["comppct_r"] = None
    p = aggregate_soil(FID, raw)
    assert 0.2 < p.null_weight_fraction <= 0.5 and p.quality.status == "partial"


def test_climate_completeness_rule_and_not_yet_published():
    full = build_climate_profile(FID, 2024, None, synthetic_power_daily(2024))
    precip = next(i for i in full.indicators if i.key == "precip_total_season")
    assert precip.value.value == 732.0 and precip.quality.completeness == 1.0

    gappy = build_climate_profile(FID, 2024, None, synthetic_power_daily(2024, fill_days=40))  # 89 % present
    p2 = next(i for i in gappy.indicators if i.key == "precip_total_season")
    assert p2.value.value is None and p2.value.missing_reason == "INSUFFICIENT_COVERAGE"
    pts = gappy.series[0].points
    assert pts[0].value is None and pts[0].missing_reason == "FILL_VALUE"

    partial = build_climate_profile(FID, 2024, None, synthetic_power_daily(2024, end=date(2024, 6, 30)))
    last = partial.series[0].points[-1]
    assert last.missing_reason == "NOT_YET_PUBLISHED" and last.value is None


def test_climate_unit_mismatch_is_withheld_not_converted():
    d = synthetic_power_daily(2024)
    d.units["T2M"] = "F"
    prof = build_climate_profile(FID, 2024, None, d)
    assert "t2m" not in {s.variable for s in prof.series}
    assert any(f.code == "UNIT_MISMATCH" for f in prof.quality.flags)


def test_climate_plausibility_flags_without_dropping():
    d = synthetic_power_daily(2024)
    d.values["RH2M"][date(2024, 3, 1)] = 120.0
    prof = build_climate_profile(FID, 2024, None, d)
    rh = next(s for s in prof.series if s.variable == "rh2m")
    pt = next(p for p in rh.points if p.t == "2024-03-01")
    assert pt.value == 120.0 and pt.quality_status == "flagged"


def test_climate_failure_profile():
    prof = build_climate_profile(FID, 2024, None, None, failure_reason="UPSTREAM_ERROR", failure_message="down")
    assert prof.series == [] and prof.quality.status == "missing"
    assert all(i.value.value is None for i in prof.indicators)


def test_inward_buffer_rule():
    g = shape({"type": "MultiPolygon", "coordinates": RENO_SQUARE})
    b, applied = inward_buffer_5070(g, 15)
    assert applied and b.area < reproject(g, "EPSG:4326", "EPSG:5070").area
    narrow = box(-98.05, 37.95, -98.0497, 37.96)  # ~26 m wide strip
    _, applied = inward_buffer_5070(narrow, 15)
    assert not applied
    assert 95 < area_ha(g) < 100


def test_cdl_zonal_histogram_and_history(tmp_path):
    g = shape({"type": "MultiPolygon", "coordinates": RENO_SQUARE})
    p = write_cdl_raster(tmp_path / "c.tif", g, lambda c, w: 24 if c < w / 2 else 0)
    counts, total, background, res = zonal_histogram(p, reproject(g, "EPSG:4326", "EPSG:5070"))
    assert res == 30 and background > 0 and set(counts) == {24}
    raster = CdlCountyRaster(year=2020, fips="20155", path=p, url="u", acquisition=acq("usda_nass_cdl"),
                             legend={24: "Winter Wheat"})
    hist = build_crop_history(FID, g, 2019, 2020, {2019: ProviderError("x", "OUT_OF_TEMPORAL_RANGE"), 2020: raster})
    y2019, y2020 = hist.years
    assert y2019.missing_reason == "OUT_OF_TEMPORAL_RANGE" and y2019.purity is None
    assert y2020.purity == 1.0 and y2020.histogram[0].crop_name == "Winter Wheat"
    assert any(f.code == "PIXELS_OUTSIDE_COUNTY" for f in hist.quality.flags)
    assert hist.quality.status == "partial" and hist.quality.completeness == 0.5


def test_horn_slope_on_plane():
    dem = np.add.outer(np.arange(10) * 3.0, np.zeros(10))  # 3 m rise per 30 m row -> 10 %
    s = horn_slope_pct(dem, 30, 30)
    assert np.isnan(s[0, 0]) and s[5, 5] == pytest.approx(10.0)
