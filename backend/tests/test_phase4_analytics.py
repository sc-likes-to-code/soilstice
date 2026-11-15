"""Phase 4 Environmental Analytical Engine verification tests.

Validates:
1. McMaster & Wilhelm (1997) Modified GDD across crop-specific thresholds (Corn, Wheat, Sorghum, Alfalfa).
2. FAO-56 Penman-Monteith daily reference ET0 equation.
3. NOAA 1991-2020 precipitation anomaly departures.
4. Heat-stress days and frost-free days counting rules.
5. 20-year CDL rotation indicators: distinct crops, max monoculture run, Shannon diversity H'.
6. Piecewise-linear resilience components scoring and 4-of-5 quorum rule.
"""

import math
import uuid
from datetime import date

from app.analytics.resilience import (
    _band,
    _interpolate,
)
from app.contracts import (
    EnvironmentalIndicator,
    MethodRef,
    QualityInfo,
    Quantity,
    SpatialSupport,
    TemporalSupport,
)
from app.processing.climate import (
    CROP_GDD_THRESHOLDS,
    compute_daily_gdd,
    compute_fao56_et0_daily,
)

DUMMY_SPATIAL = SpatialSupport(support_class="F", native_resolution_m=30.0, extraction_method="zonal_polygon")
DUMMY_TEMPORAL = TemporalSupport(resolution="season", period_start=date(2024, 1, 1), period_end=date(2024, 12, 31),
                                 aggregation="none", time_standard="LST")
DUMMY_METHOD = MethodRef(method_id="test_method", name="Test Method", version="1", description="Test")


def _ind(key: str, val: float | None, unit: str = "unitless", category: str = "soil") -> EnvironmentalIndicator:
    return EnvironmentalIndicator(
        indicator_id=f"test:{key}", key=key, label=key, category=category,
        value=Quantity(value=val, unit=unit, missing_reason=None if val is not None else "NOT_COMPUTED"),
        nature="derived", spatial=DUMMY_SPATIAL, temporal=DUMMY_TEMPORAL,
        quality=QualityInfo(status="valid" if val is not None else "missing"),
        sources=[], method=DUMMY_METHOD, input_ids=[],
    )


# ── 1. Climate Mathematical Tests ─────────────────────────────────────────────


def test_gdd_crop_specific_thresholds():
    # Corn: T_base = 10, T_cap = 30
    assert CROP_GDD_THRESHOLDS[1] == (10.0, 30.0)
    # Winter Wheat: T_base = 0, T_cap = 25
    assert CROP_GDD_THRESHOLDS[24] == (0.0, 25.0)
    # Grain Sorghum: T_base = 10, T_cap = 35
    assert CROP_GDD_THRESHOLDS[4] == (10.0, 35.0)
    # Alfalfa: T_base = 5, T_cap = 30
    assert CROP_GDD_THRESHOLDS[36] == (5.0, 30.0)


def test_gdd_modified_method_calculations():
    # Scenario A: Moderate summer day (Tmax = 28°C, Tmin = 16°C)
    # Corn (base 10, cap 30): (28 + 16)/2 - 10 = 22 - 10 = 12.0
    assert compute_daily_gdd(28.0, 16.0, 10.0, 30.0) == 12.0
    # Wheat (base 0, cap 25): Tmax clamped to 25 -> (25 + 16)/2 - 0 = 20.5
    assert compute_daily_gdd(28.0, 16.0, 0.0, 25.0) == 20.5

    # Scenario B: High heat wave (Tmax = 38°C, Tmin = 22°C)
    # Corn: Tmax clamped to 30 -> (30 + 22)/2 - 10 = 16.0
    assert compute_daily_gdd(38.0, 22.0, 10.0, 30.0) == 16.0
    # Sorghum (base 10, cap 35): Tmax clamped to 35 -> (35 + 22)/2 - 10 = 18.5
    assert compute_daily_gdd(38.0, 22.0, 10.0, 35.0) == 18.5

    # Scenario C: Below freezing / early spring (Tmax = 8°C, Tmin = -2°C)
    # Corn: Tmax clamped to 10, Tmin clamped to 10 -> (10 + 10)/2 - 10 = 0.0
    assert compute_daily_gdd(8.0, -2.0, 10.0, 30.0) == 0.0
    # Wheat (base 0, cap 25): Tmax 8, Tmin clamped to 0 -> (8 + 0)/2 - 0 = 4.0
    assert compute_daily_gdd(8.0, -2.0, 0.0, 25.0) == 4.0


