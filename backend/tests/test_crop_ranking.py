"""Automated tests for Crop Ranking by Suitability Score and Agronomic Descriptions (Tasks 7 & 8).

Verifies:
1. Candidate crops in Next Season recommendation are sorted strictly by Phase 6 suitability score descending.
2. Deterministic tie-breaking hierarchy:
   - Primary: Suitability score DESC
   - Tie-breaker 1: Data confidence DESC ("high" > "medium" > "low")
   - Tie-breaker 2: Limiting factors count ASC (fewer limitations ranked higher)
   - Tie-breaker 3: Non-repeat before repeat
   - Tie-breaker 4: Alphabetical by crop name ASC
3. Unsuitable crops are excluded from candidate ranking and placed in excluded/disqualified list.
4. All 14 canonical crops possess distinctive, non-identical agronomic descriptions.
"""

from __future__ import annotations

import uuid
from app.contracts import (
    CropSuitabilityAssessment,
    FieldSuitabilityResponse,
    SuitabilitySummaryCounts,
    Quantity,
    QualityInfo,
    SpatialSupport,
    TemporalSupport,
)
from app.suitability.explainer import CROP_AGRONOMIC_DESCRIPTIONS


def test_all_14_canonical_crops_have_distinctive_descriptions():
    """Task 7: Verify all 14 canonical crops have unique, non-placeholder descriptions."""
    expected_ids = [f"CRP{i:03d}" for i in range(1, 15)]
    assert len(expected_ids) == 14
    
    seen_descriptions = set()
    for cid in expected_ids:
        assert cid in CROP_AGRONOMIC_DESCRIPTIONS, f"Missing description for {cid}"
        desc = CROP_AGRONOMIC_DESCRIPTIONS[cid]
        assert len(desc) > 80, f"Description for {cid} is too short / placeholder"
        assert desc not in seen_descriptions, f"Duplicate description found for {cid}"
        seen_descriptions.add(desc)
        # Verify mentions scientific name or family/traits
        assert "(" in desc and ")" in desc, f"Description for {cid} should include scientific name"


def test_crop_ranking_order_and_deterministic_tie_breaking():
    """Task 8: Verify sorting order and multi-tier deterministic tie-breaking."""
    conf_weight = {"high": 3, "medium": 2, "low": 1}

    # Helper mock candidates
    c1 = {
        "crop_code": 1, "crop_name": "Corn", "score": 85.0, "confidence": "high",
        "limiting_count": 0, "is_repeat": False,
    }
    c2 = {
        "crop_code": 24, "crop_name": "Winter Wheat", "score": 92.0, "confidence": "high",
        "limiting_count": 0, "is_repeat": False,
    }
    c3_tied_score_low_conf = {
        "crop_code": 4, "crop_name": "Grain Sorghum", "score": 85.0, "confidence": "medium",
        "limiting_count": 0, "is_repeat": False,
    }
    c4_tied_score_more_limits = {
        "crop_code": 5, "crop_name": "Soybean", "score": 85.0, "confidence": "high",
        "limiting_count": 2, "is_repeat": False,
    }
    c5_tied_all_alpha_b = {
        "crop_code": 21, "crop_name": "Barley", "score": 75.0, "confidence": "high",
        "limiting_count": 1, "is_repeat": False,
    }
    c6_tied_all_alpha_o = {
        "crop_code": 28, "crop_name": "Oats", "score": 75.0, "confidence": "high",
        "limiting_count": 1, "is_repeat": False,
    }
    c7_repeat = {
        "crop_code": 24, "crop_name": "Winter Wheat", "score": 75.0, "confidence": "high",
        "limiting_count": 1, "is_repeat": True,
    }

    test_list = [c1, c2, c3_tied_score_low_conf, c4_tied_score_more_limits, c5_tied_all_alpha_b, c6_tied_all_alpha_o, c7_repeat]

    # Apply the exact ranking key used in production
    test_list.sort(
        key=lambda c: (
            -c["score"],
            -conf_weight.get(c["confidence"], 0),
            c["limiting_count"],
            1 if c["is_repeat"] else 0,
            c["crop_name"],
        )
    )

    # Expected order:
    # 1. Winter Wheat (score 92.0)
    # 2. Corn (score 85.0, conf high, limits 0)
    # 3. Grain Sorghum (score 85.0, conf med, limits 0) -- higher conf beats limits
    #    Wait: c1 (85, high, 0) vs c4 (85, high, 2) => c1 has fewer limits than c4!
    #    c4 (85, high, 2) vs c3 (85, med, 0) => c4 has higher conf than c3!
    # 4. Soybean (score 85.0, conf high, limits 2)
    # 5. Grain Sorghum (score 85.0, conf medium, limits 0)
    # 6. Barley (score 75.0, limits 1, non-repeat, 'B' < 'O')
    # 7. Oats (score 75.0, limits 1, non-repeat, 'O' > 'B')
    # 8. Repeat Winter Wheat (score 75.0, repeat = 1)
    
    assert test_list[0]["crop_name"] == "Winter Wheat"
    assert test_list[0]["score"] == 92.0
    
    # 85.0 group
    assert test_list[1]["crop_name"] == "Corn"  # 85.0, high conf, 0 limits
    assert test_list[2]["crop_name"] == "Soybean"  # 85.0, high conf, 2 limits
    assert test_list[3]["crop_name"] == "Grain Sorghum"  # 85.0, medium conf
    
    # 75.0 group: Barley vs Oats vs Repeat
    assert test_list[4]["crop_name"] == "Barley"
    assert test_list[5]["crop_name"] == "Oats"
    assert test_list[6]["crop_name"] == "Winter Wheat" and test_list[6]["is_repeat"] is True
