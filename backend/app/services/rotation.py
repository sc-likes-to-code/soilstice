"""Rotation services (E17, E20–E25). Scenario CRUD is real; evaluation/recommendation await the cited KB."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.catalog import SPATIAL
from app.contracts import (
    CompareScenariosRequest,
    CompareScenariosResponse,
    CropEvidenceRecord,
    CropHistory,
    CropOption,
    CropProfile,
    CropProfileSummary,
    DirectedRotationTransition,
    GenerateCandidate,
    GenerateRotationsRequest,
    GenerateRotationsResponse,
    KnowledgeBaseMetadata,
    QualityInfo,
    RotationRecommendation,
    RotationScenario,
    ScenarioEvaluation,
    ScenarioYear,
    TradeoffFinding,
    UpsertScenarioRequest,
    YearPeriod,
)
from app.errors import NotFound, ValidationFailed
from app.processing.crop_history import _missing_year

from .container import Container
from .fields import FieldService


class RotationService:
    def __init__(self, ctx: Container):
        self.ctx = ctx
        self.repos = ctx.repos
        self.fields = FieldService(ctx)

    def crops(self) -> list[CropOption]:
        return self.ctx.kb.crops

    def canonical_crops(self, role: str | None = None, family: str | None = None) -> list[CropProfileSummary]:
        return self.ctx.kb.list_crop_summaries(role=role, family=family)

    def get_crop(self, crop_id: str) -> CropProfile:
        crop = self.ctx.kb.get_crop(crop_id)
        if crop is None:
            raise NotFound(
                f"Crop '{crop_id}' not found in knowledge base.",
                details={"crop_id": crop_id, "valid_range": "CRP001 to CRP014, or supported CDL codes"},
            )
        return crop

    def get_crop_attributes(
        self, crop_id: str, domain: str | None = None, attribute: str | None = None
    ) -> dict[str, Any]:
        crop = self.get_crop(crop_id)
        data = {
            "crop_identity": crop.crop_identity,
            "growing_duration": crop.growing_duration,
            "temperature_requirements": crop.temperature_requirements,
            "rainfall_requirements": crop.rainfall_requirements,
            "water_demand_and_tolerance": crop.water_demand_and_tolerance,
            "soil_preferences": crop.soil_preferences,
            "root_and_nutrients": crop.root_and_nutrients,
            "nitrogen_and_biomass": crop.nitrogen_and_biomass,
            "rotation_compatibility": crop.rotation_compatibility,
            "regional_suitability": crop.regional_suitability,
        }
        if domain:
            if domain not in data:
                raise NotFound(
                    f"Domain '{domain}' not found for crop '{crop_id}'.",
                    details={"crop_id": crop_id, "valid_domains": list(data.keys())},
                )
            domain_data = data[domain]
            if attribute:
                parts = attribute.split(".")
                curr = domain_data
                for p in parts:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        raise NotFound(
                            f"Attribute '{attribute}' not found in domain '{domain}'.",
                            details={"attribute": attribute, "domain": domain},
                        )
                return {attribute: curr}
            return {domain: domain_data}
        return data

    def get_rotation(self, previous_crop: str, next_crop: str) -> DirectedRotationTransition:
        rot = self.ctx.kb.get_rotation(previous_crop, next_crop)
        if rot is None:
            raise NotFound(
                f"Directed rotation transition from '{previous_crop}' to '{next_crop}' not found.",
                details={"previous_crop": previous_crop, "next_crop": next_crop},
            )
        return rot

    def list_rotation_matrix(self, crop_id: str | None = None) -> list[DirectedRotationTransition]:
        return self.ctx.kb.list_rotations(crop_id)

    def get_evidence(self, evidence_id: str) -> CropEvidenceRecord:
        ev = self.ctx.kb.get_evidence(evidence_id)
        if ev is None:
            raise NotFound(
                f"Evidence record '{evidence_id}' not found.",
                details={"evidence_id": evidence_id, "valid_range": "EV0001 to EV0212"},
            )
        return ev

    def get_kb_metadata(self) -> KnowledgeBaseMetadata:
        if self.ctx.kb.metadata:
            return self.ctx.kb.metadata
        return KnowledgeBaseMetadata(
            dataset_name="Fallback Crop Knowledge Base",
            schema_version=self.ctx.kb.kb_version,
            stage="unloaded",
            effective_date="2026-11-14",
            geographic_scope="CONUS",
            canonical_crop_count=len(self.ctx.kb.crops),
            evidence_records_count=0,
            directed_rotation_transitions_count=0,
            description=self.ctx.kb.status_message,
        )

    def crop_history(self, field_id) -> CropHistory:
        f = self.fields.get_field(field_id)
        h = self.repos.crop_history.get(str(f.field_id))
        if h is not None:
            return h
        st = self.repos.dataset_states.get(f"{f.field_id}:usda_nass_cdl")
        reason = "PENDING_PROCESSING" if st is None or st.state == "pending" else (st.missing_reason or "UPSTREAM_ERROR")
        s = self.ctx.settings
        return CropHistory(
            field_id=f.field_id, period=YearPeriod(start_year=s.cdl_first_year, end_year=s.cdl_last_year),
            years=[_missing_year(y, reason) for y in range(s.cdl_first_year, s.cdl_last_year + 1)], metrics=[],
            spatial=SPATIAL["usda_nass_cdl"], quality=QualityInfo(status="missing", completeness=0.0,
                                                                  missing_reason=reason),
        )

    def recommendation(self, field_id, season_year: int) -> RotationRecommendation:
        f = self.fields.get_field(field_id)
        # Attempt to synthesize recommendation from Phase 6 Environmental Suitability Engine
        try:
            from app.services.suitability import SuitabilityService
            suit_svc = SuitabilityService(self.ctx)
            default_year = self.ctx.settings.default_season_year()
            baseline_year = season_year if season_year <= default_year else default_year
            suit_res = suit_svc.evaluate_field(f.field_id, baseline_year)
        except Exception:
            suit_res = None

        if (
            suit_res is None
            or suit_res.status == "insufficient_data"
            or not any(c.assessment_status != "insufficient_data" for c in suit_res.crops)
        ):
            return self.ctx.rotation.recommend(f.field_id, season_year, self.ctx.kb)

        # Retrieve field crop history to assess rotation continuity and monoculture risks
        history = self.crop_history(f.field_id)
        last_crop_code = None
        last_crop_name = None
        recent_codes = set()
        valid_years = []
        if history and history.years:
            valid_years = [y for y in history.years if y.majority and y.majority.crop_code is not None]
            if valid_years:
                last_crop_code = valid_years[-1].majority.crop_code
                last_crop_name = valid_years[-1].majority.crop_name
                recent_codes = {y.majority.crop_code for y in valid_years[-5:]}

        candidates = []
        excluded = []

        class_to_band = {
            "suitable": "suitable",
            "conditionally_suitable": "marginal",
            "limited_suitability": "marginal",
            "unsuitable": "unsuitable",
            "unknown": "unknown",
        }

        compat_to_band = {
            "optimal": "suitable",
            "compatible": "suitable",
            "manageable_limitation": "marginal",
            "moderate_limitation": "marginal",
            "critical_limitation": "unsuitable",
            "unknown": "unknown",
        }

        from app.rotation.kb import CDL_TO_CROP_ID

        for crop_eval in suit_res.crops:
            if crop_eval.cdl_code is None:
                continue

            cdl_code = crop_eval.cdl_code
            crop_name = crop_eval.crop_name

            if crop_eval.suitability_class == "unsuitable":
                from app.contracts import ExcludedCrop
                excluded.append(
                    ExcludedCrop(
                        crop_code=cdl_code,
                        crop_name=crop_name,
                        reason=crop_eval.explanation or "Environmental constraints exceed agronomic tolerances.",
                    )
                )
                continue

            factors_map = {}
            for fa in crop_eval.factor_assessments:
                fkey = fa.factor_key
                mapped_key = None
                if fkey in ("soil_ph", "ph"):
                    mapped_key = "ph"
                elif fkey in ("soil_drainage", "drainage"):
                    mapped_key = "drainage"
                elif fkey in ("available_water", "available_water_storage", "water_holding"):
                    mapped_key = "water_holding"
                elif fkey in ("thermal_gdd", "gdd"):
                    mapped_key = "gdd"
                elif fkey in ("terrain_slope", "slope_p90", "slope"):
                    mapped_key = "slope"
                elif fkey in ("water_precipitation", "thermal_heat_stress", "regional_adaptation", "regional_climate"):
                    mapped_key = "regional_climate"

                if mapped_key and mapped_key not in factors_map:
                    band = compat_to_band.get(fa.compatibility, class_to_band.get(fa.severity, "unknown"))
                    support = "R" if mapped_key in ("gdd", "regional_climate") else "F"
                    ev_uuids = []
                    for ev_id in fa.evidence_ids:
                        try:
                            ev_uuids.append(uuid.UUID(ev_id))
                        except Exception:
                            pass
                    from app.contracts import FactorAssessment
                    factors_map[mapped_key] = FactorAssessment(
                        factor=mapped_key,
                        band=band,
                        observed=fa.observed_value,
                        requirement=fa.crop_requirement or fa.interpretation or "Agronomic tolerance threshold",
                        support_class=support,
                        evidence_ids=ev_uuids,
                    )

            rot_effects = []
            from app.contracts import QualityFlag

            # Check directed rotation compatibility from Crop Knowledge Base (EV0001–EV0212)
            prev_id = CDL_TO_CROP_ID.get(last_crop_code) if last_crop_code is not None else None
            following_id = CDL_TO_CROP_ID.get(cdl_code)
            rot_trans = self.ctx.kb.get_rotation(prev_id, following_id) if (prev_id and following_id) else None

            if last_crop_code is not None:
                if cdl_code == last_crop_code:
                    rot_band = "marginal"
                    rot_effects.append(
                        QualityFlag(
                            code="REPEATS_LAST_CROP",
                            severity="warning",
                            message=f"Would repeat {last_crop_name} on this parcel.",
                        )
                    )
                    rot_req = (
                        rot_trans.limitations[0]
                        if (rot_trans and rot_trans.limitations)
                        else f"Avoid consecutive monoculture of {crop_name}."
                    )
                else:
                    rot_effects.append(
                        QualityFlag(
                            code="BREAKS_RUN",
                            severity="info",
                            message=f"Breaks sequence of {last_crop_name}.",
                        )
                    )
                    if rot_trans and rot_trans.compatibility_rating == "recommended":
                        rot_band = "suitable"
                        rot_req = f"Recommended rotation: {rot_trans.synergy_mechanisms or 'favorable sequence'}"
                    elif rot_trans and rot_trans.compatibility_rating in ("caution", "not_recommended"):
                        rot_band = "marginal"
                        rot_req = f"Rotational caution: {rot_trans.shared_pest_disease_risks or rot_trans.herbicide_carryover_risks or 'potential carryover risk'}"
                    else:
                        rot_band = "suitable"
                        rot_req = f"Compatible transition following {last_crop_name}."

                    # Diversity benefit requires >= 3 valid historical seasons to verify absence
                    if len(valid_years) >= 3 and cdl_code not in recent_codes:
                        rot_effects.append(
                            QualityFlag(
                                code="DIVERSITY_BENEFIT",
                                severity="info",
                                message="Introduces rotational diversity (not grown in past 5 seasons).",
                            )
                        )
            else:
                rot_band = "unknown"
                rot_req = "Historical crop sequence data unavailable for parcel."

            from app.contracts import FactorAssessment
            factors_map["rotation_history"] = FactorAssessment(
                factor="rotation_history",
                band=rot_band,
                observed=None,
                requirement=rot_req,
                support_class="F",
                evidence_ids=[],
            )

            for req_f in ("ph", "drainage", "water_holding", "slope", "gdd", "regional_climate"):
                if req_f not in factors_map:
                    support = "R" if req_f in ("gdd", "regional_climate") else "F"
                    factors_map[req_f] = FactorAssessment(
                        factor=req_f,
                        band="unknown",
                        observed=None,
                        requirement="Observation not available for this parcel",
                        support_class=support,
                        evidence_ids=[],
                    )

            factors_list = [
                factors_map[k]
                for k in ["ph", "drainage", "water_holding", "gdd", "slope", "rotation_history", "regional_climate"]
            ]

            overall_band = class_to_band.get(crop_eval.suitability_class, "marginal")
            if rot_band == "marginal" and overall_band == "suitable":
                overall_band = "marginal"

            reasons = [crop_eval.explanation]
            if crop_eval.limiting_factors:
                reasons.append(f"Limiting factors: {', '.join(crop_eval.limiting_factors)}")
            if crop_eval.favorable_factors:
                reasons.append(f"Favorable factors: {', '.join(crop_eval.favorable_factors[:3])}")

            score = crop_eval.suitability_score or 0.0
            if len(crop_eval.unknown_factors) > 2:
                conf = "low"
            elif score >= 75:
                conf = "high"
            else:
                conf = "medium"

            candidates.append({
                "crop_code": cdl_code,
                "crop_name": crop_name,
                "overall": overall_band,
                "confidence": conf,
                "factors": factors_list,
                "rotation_effects": rot_effects,
                "reasons": reasons,
                "score": score,
                "limiting_count": len(crop_eval.limiting_factors),
                "is_repeat": (cdl_code == last_crop_code),
            })

        # Explicit ranking by Phase 6 suitability score descending with deterministic tie-breaking (Task 8)
        conf_weight = {"high": 3, "medium": 2, "low": 1}
        candidates.sort(
            key=lambda c: (
                -c["score"],  # 1. Primary: Suitability score descending
                -conf_weight.get(c["confidence"], 0),  # 2. Tie-break: Higher data confidence first
                c["limiting_count"],  # 3. Tie-break: Fewer limiting factors first
                1 if c["is_repeat"] else 0,  # 4. Tie-break: Non-repeat before repeat
                c["crop_name"],  # 5. Tie-break: Alphabetical by crop name
            )
        )

        from app.contracts import RecommendationCandidate, TargetSeason
        from datetime import date
        final_candidates = [
            RecommendationCandidate(
                rank=i + 1,
                crop_code=c["crop_code"],
                crop_name=c["crop_name"],
                overall=c["overall"],
                confidence=c["confidence"],
                factors=c["factors"],
                rotation_effects=c["rotation_effects"],
                reasons=c["reasons"],
            )
            for i, c in enumerate(candidates)
        ]

        rec_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{f.field_id}:{season_year}:rec")
        return RotationRecommendation(
            recommendation_id=rec_id,
            field_id=f.field_id,
            target_season=TargetSeason(
                label=f"{season_year} season",
                start=date(season_year - 1, 9, 1),
                end=date(season_year, 11, 30),
            ),
            engine_version="soilstice-suitability-v1.0",
            kb_version=self.ctx.kb.kb_version,
            status="computed",
            candidates=final_candidates,
            excluded=excluded,
            disclaimers=[
                "Not a yield or profit forecast.",
                "Recommendations synthesized from Phase 6 Environmental Suitability scores and historical rotation best practices.",
                "Factors marked 'Regional context' (R) cannot make a crop unsuitable on their own.",
                "Multi-year sequence optimization and economic scenario modeling will arrive in Phase 7.",
            ],
            generated_at=datetime.now(UTC),
        )

    # ── scenarios ──────────────────────────────────────────────────────────
    def list_scenarios(self, field_id) -> list[RotationScenario]:
        f = self.fields.get_field(field_id)
        return self.repos.scenarios.list(parent=str(f.field_id))

    def _sequence(self, req: UpsertScenarioRequest) -> list[ScenarioYear]:
        errors = []
        for i, item in enumerate(req.sequence):
            if item.year != req.start_year + i:
                errors.append({"index": i, "year": item.year, "expected": req.start_year + i,
                               "error": "years must be consecutive starting at start_year"})
            if self.ctx.kb.crop_name(item.crop_code) is None:
                errors.append({"index": i, "crop_code": item.crop_code, "error": "unknown crop code"})
        if errors:
            raise ValidationFailed("Scenario sequence is invalid.", details={"errors": errors})
        return [ScenarioYear(year=i.year, crop_code=i.crop_code, crop_name=self.ctx.kb.crop_name(i.crop_code))
                for i in req.sequence]

    def _evaluate_scenario(self, field_id: uuid.UUID, seq: list[ScenarioYear]) -> ScenarioEvaluation:
        try:
            from app.services.suitability import SuitabilityService
            suit_svc = SuitabilityService(self.ctx)
            default_year = self.ctx.settings.default_season_year()
            suit_res = suit_svc.evaluate_field(field_id, default_year)
        except Exception:
            suit_res = None

        history = self.crop_history(field_id)
        last_crop_code = None
        if history and history.years:
            valid_years = [y for y in history.years if y.majority and y.majority.crop_code is not None]
            if valid_years:
                last_crop_code = valid_years[-1].majority.crop_code

        return self.ctx.rotation.evaluate(
            sequence=seq,
            kb=self.ctx.kb,
            field_id=field_id,
            baseline_suitability=suit_res,
            antecedent_crop=last_crop_code,
        )

    def create_scenario(self, field_id, req: UpsertScenarioRequest) -> RotationScenario:
        f = self.fields.get_field(field_id)
        seq = self._sequence(req)
        t = datetime.now(UTC)
        sc = RotationScenario(scenario_id=uuid.uuid4(), field_id=f.field_id, name=req.name.strip(),
                              start_year=req.start_year, sequence=seq,
                              evaluation=self._evaluate_scenario(f.field_id, seq), created_at=t, updated_at=t)
        return self.repos.scenarios.put(str(sc.scenario_id), sc, parent=f.field_id)

    def _get(self, scenario_id) -> RotationScenario:
        sc = self.repos.scenarios.get(str(scenario_id))
        if sc is None:
            raise NotFound(f"Scenario {scenario_id} not found.", details={"scenario_id": str(scenario_id)})
        return sc

    def update_scenario(self, scenario_id, req: UpsertScenarioRequest) -> RotationScenario:
        sc = self._get(scenario_id)
        seq = self._sequence(req)
        sc = sc.model_copy(update={"name": req.name.strip(), "start_year": req.start_year, "sequence": seq,
                                   "evaluation": self._evaluate_scenario(sc.field_id, seq),
                                   "updated_at": datetime.now(UTC)})
        return self.repos.scenarios.put(str(sc.scenario_id), sc, parent=sc.field_id)

    def delete_scenario(self, scenario_id) -> None:
        self._get(scenario_id)
        self.repos.scenarios.delete(str(scenario_id))

    def generate_rotations(self, field_id, req: GenerateRotationsRequest) -> GenerateRotationsResponse:
        f = self.fields.get_field(field_id)
        try:
            from app.services.suitability import SuitabilityService
            suit_svc = SuitabilityService(self.ctx)
            default_year = self.ctx.settings.default_season_year()
            suit_res = suit_svc.evaluate_field(f.field_id, default_year)
        except Exception:
            suit_res = None

        history = self.crop_history(f.field_id)
        last_crop_code = None
        antecedent_crop = None
        if history and history.years:
            valid_years = [y for y in history.years if y.majority and y.majority.crop_code is not None]
            if valid_years:
                last_y = valid_years[-1]
                last_crop_code = last_y.majority.crop_code
                antecedent_crop = ScenarioYear(
                    year=last_y.year,
                    crop_code=last_crop_code,
                    crop_name=last_y.majority.crop_name or self.ctx.kb.crop_name(last_crop_code) or f"Crop {last_crop_code}",
                )

        candidates = self.ctx.rotation.generate_candidates(
            field_id=f.field_id,
            horizon=req.horizon,
            start_year=req.start_year,
            kb=self.ctx.kb,
            baseline_suitability=suit_res,
            antecedent_crop_code=last_crop_code,
            include_cover_crops=req.include_cover_crops,
            max_candidates=req.max_candidates,
        )

        return GenerateRotationsResponse(
            field_id=f.field_id,
            horizon=req.horizon,
            start_year=req.start_year,
            antecedent_crop=antecedent_crop,
            candidates=candidates,
            pareto_optimal_count=sum(1 for c in candidates if getattr(c, "is_pareto_optimal", True)),
            generated_at=datetime.now(UTC),
        )

    def compare_scenarios(self, field_id, req: CompareScenariosRequest) -> CompareScenariosResponse:
        f = self.fields.get_field(field_id)
        scenarios: list[RotationScenario] = []
        for sid in req.scenario_ids:
            sc = self._get(sid)
            if sc.field_id != f.field_id:
                raise ValidationFailed(
                    f"Scenario {sid} does not belong to field {f.field_id}.",
                    details={"scenario_id": str(sid), "field_id": str(f.field_id)},
                )
            scenarios.append(sc)

        return self.ctx.rotation.compare_scenarios(scenarios, self.ctx.kb)
