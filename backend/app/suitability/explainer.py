"""Phase 6: Suitability Explainer.

Generates evidence-backed agronomic explanations and extracts
limiting, favorable, and unknown factors.
"""

from __future__ import annotations

from app.contracts import (
    CropProfile,
    SuitabilityClass,
    SuitabilityFactorAssessment,
)


def extract_factor_lists(
    factors: list[SuitabilityFactorAssessment],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Extract limiting, favorable, unknown factor summaries and collected evidence IDs."""
    limiting: list[str] = []
    favorable: list[str] = []
    unknown: list[str] = []
    ev_ids_set: set[str] = set()

    for f in factors:
        for eid in f.evidence_ids:
            if eid and eid.startswith("EV"):
                ev_ids_set.add(eid)

        if f.is_limiting:
            severity_tag = "[CRITICAL] " if f.severity == "critical" else "[MODERATE] "
            limiting.append(f"{severity_tag}{f.factor_name}: {f.interpretation}")
        elif f.is_favorable:
            favorable.append(f"{f.factor_name}: {f.interpretation}")
        elif f.data_status in {"missing", "not_integrated"} or f.compatibility == "unknown":
            unknown.append(f"{f.factor_name}: Data unavailable or requirement not documented.")

    return limiting, favorable, unknown, sorted(list(ev_ids_set))


def build_explanation(
    crop: CropProfile,
    suitability_class: SuitabilityClass,
    limiting: list[str],
    favorable: list[str],
    unknown: list[str],
    class_reason: str,
) -> str:
    """Compose an evidence-backed narrative explanation of the suitability assessment."""
    lines = [f"{crop.common_name} ({crop.scientific_name}) is classified as '{suitability_class.replace('_', ' ').title()}'. {class_reason}"]

    if limiting:
        lines.append(f"Identified limitations ({len(limiting)}):")
        for lim in limiting:
            lines.append(f"• {lim}")

    if favorable:
        lines.append(f"Favorable conditions ({len(favorable)}):")
        for fav in favorable:
            lines.append(f"• {fav}")

    if unknown:
        lines.append(f"Uncertainty / Missing data ({len(unknown)}):")
        for unk in unknown:
            lines.append(f"• {unk}")

    return "\n\n".join(lines)


def build_limitations_list(
    factors: list[SuitabilityFactorAssessment],
    crop: CropProfile,
) -> list[str]:
    """Collect scientific limitations and guardrails for this crop evaluation."""
    limits = [
        "Decision-support advisory only: does not constitute a guaranteed crop emergence, yield, or commercial return.",
        "Regional climate observations (NASA POWER, ~50 km spatial grid) do not substitute for in-situ field weather monitoring.",
        "SSURGO soil indicators represent survey-derived polygon-weighted mapunit approximations rather than direct laboratory soil core tests or in-situ field sensor measurements.",
        "SSURGO profile depth reflects the lower boundary of described soil horizons (typically 100–150 cm), not confirmed depth to restrictive bedrock layers or in-situ root penetration resistance.",
    ]

    # Crop-specific limitations from Phase 5 KB
    if crop.crop_id == "CRP014":
        limits.append("Oilseed radish scavenging captures up to 100–220 kg N/ha of residual soil nitrate; this is recycled profile N, NOT newly fixed biological N.")
        limits.append("Radish winter-kill efficacy requires sustained temperatures <= -6°C to -9°C for >= 4–6 continuous hours.")
    elif crop.crop_id in {"CRP012", "CRP013"}:
        limits.append("Legume gross biological nitrogen fixation is not net soil organic nitrogen addition due to mineralization and potential leaching losses upon termination.")
    elif crop.crop_id == "CRP011":
        limits.append("Alfalfa stand re-establishment into preceding alfalfa is inhibited by medicarpin autotoxicity; requires a 1–2 year rotational break.")
    elif crop.crop_id == "CRP001":
        limits.append("Corn yield benefits following taproot cover crops are conditional on compacted subsoils and summer water stress; premiums are negligible in uncompacted soils.")

    return limits
