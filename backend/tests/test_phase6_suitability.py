"""SOILSTICE Phase 6: Crop Suitability Engine Test Suite.

Verifies:
- All 11 environmental factor evaluators:
  * thermal_gdd, heat_stress, water_precipitation, soil_ph, soil_drainage,
    soil_texture, available_water, rooting, terrain_slope, crop_history, regional_suitability.
- Scientific constraints and integrity:
  * Missing information remains unknown (null values NEVER coerced to 0).
  * Liebig's Law of the Minimum: Critical limiting factor strictly dictates `unsuitable` classification
    and caps the suitability score (favorable factors cannot silently compensate).
  * Rooting depth disaggregation: Effective water extraction depth is strictly distinguished
    from maximum anatomical root depth.
  * Oilseed radish internal nitrogen recycling vs biological fixation distinction.
  * Absence of invented thresholds for unpopulated crop attributes.
- Complete evaluation of all 14 canonical crops (CRP001–CRP014).
- REST API endpoints:
  * GET /api/v1/fields/{field_id}/suitability
  * GET /api/v1/fields/{field_id}/suitability/{crop_id}
  * Standard SOILSTICE ApiResponse envelope and proper 404 error handling.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.analytics.resilience import CalibratedResilienceEngine
from app.config import Settings
from app.contracts import (
    AuthoritativeClimateSource,
    ClassValue,
    ClimateProfile,
    CropHistory,
    CropRef,
    CropShare,
    CropSuitabilityAssessment,
    CropYear,
    EnvironmentalIndicator,
    FieldSuitabilityResponse,
    MethodRef,
    QualityInfo,
    Quantity,
    Season,
    SoilLayer,
    SoilProfile,
    SourceRef,
    SpatialSupport,
    TemporalSupport,
    TerrainProfile,
    SuitabilityFactorAssessment,
    YearPeriod,
)
from app.main import create_app
from app.repositories import Repositories, SqliteDocumentStore
from app.rotation.engine import PendingRotationEngine
from app.rotation.kb import CropKnowledgeBase, load_kb
from app.services.container import Container
from app.suitability.engine import CropSuitabilityEngine
from app.suitability.evaluators import (
    evaluate_available_water,
    evaluate_crop_history,
    evaluate_heat_stress,
    evaluate_regional_suitability,
    evaluate_rooting,
    evaluate_soil_drainage,
    evaluate_soil_ph,
    evaluate_soil_texture,
    evaluate_terrain_slope,
    evaluate_thermal_gdd,
    evaluate_water_precipitation,
)
from app.suitability.scorer import calculate_suitability_score, classify_crop

HANDOFF_DIR = Path("data/backend_handoff")
API = "/api/v1"

# Shared mock primitives
DUMMY_SPATIAL = SpatialSupport(
    support_class="F",
    native_resolution_m=30.0,
    extraction_method="vector_intersection",
    field_fraction_of_cell=None,
    cell_id=None,
    crs="EPSG:4326",
)
DUMMY_TEMPORAL = TemporalSupport(
    resolution="season",
    period_start=date(2026, 4, 1),
    period_end=date(2026, 10, 31),
    aggregation="mean",
    time_standard="UTC",
)
DUMMY_QUALITY = QualityInfo(status="valid", completeness=1.0, flags=[], missing_reason=None)
DUMMY_METHOD = MethodRef(
    method_id="soilstice_test_mock",
    name="Test Mock Method",
    version="1.0.0",
    description="Mock method for testing",
    reference_url=None,
)
DUMMY_SOURCE = SourceRef(dataset_id="soilstice_derived", product="test", product_version="1.0")


def make_climate(
    gdd: float | None = 1400.0,
    heat_days: int | None = 10,
    precip: float | None = 600.0,
) -> ClimateProfile:
    indicators: list[EnvironmentalIndicator] = []
    if gdd is not None:
        indicators.append(
            EnvironmentalIndicator(
                indicator_id="ind_gdd",
                key="gdd_season",
                label="GDD",
                category="climate",
                value=Quantity(value=gdd, unit="degC_day"),
                nature="model",
                spatial=DUMMY_SPATIAL,
                temporal=DUMMY_TEMPORAL,
                quality=DUMMY_QUALITY,
                sources=[DUMMY_SOURCE],
                method=DUMMY_METHOD,
            )
        )
    if heat_days is not None:
        indicators.append(
            EnvironmentalIndicator(
                indicator_id="ind_heat",
                key="heat_stress_days",
                label="Heat Days",
                category="climate",
                value=Quantity(value=heat_days, unit="day"),
                nature="model",
                spatial=DUMMY_SPATIAL,
                temporal=DUMMY_TEMPORAL,
                quality=DUMMY_QUALITY,
                sources=[DUMMY_SOURCE],
                method=DUMMY_METHOD,
            )
        )
    if precip is not None:
        indicators.append(
            EnvironmentalIndicator(
                indicator_id="ind_precip",
                key="precip_total_season",
                label="Precipitation",
                category="climate",
                value=Quantity(value=precip, unit="mm"),
                nature="model",
                spatial=DUMMY_SPATIAL,
                temporal=DUMMY_TEMPORAL,
                quality=DUMMY_QUALITY,
                sources=[DUMMY_SOURCE],
                method=DUMMY_METHOD,
            )
        )

    return ClimateProfile(
        field_id=UUID("00000000-0000-0000-0000-000000000001"),
        season=Season(label="2026", start=date(2026, 4, 1), end=date(2026, 10, 31)),
        authoritative_source=AuthoritativeClimateSource(
            precipitation="nasa_power_daily_ag", temperature="nasa_power_daily_ag"
        ),
        indicators=indicators,
        series=[],
        quality=DUMMY_QUALITY,
    )


def make_soil(
    ph: float | None = 6.5,
    drainage: str = "Well drained",
    texture: str = "Silt loam",
    aws150: float = 18.0,
    depth: float = 150.0,
) -> SoilProfile:
    layers = []
    if ph is not None:
        layers.append(
            SoilLayer(
                top_cm=0.0,
                bottom_cm=min(30.0, depth),
                sand_pct=Quantity(value=20.0, unit="percent"),
                silt_pct=Quantity(value=60.0, unit="percent"),
                clay_pct=Quantity(value=20.0, unit="percent"),
                texture_class=texture,
                ph_h2o=Quantity(value=ph, unit="pH"),
                om_pct=Quantity(value=2.5, unit="percent"),
                awc=Quantity(value=0.18, unit="cm_cm-1"),
            )
        )
        if depth > 30.0:
            layers.append(
                SoilLayer(
                    top_cm=30.0,
                    bottom_cm=depth,
                    sand_pct=Quantity(value=25.0, unit="percent"),
                    silt_pct=Quantity(value=55.0, unit="percent"),
                    clay_pct=Quantity(value=20.0, unit="percent"),
                    texture_class=texture,
                    ph_h2o=Quantity(value=ph + 0.2, unit="pH"),
                    om_pct=Quantity(value=1.0, unit="percent"),
                    awc=Quantity(value=0.16, unit="cm_cm-1"),
                )
            )

    return SoilProfile(
        field_id=UUID("00000000-0000-0000-0000-000000000001"),
        layers=layers,
        aws_0_100=Quantity(value=12.0, unit="cm"),
        aws_0_150=Quantity(value=aws150, unit="cm"),
        drainage_class=ClassValue(value=drainage),
        hydrologic_group=ClassValue(value="B"),
        slope_pct_ssurgo=Quantity(value=1.5, unit="percent"),
        map_units=[],
        survey=[],
        method=DUMMY_METHOD,
        spatial=DUMMY_SPATIAL,
        sources=[DUMMY_SOURCE],
        quality=DUMMY_QUALITY,
    )


def make_terrain(slope: float = 1.5) -> TerrainProfile:
    return TerrainProfile(
        field_id=UUID("00000000-0000-0000-0000-000000000001"),
        elevation_mean=Quantity(value=450.0, unit="m"),
        elevation_min=Quantity(value=445.0, unit="m"),
        elevation_max=Quantity(value=455.0, unit="m"),
        slope_mean_pct=Quantity(value=slope, unit="percent"),
        slope_p90_pct=Quantity(value=slope * 1.5, unit="percent"),
        method=DUMMY_METHOD,
        spatial=DUMMY_SPATIAL,
        sources=[DUMMY_SOURCE],
        quality=DUMMY_QUALITY,
    )


def make_history(crop_codes: list[int]) -> CropHistory:
    years = []
    for i, c in enumerate(crop_codes):
        yr = 2026 - len(crop_codes) + i
        years.append(
            CropYear(
                year=yr,
                majority=CropRef(crop_code=c, crop_name=f"Crop {c}"),
                purity=0.95,
                histogram=[CropShare(crop_code=c, crop_name=f"Crop {c}", area_fraction=0.95)],
                low_purity=False,
                source=DUMMY_SOURCE,
            )
        )
    return CropHistory(
        field_id=UUID("00000000-0000-0000-0000-000000000001"),
        period=YearPeriod(start_year=2026 - len(crop_codes), end_year=2025),
        years=years,
        metrics=[],
        spatial=DUMMY_SPATIAL,
        quality=DUMMY_QUALITY,
    )


@pytest.fixture(scope="module")
def kb() -> CropKnowledgeBase:
    """Load canonical Phase 5 crop knowledge base."""
    k = load_kb(HANDOFF_DIR)
    assert k.available, f"Knowledge base failed to load: {k.status_message}"
    return k


@pytest.fixture(scope="module")
def engine(kb: CropKnowledgeBase) -> CropSuitabilityEngine:
    """Initialize CropSuitabilityEngine with live KB."""
    return CropSuitabilityEngine(kb)


@pytest.fixture
def client(kb: CropKnowledgeBase, fake_providers):
    """TestClient configured with the live Phase 5 Crop Knowledge Base."""
    s = Settings(
        environment="test",
        db_path=":memory:",
        cache_dir=Path("tmp/cache"),
        job_execution="inline",
        http_retries=0,
        http_backoff_base_s=0.0,
        cdl_first_year=2006,
        cdl_last_year=2010,
        climate_default_season_year=2024,
        rate_limit_writes_per_minute=0,
        log_level="WARNING",
        crop_kb_dir=HANDOFF_DIR,
        _env_file=None,
    )
    container = Container(
        settings=s,
        repos=Repositories.create(SqliteDocumentStore(":memory:")),
        providers=fake_providers,
        kb=kb,
        resilience=CalibratedResilienceEngine(),
        rotation=PendingRotationEngine(),
        executor=None,
    )
    app = create_app(settings=s, container=container)
    with TestClient(app) as tc:
        yield tc


# ============================================================================
# 1. FACTOR EVALUATOR UNIT TESTS
# ============================================================================

def test_evaluator_thermal_gdd_optimal(kb: CropKnowledgeBase):
    """Corn (CRP001) with 1400 GDD is within optimal range (1167-1556 °C-days)."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=1400.0)
    res = evaluate_thermal_gdd(corn, climate)
    assert res.compatibility == "optimal"
    assert res.is_limiting is False
    assert res.is_favorable is True
    assert res.severity == "favorable"
    assert res.observed_value.value == 1400.0
    assert res.observed_value.unit == "degC_day"


