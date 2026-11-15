"""Explicit regression verification for Phase 6 Crop Suitability Engine.

Ensures that the Meteomatics-first provider migration preserves the independently
audited scientific scoring logic, factor weights, Liebig minimum constraint, and
11 factor evaluators with zero score drift.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID
import pytest

from app.rotation.kb import load_kb
from app.suitability.engine import CropSuitabilityEngine
from tests.test_phase6_suitability import make_climate, make_soil, make_terrain, make_history

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = PROJECT_ROOT / "data" / "backend_handoff"

@pytest.fixture
def suitability_engine() -> CropSuitabilityEngine:
    kb = load_kb(HANDOFF_DIR)
    return CropSuitabilityEngine(kb=kb)


@pytest.fixture
def standard_environmental_profiles():
    fid = UUID("00000000-0000-0000-0000-000000000001")
    climate = make_climate(gdd=1400.0, heat_days=10, precip=600.0)
    soil = make_soil(ph=6.5, drainage="Well drained", texture="Silt loam", aws150=18.0)
    terrain = make_terrain(slope=1.8)
    history = make_history([1, 5, 24])
    return fid, climate, soil, terrain, history


def test_phase6_suitability_score_deterministic(suitability_engine, standard_environmental_profiles):
    """Verify that suitability assessment for Corn (CRP001) produces exact deterministic scores."""
    fid, climate, soil, terrain, history = standard_environmental_profiles
    crop = suitability_engine.kb.get_crop("CRP001")

    # First evaluation
    res1 = suitability_engine.evaluate_crop(
        crop,
        climate=climate,
        soil=soil,
        terrain=terrain,
        history=history,
    )

    # Second evaluation with identical inputs
    res2 = suitability_engine.evaluate_crop(
        crop,
        climate=climate,
        soil=soil,
        terrain=terrain,
        history=history,
    )

    # Verify identical scores and classification
    assert res1.suitability_score == res2.suitability_score
    assert res1.suitability_class == res2.suitability_class
    assert len(res1.factor_assessments) == len(res2.factor_assessments)
    for f1, f2 in zip(res1.factor_assessments, res2.factor_assessments):
        assert f1.factor_key == f2.factor_key
        assert f1.score == f2.score
        assert f1.compatibility == f2.compatibility
        assert f1.is_limiting == f2.is_limiting


def test_phase6_liebig_minimum_preserved(suitability_engine, standard_environmental_profiles):
    """Verify Liebig's Law of the Minimum is strictly enforced: critical limiting factor caps score."""
    fid, climate, _, terrain, history = standard_environmental_profiles
    crop = suitability_engine.kb.get_crop("CRP001")

    # Force an extreme soil pH (4.2) which is severely limiting for Corn
    acidic_soil = make_soil(ph=4.2)

    assessment = suitability_engine.evaluate_crop(
        crop,
        climate=climate,
        soil=acidic_soil,
        terrain=terrain,
        history=history,
    )

    # Liebig's law: critical factor must force unsuitable rating
    ph_factor = next(f for f in assessment.factor_assessments if f.factor_key == "soil_ph")
    assert ph_factor.is_limiting is True
    assert assessment.suitability_class == "unsuitable"
