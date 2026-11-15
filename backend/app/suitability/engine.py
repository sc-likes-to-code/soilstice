"""Phase 6: Crop Suitability Engine.

Orchestrates the evaluation of all 14 canonical agricultural crops for a specific field
using integrated environmental indicators from Phase 4 and the Phase 5 Crop Knowledge Base.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.contracts import (
    ClimateProfile,
    CropHistory,
    CropProfile,
    CropSuitabilityAssessment,
    FieldSuitabilityResponse,
    QualityInfo,
    SoilProfile,
    SpatialSupport,
    SuitabilitySummaryCounts,
    TemporalSupport,
    TerrainProfile,
)
from app.rotation.kb import CropKnowledgeBase
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
from app.suitability.explainer import (
    build_explanation,
    build_limitations_list,
    extract_factor_lists,
)
from app.suitability.scorer import (
    calculate_suitability_score,
    classify_crop,
)

ENGINE_VERSION = "1.0.0-phase6"


class CropSuitabilityEngine:
    """Core analytical engine for evaluating field-scale crop suitability."""

    def __init__(self, kb: CropKnowledgeBase):
        self.kb = kb

    def evaluate_crop(
        self,
        crop: CropProfile,
        *,
        soil: SoilProfile | None,
        climate: ClimateProfile | None,
        terrain: TerrainProfile | None,
        history: CropHistory | None,
        state_code: str = "KS",
    ) -> CropSuitabilityAssessment:
        """Evaluate a single canonical crop against field environmental conditions."""
        factors = [
            evaluate_thermal_gdd(crop, climate),
            evaluate_heat_stress(crop, climate),
            evaluate_water_precipitation(crop, climate),
            evaluate_soil_ph(crop, soil),
            evaluate_soil_drainage(crop, soil),
            evaluate_soil_texture(crop, soil),
            evaluate_available_water(crop, soil),
            evaluate_rooting(crop, soil),
            evaluate_terrain_slope(crop, terrain),
            evaluate_crop_history(crop, history),
            evaluate_regional_suitability(crop, state_code),
        ]

        suitability_class, class_reason = classify_crop(factors)
        suitability_score, score_method = calculate_suitability_score(factors, suitability_class)
        limiting, favorable, unknown, factor_ev_ids = extract_factor_lists(factors)

        # Merge crop-level evidence IDs with factor-level evidence IDs
        all_evidence = sorted(list(set(factor_ev_ids + (crop.evidence_ids or []))))

        explanation = build_explanation(crop, suitability_class, limiting, favorable, unknown, class_reason)
        limitations = build_limitations_list(factors, crop)

        # Determine assessment status
        if suitability_class == "insufficient_data":
            assessment_status = "insufficient_data"
        elif unknown:
            assessment_status = "provisional"
        else:
            assessment_status = "evaluated"

        # Quality and support attribution
        has_soil = soil is not None and soil.quality.status != "missing"
        has_climate = climate is not None and climate.quality.status != "missing"

        if has_soil and has_climate:
            quality = QualityInfo(status="valid", completeness=0.92)
        elif has_soil or has_climate:
            quality = QualityInfo(status="partial", completeness=0.55)
        else:
            quality = QualityInfo(status="missing", completeness=0.0, missing_reason="INSUFFICIENT_COVERAGE")

        spatial = SpatialSupport(
            support_class="F",
            native_resolution_m=30.0,
            extraction_method="vector_intersection",
        )
        temporal = TemporalSupport(
            resolution="season",
            period_start=climate.season.start if climate else None,
            period_end=climate.season.end if climate else None,
            aggregation="mean",
            time_standard="UTC",
        )

        return CropSuitabilityAssessment(
            crop_id=crop.crop_id,
            crop_name=crop.common_name,
            cdl_code=crop.cdl_code,
            botanical_family=crop.botanical_family,
            portfolio_role=crop.portfolio_role,
            is_cover_crop=crop.is_cover_crop,
            assessment_status=assessment_status,
            suitability_class=suitability_class,
            suitability_score=suitability_score,
            score_methodology=score_method,
            factor_assessments=factors,
            limiting_factors=limiting,
            favorable_factors=favorable,
            unknown_factors=unknown,
            data_quality=quality,
            spatial_support=spatial,
            temporal_support=temporal,
            evidence_ids=all_evidence,
            explanation=explanation,
            limitations=limitations,
        )

    def evaluate_field(
        self,
        field_id: UUID,
        season_year: int,
        *,
        soil: SoilProfile | None,
        climate: ClimateProfile | None,
        terrain: TerrainProfile | None,
        history: CropHistory | None,
        state_code: str = "KS",
    ) -> FieldSuitabilityResponse:
        """Evaluate all 14 canonical crops for the specified field."""
        crops_evaluated: list[CropSuitabilityAssessment] = []

        # Iterate over all 14 canonical crops in canonical order (CRP001 through CRP014)
        for crop_id in [f"CRP{i:03d}" for i in range(1, 15)]:
            crop = self.kb.get_crop_by_id(crop_id)
            if not crop:
                continue
            assessment = self.evaluate_crop(
                crop,
                soil=soil,
                climate=climate,
                terrain=terrain,
                history=history,
                state_code=state_code,
            )
            crops_evaluated.append(assessment)

        # Compute summary counts
        counts = SuitabilitySummaryCounts(
            total_evaluated=len(crops_evaluated),
            suitable=sum(1 for c in crops_evaluated if c.suitability_class == "suitable"),
            conditionally_suitable=sum(1 for c in crops_evaluated if c.suitability_class == "conditionally_suitable"),
            limited_suitability=sum(1 for c in crops_evaluated if c.suitability_class == "limited_suitability"),
            unsuitable=sum(1 for c in crops_evaluated if c.suitability_class == "unsuitable"),
            insufficient_data=sum(1 for c in crops_evaluated if c.suitability_class == "insufficient_data"),
        )

        overall_status = "evaluated"
        if counts.insufficient_data == len(crops_evaluated):
            overall_status = "insufficient_data"
        elif any(c.assessment_status == "provisional" for c in crops_evaluated):
            overall_status = "provisional"

        disclaimers = [
            "This suitability assessment is an agronomic decision-support model synthesized from USDA SSURGO, NASA POWER, NASA SRTM, and USDA-ARS crop research.",
            "Suitability classifications and scores reflect environmental compatibility under standard good agricultural practices; they do NOT constitute a guarantee of crop emergence, yield, marketability, or commercial profitability.",
            "Field decisions must be corroborated with localized soil core testing, weed/pest pressure history, and equipment/irrigation availability.",
        ]

        return FieldSuitabilityResponse(
            field_id=field_id,
            season_year=season_year,
            as_of=date.today(),
            engine_version=ENGINE_VERSION,
            kb_version=self.kb.kb_version,
            status=overall_status,
            summary=counts,
            crops=crops_evaluated,
            disclaimers=disclaimers,
        )