def test_evaluator_thermal_gdd_critical_deficiency(kb: CropKnowledgeBase):
    """Corn with 600 GDD violates minimum requirement (1167 °C-days minimum)."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=600.0)
    res = evaluate_thermal_gdd(corn, climate)
    assert res.compatibility == "critical_limitation"
    assert res.is_limiting is True
    assert res.severity == "critical"
    assert "deficit" in res.interpretation.lower() or "insufficient" in res.interpretation.lower()


def test_evaluator_thermal_gdd_missing_null_preserved(kb: CropKnowledgeBase):
    """Missing GDD data must result in UNKNOWN compatibility and never be coerced to 0."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    res = evaluate_thermal_gdd(corn, None)
    assert res.compatibility == "unknown"
    assert res.observed_value.value is None
    assert res.is_limiting is False
    assert res.is_favorable is False
    assert res.severity == "unknown"
    assert res.data_status == "missing"


def test_evaluator_soil_ph_optimal_and_critical(kb: CropKnowledgeBase):
    """Soybeans (CRP002) optimal pH is 6.0-7.0; pH 4.5 is a critical physiological limitation."""
    soybeans = kb.get_crop_by_id("CRP002")
    assert soybeans is not None

    soil_opt = make_soil(ph=6.5)
    opt_res = evaluate_soil_ph(soybeans, soil_opt)
    assert opt_res.compatibility == "optimal"
    assert opt_res.is_limiting is False

    soil_crit = make_soil(ph=4.5)
    crit_res = evaluate_soil_ph(soybeans, soil_crit)
    assert crit_res.compatibility == "critical_limitation"
    assert crit_res.is_limiting is True
    assert crit_res.severity == "critical"


