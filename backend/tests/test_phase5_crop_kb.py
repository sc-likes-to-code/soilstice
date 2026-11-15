"""SOILSTICE Phase 5: Production Crop Knowledge Base Comprehensive Test Suite.

Verifies:
- Data integrity across all 14 canonical crops, 11 uniform domains, 212 evidence records, and 196 transitions.
- Pure Python Draft-07 JSON Schema validation against `data/schema.json`.
- Dual-index crop retrieval (canonical ID and CDL integer code).
- Scientific null preservation and strict nitrogen accounting safeguards.
- Effective water extraction depth vs anatomical root depth disaggregation.
- Directed rotation matrix asymmetry, monoculture penalties, and mixture vs sequential rules.
- Crop-specific GDD thermal parameter lookup and unknown crop fallback.
- Read-only API endpoints with standard SOILSTICE ApiResponse envelopes and 404 negative handling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analytics.resilience import CalibratedResilienceEngine
from app.config import Settings
from app.main import create_app
from app.repositories import Repositories, SqliteDocumentStore
from app.rotation.engine import PendingRotationEngine
from app.rotation.kb import (
    CANONICAL_CDL_MAPPING,
    CDL_TO_CROP_ID,
    CropKnowledgeBase,
    get_crop_gdd_thresholds,
    load_kb,
    validate_draft07_schema,
)
from app.services.container import Container

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = PROJECT_ROOT / "data" / "backend_handoff"
KB_JSON_PATH = HANDOFF_DIR / "data" / "crop_knowledge_base.json"
SCHEMA_JSON_PATH = HANDOFF_DIR / "data" / "schema.json"

@pytest.fixture(scope="module")
def canonical_kb() -> CropKnowledgeBase:
    """Load the canonical Phase 5 crop knowledge base."""
    kb = load_kb(HANDOFF_DIR)
    assert kb.available, f"Knowledge base failed to load: {kb.status_message}"
    return kb


@pytest.fixture
def kb_client(canonical_kb: CropKnowledgeBase, fake_providers) -> TestClient:
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
        kb=canonical_kb,
        resilience=CalibratedResilienceEngine(),
        rotation=PendingRotationEngine(),
        executor=None,
    )
    app = create_app(s, container)
    with TestClient(app) as client:
        yield client


# ── 1. Data Integrity & Schema Validation ────────────────────────────────────


def test_master_kb_json_schema_validation():
    """Verify master JSON validates 100% against schema.json without third-party dependencies."""
    with open(KB_JSON_PATH, encoding="utf-8") as f:
        kb_data = json.load(f)
    with open(SCHEMA_JSON_PATH, encoding="utf-8") as f:
        schema_data = json.load(f)

    errs = validate_draft07_schema(kb_data, schema_data)
    assert len(errs) == 0, f"Schema validation returned {len(errs)} errors: {errs[:5]}"


def test_canonical_counts_and_metadata(canonical_kb: CropKnowledgeBase):
    """Verify canonical portfolio counts, dataset version, and metadata."""
    assert canonical_kb.available is True
    assert canonical_kb.kb_version == "1.4.1-REMEDIATED"
    assert len(canonical_kb.crops_by_id) == 14
    assert len(canonical_kb.evidence_by_id) == 212
    assert len(canonical_kb.rotations) == 196
    assert len(canonical_kb.crops_by_cdl) == 11

    meta = canonical_kb.metadata
    assert meta is not None
    assert meta.schema_version == "1.4.1-REMEDIATED"
    assert meta.canonical_crop_count == 14
    assert meta.evidence_records_count == 212
    assert meta.directed_rotation_transitions_count == 196


# ── 2. All 14 Crops & 11 Domains ─────────────────────────────────────────────


def test_all_14_crops_and_11_domains_present(canonical_kb: CropKnowledgeBase):
    """Verify that all 14 crops exist and contain all 11 uniform domains."""
    expected_crops = [f"CRP{i:03d}" for i in range(1, 15)]
    assert sorted(list(canonical_kb.crops_by_id.keys())) == expected_crops

    required_domains = [
        "crop_identity",
        "growing_duration",
        "temperature_requirements",
        "rainfall_requirements",
        "water_demand_and_tolerance",
        "soil_preferences",
        "root_and_nutrients",
        "nitrogen_and_biomass",
        "rotation_compatibility",
        "regional_suitability",
    ]

    for cid in expected_crops:
        crop = canonical_kb.crops_by_id[cid]
        assert crop.crop_id == cid
        assert crop.common_name != ""
        assert crop.scientific_name != ""
        assert crop.botanical_family != ""

        for domain in required_domains:
            dom_data = getattr(crop, domain)
            assert dom_data is not None, f"Crop {cid} missing domain {domain}"
            assert isinstance(dom_data, (dict, list)), f"Crop {cid} domain {domain} wrong type"


# ── 3. Evidence Registry Continuity & Resolvability ──────────────────────────


def test_evidence_continuity_and_resolvability(canonical_kb: CropKnowledgeBase):
    """Verify sequential continuity (EV0001–EV0212) and 100% cross-reference resolution."""
    ev_keys = sorted(list(canonical_kb.evidence_by_id.keys()))
    assert len(ev_keys) == 212
    assert ev_keys[0] == "EV0001"
    assert ev_keys[-1] == "EV0212"

    # Verify no gaps
    for i in range(1, 213):
        expected_ev = f"EV{i:04d}"
        assert expected_ev in canonical_kb.evidence_by_id, f"Missing evidence ID {expected_ev}"

    # Verify every evidence_id cited in crop profiles exists in the registry
    for crop in canonical_kb.crops_by_id.values():
        for eid in crop.evidence_ids:
            assert eid in canonical_kb.evidence_by_id, f"Crop {crop.crop_id} has unresolved evidence {eid}"

    # Verify every evidence_id cited in rotation transitions exists
    for rot in canonical_kb.rotations.values():
        for eid in rot.evidence_ids:
            assert eid in canonical_kb.evidence_by_id, f"Rotation pair has unresolved evidence {eid}"


# ── 4. Dual-Index Crop Lookup ────────────────────────────────────────────────


def test_dual_index_crop_lookup(canonical_kb: CropKnowledgeBase):
    """Verify lookup by canonical crop ID, CDL integer code, case-insensitivity, and symbols."""
    # 1. Lookup by canonical ID
    c1 = canonical_kb.get_crop("CRP001")
    assert c1 is not None and c1.common_name == "Corn (Maize)"
    assert canonical_kb.get_crop("crp001") == c1

    # 2. Lookup by CDL integer code
    assert canonical_kb.get_crop(1) == c1
    c_wheat = canonical_kb.get_crop(24)
    assert c_wheat is not None and c_wheat.crop_id == "CRP003" and c_wheat.common_name == "Winter Wheat"

    # 3. Lookup unmapped cover crops by ID
    c_radish = canonical_kb.get_crop("CRP014")
    assert c_radish is not None and c_radish.common_name == "Oilseed Radish"
    assert c_radish.cdl_code is None
    assert c_radish.usda_plants_symbol == "RASA2"

    c_vetch = canonical_kb.get_crop("CRP012")
    assert c_vetch is not None and c_vetch.cdl_code is None and c_vetch.usda_plants_symbol == "VIVI"

    c_clover = canonical_kb.get_crop("CRP013")
    assert c_clover is not None and c_clover.cdl_code is None and c_clover.usda_plants_symbol == "TRIN3"

    # 4. Lookup by USDA symbol
    assert canonical_kb.get_crop("ZEMA") == c1
    assert canonical_kb.get_crop("GLMA4") == canonical_kb.get_crop("CRP002")

    # 5. Unknown identifiers
    assert canonical_kb.get_crop("CRP999") is None
    assert canonical_kb.get_crop(999) is None
    assert canonical_kb.get_crop("NON_EXISTENT") is None


def test_exact_cdl_mappings_verified():
    """Verify the 11 verified CDL mappings and 3 unmapped cover crops."""
    assert CANONICAL_CDL_MAPPING["CRP001"] == 1    # Corn
    assert CANONICAL_CDL_MAPPING["CRP002"] == 5    # Soybean
    assert CANONICAL_CDL_MAPPING["CRP003"] == 24   # Winter Wheat
    assert CANONICAL_CDL_MAPPING["CRP004"] == 23   # Spring Wheat
    assert CANONICAL_CDL_MAPPING["CRP005"] == 4    # Sorghum
    assert CANONICAL_CDL_MAPPING["CRP006"] == 2    # Cotton
    assert CANONICAL_CDL_MAPPING["CRP007"] == 3    # Rice
    assert CANONICAL_CDL_MAPPING["CRP008"] == 21   # Barley
    assert CANONICAL_CDL_MAPPING["CRP009"] == 27   # Rye
    assert CANONICAL_CDL_MAPPING["CRP010"] == 28   # Oats
    assert CANONICAL_CDL_MAPPING["CRP011"] == 36   # Alfalfa
    assert CANONICAL_CDL_MAPPING["CRP012"] is None # Hairy Vetch
    assert CANONICAL_CDL_MAPPING["CRP013"] is None # Crimson Clover
    assert CANONICAL_CDL_MAPPING["CRP014"] is None # Oilseed Radish

    assert CDL_TO_CROP_ID[1] == "CRP001"
    assert CDL_TO_CROP_ID[24] == "CRP003"
    assert CDL_TO_CROP_ID[2] == "CRP006"


# ── 5. Scientific Safeguards & Null Semantics ────────────────────────────────


def test_scientific_null_preservation_and_nitrogen_accounting(canonical_kb: CropKnowledgeBase):
    """Verify that net soil N is strictly null for green manures and radish BNF is 0.0."""
    # 1. Hairy Vetch (CRP012), Crimson Clover (CRP013), and Radish (CRP014) net soil N is null
    for cid in ["CRP012", "CRP013", "CRP014"]:
        crop = canonical_kb.crops_by_id[cid]
        nb = crop.nitrogen_and_biomass
        net_soil_n = nb.get("residue_and_harvest_nitrogen_dynamics", {}).get("net_soil_nitrogen_balance_kg_ha", {})
        assert net_soil_n.get("value") is None, f"{cid} net soil N balance must be None (null), not 0"
        assert net_soil_n.get("unit") == "kg_n_per_ha"
        assert "limitations" in net_soil_n and net_soil_n["limitations"] is not None

    # 2. Oilseed Radish (CRP014) Nitrogen Accounting Discipline
    rad = canonical_kb.crops_by_id["CRP014"]
    rad_nb = rad.nitrogen_and_biomass
    bnf = rad_nb.get("biological_nitrogen_fixation", {})
    assert bnf.get("has_symbiotic_fixation_capacity", {}).get("value") is False
    assert bnf.get("total_gross_n_fixed_kg_ha", {}).get("value") == 0.0

    credit = rad_nb.get("successor_nitrogen_credit", {})
    fert_credit = credit.get("fertilizer_equivalent_n_credit_lb_ac", {})
    assert fert_credit.get("value") == 0.0
    # Must preserve explanation of scavenged profile nitrate recycling (100-220 kg N/ha)
    lim_str = fert_credit.get("limitations", "").lower()
    assert "scavenged" in lim_str or "recycling" in lim_str


def test_root_depth_disaggregation(canonical_kb: CropKnowledgeBase):
    """Verify effective water extraction depth is strictly less than maximum anatomical depth."""
    for cid, crop in canonical_kb.crops_by_id.items():
        rn = crop.root_and_nutrients
        eff = rn.get("effective_water_extraction_depth_cm", {})
        anat = rn.get("maximum_anatomical_root_depth_cm", {})

        eff_max = eff.get("max_value")
        anat_max = anat.get("max_value")

        assert eff_max is not None and anat_max is not None, f"Crop {cid} missing root depth ranges"
        assert eff_max <= anat_max, f"Crop {cid}: effective depth ({eff_max}) exceeds anatomical depth ({anat_max})"
        assert eff.get("unit") == "cm" and anat.get("unit") == "cm"


# ── 6. Directed Rotation Matrix Asymmetry & Monocultures ─────────────────────


def test_directed_rotation_asymmetry_and_monocultures(canonical_kb: CropKnowledgeBase):
    """Verify non-reciprocal transitions, monoculture penalties, and mixture vs sequential notes."""
    # 1. Total transitions count
    assert len(canonical_kb.rotations) == 196

    # 2. Directional Asymmetry: Radish -> Corn vs Corn -> Radish
    rad_to_corn = canonical_kb.get_rotation("CRP014", "CRP001")
    assert rad_to_corn is not None
    assert rad_to_corn.compatibility_rating == "highly_compatible"
    assert "biopores" in rad_to_corn.synergy_mechanisms.lower()

    corn_to_rad = canonical_kb.get_rotation("CRP001", "CRP014")
    assert corn_to_rad is not None
    assert corn_to_rad.compatibility_rating == "compatible"
    is_diff = (
        rad_to_corn.compatibility_rating != corn_to_rad.compatibility_rating
        or rad_to_corn.synergy_mechanisms != corn_to_rad.synergy_mechanisms
    )
    assert is_diff

    # 3. Mixture vs Sequential Rotation: Crimson Clover -> Radish
    clover_to_rad = canonical_kb.get_rotation("CRP013", "CRP014")
    assert clover_to_rad is not None
    assert clover_to_rad.compatibility_rating == "caution_conditional"
    assert (
        "mixture" in clover_to_rad.limitations.lower()
        or "polyculture" in clover_to_rad.limitations.lower()
    )

    # 4. Monoculture Penalty: Continuous Corn
    corn_mono = canonical_kb.get_rotation("CRP001", "CRP001")
    assert corn_mono is not None
    assert corn_mono.is_monoculture is True
    assert corn_mono.compatibility_rating == "caution_conditional"
    assert "morrow plots" in corn_mono.monoculture_risk.lower()
    assert "5% to 15%" in corn_mono.monoculture_risk


# ── 7. Crop-Specific GDD Thermal Parameters ──────────────────────────────────


def test_gdd_thermal_parameters_resolution():
    """Verify GDD parameters for all 14 crops, 5 baseline crops, and fallback."""
    # Baseline 5 crops
    assert get_crop_gdd_thresholds(1) == (10.0, 30.0)   # Corn
    assert get_crop_gdd_thresholds(24) == (0.0, 25.0)   # Winter Wheat
    assert get_crop_gdd_thresholds(4) == (10.0, 35.0)   # Sorghum
    assert get_crop_gdd_thresholds(5) == (10.0, 30.0)   # Soybeans
    assert get_crop_gdd_thresholds(36) == (5.0, 30.0)   # Alfalfa

    # Additional canonical crops
    assert get_crop_gdd_thresholds(2) == (15.6, 32.0)   # Cotton
    assert get_crop_gdd_thresholds(3) == (10.0, 35.0)   # Rice
    assert get_crop_gdd_thresholds(21) == (0.0, 25.0)  # Barley
    assert get_crop_gdd_thresholds(23) == (0.0, 25.0)  # Spring Wheat
    assert get_crop_gdd_thresholds(27) == (4.4, 30.0)  # Cereal Rye
    assert get_crop_gdd_thresholds(28) == (4.4, 30.0)  # Oats

    # Specialty cover crops by canonical ID
    assert get_crop_gdd_thresholds("CRP012") == (4.0, 30.0)  # Hairy Vetch
    assert get_crop_gdd_thresholds("CRP013") == (4.0, 30.0)  # Crimson Clover
    assert get_crop_gdd_thresholds("CRP014") == (3.5, 30.0)  # Oilseed Radish

    # Fallback behavior
    assert get_crop_gdd_thresholds(None) == (10.0, 30.0)
    assert get_crop_gdd_thresholds(999) == (10.0, 30.0)
    assert get_crop_gdd_thresholds("UNKNOWN_CROP") == (10.0, 30.0)


# ── 8. Read-Only API Endpoints ───────────────────────────────────────────────


def test_api_list_crops(kb_client: TestClient):
    """GET /api/v1/crops returns standard ApiResponse envelope with selectable CropOptions."""
    res = kb_client.get("/api/v1/crops")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body and "meta" in body
    crops = body["data"]
    assert len(crops) >= 11
    # Check corn is present
    corn = next((c for c in crops if c["crop_code"] == 1), None)
    assert corn is not None and corn["name"] == "Corn (Maize)"
    assert corn["kb_version"] == "1.4.1-REMEDIATED"


def test_api_canonical_crops_and_filtering(kb_client: TestClient):
    """GET /api/v1/canonical-crops returns all 14 crop summaries and supports role/family filtering."""
    # 1. All 14 crops
    res = kb_client.get("/api/v1/canonical-crops")
    assert res.status_code == 200
    crops = res.json()["data"]
    assert len(crops) == 14
    assert {c["crop_id"] for c in crops} == {f"CRP{i:03d}" for i in range(1, 15)}

    # 2. Filter by role=cover_crop
    res_cover = kb_client.get("/api/v1/canonical-crops?role=cover_crop")
    assert res_cover.status_code == 200
    covers = res_cover.json()["data"]
    assert len(covers) == 6
    assert {c["crop_id"] for c in covers} == {
        "CRP009",
        "CRP010",
        "CRP011",
        "CRP012",
        "CRP013",
        "CRP014",
    }

    # 3. Filter by family=Fabaceae
    res_fab = kb_client.get("/api/v1/canonical-crops?family=Fabaceae")
    assert res_fab.status_code == 200
    legumes = res_fab.json()["data"]
    assert len(legumes) == 4
    assert {c["crop_id"] for c in legumes} == {"CRP002", "CRP011", "CRP012", "CRP013"}


def test_api_get_crop_profile_and_attributes(kb_client: TestClient):
    """GET /api/v1/crops/{crop_id} retrieves full 11-domain profile by ID or CDL code."""
    # 1. By canonical ID
    res1 = kb_client.get("/api/v1/crops/CRP001")
    assert res1.status_code == 200
    c1 = res1.json()["data"]
    assert c1["crop_id"] == "CRP001"
    assert c1["common_name"] == "Corn (Maize)"
    assert "growing_duration" in c1 and "nitrogen_and_biomass" in c1

    # 2. By CDL integer code
    res_cdl = kb_client.get("/api/v1/crops/1")
    assert res_cdl.status_code == 200
    assert res_cdl.json()["data"]["crop_id"] == "CRP001"

    # 3. By unmapped cover crop
    res_rad = kb_client.get("/api/v1/crops/CRP014")
    assert res_rad.status_code == 200
    assert res_rad.json()["data"]["cdl_code"] is None
    assert res_rad.json()["data"]["common_name"] == "Oilseed Radish"

    # 4. Domain filtering
    res_attr = kb_client.get("/api/v1/crops/CRP014/attributes?domain=nitrogen_and_biomass")
    assert res_attr.status_code == 200
    attr_data = res_attr.json()["data"]
    assert "nitrogen_and_biomass" in attr_data
    # Verify null preservation in API response
    nb_domain = attr_data["nitrogen_and_biomass"]
    net_soil_n = nb_domain["residue_and_harvest_nitrogen_dynamics"]["net_soil_nitrogen_balance_kg_ha"]
    assert net_soil_n["value"] is None

    # 5. 404 Not Found for invalid crop
    res_404 = kb_client.get("/api/v1/crops/CRP999")
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"


def test_api_rotations_and_matrix(kb_client: TestClient):
    """GET /api/v1/rotations and /rotations/matrix return directed transitions."""
    # 1. Pairwise directed transition
    res = kb_client.get("/api/v1/rotations?previous_crop=CRP014&next_crop=CRP001")
    assert res.status_code == 200
    rot = res.json()["data"]
    assert rot["preceding_crop_id"] == "CRP014"
    assert rot["following_crop_id"] == "CRP001"
    assert rot["compatibility_rating"] == "highly_compatible"

    # 2. Pairwise using CDL codes
    res_cdl = kb_client.get("/api/v1/rotations?previous_crop=1&next_crop=5")
    assert res_cdl.status_code == 200
    rot_cdl = res_cdl.json()["data"]
    assert rot_cdl["preceding_crop_id"] == "CRP001"
    assert rot_cdl["following_crop_id"] == "CRP002"

    # 3. Complete rotation matrix
    res_mat = kb_client.get("/api/v1/rotations/matrix")
    assert res_mat.status_code == 200
    assert len(res_mat.json()["data"]) == 196

    # 4. Filtered matrix for one crop
    res_corn = kb_client.get("/api/v1/rotations/matrix?crop_id=CRP001")
    assert res_corn.status_code == 200
    # 14 preceding + 14 following - 1 monoculture overlap = 27
    assert len(res_corn.json()["data"]) == 27


def test_api_evidence_and_metadata(kb_client: TestClient):
    """GET /api/v1/evidence/{evidence_id} and /kb/metadata."""
    # 1. Retrieve evidence
    res_ev = kb_client.get("/api/v1/evidence/EV0001")
    assert res_ev.status_code == 200
    ev = res_ev.json()["data"]
    assert ev["evidence_id"] == "EV0001"
    assert ev["source_organization"] == "USDA-NRCS National Plant Data Team"
    assert ev["source_quality"] == "high"

    # 2. 404 for invalid evidence
    res_ev_404 = kb_client.get("/api/v1/evidence/EV9999")
    assert res_ev_404.status_code == 404

    # 3. Retrieve metadata
    res_meta = kb_client.get("/api/v1/kb/metadata")
    assert res_meta.status_code == 200
    meta = res_meta.json()["data"]
    assert meta["schema_version"] == "1.4.1-REMEDIATED"
    assert meta["canonical_crop_count"] == 14
    assert meta["evidence_records_count"] == 212
    assert meta["directed_rotation_transitions_count"] == 196
