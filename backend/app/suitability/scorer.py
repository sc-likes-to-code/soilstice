"""Phase 6: Suitability Scorer and Classifier.

Implements the Limiting-Factor Principle (Liebig's Law of the Minimum):
- Critical limiting factors cannot be masked or compensated for by favorable factors.
- Any critical factor automatically classifies a crop as 'unsuitable'.
- Missing inputs remain unknown and do not default to 0.0 or penalize into unsuitable.
- Numerical scores are generated only when scientifically justified and are strictly
  bounded by limiting factor scores.
"""

from __future__ import annotations

from app.contracts import SuitabilityClass, SuitabilityFactorAssessment

FACTOR_WEIGHTS: dict[str, float] = {
    "thermal_gdd": 0.20,
    "water_precipitation": 0.20,
    "soil_ph": 0.20,
    "soil_drainage": 0.15,
    "available_water": 0.15,
    "terrain_slope": 0.10,
}


def is_valid_evaluated_factor(f: SuitabilityFactorAssessment) -> bool:
    """A factor is validly evaluated only when observed value, crop requirement,
    non-unknown compatibility, and numerical score are all populated.
    Missing requirements, missing observations, or null scores CANNOT satisfy domain quorum.
    """
    return (
        f.data_status == "available"
        and f.observed_value.value is not None
        and f.crop_requirement is not None
        and f.compatibility != "unknown"
        and f.score is not None
    )


def classify_crop(factors: list[SuitabilityFactorAssessment]) -> tuple[SuitabilityClass, str]:
    """Classify crop suitability using the transparent limiting-factor methodology."""
    critical_factors = [f for f in factors if f.severity == "critical"]
    moderate_factors = [f for f in factors if f.severity == "moderate"]

    # Only factors with valid observations, non-null crop requirements, and valid scores
    # are permitted to satisfy the domain quorum. Factors with missing crop requirements,
    # missing observations, or null scores cannot satisfy domain quorum.
    valid_factors = [f for f in factors if is_valid_evaluated_factor(f)]

    # Domain Quorum Rule: Agronomic suitability requires at least one climate factor
    # AND at least one soil factor, and a minimum of 3 valid evaluated factors overall.
    has_climate = any(f.category in {"thermal", "water_climate"} for f in valid_factors)
    has_soil = any(f.category in {"soil", "rooting"} for f in valid_factors)

    if not has_climate or not has_soil or len(valid_factors) < 3:
        return (
            "insufficient_data",
            "Insufficient environmental observations or crop requirements: agronomic suitability requires at least one climate factor and one soil factor with valid evaluated requirements and scores.",
        )

    # 1. Critical limitations override all else
    if critical_factors:
        crit_names = [f.factor_name for f in critical_factors]
        return (
            "unsuitable",
            f"Crop is classified as unsuitable due to {len(critical_factors)} critical environmental constraint(s): {', '.join(crit_names)}.",
        )

    # 2. Moderate limitations
    if not moderate_factors:
        return (
            "suitable",
            "All evaluated environmental parameters satisfy optimal or compatible crop requirements.",
        )
    elif len(moderate_factors) <= 2:
        mod_names = [f.factor_name for f in moderate_factors]
        return (
            "conditionally_suitable",
            f"Crop is conditionally suitable with {len(moderate_factors)} manageable limitation(s): {', '.join(mod_names)}.",
        )
    else:
        mod_names = [f.factor_name for f in moderate_factors]
        return (
            "limited_suitability",
            f"Crop exhibits limited suitability due to {len(moderate_factors)} compounding constraints: {', '.join(mod_names)}.",
        )


def calculate_suitability_score(
    factors: list[SuitabilityFactorAssessment],
    suitability_class: SuitabilityClass,
) -> tuple[float | None, str | None]:
    """Compute a scientifically defensible numerical score bounded by limiting factors."""
    if suitability_class == "insufficient_data":
        return (
            None,
            "Score withheld: essential environmental observations unavailable for field.",
        )

    scored_factors = [f for f in factors if is_valid_evaluated_factor(f) and f.factor_key in FACTOR_WEIGHTS]

    # Need at least 3 weighted core factors to compute a defensible score
    if len(scored_factors) < 3:
        return (
            None,
            "Provisional assessment: numerical score withheld due to fewer than 3 valid environmental factor scores.",
        )

    total_weight = sum(FACTOR_WEIGHTS[f.factor_key] for f in scored_factors)
    weighted_sum = sum(f.score * FACTOR_WEIGHTS[f.factor_key] for f in scored_factors)  # type: ignore
    raw_score = weighted_sum / total_weight

    min_factor_score = min(f.score for f in scored_factors)  # type: ignore
    coverage_desc = f"{len(scored_factors)} of 6 core environmental factors ({len(scored_factors) / 6 * 100:0.1f}% coverage)"

    # Limiting Factor Bounding:
    # A critical limitation strictly caps the score at min_factor_score and at most 35.0 (engineering ceiling)
    if suitability_class == "unsuitable":
        final_score = min(raw_score, min_factor_score, 35.0)
        methodology = (
            f"Engineering heuristic index: raw weighted average was {raw_score:0.1f}, "
            f"capped at {final_score:0.1f} by critical constraint ({min_factor_score:0.1f}). "
            f"Note: numerical scoring for unsuitable crops is an engineering heuristic ({coverage_desc}); "
            f"biological yield models do not support continuous numerical scoring under critical physiological disqualification."
        )
    elif suitability_class == "limited_suitability":
        final_score = min(raw_score, 59.9)
        methodology = (
            f"Weighted multi-factor score ({final_score:0.1f}/100) reflecting compounding limitations "
            f"across {coverage_desc}."
        )
    elif suitability_class == "conditionally_suitable":
        final_score = min(raw_score, 74.9)
        methodology = (
            f"Weighted multi-factor score ({final_score:0.1f}/100) reflecting manageable conditional limitations "
            f"across {coverage_desc}."
        )
    else:  # suitable
        final_score = min(raw_score, 100.0)
        methodology = (
            f"Weighted multi-factor score ({final_score:0.1f}/100) reflecting high environmental compatibility "
            f"across {coverage_desc}."
        )

    return round(final_score, 1), methodology