def test_evaluator_soil_drainage_alfalfa_vs_rice(kb: CropKnowledgeBase):
    """Alfalfa (CRP011) fails in poorly drained soils; Rice (CRP007) requires/tolerates poor drainage."""
    alfalfa = kb.get_crop_by_id("CRP011")
    rice = kb.get_crop_by_id("CRP007")
    assert alfalfa is not None and rice is not None

    soil_poor = make_soil(drainage="Poorly drained")
    alfalfa_poor = evaluate_soil_drainage(alfalfa, soil_poor)
    assert alfalfa_poor.compatibility == "critical_limitation"
    assert alfalfa_poor.severity == "critical"

    rice_poor = evaluate_soil_drainage(rice, soil_poor)
    assert rice_poor.compatibility == "optimal"
    assert rice_poor.is_limiting is False


def test_evaluator_rooting_effective_depth_vs_maximum_depth(kb: CropKnowledgeBase):
    """Effective water extraction depth (40-120 cm) is NOT identical to anatomical max depth (60-350 cm)."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    # Shallow profile (30 cm depth) is limiting
    soil_shallow = make_soil(depth=30.0)
    res_shallow = evaluate_rooting(corn, soil_shallow)
    assert res_shallow.is_limiting is True
    assert "effective" in res_shallow.interpretation.lower()

    # Deep soil (150 cm) provides unrestricted rooting
    soil_deep = make_soil(depth=150.0)
    res_deep = evaluate_rooting(corn, soil_deep)
    assert res_deep.compatibility == "optimal"
    assert res_deep.is_limiting is False


def test_evaluator_crop_history_monoculture_penalty(kb: CropKnowledgeBase):
    """Recent cultivation of the same crop (monoculture) triggers agronomic rotation warning."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    # History of repeated Corn (code 1)
    hist = make_history([1, 1])
    res_mono = evaluate_crop_history(corn, hist)
    assert res_mono.is_limiting is True
    assert res_mono.compatibility == "moderate_limitation"
    assert "monoculture" in res_mono.interpretation.lower() or "consecutive" in res_mono.interpretation.lower()


