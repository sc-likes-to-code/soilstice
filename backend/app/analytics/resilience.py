"""Resilience engine interface & expert-rule piecewise-linear models (DATA_ARCHITECTURE §5.10).

Evaluates 5 distinct environmental components using absolute agronomic breakpoints and engineering scoring heuristics.
This model is an expert-informed decision-support heuristic, NOT an empirically calibrated outcome model.
Fields are NEVER ranked against each other.
Enforces the minimum component quorum rule (>= 4 of 5 components required for composite score).
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
    ScoreBand,
)

MODEL_VERSION = "soilstice-resilience-1.0.0"
PENDING_VERSION = "soilstice-resilience-0.0.0-pending"
NAMESPACE = uuid.UUID("6f1c3d0e-5a9b-4c2e-9d7a-50115713c0de")

COMPONENTS = [
    ("soil_water_buffer", "Soil water buffer", "F", ["aws_0_150"]),
    ("terrain_erosion_risk", "Terrain erosion risk", "F", ["slope_p90_pct"]),
    ("climate_exposure", "Climate exposure", "R", ["precip_anomaly_pct", "heat_stress_days"]),
    ("rotation_diversity", "Rotation diversity", "F", ["distinct_crops", "max_monoculture_run", "rotation_shannon"]),
    ("vegetation_stability", "Vegetation stability", "F", ["ndvi_peak_cv"]),
]

RULE_SOIL_WATER = MethodRef(
    method_id="resilience_soil_water_buffer", name="Soil Water Buffer Breakpoint Model", version="1",
    description="Piecewise-linear scoring of profile available water storage (aws_0_150). Breakpoints (6, 10, 15, "
                "20, 25 cm) represent engineering scoring thresholds informed by NRCS Soil Quality Technical Note No. 2 "
                "and K-State Extension MF-2980 available water capacity ranges.",
)
RULE_TERRAIN_EROSION = MethodRef(
    method_id="resilience_terrain_erosion_risk", name="Terrain Erosion Hazard Model", version="1",
    description="Piecewise-linear scoring of 90th percentile slope. Breakpoints (0.5%, 1.5%, 3%, 6%, 10%) represent "
                "engineering scoring thresholds informed by NRCS Highly Erodible Land (HEL) slope classes and RUSLE.",
)
RULE_CLIMATE_EXPOSURE = MethodRef(
    method_id="resilience_climate_exposure", name="Climatic Extremity & Heat Stress Model", version="1",
    description="Piecewise-linear scoring of seasonal heat-stress days and precipitation departure vs 1991–2020 normal "
                "using engineering heuristic weighting (0.60 heat / 0.40 precip) informed by Schlenker & Roberts (2009).",
)
RULE_ROTATION_DIVERSITY = MethodRef(
    method_id="resilience_rotation_diversity", name="Multi-Metric Rotation Diversity Model", version="1",
    description="Engineering heuristic scoring combining crop species richness, monoculture penalty, and Shannon entropy "
                "over 20-year CDL history informed by crop diversity principles (Davis et al. 2012; Liebman & Dyck 1993).",
)
RULE_VEGETATION_STABILITY = MethodRef(
    method_id="resilience_vegetation_stability", name="Canopy Temporal Stability Model", version="1",
    description="Peak NDVI interannual coefficient of variation scoring using engineering heuristic breakpoints "
                "(0.08, 0.15, 0.25, 0.40) informed by satellite phenology stability literature (Pettorelli et al. 2005).",
)
RULE_PENDING = MethodRef(
    method_id="resilience_breakpoints", name="Resilience breakpoint table (not yet defined)", version="0",
    description="Absolute, cited breakpoints per component are set in Phase 4 (DATA_ARCHITECTURE §5.10). "
                "No score is produced until the table exists.",
)

DISCLAIMERS = [
    "Resilience scores are decision-support indicators based on expert-informed agronomic breakpoints, "
    "not empirically calibrated outcome models or agronomic prescriptions.",
    "Components marked support class R (e.g. Climate Exposure) describe regional context and do not measure "
    "field-level variation.",
    "Composite resilience requires a minimum quorum of 4 valid components; fields missing required inputs are labeled "
    "insufficient_data rather than assigned fabricated scores.",
]


def _interpolate(val: float, breakpoints: list[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation across a sorted list of (threshold, score) pairs."""
    if val <= breakpoints[0][0]:
        return breakpoints[0][1]
    if val >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x0 <= val <= x1:
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (val - x0) / (x1 - x0)
    return breakpoints[-1][1]