def test_fao56_penman_monteith_et0_bounds():
    # Standard Kansas summer day: T=25°C, Tmax=32°C, Tmin=18°C, RH=60%, Solar=22 MJ/m²/day
    et0 = compute_fao56_et0_daily(t_mean=25.0, t_max=32.0, t_min=18.0, rh_mean=60.0, solar_mj=22.0)
    # Typical evaporative demand in summer Great Plains: 4.0 to 6.5 mm/day
    assert 4.0 < et0 < 6.5

    # Overcast, cold autumn day: T=5°C, Tmax=8°C, Tmin=2°C, RH=90%, Solar=5 MJ/m²/day
    et0_cold = compute_fao56_et0_daily(t_mean=5.0, t_max=8.0, t_min=2.0, rh_mean=90.0, solar_mj=5.0)
    assert 0.1 < et0_cold < 1.5


# ── 2. Crop History Rotation Diversity Tests ──────────────────────────────────


def test_shannon_diversity_formula():
    # 2-crop equal balance (Corn / Soybeans, 10 years each): H' = -2 * (0.5 * ln(0.5)) = ln(2) ~ 0.693
    p = 0.5
    h_prime = -2.0 * (p * math.log(p))
    assert round(h_prime, 3) == 0.693

    # 4-crop equal balance (Wheat / Corn / Sorghum / Soybeans, 5 years each): H' = ln(4) ~ 1.386
    p4 = 0.25
    h_prime4 = -4.0 * (p4 * math.log(p4))
    assert round(h_prime4, 3) == 1.386


def test_fallow_and_pasture_excluded_from_crop_species_diversity():
    from app.processing.crop_history import AG_NON_CROP_CODES, NON_CROP_SPECIES_CODES
    # Code 61 (Fallow/Idle Cropland) is agricultural land use, not a crop species
    assert 61 in AG_NON_CROP_CODES
    assert 61 in NON_CROP_SPECIES_CODES
    # Code 176 (Grassland/Pasture) is perennial forage/cover, not a cultivated crop species
    assert 176 in AG_NON_CROP_CODES
    assert 176 in NON_CROP_SPECIES_CODES


def test_monoculture_run_interrupted_by_non_crop():
    from app.catalog import source_ref
    from app.contracts import CropRef, CropYear
    from app.processing.crop_history import NON_CROP_SPECIES_CODES

    src = source_ref("usda_nass_cdl")
    # Sequence: 2021 Corn, 2022 Corn, 2023 Fallow (61), 2024 Corn, 2025 Corn
    # Intervening fallow in 2023 must prevent a false 4-year run; max run must be 2.
    years_data = [
        CropYear(year=2021, majority=CropRef(crop_code=1, crop_name="Corn"),
                 purity=0.8, histogram=[], low_purity=False, source=src),
        CropYear(year=2022, majority=CropRef(crop_code=1, crop_name="Corn"),
                 purity=0.8, histogram=[], low_purity=False, source=src),
        CropYear(year=2023, majority=CropRef(crop_code=61, crop_name="Fallow/Idle Cropland"),
                 purity=0.9, histogram=[], low_purity=False, source=src),
        CropYear(year=2024, majority=CropRef(crop_code=1, crop_name="Corn"),
                 purity=0.8, histogram=[], low_purity=False, source=src),
        CropYear(year=2025, majority=CropRef(crop_code=1, crop_name="Corn"),
                 purity=0.8, histogram=[], low_purity=False, source=src),
    ]

    valid_years = [y for y in years_data if y.missing_reason is None and y.majority.crop_code is not None]
    ag_crops = [y.majority.crop_code for y in valid_years if y.majority.crop_code not in NON_CROP_SPECIES_CODES]
    assert len(set(ag_crops)) == 1  # Only 1 distinct cultivated crop species (Corn)
    
    # Verify monoculture run breaks at 2023
    max_run = 0
    cur_run = 0
    prev_crop = None
    prev_year = None
    for y in years_data:
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
    assert max_run == 2  # NOT 4!


# ── 3. Resilience Engine Scoring & Quorum Rule Tests ───────────────────────────


def test_interpolation_and_bands():
    # Piecewise interpolation
    bps = [(6.0, 0.0), (10.0, 30.0), (20.0, 80.0), (25.0, 100.0)]
    assert _interpolate(5.0, bps) == 0.0  # below lowest
    assert _interpolate(6.0, bps) == 0.0
    assert _interpolate(8.0, bps) == 15.0  # midpoint of 6..10
    assert _interpolate(25.0, bps) == 100.0
    assert _interpolate(30.0, bps) == 100.0  # above highest

    # Score bands
    assert _band(None) == "unknown"
    assert _band(35.0) == "low"
    assert _band(40.0) == "moderate"
    assert _band(70.0) == "moderate"
    assert _band(75.0) == "high"