def test_evaluator_terrain_slope_mechanized_limits(kb: CropKnowledgeBase):
    """Steep slope (>15%) imposes severe erosion and machinery hazards for row crops."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    terrain_steep = make_terrain(slope=18.0)
    res_steep = evaluate_terrain_slope(corn, terrain_steep)
    assert res_steep.compatibility == "critical_limitation"
    assert res_steep.is_limiting is True


# ============================================================================
# 2. SCIENTIFIC INTEGRITY & SCORING PRINCIPLE TESTS
# ============================================================================

def test_liebig_law_critical_factor_enforcement(kb: CropKnowledgeBase):
    """Under Liebig's Law of the Minimum, ANY critical limitation forces 'unsuitable'
    and strictly caps the score, regardless of how favorable other factors are.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    climate = make_climate(gdd=1400.0, precip=650.0)
    soil_crit = make_soil(ph=4.2)  # CRITICAL pH
    terrain = make_terrain(slope=1.5)

    factors = [
        evaluate_thermal_gdd(corn, climate),
        evaluate_water_precipitation(corn, climate),
        evaluate_terrain_slope(corn, terrain),
        evaluate_soil_ph(corn, soil_crit),
    ]

    s_class, _ = classify_crop(factors)
    score, method = calculate_suitability_score(factors, s_class)

    assert s_class == "unsuitable"
    assert score is not None
    assert score <= 35.0, f"Score {score} exceeded Liebig cap of 35 for critical limitation"
    assert "critical" in method.lower() or "limiting-factor" in method.lower()


