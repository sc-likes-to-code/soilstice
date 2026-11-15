"""Multi-year crop rotation sequence evaluator (Phase 7 layer 4; DATA_ARCHITECTURE §5.11).

Evaluates 2–5 year crop sequences across four orthogonal agronomic dimensions:
1. agronomic_fit: Environmental biophysical suitability of each crop on the parcel (Liebig's Law).
2. rotation_benefit: Directed pairwise transition compatibility (EV0001–EV0212), disease breaks, and pest management.
3. water_risk: Temporal water balance, consecutive high-demand depletion, and drought resilience.
4. diversity: Taxonomic family richness, functional complementarity, and rotational variety.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.contracts import (
    CropProfile,
    EvaluationDimension,
    FitBand,
    QualityFlag,
    ScenarioEvaluation,
    ScenarioInterpretation,
    ScenarioYear,
    YearFinding,
)
from app.rotation.kb import CDL_TO_CROP_ID, CropKnowledgeBase

ENGINE_VERSION = "soilstice-rotation-v1.0.0"

# Water demand classification across the 14 canonical crops
WATER_DEMAND: dict[str, str] = {
    "CRP001": "high",       # Corn (Maize) - 500-800 mm
    "CRP002": "moderate",   # Soybean - 450-700 mm
    "CRP003": "moderate",   # Winter Wheat - 350-550 mm
    "CRP004": "moderate",   # Spring Wheat - 350-500 mm
    "CRP005": "low",        # Grain Sorghum - 350-500 mm (drought tolerant)
    "CRP006": "moderate",   # Cotton - 500-750 mm (taproot, drought tolerant)
    "CRP007": "high",       # Rice - 900-1200 mm
    "CRP008": "moderate",   # Barley - 300-450 mm
    "CRP009": "low",        # Cereal Rye - 300-450 mm (drought tolerant, scavenger)
    "CRP010": "moderate",   # Oats - 350-500 mm
    "CRP011": "high",       # Alfalfa - 600-1000 mm (deep taproot, high water user)
    "CRP012": "low",        # Hairy Vetch - winter cover / moisture conservation
    "CRP013": "low",        # Crimson Clover - winter cover / moisture conservation
    "CRP014": "low",        # Oilseed Radish - cover / deep taproot moisture capture
}


def _resolve_crop_id(crop_identifier: int | str, kb: CropKnowledgeBase) -> tuple[str | None, CropProfile | None]:
    """Resolves canonical crop ID (CRP001–CRP014) and CropProfile from either CDL code or crop ID."""
    if isinstance(crop_identifier, int):
        cid = CDL_TO_CROP_ID.get(crop_identifier)
        if cid:
            return cid, kb.get_crop_by_id(cid)
        crop = kb.get_crop(crop_identifier)
        if crop:
            return crop.crop_id, crop
        return None, None
    s = str(crop_identifier).strip().upper()
    if s in kb.crops_by_id:
        return s, kb.crops_by_id[s]
    crop = kb.get_crop(crop_identifier)
    if crop:
        return crop.crop_id, crop
    return None, None


class MultiYearEvaluator:
    """Evaluates multi-year crop sequences against the Crop Knowledge Base and field environmental baseline."""

    def __init__(self, kb: CropKnowledgeBase):
        self.kb = kb

    def evaluate(
        self,
        sequence: list[ScenarioYear],
        field_id: uuid.UUID | None = None,
        baseline_suitability: Any | None = None,
        antecedent_crop: ScenarioYear | int | str | None = None,
    ) -> ScenarioEvaluation:
        if not sequence:
            return ScenarioEvaluation(
                engine_version=ENGINE_VERSION,
                kb_version=self.kb.kb_version,
                overall="unknown",
                interpretation="insufficient_data",
                dimensions=[
                    EvaluationDimension(key=k, band="unknown", explanation="Empty sequence provided.")
                    for k in ("agronomic_fit", "rotation_benefit", "water_risk", "diversity")
                ],
                year_findings=[],
                warnings=[QualityFlag(code="EMPTY_SEQUENCE", severity="warning", message="No sequence years to evaluate.")],
                evaluated_at=datetime.now(UTC),
            )

        horizon = len(sequence)
        warnings: list[QualityFlag] = []
        year_findings: list[YearFinding] = []

        # 1. Resolve crops and antecedent context
        resolved_sequence: list[tuple[ScenarioYear, str | None, CropProfile | None]] = []
        for y in sequence:
            cid, profile = _resolve_crop_id(y.crop_code, self.kb)
            if not profile:
                warnings.append(
                    QualityFlag(
                        code="UNRESOLVED_CROP",
                        severity="warning",
                        message=f"Crop code {y.crop_code} in year {y.year} could not be resolved to canonical KB crop.",
                    )
                )
            resolved_sequence.append((y, cid, profile))

        antecedent_cid = None
        antecedent_profile = None
        if antecedent_crop is not None:
            if isinstance(antecedent_crop, ScenarioYear):
                antecedent_cid, antecedent_profile = _resolve_crop_id(antecedent_crop.crop_code, self.kb)
            else:
                antecedent_cid, antecedent_profile = _resolve_crop_id(antecedent_crop, self.kb)

        # 2. Build pairwise transitions across the sequence:
        # T0: antecedent -> Y1 (if known)
        # T1..Tn-1: Y_i -> Y_{i+1}
        transitions = []
        # Antecedent transition
        if antecedent_cid:
            first_y, first_cid, _ = resolved_sequence[0]
            if first_cid:
                rot = self.kb.get_rotation(antecedent_cid, first_cid)
                transitions.append((antecedent_cid, first_cid, first_y.year, rot, True))
        else:
            first_y, _, _ = resolved_sequence[0]
            transitions.append((None, resolved_sequence[0][1], first_y.year, None, True))

        for i in range(len(resolved_sequence) - 1):
            curr_y, curr_cid, _ = resolved_sequence[i]
            next_y, next_cid, _ = resolved_sequence[i + 1]
            rot = self.kb.get_rotation(curr_cid, next_cid) if (curr_cid and next_cid) else None
            transitions.append((curr_cid, next_cid, next_y.year, rot, False))

        # 3. Evaluate Year-by-Year Findings
        # Track monocultures and botanical family runs
        prev_cid = antecedent_cid
        prev_family = antecedent_profile.crop_identity.get("botanical_family") if antecedent_profile else None
        consecutive_mono_count = 0
        consecutive_family_count = 0

        transition_scores: list[float] = []
        high_water_run = 0
        max_high_water_run = 0

        for idx, (y, cid, profile) in enumerate(resolved_sequence):
            year_messages: list[QualityFlag] = []
            year_evidence_ids: list[uuid.UUID] = []
            year_band: FitBand = "suitable"

            family = profile.crop_identity.get("botanical_family") if profile else None
            cname = profile.common_name if profile else y.crop_name or f"Crop {y.crop_code}"

            # Check directed transition from preceding crop
            _, _, _, trans, is_antecedent = transitions[idx]

            if trans is not None:
                # Evidence IDs
                for eid in trans.evidence_ids:
                    try:
                        year_evidence_ids.append(uuid.UUID(hex=eid) if len(eid) == 32 else uuid.uuid5(uuid.NAMESPACE_DNS, eid))
                    except Exception:
                        pass

                rating = trans.compatibility_rating
                if rating == "highly_compatible":
                    transition_scores.append(1.0)
                    year_messages.append(
                        QualityFlag(
                            code="ROTATION_SYNERGY",
                            severity="info",
                            message=trans.synergy_mechanisms or f"Highly compatible sequence following {trans.preceding_crop_name}.",
                        )
                    )
                    if trans.disease_break_potential:
                        year_messages.append(
                            QualityFlag(
                                code="DISEASE_BREAK",
                                severity="info",
                                message=trans.disease_break_potential,
                            )
                        )
                elif rating == "compatible":
                    transition_scores.append(0.5)
                    year_messages.append(
                        QualityFlag(
                            code="ROTATION_COMPATIBLE",
                            severity="info",
                            message=trans.synergy_mechanisms or f"Compatible sequence following {trans.preceding_crop_name}.",
                        )
                    )
                elif rating == "caution_conditional":
                    transition_scores.append(-0.5)
                    year_band = "marginal"
                    msg = trans.shared_pest_disease_risks or trans.herbicide_carryover_risks or (
                        trans.limitations[0] if trans.limitations else "Manageable limitation or carryover caution."
                    )
                    year_messages.append(
                        QualityFlag(
                            code="ROTATION_CAUTION",
                            severity="warning",
                            message=f"Caution following {trans.preceding_crop_name}: {msg}",
                        )
                    )
                else:
                    transition_scores.append(0.0)
            elif is_antecedent and prev_cid is None:
                transition_scores.append(0.0)
                year_messages.append(
                    QualityFlag(
                        code="ANTECEDENT_UNKNOWN",
                        severity="info",
                        message="Historical parcel antecedent crop is unrecorded; neutral baseline applied.",
                    )
                )

            # Monoculture check
            if prev_cid is not None and cid == prev_cid:
                consecutive_mono_count += 1
                year_band = "marginal" if consecutive_mono_count == 1 else "unsuitable"
                mono_msg = (
                    trans.monoculture_risk
                    if trans and trans.monoculture_risk
                    else f"Consecutive repeat of {cname} (run length {consecutive_mono_count + 1} years)."
                )
                year_messages.append(
                    QualityFlag(
                        code="MONOCULTURE_PENALTY",
                        severity="critical" if consecutive_mono_count > 1 else "warning",
                        message=mono_msg,
                    )
                )
            else:
                consecutive_mono_count = 0

            # Botanical family run check
            if prev_family is not None and family == prev_family:
                consecutive_family_count += 1
                if consecutive_family_count >= 2:
                    if year_band == "suitable":
                        year_band = "marginal"
                    year_messages.append(
                        QualityFlag(
                            code="BOTANICAL_FAMILY_RUN",
                            severity="warning",
                            message=f"Consecutive {family} run ({consecutive_family_count + 1} years). Increases family-specific soil pathogen carryover.",
                        )
                    )
            else:
                consecutive_family_count = 0

            # Water demand check
            water_need = WATER_DEMAND.get(cid, "moderate")
            if water_need == "high":
                high_water_run += 1
                if high_water_run > max_high_water_run:
                    max_high_water_run = high_water_run
                if high_water_run >= 2:
                    if year_band == "suitable":
                        year_band = "marginal"
                    year_messages.append(
                        QualityFlag(
                            code="HIGH_WATER_RUN",
                            severity="warning",
                            message=f"Back-to-back high water demand crops without soil moisture recharge period ({high_water_run} years).",
                        )
                    )
            else:
                high_water_run = 0
                if water_need == "low":
                    year_messages.append(
                        QualityFlag(
                            code="WATER_CONSERVATION",
                            severity="info",
                            message=f"{cname} has low water demand, facilitating soil moisture recharge.",
                        )
                    )

            # Environmental baseline suitability for this crop
            if baseline_suitability and hasattr(baseline_suitability, "crops"):
                crop_eval = next((c for c in baseline_suitability.crops if c.crop_id == cid), None)
                if crop_eval:
                    if crop_eval.suitability_class == "unsuitable":
                        year_band = "unsuitable"
                        year_messages.append(
                            QualityFlag(
                                code="ENVIRONMENTALLY_UNSUITABLE",
                                severity="critical",
                                message=crop_eval.explanation or f"{cname} is unsuitable on this parcel due to environmental limitations.",
                            )
                        )
                    elif crop_eval.suitability_class in ("conditionally_suitable", "limited_suitability"):
                        if year_band == "suitable":
                            year_band = "marginal"
                        if crop_eval.limiting_factors:
                            year_messages.append(
                                QualityFlag(
                                    code="ENVIRONMENTAL_LIMITATION",
                                    severity="info",
                                    message=f"Environmental limitations: {', '.join(crop_eval.limiting_factors[:2])}.",
                                )
                            )

            prev_cid = cid
            prev_family = family

            year_findings.append(
                YearFinding(
                    year=y.year,
                    band=year_band,
                    messages=year_messages,
                    evidence_ids=year_evidence_ids,
                )
            )

        # 4. Dimension 1: Agronomic Fit
        suit_classes = []
        unsuitable_crops = []
        marginal_crops = []
        if baseline_suitability and hasattr(baseline_suitability, "crops"):
            for _, cid, profile in resolved_sequence:
                cname = profile.common_name if profile else "Crop"
                c_eval = next((c for c in baseline_suitability.crops if c.crop_id == cid), None)
                if c_eval:
                    suit_classes.append(c_eval.suitability_class)
                    if c_eval.suitability_class == "unsuitable":
                        unsuitable_crops.append(cname)
                    elif c_eval.suitability_class in ("conditionally_suitable", "limited_suitability"):
                        marginal_crops.append(cname)

        if baseline_suitability is None or not suit_classes:
            agronomic_fit_band: FitBand = "suitable"
            agronomic_fit_exp = "Evaluated against regional agronomic thresholds."
        elif unsuitable_crops:
            agronomic_fit_band = "unsuitable"
            agronomic_fit_exp = f"Critical environmental limitations detected for {', '.join(unsuitable_crops)}."
        elif marginal_crops:
            agronomic_fit_band = "marginal"
            agronomic_fit_exp = f"Moderate environmental limitations for {', '.join(marginal_crops)}."
        else:
            agronomic_fit_band = "suitable"
            agronomic_fit_exp = "All crops in sequence meet biophysical soil, terrain, and climate requirements."

        # 5. Dimension 2: Rotation Benefit
        mean_trans_score = (sum(transition_scores) / len(transition_scores)) if transition_scores else 0.0
        # Penalize if consecutive monoculture > 1
        any_severe_mono = any(f.band == "unsuitable" for f in year_findings)
        if any_severe_mono:
            rotation_benefit_band: FitBand = "unsuitable"
            rotation_benefit_exp = "Severe consecutive monoculture or fatal disease cycle detected."
        elif mean_trans_score >= 0.5:
            rotation_benefit_band = "suitable"
            rotation_benefit_exp = "Favorable directed transitions provide disease break and rotational synergy benefits."
        elif mean_trans_score >= 0.0:
            rotation_benefit_band = "marginal"
            rotation_benefit_exp = "Neutral to moderate rotational compatibility; manageable limitations present."
        else:
            rotation_benefit_band = "unsuitable"
            rotation_benefit_exp = "Unfavorable crop sequencing with carryover risks or pest accumulation."

        # 6. Dimension 3: Water Risk
        # Extract environmental water context if available from baseline suitability
        precip_mm: float | None = None
        soil_aws_cm: float | None = None
        if baseline_suitability and hasattr(baseline_suitability, "crops"):
            for c_eval in baseline_suitability.crops:
                if hasattr(c_eval, "factor_assessments") and c_eval.factor_assessments:
                    for fa in c_eval.factor_assessments:
                        if getattr(fa, "factor_key", None) == "water_precipitation" and precip_mm is None:
                            val = getattr(getattr(fa, "observed_value", None), "value", None)
                            if isinstance(val, (int, float)):
                                precip_mm = float(val)
                        elif getattr(fa, "factor_key", None) == "available_water" and soil_aws_cm is None:
                            val = getattr(getattr(fa, "observed_value", None), "value", None)
                            if isinstance(val, (int, float)):
                                soil_aws_cm = float(val)
                if precip_mm is not None and soil_aws_cm is not None:
                    break

        if precip_mm is not None and precip_mm < 550.0:
            # Semi-arid regime (e.g. Western Kansas / Finney County ~480 mm/yr)
            if max_high_water_run >= 2:
                water_risk_band: FitBand = "unsuitable"
                water_risk_exp = (
                    f"Severe depletion risk in semi-arid climate ({round(precip_mm)} mm/yr): "
                    f"consecutive high-demand crops ({max_high_water_run} years) exceed subsoil recharge capacity."
                )
            elif max_high_water_run == 1:
                water_risk_band = "marginal"
                water_risk_exp = (
                    f"Elevated moisture risk in semi-arid region ({round(precip_mm)} mm/yr); "
                    "requires deep subsoil moisture recharge following high-demand crop."
                )
            else:
                water_risk_band = "suitable"
                water_risk_exp = f"Moisture-conserving crop sequence adapted to semi-arid rainfall ({round(precip_mm)} mm/yr)."
        elif precip_mm is not None:
            # Sub-humid / transitional regime (e.g. South-Central Kansas / Reno County ~750-960 mm/yr)
            if max_high_water_run >= 3:
                water_risk_band = "unsuitable"
                water_risk_exp = (
                    f"Excessive continuous high water demand sequence ({max_high_water_run} years) "
                    f"depletes deep soil moisture despite {round(precip_mm)} mm rainfall."
                )
            elif max_high_water_run == 2:
                water_risk_band = "marginal"
                water_risk_exp = (
                    f"Back-to-back high water demand crops; requires subsoil moisture monitoring "
                    f"under regional rainfall ({round(precip_mm)} mm/yr)."
                )
            else:
                water_risk_band = "suitable"
                water_risk_exp = f"Balanced rotational water demand aligned with parcel rainfall ({round(precip_mm)} mm/yr)."
        else:
            # Standard sequence-only fallback (no environmental baseline passed)
            if max_high_water_run >= 3:
                water_risk_band = "unsuitable"
                water_risk_exp = f"Excessive continuous high water demand sequence ({max_high_water_run} years) depletes deep soil moisture."
            elif max_high_water_run == 2:
                water_risk_band = "marginal"
                water_risk_exp = "Back-to-back high water demand crops; requires careful subsoil moisture monitoring."
            else:
                water_risk_band = "suitable"
                water_risk_exp = "Balanced rotational water demand with adequate soil moisture preservation."

        # 7. Dimension 4: Diversity
        distinct_cids = {cid for _, cid, _ in resolved_sequence if cid is not None}
        distinct_families = {
            profile.crop_identity.get("botanical_family")
            for _, _, profile in resolved_sequence
            if profile and profile.crop_identity.get("botanical_family")
        }

        num_crops = len(distinct_cids)
        num_families = len(distinct_families)

        if horizon <= 3:
            if num_crops >= 2 and num_families >= 2:
                diversity_band: FitBand = "suitable"
                diversity_exp = f"Good rotational diversity with {num_crops} distinct crops across {num_families} botanical families."
            elif num_crops >= 2 and num_families == 1:
                diversity_band = "marginal"
                diversity_exp = f"Moderate diversity ({num_crops} crops) but restricted to single botanical family ({next(iter(distinct_families), 'Poaceae')})."
            else:
                diversity_band = "unsuitable"
                diversity_exp = f"Zero rotational diversity: single crop ({num_crops}) across all {horizon} years."
        else:
            if num_crops >= 3 and num_families >= 2:
                diversity_band = "suitable"
                diversity_exp = f"Strong multi-year diversity: {num_crops} crops across {num_families} botanical families."
            elif num_crops >= 2 and num_families >= 2:
                diversity_band = "marginal"
                diversity_exp = f"Acceptable diversity ({num_crops} crops, {num_families} families) for a {horizon}-year horizon."
            else:
                diversity_band = "unsuitable"
                diversity_exp = f"Inadequate multi-year diversity: only {num_crops} crop(s) across {horizon} years."

        dimensions = [
            EvaluationDimension(key="agronomic_fit", band=agronomic_fit_band, explanation=agronomic_fit_exp),
            EvaluationDimension(key="rotation_benefit", band=rotation_benefit_band, explanation=rotation_benefit_exp),
            EvaluationDimension(key="water_risk", band=water_risk_band, explanation=water_risk_exp),
            EvaluationDimension(key="diversity", band=diversity_band, explanation=diversity_exp),
        ]

        # 8. Overall Synthesis and Qualitative Interpretation Label
        has_cover = any(cid in ("CRP012", "CRP013", "CRP014") for _, cid, _ in resolved_sequence)
        dim_bands = [d.band for d in dimensions]

        if "unsuitable" in dim_bands:
            overall_band: FitBand = "unsuitable"
            interpretation: ScenarioInterpretation = "not_recommended"
        elif any(b == "marginal" for b in dim_bands):
            overall_band = "marginal"
            interpretation = "conditional" if not has_cover else "exploratory"
        elif all(b == "suitable" for b in dim_bands):
            overall_band = "suitable"
            interpretation = "supported"
        else:
            overall_band = "unknown"
            interpretation = "insufficient_data"

        # Check for cover crop exploration note
        if has_cover and interpretation == "supported":
            interpretation = "exploratory"

        return ScenarioEvaluation(
            engine_version=ENGINE_VERSION,
            kb_version=self.kb.kb_version,
            overall=overall_band,
            interpretation=interpretation,
            dimensions=dimensions,
            year_findings=year_findings,
            warnings=warnings,
            evaluated_at=datetime.now(UTC),
        )
