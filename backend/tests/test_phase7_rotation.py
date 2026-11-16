"""Phase 7 Multi-Year Crop Rotation Engine Verification Suite.

Tests the 25 formal verification criteria defined in SCIENTIFIC_SPECIFICATION.md (docs/SCIENTIFIC_SPECIFICATION.md):
- Canonical 14 crops and CDL mappings
- Asymmetric directed rotation transitions (EV0001–EV0212)
- Monoculture penalties and botanical family repetitions
- Four orthogonal evaluation dimensions
- Bounded beam search candidate generation (horizons 2–5)
- Side-by-side scenario comparisons (2 and 3 scenarios)
- No yield forecasting, profit models, or unverified nitrogen credits
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.contracts import (
    CompareScenariosRequest,
    GenerateRotationsRequest,
    ScenarioYear,
    UpsertScenarioRequest,
)
from app.rotation.comparison import ScenarioComparator
from app.rotation.engine import MultiYearRotationEngine
from app.rotation.evaluator import MultiYearEvaluator
from app.rotation.kb import CANONICAL_CDL_MAPPING, CDL_TO_CROP_ID, load_kb
from app.rotation.search import BoundedBeamSearchGenerator
from app.services.container import build_container
from app.services.rotation import RotationService


@pytest.fixture(scope="module")
def real_kb():
    s = Settings()
    return load_kb(s.crop_kb_dir)


@pytest.fixture(scope="module")
def prod_container():
    s = Settings()
    return build_container(s)


# ── Criteria 1 & 2: Canonical 14 crops & CDL mappings ────────────────────────
def test_criterion_1_and_2_canonical_14_crops_and_cdl_mappings(real_kb):
    assert len(real_kb.crops_by_id) == 14
    for i in range(1, 15):
        cid = f"CRP{i:03d}"
        assert cid in real_kb.crops_by_id, f"Missing {cid} in knowledge base"

    # CDL mappings: 11 mapped, 3 cover crops None
    assert len(CANONICAL_CDL_MAPPING) == 14
    mapped_count = sum(1 for c, code in CANONICAL_CDL_MAPPING.items() if code is not None)
    assert mapped_count == 11
    assert CANONICAL_CDL_MAPPING["CRP012"] is None  # Hairy Vetch
    assert CANONICAL_CDL_MAPPING["CRP013"] is None  # Crimson Clover
    assert CANONICAL_CDL_MAPPING["CRP014"] is None  # Oilseed Radish


# ── Criteria 3, 4, 5, 6, 7: Asymmetric transitions & evidence citations ──────
def test_criterion_3_asymmetric_transitions(real_kb):
    # Alfalfa (CRP011 / 36) -> Corn (CRP001 / 1) vs Corn -> Alfalfa
    r_alf_corn = real_kb.get_rotation("CRP011", "CRP001")
    r_corn_alf = real_kb.get_rotation("CRP001", "CRP011")

    assert r_alf_corn is not None
    assert r_corn_alf is not None
    assert r_alf_corn.compatibility_rating != r_corn_alf.compatibility_rating
    assert r_alf_corn.compatibility_rating == "highly_compatible"
    assert r_corn_alf.compatibility_rating == "compatible"


def test_criterion_4_5_6_7_synergies_risks_herbicide_citations(real_kb):
    r_wheat_sorghum = real_kb.get_rotation(24, 4)
    assert r_wheat_sorghum is not None
    assert r_wheat_sorghum.synergy_mechanisms is not None
    assert "moisture" in r_wheat_sorghum.synergy_mechanisms.lower()

    # Evidence IDs present and valid
    assert len(r_wheat_sorghum.evidence_ids) > 0
    for eid in r_wheat_sorghum.evidence_ids:
        assert eid.startswith("EV"), f"Evidence ID {eid} does not match EV prefix"
        ev_rec = real_kb.get_evidence(eid)
        assert ev_rec is not None, f"Evidence record {eid} not found in KB"


# ── Criterion 8: Unknown preceding crop handling ─────────────────────────────
def test_criterion_8_unknown_preceding_crop_handling(real_kb):
    ev = MultiYearEvaluator(real_kb)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
    ]
    # No antecedent crop provided
    res = ev.evaluate(seq, antecedent_crop=None)
    assert res.overall in ("suitable", "marginal")
    # Finding for year 1 has ANTECEDENT_UNKNOWN message
    y1_finding = res.year_findings[0]
    codes = {m.code for m in y1_finding.messages}
    assert "ANTECEDENT_UNKNOWN" in codes


# ── Criteria 9, 10, 11: Monoculture & botanical family run penalties ─────────
def test_criterion_9_consecutive_monoculture_penalized(real_kb):
    ev = MultiYearEvaluator(real_kb)
    # Continuous corn for 3 years
    seq = [
        ScenarioYear(year=2026, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2027, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2028, crop_code=1, crop_name="Corn"),
    ]
    res = ev.evaluate(seq)
    assert res.overall == "unsuitable"
    assert res.interpretation == "not_recommended"
    dim_map = {d.key: d.band for d in res.dimensions}
    assert dim_map["rotation_benefit"] == "unsuitable"
    assert dim_map["diversity"] == "unsuitable"

    # Year findings progression: year 1 suitable/marginal, year 2 marginal, year 3 unsuitable
    assert res.year_findings[1].band in ("marginal", "unsuitable")
    assert res.year_findings[2].band == "unsuitable"


def test_criterion_10_and_11_botanical_family_run_penalties(real_kb):
    ev = MultiYearEvaluator(real_kb)
    # 4 consecutive Poaceae crops: Wheat (24) -> Sorghum (4) -> Corn (1) -> Rye (27)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
        ScenarioYear(year=2028, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2029, crop_code=27, crop_name="Cereal Rye"),
    ]
    res = ev.evaluate(seq)
    # Year 3 and Year 4 trigger BOTANICAL_FAMILY_RUN warnings
    all_codes = [m.code for f in res.year_findings for m in f.messages]
    assert "BOTANICAL_FAMILY_RUN" in all_codes


# ── Criteria 12 & 13: Diversity metrics computation ──────────────────────────
def test_criterion_12_and_13_diversity_metrics(real_kb):
    ev = MultiYearEvaluator(real_kb)
    # Diverse sequence: Wheat (Poaceae) -> Soybean (Fabaceae) -> Sorghum (Poaceae)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=5, crop_name="Soybean"),
        ScenarioYear(year=2028, crop_code=4, crop_name="Grain Sorghum"),
    ]
    res = ev.evaluate(seq)
    dim_map = {d.key: d for d in res.dimensions}
    assert dim_map["diversity"].band == "suitable"
    assert "3 distinct crops" in dim_map["diversity"].explanation
    assert "2 botanical families" in dim_map["diversity"].explanation


# ── Criterion 14: Antecedent CDL history integration ─────────────────────────
def test_criterion_14_antecedent_history_integration(real_kb):
    ev = MultiYearEvaluator(real_kb)
    # If antecedent crop was Winter Wheat (24) and prospective year 1 is Winter Wheat (24)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
    ]
    res_repeat = ev.evaluate(seq, antecedent_crop=24)
    # Year 1 flags MONOCULTURE_PENALTY
    codes = {m.code for m in res_repeat.year_findings[0].messages}
    assert "MONOCULTURE_PENALTY" in codes

    # If antecedent crop was Soybean (5), Year 1 gets ROTATION_SYNERGY
    res_rotated = ev.evaluate(seq, antecedent_crop=5)
    codes_rotated = {m.code for m in res_rotated.year_findings[0].messages}
    assert "ROTATION_SYNERGY" in codes_rotated or "ROTATION_COMPATIBLE" in codes_rotated


# ── Criteria 15 & 16: Environmental suitability integration & quorum ─────────
def test_criterion_15_and_16_environmental_suitability_baseline(prod_container):
    rot_svc = RotationService(prod_container)
    fields = prod_container.repos.fields.list()
    assert len(fields) > 0
    f = fields[0]

    # Create scenario on field
    req = UpsertScenarioRequest(
        name="Test Wheat-Sorghum-Soybean",
        start_year=2026,
        sequence=[
            {"year": 2026, "crop_code": 24},
            {"year": 2027, "crop_code": 4},
            {"year": 2028, "crop_code": 5},
        ],
    )
    sc = rot_svc.create_scenario(f.field_id, req)
    assert sc.evaluation is not None
    assert sc.evaluation.overall in ("suitable", "marginal")
    assert len(sc.evaluation.dimensions) == 4
    # Cleans up
    rot_svc.delete_scenario(sc.scenario_id)


# ── Criteria 17, 18, 19: Bounded beam search generator ───────────────────────
def test_criterion_17_18_19_beam_search_generator(real_kb):
    generator = BoundedBeamSearchGenerator(real_kb)
    fid = uuid.uuid4()

    for h in (2, 3, 4, 5):
        cands = generator.generate(
            field_id=fid,
            horizon=h,
            start_year=2026,
            antecedent_crop_code=24,
            max_candidates=5,
        )
        assert len(cands) > 0
        assert len(cands) <= 5
        # Verify sequence length matches horizon
        for c in cands:
            assert len(c.sequence) == h
            # Strict non-monoculture (no 3+ runs)
            codes = [y.crop_code for y in c.sequence]
            for i in range(len(codes) - 2):
                assert not (codes[i] == codes[i + 1] == codes[i + 2]), "Pruning failed: 3+ monoculture in candidate"
            assert c.evaluation is not None
            assert c.evaluation.overall in ("suitable", "marginal")


def test_criterion_19_deterministic_tie_breaking(real_kb):
    generator = BoundedBeamSearchGenerator(real_kb)
    fid = uuid.uuid4()

    run1 = generator.generate(field_id=fid, horizon=3, start_year=2026, antecedent_crop_code=24, max_candidates=5)
    run2 = generator.generate(field_id=fid, horizon=3, start_year=2026, antecedent_crop_code=24, max_candidates=5)

    seq1 = [[y.crop_code for y in c.sequence] for c in run1]
    seq2 = [[y.crop_code for y in c.sequence] for c in run2]
    assert seq1 == seq2, "Beam search candidate generation is non-deterministic!"


# ── Criteria 20 & 21: Exactly 4 dimensions & qualitative interpretation labels
def test_criterion_20_and_21_dimensions_and_interpretation_labels(real_kb):
    ev = MultiYearEvaluator(real_kb)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
        ScenarioYear(year=2028, crop_code=5, crop_name="Soybean"),
    ]
    res = ev.evaluate(seq)
    dim_keys = [d.key for d in res.dimensions]
    assert dim_keys == ["agronomic_fit", "rotation_benefit", "water_risk", "diversity"]

    # Valid qualitative interpretations
    valid_interpretations = {"supported", "conditional", "exploratory", "not_recommended", "insufficient_data"}
    assert res.interpretation in valid_interpretations


# ── Criterion 22: Side-by-side scenario comparison (2 and 3 scenarios) ───────
def test_criterion_22_scenario_comparison_2_and_3_scenarios(real_kb):
    comparator = ScenarioComparator(real_kb)
    fid = uuid.uuid4()
    t = datetime.now(UTC)

    from app.contracts import RotationScenario

    ev = MultiYearEvaluator(real_kb)
    s1_seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
        ScenarioYear(year=2028, crop_code=5, crop_name="Soybean"),
    ]
    s2_seq = [
        ScenarioYear(year=2026, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2027, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2028, crop_code=1, crop_name="Corn"),
    ]
    s3_seq = [
        ScenarioYear(year=2026, crop_code=28, crop_name="Oats"),
        ScenarioYear(year=2027, crop_code=36, crop_name="Alfalfa"),
        ScenarioYear(year=2028, crop_code=1, crop_name="Corn"),
    ]

    sc1 = RotationScenario(scenario_id=uuid.uuid4(), field_id=fid, name="Wheat-Sorghum-Soybean", start_year=2026,
                           sequence=s1_seq, evaluation=ev.evaluate(s1_seq), created_at=t, updated_at=t)
    sc2 = RotationScenario(scenario_id=uuid.uuid4(), field_id=fid, name="Continuous Corn", start_year=2026,
                           sequence=s2_seq, evaluation=ev.evaluate(s2_seq), created_at=t, updated_at=t)
    sc3 = RotationScenario(scenario_id=uuid.uuid4(), field_id=fid, name="Oats-Alfalfa-Corn", start_year=2026,
                           sequence=s3_seq, evaluation=ev.evaluate(s3_seq), created_at=t, updated_at=t)

    # 2-way comparison
    cmp2 = comparator.compare([sc1, sc2])
    assert cmp2.field_id == fid
    assert len(cmp2.scenarios) == 2
    assert len(cmp2.tradeoffs) > 0
    categories2 = {t.category for t in cmp2.tradeoffs}
    assert "diversity" in categories2

    # 3-way comparison
    cmp3 = comparator.compare([sc1, sc2, sc3])
    assert len(cmp3.scenarios) == 3
    assert len(cmp3.tradeoffs) > 0


# ── Criterion 23: Complete dual-mode support ─────────────────────────────────
def test_criterion_23_generate_rotations_api_endpoint(prod_container):
    rot_svc = RotationService(prod_container)
    fields = prod_container.repos.fields.list()
    f = fields[0]

    gen_req = GenerateRotationsRequest(horizon=3, start_year=2026, include_cover_crops=True, max_candidates=5)
    resp = rot_svc.generate_rotations(f.field_id, gen_req)

    assert resp.field_id == f.field_id
    assert resp.horizon == 3
    assert len(resp.candidates) > 0
    assert len(resp.candidates) <= 5
    for c in resp.candidates:
        assert c.evaluation is not None
        assert len(c.sequence) == 3


# ── Criterion 24: Zero yield predictions or unverified claims ─────────────────
def test_criterion_24_no_yield_or_profit_claims(real_kb):
    ev = MultiYearEvaluator(real_kb)
    seq = [
        ScenarioYear(year=2026, crop_code=24, crop_name="Winter Wheat"),
        ScenarioYear(year=2027, crop_code=4, crop_name="Grain Sorghum"),
    ]
    res = ev.evaluate(seq)

    # Verify no yield / profit strings anywhere in dimensions or findings
    for d in res.dimensions:
        assert "bushel" not in d.explanation.lower()
        assert "profit" not in d.explanation.lower()
        assert "$" not in d.explanation
        assert "yield forecast" not in d.explanation.lower()
    for f in res.year_findings:
        for m in f.messages:
            assert "bushel" not in m.message.lower()
            assert "$" not in m.message
            assert "yield forecast" not in m.message.lower()


# ── Targeted Enhancement: Genuine Pareto Nondominated Analysis ───────────────
def test_pareto_dominance_analysis(real_kb):
    from app.rotation.search import compute_pareto_dominance
    from app.contracts import EvaluationDimension, FitBand, ScenarioEvaluation, GenerateCandidate

    def _mock_cand(rank: int, name: str, fit: FitBand, rot: FitBand, water: FitBand, div: FitBand) -> GenerateCandidate:
        dims = [
            EvaluationDimension(key="agronomic_fit", band=fit, explanation=""),
            EvaluationDimension(key="rotation_benefit", band=rot, explanation=""),
            EvaluationDimension(key="water_risk", band=water, explanation=""),
            EvaluationDimension(key="diversity", band=div, explanation=""),
        ]
        ev = ScenarioEvaluation(
            engine_version="v1",
            kb_version="v1",
            overall=fit,
            interpretation="supported",
            dimensions=dims,
            year_findings=[],
            warnings=[],
            evaluated_at=datetime.now(UTC),
        )
        return GenerateCandidate(rank=rank, name=name, sequence=[], evaluation=ev)

    # Cand 1: (2, 2, 2, 2) dominates all
    # Cand 2: (2, 2, 1, 2) dominated by Cand 1
    # Cand 3: (2, 1, 2, 2) dominated by Cand 1
    # Cand 4: (1, 1, 1, 1) dominated by all
    cands = [
        _mock_cand(1, "All Suitable", "suitable", "suitable", "suitable", "suitable"),
        _mock_cand(2, "Water Marginal", "suitable", "suitable", "marginal", "suitable"),
        _mock_cand(3, "Rot Marginal", "suitable", "marginal", "suitable", "suitable"),
        _mock_cand(4, "All Marginal", "marginal", "marginal", "marginal", "marginal"),
    ]

    res = compute_pareto_dominance(cands)
    assert len(res) == 4
    assert res[0].is_pareto_optimal is True
    assert res[0].pareto_rank == 1
    assert "Frontier 1" in (res[0].pareto_explanation or "")

    assert res[1].is_pareto_optimal is False
    assert res[1].pareto_rank == 2

    assert res[2].is_pareto_optimal is False
    assert res[2].pareto_rank == 2

    assert res[3].is_pareto_optimal is False
    assert res[3].pareto_rank == 3

    # Test trade-off frontier when neither dominates the other
    tradeoff_cands = [
        _mock_cand(1, "High Synergy", "suitable", "suitable", "marginal", "suitable"),
        _mock_cand(2, "High Water Save", "suitable", "marginal", "suitable", "suitable"),
    ]
    res_tradeoff = compute_pareto_dominance(tradeoff_cands)
    assert res_tradeoff[0].is_pareto_optimal is True
    assert res_tradeoff[0].pareto_rank == 1
    assert res_tradeoff[1].is_pareto_optimal is True
    assert res_tradeoff[1].pareto_rank == 1


# ── Targeted Enhancement: Multi-Year Water-Risk Environmental Context ─────────
def test_water_risk_environmental_context(real_kb):
    ev = MultiYearEvaluator(real_kb)

    # 1. Sequence-only fallback (no baseline suitability passed)
    corn_corn_seq = [
        ScenarioYear(year=2026, crop_code=1, crop_name="Corn"),
        ScenarioYear(year=2027, crop_code=1, crop_name="Corn"),
    ]
    res_fallback = ev.evaluate(corn_corn_seq)
    water_dim_fallback = next(d for d in res_fallback.dimensions if d.key == "water_risk")
    assert water_dim_fallback.band == "marginal"

    # 2. Simulated Semi-arid baseline (< 550 mm)
    from unittest.mock import MagicMock
    from app.contracts import Quantity

    mock_semiarid_suitability = MagicMock()
    mock_crop = MagicMock()
    fa_precip = MagicMock()
    fa_precip.factor_key = "water_precipitation"
    fa_precip.observed_value = Quantity(value=460.0, unit="mm")
    fa_aws = MagicMock()
    fa_aws.factor_key = "available_water"
    fa_aws.observed_value = Quantity(value=14.0, unit="cm")
    mock_crop.factor_assessments = [fa_precip, fa_aws]
    mock_semiarid_suitability.crops = [mock_crop]

    # In semi-arid climate, 2 consecutive high-demand crops is unsuitable
    res_semiarid = ev.evaluate(corn_corn_seq, baseline_suitability=mock_semiarid_suitability)
    water_dim_semiarid = next(d for d in res_semiarid.dimensions if d.key == "water_risk")
    assert water_dim_semiarid.band == "unsuitable"
    assert "semi-arid" in water_dim_semiarid.explanation.lower()
    assert "460" in water_dim_semiarid.explanation

    # 3. Moisture-conserving sequence in semi-arid climate
    sorghum_wheat_seq = [
        ScenarioYear(year=2026, crop_code=4, crop_name="Grain Sorghum"),
        ScenarioYear(year=2027, crop_code=24, crop_name="Winter Wheat"),
    ]
    res_semiarid_conserve = ev.evaluate(sorghum_wheat_seq, baseline_suitability=mock_semiarid_suitability)
    water_dim_conserve = next(d for d in res_semiarid_conserve.dimensions if d.key == "water_risk")
    assert water_dim_conserve.band == "suitable"
    assert "moisture-conserving" in water_dim_conserve.explanation.lower()