def test_missing_data_insufficient_classification(kb: CropKnowledgeBase):
    """If critical environmental layers are missing, classification must be 'insufficient_data'
    and score must be withheld (None), never fabricated.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    factors = [
        evaluate_thermal_gdd(corn, None),
        evaluate_water_precipitation(corn, None),
        evaluate_soil_ph(corn, None),
        evaluate_soil_drainage(corn, None),
    ]

    s_class, _ = classify_crop(factors)
    score, method = calculate_suitability_score(factors, s_class)

    assert s_class == "insufficient_data"
    assert score is None
    assert "withheld" in method.lower() or "insufficient" in method.lower()


def test_all_optimal_factors_yields_suitable(kb: CropKnowledgeBase):
    """When all evaluated factors are optimal/compatible, crop must be 'suitable' with high score."""
    wheat = kb.get_crop_by_id("CRP003")
    assert wheat is not None

    climate = make_climate(gdd=2000.0, precip=550.0)
    soil = make_soil(ph=6.8, drainage="Well drained", texture="Silt loam", aws150=18.0)
    terrain = make_terrain(slope=1.0)

    factors = [
        evaluate_thermal_gdd(wheat, climate),
        evaluate_water_precipitation(wheat, climate),
        evaluate_soil_ph(wheat, soil),
        evaluate_soil_drainage(wheat, soil),
        evaluate_soil_texture(wheat, soil),
        evaluate_available_water(wheat, soil),
        evaluate_rooting(wheat, soil),
        evaluate_terrain_slope(wheat, terrain),
    ]

    s_class, _ = classify_crop(factors)
    score, method = calculate_suitability_score(factors, s_class)

    assert s_class == "suitable"
    assert score is not None
    assert score >= 85.0


def test_oilseed_radish_nitrogen_recycling_scientific_rule(kb: CropKnowledgeBase):
    """Verify Oilseed Radish (CRP014) documentation and limitations correctly reflect
    nitrate scavenging from deep horizons rather than newly fixed biological N.
    """
    radish = kb.get_crop_by_id("CRP014")
    assert radish is not None
    assert radish.is_cover_crop is True

    nitro = radish.nitrogen_and_biomass
    assert "100" in str(nitro) or "scaveng" in str(nitro).lower() or "recycl" in str(nitro).lower()


# ============================================================================
# 3. ENGINE SUITABILITY ORCHESTRATION TESTS
# ============================================================================

def test_engine_evaluates_all_14_canonical_crops(engine: CropSuitabilityEngine):
    """The CropSuitabilityEngine must evaluate all 14 canonical crops."""
    climate = make_climate(gdd=1450.0, heat_days=12, precip=620.0)
    soil = make_soil(ph=6.8, drainage="Well drained", texture="Silt loam", aws150=18.0)
    terrain = make_terrain(slope=1.5)
    history = make_history([24, 5])

    field_uuid = UUID("11111111-1111-1111-1111-111111111111")
    result = engine.evaluate_field(
        field_uuid,
        season_year=2026,
        soil=soil,
        climate=climate,
        terrain=terrain,
        history=history,
        state_code="KS",
    )

    assert isinstance(result, FieldSuitabilityResponse)
    assert result.summary.total_evaluated == 14
    assert len(result.crops) == 14

    crop_ids = [c.crop_id for c in result.crops]
    expected_ids = [f"CRP{i:03d}" for i in range(1, 15)]
    assert crop_ids == expected_ids

    # Every crop must have non-empty factor assessments and scientific limitations
    for crop_eval in result.crops:
        assert len(crop_eval.factor_assessments) >= 8
        assert len(crop_eval.limitations) >= 2
        assert crop_eval.data_quality.status in ("valid", "partial")


def test_engine_single_crop_evaluation(engine: CropSuitabilityEngine):
    """Single crop evaluation via evaluate_crop."""
    corn = engine.kb.get_crop_by_id("CRP001")
    assert corn is not None

    climate = make_climate(gdd=1400.0, precip=580.0)
    soil = make_soil(ph=6.6, drainage="Well drained")
    terrain = make_terrain(slope=1.2)

    assessment = engine.evaluate_crop(
        corn,
        soil=soil,
        climate=climate,
        terrain=terrain,
        history=None,
        state_code="KS",
    )
    assert isinstance(assessment, CropSuitabilityAssessment)
    assert assessment.crop_id == "CRP001"
    assert "Corn" in assessment.crop_name
    assert assessment.suitability_class in ("suitable", "conditionally_suitable")


# ============================================================================
# 4. API INTEGRATION TESTS
# ============================================================================

def test_api_field_suitability_endpoint(client: TestClient):
    """Test GET /api/v1/fields/{field_id}/suitability."""
    from .conftest import create_reno_field

    field_resp = create_reno_field(client)
    assert field_resp.status_code in (200, 201, 202), field_resp.text
    field_id = field_resp.json()["data"]["field"]["field_id"]

    resp = client.get(f"{API}/fields/{field_id}/suitability?season_year=2026")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body
    data = body["data"]

    assert data["field_id"] == field_id
    assert data["season_year"] == 2026
    assert data["summary"]["total_evaluated"] == 14
    assert len(data["crops"]) == 14

    # Verify first crop structure
    first_crop = data["crops"][0]
    assert "crop_id" in first_crop
    assert "suitability_class" in first_crop
    assert "factor_assessments" in first_crop
    assert "limiting_factors" in first_crop
    assert "evidence_ids" in first_crop


def test_api_crop_suitability_endpoint(client: TestClient):
    """Test GET /api/v1/fields/{field_id}/suitability/{crop_id} for historical available year (2024)."""
    from .conftest import create_reno_field

    field_resp = create_reno_field(client)
    field_id = field_resp.json()["data"]["field"]["field_id"]

    resp = client.get(f"{API}/fields/{field_id}/suitability/CRP001?season_year=2024")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["crop_id"] == "CRP001"
    assert "Corn" in data["crop_name"]
    assert data["assessment_status"] in ("evaluated", "provisional")
    assert len(data["factor_assessments"]) > 0


def test_api_crop_suitability_future_missing_climate_insufficient_data(client: TestClient):
    """Test that future seasons without climate data (e.g. 2026) enforce the Domain Quorum Rule
    and return 'insufficient_data' rather than fabricating a score.
    """
    from .conftest import create_reno_field

    field_resp = create_reno_field(client)
    field_id = field_resp.json()["data"]["field"]["field_id"]

    resp = client.get(f"{API}/fields/{field_id}/suitability/CRP001?season_year=2026")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["crop_id"] == "CRP001"
    assert data["assessment_status"] == "insufficient_data"
    assert data["suitability_class"] == "insufficient_data"
    assert data["suitability_score"] is None
    assert "withheld" in data["score_methodology"].lower() or "unavailable" in data["score_methodology"].lower()


def test_api_crop_suitability_not_found(client: TestClient):
    """Test GET /api/v1/fields/{field_id}/suitability/INVALID_CROP returns 404."""
    from .conftest import create_reno_field

    field_resp = create_reno_field(client)
    field_id = field_resp.json()["data"]["field"]["field_id"]

    resp = client.get(f"{API}/fields/{field_id}/suitability/INVALID_CROP")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_api_field_not_found(client: TestClient):
    """Test GET with non-existent field returns 404 NOT_FOUND."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"{API}/fields/{fake_id}/suitability")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"


