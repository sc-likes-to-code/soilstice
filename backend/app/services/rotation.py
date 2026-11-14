"""Rotation services (E17, E20–E25). Scenario CRUD is real; evaluation/recommendation await the cited KB."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.catalog import SPATIAL
from app.contracts import (
    CropEvidenceRecord,
    CropHistory,
    CropOption,
    CropProfile,
    CropProfileSummary,
    DirectedRotationTransition,
    KnowledgeBaseMetadata,
    QualityInfo,
    RotationRecommendation,
    RotationScenario,
    ScenarioYear,
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
        return self.ctx.rotation.recommend(f.field_id, season_year, self.ctx.kb)

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

    def create_scenario(self, field_id, req: UpsertScenarioRequest) -> RotationScenario:
        f = self.fields.get_field(field_id)
        seq = self._sequence(req)
        t = datetime.now(UTC)
        sc = RotationScenario(scenario_id=uuid.uuid4(), field_id=f.field_id, name=req.name.strip(),
                              start_year=req.start_year, sequence=seq,
                              evaluation=self.ctx.rotation.evaluate(seq, self.ctx.kb), created_at=t, updated_at=t)
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
                                   "evaluation": self.ctx.rotation.evaluate(seq, self.ctx.kb),
                                   "updated_at": datetime.now(UTC)})
        return self.repos.scenarios.put(str(sc.scenario_id), sc, parent=sc.field_id)

    def delete_scenario(self, scenario_id) -> None:
        self._get(scenario_id)
        self.repos.scenarios.delete(str(scenario_id))