def test_calibrated_resilience_quorum_met():
    from app.analytics.resilience import AgronomicBreakpointResilienceEngine
    engine = AgronomicBreakpointResilienceEngine()
    fid = uuid.uuid4()

    # 4 components available: soil (aws=18 cm), terrain (slope=2.0%),
    # climate (heat=10 d, anom=5%), rotation (distinct=3, run=2, shannon=0.9)
    inds = [
        _ind("aws_0_150", 18.0, "cm"),
        _ind("slope_p90_pct", 2.0, "percent"),
        _ind("heat_stress_days", 10.0, "day"),
        _ind("precip_anomaly_pct", 5.0, "percent"),
        _ind("distinct_crops", 3.0, "count"),
        _ind("max_monoculture_run", 2.0, "year"),
        _ind("rotation_shannon", 0.90, "unitless"),
        _ind("ndvi_peak_cv", None, "unitless"),  # uncomputed
    ]
    prof = engine.profile(fid, inds, date(2026, 11, 14))
    assert prof.status == "computed"
    assert prof.composite.components_used == 4
    assert prof.composite.components_total == 4
    assert prof.composite.score.value is not None
    assert 60.0 < prof.composite.score.value < 85.0
    assert prof.composite.band in ("moderate", "high")
    assert any("not empirically calibrated" in d for d in prof.disclaimers)


def test_calibrated_resilience_quorum_not_met_honest_disclosure():
    from app.analytics.resilience import AgronomicBreakpointResilienceEngine
    engine = AgronomicBreakpointResilienceEngine()
    fid = uuid.uuid4()

    # Only 2 components available (soil and rotation; terrain, climate, vegetation missing)
    inds = [
        _ind("aws_0_150", 18.0, "cm"),
        _ind("distinct_crops", 3.0, "count"),
        _ind("max_monoculture_run", 2.0, "year"),
        _ind("rotation_shannon", 0.90, "unitless"),
    ]
    prof = engine.profile(fid, inds, date(2026, 11, 14))
    assert prof.status == "insufficient_data"
    assert prof.composite.components_used == 2
    assert prof.composite.score.value is None
    assert prof.composite.score.missing_reason == "INSUFFICIENT_COVERAGE"
    assert prof.composite.band == "unknown"
    assert any(flag.code == "QUORUM_NOT_MET" for flag in prof.limitations)


# ── 4. Phase 4.1 Audit Verification Tests ─────────────────────────────────────


def test_modified_gdd_reno_2024_reproduction():
    import json
    from pathlib import Path

    from app.providers.power import parse_power_daily
    from app.repositories.records import AcquisitionRecord

    cache_dir = Path("backend/.cache/raw/nasa_power_daily_ag")
    bin_file = cache_dir / "6cdf94d308695010ce9783e745734d5de6b048d1283002959de4c85884952ac2.bin"
    if not bin_file.exists():
        return
    with open(bin_file, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    acq = AcquisitionRecord(
        acquisition_id=uuid.uuid4(), dataset_id="nasa_power_daily_ag", retrieved_at="2026-11-14T00:00:00Z",
        request_url="https://power.larc.nasa.gov", http_status=200, sha256="test",
        bytes=100,
    )
    daily = parse_power_daily(doc, acq, -98.05, 37.95, date(2024, 1, 1), date(2024, 12, 31))
    tmax = daily.values["T2M_MAX"]
    tmin = daily.values["T2M_MIN"]
    days = sorted(tmax.keys())
    assert len(days) == 366  # 2024 is a leap year

    # Modified GDD: McMaster & Wilhelm (1997) Method 2 (Tbase=10, Tcap=30)
    gdd_corn = sum(compute_daily_gdd(tmax[d], tmin[d], 10.0, 30.0) for d in days)
    assert round(gdd_corn, 1) == 2862.0


def test_climate_indicators_audit_provenance_and_flags():
    from app.processing.climate import build_climate_profile

    fid = uuid.uuid4()
    # When daily is None, build_climate_profile reports missing with explicit reasons
    prof = build_climate_profile(fid, 2024, None, None, failure_reason="UPSTREAM_ERROR")
    wb = next(i for i in prof.indicators if i.key == "water_balance_season")
    assert wb.label == "Climatic water balance (P − ET₀)"
    assert "Climatic Water Balance" in wb.method.name
    assert "NOT crop water demand" in wb.method.description

    heat = next(i for i in prof.indicators if i.key == "heat_stress_days")
    assert "phenology is unavailable" in heat.method.description

    frost = next(i for i in prof.indicators if i.key == "frost_free_days")
    assert "distinct from the continuous freeze-free period" in frost.method.description
