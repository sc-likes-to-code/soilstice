"""Rotation recommendation engine interface (layer 4; DATA_ARCHITECTURE §5.11).

The limiting-factor engine is NOT implemented in Phase 2: it needs the cited crop KB. `PendingRotationEngine`
returns contract-valid "insufficient_data" recommendations and "unknown" scenario evaluations, and never produces
suitability classes, rankings or thresholds.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Protocol

from app.contracts import (
    EvaluationDimension,
    QualityFlag,
    RotationRecommendation,
    ScenarioEvaluation,
    ScenarioYear,
    TargetSeason,
    YearFinding,
)

from .kb import CropKnowledgeBase

ENGINE_VERSION = "soilstice-rotation-0.0.0-pending"
NAMESPACE = uuid.UUID("0b7e4f1a-2c3d-4e5f-8a9b-7c6d5e4f3a21")
DISCLAIMERS = [
    "Not a yield or profit forecast.",
    "Crop suitability and rotation recommendations require the cited crop knowledge base (Phase 5), which is not yet "
    "available. No recommendation is made.",
]


class RotationEngine(Protocol):
    def recommend(self, field_id: uuid.UUID, season_year: int, kb: CropKnowledgeBase) -> RotationRecommendation: ...
    def evaluate(self, sequence: list[ScenarioYear], kb: CropKnowledgeBase) -> ScenarioEvaluation: ...


class PendingRotationEngine:
    def recommend(self, field_id, season_year, kb):
        return RotationRecommendation(
            recommendation_id=uuid.uuid5(NAMESPACE, f"{field_id}:{season_year}:{kb.kb_version}:{ENGINE_VERSION}"),
            field_id=field_id,
            target_season=TargetSeason(label=f"Calendar year {season_year} (crop season windows pending KB)",
                                       start=date(season_year, 1, 1), end=date(season_year, 12, 31)),
            engine_version=ENGINE_VERSION, kb_version=kb.kb_version, status="insufficient_data",
            candidates=[], excluded=[], disclaimers=DISCLAIMERS, generated_at=datetime.now(UTC),
        )

    def evaluate(self, sequence, kb):
        msg = "Not evaluated: the rotation engine requires the cited crop knowledge base (Phase 5)."
        return ScenarioEvaluation(
            engine_version=ENGINE_VERSION, kb_version=kb.kb_version, overall="unknown",
            dimensions=[EvaluationDimension(key=k, band="unknown", explanation=msg)
                        for k in ("agronomic_fit", "rotation_benefit", "water_risk", "diversity")],
            year_findings=[YearFinding(year=y.year, band="unknown", messages=[], evidence_ids=[]) for y in sequence],
            warnings=[QualityFlag(code="ENGINE_PENDING_KB", severity="warning", message=msg)],
            evaluated_at=datetime.now(UTC),
        )