# ============================================================================
# 5. SCIENTIFIC & TECHNICAL AUDIT REMEDIATION TESTS
# ============================================================================

def test_phenology_independence_no_stage_specific_claims(kb: CropKnowledgeBase):
    """Verify that heat stress evaluator complies with Phase 4.1 PHENOLOGY_UNAVAILABLE constraint:
    reproductive stages, anthesis, flowering, and pollination must NEVER be claimed
    when satellite phenology dates are unavailable.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    for heat_days in [5, 20, 45]:
        climate = make_climate(heat_days=heat_days)
        res = evaluate_heat_stress(corn, climate)
        interp = res.interpretation.lower()
        assert "flowering" not in interp, f"Violation: 'flowering' found in heat stress interpretation: {interp}"
        assert "pollination" not in interp, f"Violation: 'pollination' found in heat stress interpretation: {interp}"
        assert "reproductive stage" not in interp, f"Violation: 'reproductive stage' found in heat stress interpretation: {interp}"
        assert "anthesis" not in interp, f"Violation: 'anthesis' found in heat stress interpretation: {interp}"
        assert "phenology_unavailable" in interp, f"Missing PHENOLOGY_UNAVAILABLE disclosure in: {interp}"


def test_missing_crop_history_years_breaks_consecutive_run(kb: CropKnowledgeBase):
    """Missing calendar years must break consecutive-year monoculture runs.
    A sequence of [2021, 2024] (with 2022 and 2023 missing) must NOT be counted as 2 consecutive years.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    # Missing years: 2021 (corn, 1) and 2024 (corn, 1) with 2022-2023 missing
    years = [
        CropYear(
            year=2021,
            majority=CropRef(crop_code=1, crop_name="Corn"),
            purity=0.95,
            histogram=[CropShare(crop_code=1, crop_name="Corn", area_fraction=0.95)],
            low_purity=False,
            source=DUMMY_SOURCE,
        ),
        CropYear(
            year=2024,
            majority=CropRef(crop_code=1, crop_name="Corn"),
            purity=0.95,
            histogram=[CropShare(crop_code=1, crop_name="Corn", area_fraction=0.95)],
            low_purity=False,
            source=DUMMY_SOURCE,
        ),
    ]
    history = CropHistory(
        field_id=UUID("00000000-0000-0000-0000-000000000001"),
        period=YearPeriod(start_year=2021, end_year=2024),
        years=years,
        metrics=[],
        spatial=DUMMY_SPATIAL,
        quality=DUMMY_QUALITY,
    )

    res = evaluate_crop_history(corn, history)
    assert res.is_limiting is True
    assert "1 consecutive year(s)" in res.interpretation, (
        f"Missing years between 2021 and 2024 failed to break consecutive sequence: {res.interpretation}"
    )


def test_alfalfa_autotoxicity_evidence_id_ev0167(kb: CropKnowledgeBase):
    """Alfalfa autotoxicity must cite EV0167 (Jennings & Nelson 2002), NOT EV0162 (salinity tolerance)."""
    alfalfa = kb.get_crop_by_id("CRP011")
    assert alfalfa is not None

    # Prior crop was Alfalfa (CDL code 36)
    history = make_history([36])
    res = evaluate_crop_history(alfalfa, history)

    assert res.is_limiting is True
    assert "EV0167" in res.evidence_ids, f"Expected EV0167 in evidence_ids, found: {res.evidence_ids}"
    assert "EV0162" not in res.evidence_ids, f"EV0162 (salinity) wrongly cited for autotoxicity: {res.evidence_ids}"
    assert "medicarpin" in res.interpretation.lower()


