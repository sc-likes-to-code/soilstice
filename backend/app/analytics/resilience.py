"""Resilience engine interface (DATA_ARCHITECTURE §5.10). Framework frozen; breakpoints are set and cited in Phase 4.

Until a versioned, cited breakpoint table exists, `PendingResilienceEngine` returns status "pending" with every
score null (NOT_COMPUTED) and band "unknown". It never fabricates a score.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from app.contracts import (
    EnvironmentalIndicator,
    MethodRef,
    QualityFlag,
    Quantity,
    ResilienceComponent,
    ResilienceComposite,
    ResilienceProfile,
)

MODEL_VERSION = "soilstice-resilience-0.0.0-pending"
NAMESPACE = uuid.UUID("6f1c3d0e-5a9b-4c2e-9d7a-50115713c0de")

COMPONENTS = [
    ("soil_water_buffer", "Soil water buffer", "F", ["aws_0_150"]),
    ("terrain_erosion_risk", "Terrain erosion risk", "F", ["slope_p90_pct"]),
    ("vegetation_stability", "Vegetation stability", "F", ["ndvi_peak_cv"]),
    ("climate_exposure", "Climate exposure", "R", ["precip_anomaly_pct", "heat_stress_days", "sm_rootzone_dry_days"]),
    ("rotation_diversity", "Rotation diversity", "F", ["distinct_crops", "max_monoculture_run", "rotation_shannon"]),
]

RULE_PENDING = MethodRef(
    method_id="resilience_breakpoints", name="Resilience breakpoint table (not yet defined)", version="0",
    description="Absolute, cited breakpoints per component are set in Phase 4 (DATA_ARCHITECTURE §5.10). "
                "No score is produced until the table exists.",
)
DISCLAIMERS = [
    "Resilience scoring is not yet available: breakpoint tables are defined and cited in Phase 4.",
    "Scores, when available, are decision-support indicators, not agronomic prescriptions.",
    "Components marked support class R are regional context and do not measure this field.",
]


class ResilienceEngine(Protocol):
    def profile(self, field_id: uuid.UUID, indicators: list[EnvironmentalIndicator], as_of: date
                ) -> ResilienceProfile: ...


class PendingResilienceEngine:
    def profile(self, field_id, indicators, as_of):
        by_key = {i.key: i.indicator_id for i in indicators}
        comps = [
            ResilienceComponent(
                key=key, label=label, score=Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED"),
                band="unknown", support_class=support, confidence="low",
                input_indicator_ids=[by_key[k] for k in inputs if k in by_key],
                explanation="Not scored: the Phase 4 breakpoint table for this component is not yet defined.",
                rule_ref=RULE_PENDING,
            )
            for key, label, support, inputs in COMPONENTS
        ]
        return ResilienceProfile(
            profile_id=uuid.uuid5(NAMESPACE, f"{field_id}:{as_of.isoformat()}:{MODEL_VERSION}"),
            field_id=field_id, as_of=as_of, model_version=MODEL_VERSION, status="pending",
            composite=ResilienceComposite(score=Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED"),
                                          band="unknown", confidence="low", components_used=0),
            components=comps,
            limitations=[QualityFlag(code="BREAKPOINTS_PENDING", severity="info",
                                     message="Resilience breakpoints are not yet defined (Phase 4).")],
            disclaimers=DISCLAIMERS,
        )