def _band(score: float | None) -> ScoreBand:
    if score is None:
        return "unknown"
    if score < 40.0:
        return "low"
    if score <= 70.0:
        return "moderate"
    return "high"


class ResilienceEngine(Protocol):
    def profile(self, field_id: uuid.UUID, indicators: list[EnvironmentalIndicator], as_of: date
                ) -> ResilienceProfile: ...


class AgronomicBreakpointResilienceEngine:
    """Phase 4 resilience engine implementing expert-informed agronomic breakpoints and scoring heuristics."""

    def profile(self, field_id: uuid.UUID, indicators: list[EnvironmentalIndicator], as_of: date) -> ResilienceProfile:
        val_map: dict[str, float | None] = {i.key: i.value.value for i in indicators}
        id_map: dict[str, str] = {i.key: i.indicator_id for i in indicators}

        components: list[ResilienceComponent] = []

        # 1. Soil Water Buffer (aws_0_150)
        aws = val_map.get("aws_0_150")
        if aws is not None:
            # Breakpoints: <=6 cm -> 0; 10 cm -> 30; 15 cm -> 55; 20 cm -> 80; >=25 cm -> 100
            score_sw = round(_interpolate(
                aws, [(6.0, 0.0), (10.0, 30.0), (15.0, 55.0), (20.0, 80.0), (25.0, 100.0)]
            ), 1)
            band_sw = _band(score_sw)
            conf_sw = "high"
            expl_sw = (f"Soil profile available water storage of {aws:.1f} cm provides {band_sw} drought buffering "
                       "capacity (USDA NRCS Soil Quality Technical Note No. 2).")
            q_sw = Quantity(value=score_sw, unit="score_0_100")
        else:
            band_sw = "unknown"
            conf_sw = "low"
            expl_sw = "Soil profile available water storage (0–150 cm) is uncomputed or unavailable."
            q_sw = Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED")

        components.append(ResilienceComponent(
            key="soil_water_buffer", label="Soil water buffer", score=q_sw, band=band_sw,
            support_class="F", confidence=conf_sw,
            input_indicator_ids=[id_map["aws_0_150"]] if "aws_0_150" in id_map else [],
            explanation=expl_sw, rule_ref=RULE_SOIL_WATER,
        ))

        # 2. Terrain Erosion Risk (slope_p90_pct)
        slope = val_map.get("slope_p90_pct")
        if slope is not None:
            # Breakpoints: <=0.5% -> 100; 1.5% -> 85; 3.0% -> 65; 6.0% -> 35; >=10.0% -> 10
            score_ter = round(_interpolate(
                slope, [(0.5, 100.0), (1.5, 85.0), (3.0, 65.0), (6.0, 35.0), (10.0, 10.0)]
            ), 1)
            band_ter = _band(score_ter)
            conf_ter = "high"
            expl_ter = (f"Field 90th percentile slope of {slope:.1f}% indicates {band_ter} erosion hazard resilience "
                        "(USDA NRCS Highly Erodible Land criteria).")
            q_ter = Quantity(value=score_ter, unit="score_0_100")
        else:
            band_ter = "unknown"
            conf_ter = "low"
            expl_ter = "Terrain slope uncomputed: SRTM extraction requires Earthdata Login credentials."
            q_ter = Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED")

        components.append(ResilienceComponent(
            key="terrain_erosion_risk", label="Terrain erosion risk", score=q_ter, band=band_ter,
            support_class="F", confidence=conf_ter,
            input_indicator_ids=[id_map["slope_p90_pct"]] if "slope_p90_pct" in id_map else [],
            explanation=expl_ter, rule_ref=RULE_TERRAIN_EROSION,
        ))

        # 3. Climate Exposure (heat_stress_days, precip_anomaly_pct)
        heat = val_map.get("heat_stress_days")
        precip_anom = val_map.get("precip_anomaly_pct")
        heat_inputs = [id_map[k] for k in ("heat_stress_days", "precip_anomaly_pct") if k in id_map]
        if heat is not None or precip_anom is not None:
            heat_sub: float = 100.0
            if heat is not None:
                # <=5 days -> 100; 15 -> 75; 30 -> 45; >=50 -> 10
                heat_sub = _interpolate(heat, [(5.0, 100.0), (15.0, 75.0), (30.0, 45.0), (50.0, 10.0)])
            precip_sub: float = 100.0
            if precip_anom is not None:
                if precip_anom < 0:
                    precip_sub = max(20.0, 100.0 + (precip_anom / 50.0) * 80.0)
                elif precip_anom <= 20.0:
                    precip_sub = 100.0
                else:
                    precip_sub = max(60.0, 100.0 - ((precip_anom - 20.0) / 30.0) * 40.0)
            if heat is not None and precip_anom is not None:
                score_clim = round(0.60 * heat_sub + 0.40 * precip_sub, 1)
                expl_clim = (f"Regional climate exposure with {heat:.0f} heat-stress days and {precip_anom:+.1f}% "
                             f"precipitation anomaly yields {score_clim:.1f} ({_band(score_clim)} resilience).")
            elif heat is not None:
                score_clim = round(heat_sub, 1)
                expl_clim = (f"Regional heat exposure with {heat:.0f} heat-stress days yields "
                             f"{_band(score_clim)} resilience.")
            else:
                score_clim = round(precip_sub, 1)
                expl_clim = (f"Regional precipitation anomaly of {precip_anom:+.1f}% yields "
                             f"{_band(score_clim)} resilience.")
            band_clim = _band(score_clim)
            conf_clim = "low"  # Support class R
            q_clim = Quantity(value=score_clim, unit="score_0_100")
        else:
            band_clim = "unknown"
            conf_clim = "low"
            expl_clim = "Regional climate indicators unavailable."
            q_clim = Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED")

        components.append(ResilienceComponent(
            key="climate_exposure", label="Climate exposure", score=q_clim, band=band_clim,
            support_class="R", confidence=conf_clim,
            input_indicator_ids=heat_inputs,
            explanation=expl_clim, rule_ref=RULE_CLIMATE_EXPOSURE,
        ))

        # 4. Rotation Diversity (distinct_crops, max_monoculture_run, rotation_shannon)
        distinct = val_map.get("distinct_crops")
        max_run = val_map.get("max_monoculture_run")
        shannon = val_map.get("rotation_shannon")
        rot_inputs = [id_map[k] for k in ("distinct_crops", "max_monoculture_run", "rotation_shannon") if k in id_map]
        if distinct is not None and max_run is not None and shannon is not None:
            sub1 = max(0.0, 100.0 - (max_run - 1.0) * 20.0)
            sub2 = min(100.0, distinct * 25.0)
            sub3 = min(100.0, (shannon / 1.386) * 100.0)
            score_rot = round(0.40 * sub1 + 0.30 * sub2 + 0.30 * sub3, 1)
            band_rot = _band(score_rot)
            conf_rot = "high"
            expl_rot = (f"20-year CDL history reveals {distinct:.0f} distinct crops, maximum monoculture run of "
                        f"{max_run:.0f} yr, and Shannon diversity index of {shannon:.2f} (Davis et al. 2012).")
            q_rot = Quantity(value=score_rot, unit="score_0_100")
        else:
            band_rot = "unknown"
            conf_rot = "low"
            expl_rot = "Crop history rotation metrics unavailable."
            q_rot = Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED")

        components.append(ResilienceComponent(
            key="rotation_diversity", label="Rotation diversity", score=q_rot, band=band_rot,
            support_class="F", confidence=conf_rot,
            input_indicator_ids=rot_inputs,
            explanation=expl_rot, rule_ref=RULE_ROTATION_DIVERSITY,
        ))

        # 5. Vegetation Stability (ndvi_peak_cv)
        ndvi_cv = val_map.get("ndvi_peak_cv")
        if ndvi_cv is not None:
            # <=0.08 -> 100; 0.15 -> 75; 0.25 -> 45; >=0.40 -> 10
            score_veg = round(_interpolate(ndvi_cv, [(0.08, 100.0), (0.15, 75.0), (0.25, 45.0), (0.40, 10.0)]), 1)
            band_veg = _band(score_veg)
            conf_veg = "high"
            expl_veg = f"Peak NDVI interannual CV of {ndvi_cv:.3f} indicates {band_veg} canopy buffering stability."
            q_veg = Quantity(value=score_veg, unit="score_0_100")
        else:
            band_veg = "unknown"
            conf_veg = "low"
            expl_veg = "Vegetation stability uncomputed: HLS raster extraction requires Earthdata Login credentials."
            q_veg = Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED")

        components.append(ResilienceComponent(
            key="vegetation_stability", label="Vegetation stability", score=q_veg, band=band_veg,
            support_class="F", confidence=conf_veg,
            input_indicator_ids=[id_map["ndvi_peak_cv"]] if "ndvi_peak_cv" in id_map else [],
            explanation=expl_veg, rule_ref=RULE_VEGETATION_STABILITY,
        ))

        # Composite Quorum Rule: >= 4 of 5 components must be valid
        valid_comps = [c for c in components if c.score.value is not None]
        n_valid = len(valid_comps)
        limitations: list[QualityFlag] = []

        if n_valid >= 4:
            comp_score = round(sum(c.score.value for c in valid_comps) / n_valid, 1)  # type: ignore[arg-type]
            comp_band = _band(comp_score)
            comp_conf = "low" if any(c.confidence == "low" for c in valid_comps) else "high"
            comp_q = Quantity(value=comp_score, unit="score_0_100")
            status = "computed"
        else:
            comp_q = Quantity(value=None, unit="score_0_100", missing_reason="INSUFFICIENT_COVERAGE")
            comp_band = "unknown"
            comp_conf = "low"
            status = "insufficient_data"
            limitations.append(QualityFlag(
                code="QUORUM_NOT_MET", severity="warning",
                message=f"Only {n_valid} of 5 resilience components have valid observations (minimum quorum is 4). "
                        "Composite resilience is withheld to maintain scientific integrity.",
            ))

        return ResilienceProfile(
            profile_id=uuid.uuid5(NAMESPACE, f"{field_id}:{as_of.isoformat()}:{MODEL_VERSION}"),
            field_id=field_id, as_of=as_of, model_version=MODEL_VERSION, status=status,
            composite=ResilienceComposite(
                score=comp_q, band=comp_band, confidence=comp_conf, components_used=n_valid,
            ),
            components=components,
            limitations=limitations,
            disclaimers=DISCLAIMERS,
        )


# Backwards compatibility alias
CalibratedResilienceEngine = AgronomicBreakpointResilienceEngine


class PendingResilienceEngine:
    """Fallback pending engine for backwards compatibility."""

    def profile(self, field_id: uuid.UUID, indicators: list[EnvironmentalIndicator], as_of: date) -> ResilienceProfile:
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
            profile_id=uuid.uuid5(NAMESPACE, f"{field_id}:{as_of.isoformat()}:{PENDING_VERSION}"),
            field_id=field_id, as_of=as_of, model_version=PENDING_VERSION, status="pending",
            composite=ResilienceComposite(
                score=Quantity(value=None, unit="score_0_100", missing_reason="NOT_COMPUTED"),
                band="unknown", confidence="low", components_used=0,
            ),
            components=comps,
            limitations=[QualityFlag(code="BREAKPOINTS_PENDING", severity="info",
                                     message="Resilience breakpoints are not yet defined (Phase 4).")],
            disclaimers=DISCLAIMERS,
        )