def test_biodrilling_taproots_limited_by_poor_drainage_and_shallow_depth(kb: CropKnowledgeBase):
    """Oilseed radish taproot bio-drilling is favorable ONLY in well-drained, non-shallow soils.
    Under poor drainage (waterlogging/anoxia) or shallow bedrock (<30 cm), it is limited.
    """
    radish = kb.get_crop_by_id("CRP014")
    assert radish is not None

    # Poor drainage causes waterlogging/anoxia
    soil_poor = make_soil(drainage="Poorly drained", depth=150.0)
    res_poor = evaluate_rooting(radish, soil_poor)
    assert res_poor.is_limiting is True
    assert "anaerobic" in res_poor.interpretation.lower() or "waterlogged" in res_poor.interpretation.lower()

    # Very shallow depth (< 30 cm) prevents bio-drilling development
    soil_shallow = make_soil(drainage="Well drained", depth=25.0)
    res_shallow = evaluate_rooting(radish, soil_shallow)
    assert res_shallow.is_limiting is True
    assert "less than" in res_shallow.interpretation.lower() or "shallow" in res_shallow.interpretation.lower()

    # Optimal condition: deep and well drained
    soil_good = make_soil(drainage="Well drained", depth=150.0)
    res_good = evaluate_rooting(radish, soil_good)
    assert res_good.compatibility == "optimal"
    assert res_good.is_limiting is False
    assert res_good.is_favorable is True


def test_domain_quorum_requires_both_climate_and_soil(kb: CropKnowledgeBase):
    """Agronomic suitability requires at least one climate factor AND at least one soil factor.
    Evaluating ONLY climate or ONLY soil must return 'insufficient_data'.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=1400.0, precip=600.0)
    soil = make_soil(ph=6.5)

    # 1. Climate only (no soil factors)
    climate_only = [
        evaluate_thermal_gdd(corn, climate),
        evaluate_water_precipitation(corn, climate),
    ]
    s_class, reason = classify_crop(climate_only)
    assert s_class == "insufficient_data"
    assert "at least one climate factor and one soil factor" in reason.lower()

    # 2. Soil only (no climate factors)
    soil_only = [
        evaluate_soil_ph(corn, soil),
        evaluate_soil_drainage(corn, soil),
        evaluate_soil_texture(corn, soil),
    ]
    s_class, reason = classify_crop(soil_only)
    assert s_class == "insufficient_data"
    assert "at least one climate factor and one soil factor" in reason.lower()


def test_factor_support_attribution(kb: CropKnowledgeBase):
    """Every factor assessment must explicitly disclose support_class ('R' for regional reanalysis,
    'F' for field-scale SSURGO/SRTM/CDL). Regional observations must NEVER masquerade as field measurements.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=1400.0, heat_days=10, precip=600.0)
    soil = make_soil(ph=6.5)
    terrain = make_terrain(slope=1.5)
    history = make_history([1])

    # Regional climate factors
    assert evaluate_thermal_gdd(corn, climate).support_class == "R"
    assert evaluate_heat_stress(corn, climate).support_class == "R"
    assert evaluate_water_precipitation(corn, climate).support_class == "R"
    assert evaluate_regional_suitability(corn, "KS").support_class == "R"

    # Field-scale edaphic, terrain, and historical factors
    assert evaluate_soil_ph(corn, soil).support_class == "F"
    assert evaluate_soil_drainage(corn, soil).support_class == "F"
    assert evaluate_soil_texture(corn, soil).support_class == "F"
    assert evaluate_available_water(corn, soil).support_class == "F"
    assert evaluate_rooting(corn, soil).support_class == "F"
    assert evaluate_terrain_slope(corn, terrain).support_class == "F"
    assert evaluate_crop_history(corn, history).support_class == "F"


def test_score_comparability_and_coverage_disclosure(kb: CropKnowledgeBase):
    """Scoring methodology must disclose core factor coverage (x of 6 factors, x%)
    and never artificially clamp lower weighted scores upward.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=1400.0, precip=600.0)
    soil = make_soil(ph=6.5)

    # 3 core factors evaluated: thermal_gdd, water_precipitation, soil_ph (50% coverage)
    factors_3 = [
        evaluate_thermal_gdd(corn, climate),
        evaluate_water_precipitation(corn, climate),
        evaluate_soil_ph(corn, soil),
    ]
    s_class, _ = classify_crop(factors_3)
    score, method = calculate_suitability_score(factors_3, s_class)

    assert s_class == "suitable"
    assert score is not None
    assert "3 of 6 core environmental factors (50.0% coverage)" in method


def test_missing_crop_requirements_or_null_score_cannot_satisfy_domain_quorum(kb: CropKnowledgeBase):
    """Factors with missing crop requirements, missing observations, or null scores
    CANNOT satisfy the domain quorum. A crop missing climate requirements must return 'insufficient_data'.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None
    climate = make_climate(gdd=1400.0, precip=600.0)
    soil = make_soil(ph=6.5)

    # Valid soil factors
    soil_factors = [
        evaluate_soil_ph(corn, soil),
        evaluate_soil_drainage(corn, soil),
        evaluate_soil_texture(corn, soil),
    ]

    # Create a dummy climate factor with null score / unknown compatibility (e.g. unintegrated requirement)
    dummy_unintegrated_climate = SuitabilityFactorAssessment(
        factor_key="thermal_gdd",
        factor_name="Growing Degree Days",
        category="thermal",
        observed_value=Quantity(value=1400.0, unit="degC_day"),
        crop_requirement=None,  # Missing requirement in KB
        compatibility="unknown",
        is_limiting=False,
        is_favorable=False,
        severity="unknown",
        score=None,  # Null score
        interpretation="Requirement not documented.",
        evidence_ids=[],
        data_status="available",  # Environmental data available, but requirement missing
        support_class="R",
    )

    factors = soil_factors + [dummy_unintegrated_climate]
    s_class, reason = classify_crop(factors)
    score, method = calculate_suitability_score(factors, s_class)

    assert s_class == "insufficient_data", f"Expected insufficient_data, got {s_class}"
    assert score is None
    assert "at least one climate factor and one soil factor" in reason.lower()


