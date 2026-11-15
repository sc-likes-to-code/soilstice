"""Rotation recommendation and multi-year scenario evaluation engine (layer 4; DATA_ARCHITECTURE §5.11).

Phase 7 engine providing:
1. Factor-by-factor biophysical sequence evaluation (agronomic_fit, rotation_benefit, water_risk, diversity).
2. Deterministic bounded beam search multi-year candidate generation.
3. Multi-scenario agronomic trade-off comparison.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any, Protocol

from app.contracts import (
    CompareScenariosResponse,
    EvaluationDimension,
    GenerateCandidate,
    QualityFlag,
    RotationRecommendation,
    RotationScenario,
    ScenarioEvaluation,
    ScenarioYear,
    TargetSeason,
    YearFinding,
)

from .comparison import ScenarioComparator
from .evaluator import MultiYearEvaluator
from .kb import CropKnowledgeBase
from .search import BoundedBeamSearchGenerator

ENGINE_VERSION = "soilstice-rotation-v1.0.0"
NAMESPACE = uuid.UUID("0b7e4f1a-2c3d-4e5f-8a9b-7c6d5e4f3a21")
DISCLAIMERS = [
    "Not a yield or profit forecast.",
    "Multi-year sequence evaluation is governed by the Phase 5 cited Crop Knowledge Base (EV0001–EV0212) and Phase 6 environmental suitability.",
    "Consecutive monoculture and family repetition penalize disease break and diversity ratings.",
]


class RotationEngine(Protocol):
    def recommend(self, field_id: uuid.UUID, season_year: int, kb: CropKnowledgeBase) -> RotationRecommendation: ...
    def evaluate(
        self,
        sequence: list[ScenarioYear],
        kb: CropKnowledgeBase,
        field_id: uuid.UUID | None = None,
        baseline_suitability: Any | None = None,
        antecedent_crop: Any | None = None,
    ) -> ScenarioEvaluation: ...


PENDING_ENGINE_VERSION = "soilstice-rotation-0.0.0-pending"


class MultiYearRotationEngine:
    """Production Phase 7 Multi-Year Crop Rotation Engine."""

    def __init__(self) -> None:
        self.version = ENGINE_VERSION

    def recommend(self, field_id: uuid.UUID, season_year: int, kb: CropKnowledgeBase) -> RotationRecommendation:
        return RotationRecommendation(
            recommendation_id=uuid.uuid5(NAMESPACE, f"{field_id}:{season_year}:{kb.kb_version}:{ENGINE_VERSION}"),
            field_id=field_id,
            target_season=TargetSeason(
                label=f"{season_year} season",
                start=date(season_year - 1, 9, 1),
                end=date(season_year, 11, 30),
            ),
            engine_version=ENGINE_VERSION,
            kb_version=kb.kb_version,
            status="insufficient_data",
            candidates=[],
            excluded=[],
            disclaimers=DISCLAIMERS,
            generated_at=datetime.now(UTC),
        )

    def evaluate(
        self,
        sequence: list[ScenarioYear],
        kb: CropKnowledgeBase,
        field_id: uuid.UUID | None = None,
        baseline_suitability: Any | None = None,
        antecedent_crop: Any | None = None,
    ) -> ScenarioEvaluation:
        if not kb.available or kb.kb_version == "none":
            msg = "Not evaluated: the rotation engine requires the cited crop knowledge base (Phase 5)."
            return ScenarioEvaluation(
                engine_version=self.version,
                kb_version=kb.kb_version,
                overall="unknown",
                interpretation="insufficient_data",
                dimensions=[
                    EvaluationDimension(key=k, band="unknown", explanation=msg)
                    for k in ("agronomic_fit", "rotation_benefit", "water_risk", "diversity")
                ],
                year_findings=[YearFinding(year=y.year, band="unknown", messages=[], evidence_ids=[]) for y in sequence],
                warnings=[QualityFlag(code="ENGINE_PENDING_KB", severity="warning", message=msg)],
                evaluated_at=datetime.now(UTC),
            )
        evaluator = MultiYearEvaluator(kb)
        return evaluator.evaluate(
            sequence=sequence,
            field_id=field_id,
            baseline_suitability=baseline_suitability,
            antecedent_crop=antecedent_crop,
        )

    def generate_candidates(
        self,
        field_id: uuid.UUID,
        horizon: int,
        start_year: int,
        kb: CropKnowledgeBase,
        baseline_suitability: Any | None = None,
        antecedent_crop_code: int | None = None,
        include_cover_crops: bool = True,
        max_candidates: int = 10,
    ) -> list[GenerateCandidate]:
        generator = BoundedBeamSearchGenerator(kb)
        return generator.generate(
            field_id=field_id,
            horizon=horizon,
            start_year=start_year,
            antecedent_crop_code=antecedent_crop_code,
            baseline_suitability=baseline_suitability,
            include_cover_crops=include_cover_crops,
            max_candidates=max_candidates,
        )

    def compare_scenarios(
        self,
        scenarios: list[RotationScenario],
        kb: CropKnowledgeBase,
    ) -> CompareScenariosResponse:
        comparator = ScenarioComparator(kb)
        return comparator.compare(scenarios)


class PendingRotationEngine:
    """Pre-Phase 7 placeholder engine kept for backward-compatibility with tests."""

    def recommend(self, field_id: uuid.UUID, season_year: int, kb: CropKnowledgeBase) -> RotationRecommendation:
        return RotationRecommendation(
            recommendation_id=uuid.uuid5(NAMESPACE, f"{field_id}:{season_year}:{kb.kb_version}:{PENDING_ENGINE_VERSION}"),
            field_id=field_id,
            target_season=TargetSeason(
                label=f"Calendar year {season_year} (crop season windows pending KB)",
                start=date(season_year, 1, 1),
                end=date(season_year, 12, 31),
            ),
            engine_version=PENDING_ENGINE_VERSION,
            kb_version=kb.kb_version,
            status="insufficient_data",
            candidates=[],
            excluded=[],
            disclaimers=DISCLAIMERS,
            generated_at=datetime.now(UTC),
        )

    def evaluate(
        self,
        sequence: list[ScenarioYear],
        kb: CropKnowledgeBase,
        field_id: uuid.UUID | None = None,
        baseline_suitability: Any | None = None,
        antecedent_crop: Any | None = None,
    ) -> ScenarioEvaluation:
        msg = "Not evaluated: the rotation engine requires the cited crop knowledge base (Phase 5)."
        return ScenarioEvaluation(
            engine_version=PENDING_ENGINE_VERSION,
            kb_version=kb.kb_version,
            overall="unknown",
            interpretation="insufficient_data",
            dimensions=[
                EvaluationDimension(key=k, band="unknown", explanation=msg)
                for k in ("agronomic_fit", "rotation_benefit", "water_risk", "diversity")
            ],
            year_findings=[YearFinding(year=y.year, band="unknown", messages=[], evidence_ids=[]) for y in sequence],
            warnings=[QualityFlag(code="ENGINE_PENDING_KB", severity="warning", message=msg)],
            evaluated_at=datetime.now(UTC),
        )

