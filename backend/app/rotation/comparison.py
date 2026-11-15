"""Scenario comparison and tradeoff synthesizer (Phase 7 layer 4).

Generates evidence-backed tradeoff findings across 2 or 3 prospective rotation scenarios.
"""

from __future__ import annotations

from app.contracts import (
    CompareScenariosResponse,
    RotationScenario,
    TradeoffFinding,
)
from app.rotation.kb import CDL_TO_CROP_ID, CropKnowledgeBase


class ScenarioComparator:
    """Compares 2 or 3 scenarios and synthesizes clear agronomic trade-offs."""

    def __init__(self, kb: CropKnowledgeBase):
        self.kb = kb

    def compare(self, scenarios: list[RotationScenario]) -> CompareScenariosResponse:
        if not scenarios:
            raise ValueError("At least 2 scenarios are required for comparison.")

        field_id = scenarios[0].field_id
        tradeoffs: list[TradeoffFinding] = []

        # 1. Diversity comparison
        family_counts = []
        crop_counts = []
        for s in scenarios:
            fams = set()
            crops = set()
            for y in s.sequence:
                crops.add(y.crop_code)
                cid = CDL_TO_CROP_ID.get(y.crop_code)
                if cid:
                    p = self.kb.get_crop_by_id(cid)
                    if p:
                        fams.add(p.crop_identity.get("botanical_family"))
            family_counts.append((s.name, len(fams), fams))
            crop_counts.append((s.name, len(crops)))

        # Compare diversity
        max_fam = max(family_counts, key=lambda x: x[1])
        min_fam = min(family_counts, key=lambda x: x[1])
        if max_fam[1] > min_fam[1]:
            tradeoffs.append(
                TradeoffFinding(
                    category="diversity",
                    summary=f"'{max_fam[0]}' provides greater botanical family diversity ({max_fam[1]} families: {', '.join(sorted(f for f in max_fam[2] if f))}) than '{min_fam[0]}' ({min_fam[1]} family). Greater family diversity breaks soil-borne pest and pathogen cycles.",
                )
            )
        else:
            tradeoffs.append(
                TradeoffFinding(
                    category="diversity",
                    summary=f"All compared scenarios maintain similar taxonomic diversity ({max_fam[1]} botanical families).",
                )
            )

        # 2. Water demand and risk comparison
        from app.rotation.evaluator import WATER_DEMAND

        water_profiles = []
        for s in scenarios:
            high_count = 0
            low_count = 0
            for y in s.sequence:
                cid = CDL_TO_CROP_ID.get(y.crop_code)
                demand = WATER_DEMAND.get(cid, "moderate") if cid else "moderate"
                if demand == "high":
                    high_count += 1
                elif demand == "low":
                    low_count += 1
            water_profiles.append((s.name, high_count, low_count, len(s.sequence)))

        # Check if one scenario has significantly higher water consumption
        max_high = max(water_profiles, key=lambda x: x[1])
        min_high = min(water_profiles, key=lambda x: x[1])
        if max_high[1] > min_high[1]:
            tradeoffs.append(
                TradeoffFinding(
                    category="water_risk",
                    summary=f"'{min_high[0]}' poses lower moisture depletion risk ({min_high[1]} high-demand crop seasons vs {max_high[1]} in '{max_high[0]}'), preserving subsoil moisture under rainfed or water-limited conditions.",
                )
            )
        else:
            tradeoffs.append(
                TradeoffFinding(
                    category="water_risk",
                    summary="Compared scenarios feature balanced moisture demand without excessive back-to-back high-water consumption.",
                )
            )

        # 3. Overall agronomic fit and rotation benefit comparison
        eval_ratings = []
        for s in scenarios:
            ov = s.evaluation.overall if s.evaluation else "unknown"
            interp = s.evaluation.interpretation if s.evaluation else "unknown"
            eval_ratings.append((s.name, ov, interp))

        unsuitable_scenarios = [r[0] for r in eval_ratings if r[1] == "unsuitable"]
        supported_scenarios = [r[0] for r in eval_ratings if r[2] == "supported"]

        if unsuitable_scenarios and supported_scenarios:
            tradeoffs.append(
                TradeoffFinding(
                    category="agronomic_fit",
                    summary=f"'{', '.join(supported_scenarios)}' is agronomically supported, whereas '{', '.join(unsuitable_scenarios)}' contains critical limitations or prolonged monoculture that make it not recommended.",
                )
            )
        elif all(r[1] == "suitable" for r in eval_ratings):
            tradeoffs.append(
                TradeoffFinding(
                    category="agronomic_fit",
                    summary="All compared scenarios are fully supported by parcel environmental conditions and favorable rotation synergies.",
                )
            )

        return CompareScenariosResponse(
            field_id=field_id,
            scenarios=scenarios,
            tradeoffs=tradeoffs,
        )