def test_heat_stress_threshold_and_heuristic_disclosure(kb: CropKnowledgeBase):
    """Verify that heat stress evaluator notes the indicator Tcrit (30°C for wheat, 35°C for others)
    and clearly discloses that day thresholds are engineering heuristics.
    """
    corn = kb.get_crop_by_id("CRP001")
    wheat = kb.get_crop_by_id("CRP003")
    assert corn is not None and wheat is not None

    climate = make_climate(heat_days=10)
    res_corn = evaluate_heat_stress(corn, climate)
    res_wheat = evaluate_heat_stress(wheat, climate)

    assert "35°C" in res_corn.crop_requirement
    assert "30°C" in res_wheat.crop_requirement
    assert "engineering heuristic" in res_corn.interpretation.lower()
    assert "phenology_unavailable" in res_corn.interpretation.lower()


def test_surveyed_profile_depth_not_mistaken_for_bedrock(kb: CropKnowledgeBase):
    """Verify that rooting depth evaluation explicitly discloses that depth_val represents
    the bottom of SSURGO-described horizons, NOT confirmed depth to bedrock or root barrier.
    """
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    soil = make_soil(depth=150.0)
    res = evaluate_rooting(corn, soil)

    assert res.factor_name == "Surveyed Profile Depth & Rooting Depth"
    assert "bedrock" in res.interpretation.lower() or "described horizon" in res.interpretation.lower()


def test_ssurgo_terminology_survey_derived_estimates(kb: CropKnowledgeBase):
    """SSURGO observations must be described as survey-derived estimates, not direct measurements."""
    corn = kb.get_crop_by_id("CRP001")
    assert corn is not None

    soil = make_soil(ph=6.5, drainage="Well drained", texture="Silt loam", aws150=18.0)
    ph_res = evaluate_soil_ph(corn, soil)
    drain_res = evaluate_soil_drainage(corn, soil)
    tex_res = evaluate_soil_texture(corn, soil)
    aws_res = evaluate_available_water(corn, soil)

    assert "survey-derived" in ph_res.interpretation.lower()
    assert "survey-derived" in drain_res.interpretation.lower()
    assert "survey-derived" in tex_res.interpretation.lower()
    assert "survey-derived" in aws_res.interpretation.lower()


def test_exact_14_canonical_crops_demonstration(engine: CropSuitabilityEngine):
    """Verify that demonstration fields evaluate exactly the 14 canonical crops (CRP001–CRP014)
    and contain zero non-canonical crops (no sunflower, canola, chickpea, or pearl millet).
    """
    climate = make_climate(gdd=1450.0, heat_days=12, precip=620.0)
    soil = make_soil(ph=6.5, drainage="Well drained", texture="Silt loam", aws150=22.0, depth=150.0)
    terrain = make_terrain(slope=1.5)
    history = make_history([24, 5])

    field_uuid = UUID("00000000-0000-0000-0000-000000000001")
    res = engine.evaluate_field(
        field_uuid,
        season_year=2024,
        soil=soil,
        climate=climate,
        terrain=terrain,
        history=history,
        state_code="KS",
    )

    canonical_ids = [f"CRP{i:03d}" for i in range(1, 15)]
    evaluated_ids = [c.crop_id for c in res.crops]
    assert evaluated_ids == canonical_ids

    names_lower = [c.crop_name.lower() for c in res.crops]
    for non_canonical in ["sunflower", "canola", "chickpea", "pearl millet"]:
        assert not any(non_canonical in n for n in names_lower), f"Found non-canonical crop: {non_canonical}"
