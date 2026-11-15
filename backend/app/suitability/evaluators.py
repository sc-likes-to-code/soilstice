"""Phase 6: Suitability Factor Evaluator.

Evaluates factor-by-factor compatibility between field environmental observations
and crop agronomic requirements from the Phase 5 Crop Knowledge Base.

Mandatory scientific principles:
- Never coerce null to 0.0; unknown values remain unknown.
- Missing crop requirements are never fabricated.
- Distinguish regional macro-climate from field observations.
- Distinguish effective water extraction depth from maximum anatomical root depth.
- Rainfall requirements are not irrigation requirements; P - ET0 is not crop water demand.
"""

from __future__ import annotations

from typing import Any

from app.contracts import (
    ClimateProfile,
    CropHistory,
    CropProfile,
    EnvironmentalIndicator,
    FactorCategory,
    FactorCompatibility,
    FactorSeverity,
    Quantity,
    SoilProfile,
    SuitabilityFactorAssessment,
    SupportClass,
    TerrainProfile,
)


def _factor(
    key: str,
    name: str,
    category: FactorCategory,
    observed: Quantity,
    requirement: str | None,
    compatibility: FactorCompatibility,
    severity: FactorSeverity,
    score: float | None,
    interpretation: str,
    evidence_ids: list[str] | None = None,
    data_status: str = "available",
    support_class: SupportClass = "F",
) -> SuitabilityFactorAssessment:
    return SuitabilityFactorAssessment(
        factor_key=key,
        factor_name=name,
        category=category,
        observed_value=observed,
        crop_requirement=requirement,
        compatibility=compatibility,
        is_limiting=severity in {"moderate", "critical"},
        is_favorable=severity == "favorable",
        severity=severity,
        score=score,
        interpretation=interpretation,
        evidence_ids=evidence_ids or [],
        data_status=data_status,
        support_class=support_class,
    )


def _get_crop_attr(crop_dict: dict[str, Any], *path: str) -> Any:
    curr = crop_dict
    for p in path:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return None
    return curr


def evaluate_thermal_gdd(crop: CropProfile, climate: ClimateProfile | None) -> SuitabilityFactorAssessment:
    gdd_data = _get_crop_attr(crop.growing_duration, "growing_degree_days_accumulated") or {}
    gdd_min = gdd_data.get("min_value")
    gdd_max = gdd_data.get("max_value")
    ev_ids = gdd_data.get("evidence_ids") or []
    req_str = f"{gdd_min:0.0f}–{gdd_max:0.0f} °C-days to physiological maturity" if gdd_min and gdd_max else None

    # Find GDD indicator in climate profile
    gdd_ind: EnvironmentalIndicator | None = None
    if climate and climate.indicators:
        gdd_ind = next((i for i in climate.indicators if i.key == "gdd_season"), None)

    observed_q = gdd_ind.value if gdd_ind else Quantity(value=None, unit="degC_day", missing_reason="NOT_COMPUTED")

    if observed_q.value is None or gdd_min is None:
        status = "missing" if observed_q.value is None else "not_integrated"
        interp = (
            "Seasonal GDD accumulation data unavailable for this field."
            if observed_q.value is None
            else "Crop developmental thermal requirement not documented in knowledge base."
        )
        return _factor(
            "thermal_gdd",
            "Growing Degree Days (GDD)",
            "thermal",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            interp,
            ev_ids,
            status,
            support_class="R",
        )

    val = float(observed_q.value)
    if val >= gdd_min:
        if val <= gdd_max * 1.4:
            return _factor(
                "thermal_gdd",
                "Growing Degree Days (GDD)",
                "thermal",
                observed_q,
                req_str,
                "optimal",
                "favorable",
                95.0,
                f"Observed heat accumulation ({val:0.0f} °C-days) fully satisfies the crop developmental thermal requirement ({req_str}).",
                ev_ids,
                support_class="R",
            )
        else:
            return _factor(
                "thermal_gdd",
                "Growing Degree Days (GDD)",
                "thermal",
                observed_q,
                req_str,
                "compatible",
                "none",
                85.0,
                f"Observed heat accumulation ({val:0.0f} °C-days) exceeds thermal maturity thresholds; verify crop tolerance to accelerated phenology.",
                ev_ids,
                support_class="R",
            )
    elif val >= gdd_min * 0.85:
        return _factor(
            "thermal_gdd",
            "Growing Degree Days (GDD)",
            "thermal",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            60.0,
            f"Observed heat accumulation ({val:0.0f} °C-days) is slightly below standard requirement ({gdd_min:0.0f} °C-days); requires short-maturity varieties.",
            ev_ids,
            support_class="R",
        )
    else:
        return _factor(
            "thermal_gdd",
            "Growing Degree Days (GDD)",
            "thermal",
            observed_q,
            req_str,
            "critical_limitation",
            "critical",
            20.0,
            f"Severe thermal deficit: observed {val:0.0f} °C-days is substantially below the minimum maturity requirement ({gdd_min:0.0f} °C-days).",
            ev_ids,
            support_class="R",
        )


def evaluate_heat_stress(crop: CropProfile, climate: ClimateProfile | None) -> SuitabilityFactorAssessment:
    heat_thresh = _get_crop_attr(crop.temperature_requirements, "heat_stress_threshold_c", "value")
    heat_tol = _get_crop_attr(crop.water_demand_and_tolerance, "heat_tolerance", "rating") or "moderate"
    ev_ids = _get_crop_attr(crop.temperature_requirements, "heat_stress_threshold_c", "evidence_ids") or []

    # Climate indicator threshold context: Phase 4 computes heat_stress_days at Tcrit=30°C for winter wheat, 35°C for all other crops.
    climate_tcrit = 30.0 if crop.crop_id == "CRP003" or crop.cdl_code == 24 else 35.0
    req_str = (
        f"Crop heat threshold: {heat_thresh}°C (indicator T_crit: {climate_tcrit:0.0f}°C); "
        f"tolerance: {heat_tol.replace('_', ' ')}"
        if heat_thresh
        else f"Generic thermal limit: {climate_tcrit:0.0f}°C; tolerance: {heat_tol.replace('_', ' ')}"
    )

    heat_ind: EnvironmentalIndicator | None = None
    if climate and climate.indicators:
        heat_ind = next((i for i in climate.indicators if i.key == "heat_stress_days"), None)

    observed_q = heat_ind.value if heat_ind else Quantity(value=None, unit="day", missing_reason="NOT_COMPUTED")

    if observed_q.value is None:
        return _factor(
            "thermal_heat_stress",
            "Heat Stress Days",
            "thermal",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Heat stress days observation unavailable.",
            ev_ids,
            "missing",
            support_class="R",
        )

    days = int(observed_q.value)
    is_tolerant = heat_tol in {"tolerant", "very_tolerant", "high"}
    is_sensitive = heat_tol in {"sensitive", "very_sensitive", "moderately_sensitive"}

    # Explicit disclosure of unsupported engineering heuristics:
    heuristic_disclaimer = (
        "Day brackets (<=15, 16–35, >35 days) are engineering heuristic tiers, not empirical yield response curves. "
        "Phenology dates unavailable (PHENOLOGY_UNAVAILABLE)."
    )

    if days <= 15:
        return _factor(
            "thermal_heat_stress",
            "Heat Stress Days",
            "thermal",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Low seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C). {heuristic_disclaimer}",
            ev_ids,
            support_class="R",
        )
    elif days <= 35:
        if is_tolerant:
            return _factor(
                "thermal_heat_stress",
                "Heat Stress Days",
                "thermal",
                observed_q,
                req_str,
                "optimal",
                "favorable",
                90.0,
                f"Moderate seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C); within documented crop heat tolerance. {heuristic_disclaimer}",
                ev_ids,
                support_class="R",
            )
        else:
            return _factor(
                "thermal_heat_stress",
                "Heat Stress Days",
                "thermal",
                observed_q,
                req_str,
                "compatible",
                "none",
                75.0,
                f"Moderate seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C); documented thermal sensitivity. {heuristic_disclaimer}",
                ev_ids,
                support_class="R",
            )
    else:  # > 35 days
        if is_tolerant:
            return _factor(
                "thermal_heat_stress",
                "Heat Stress Days",
                "thermal",
                observed_q,
                req_str,
                "compatible",
                "none",
                70.0,
                f"Elevated seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C); tolerated by documented physiological adaptations. {heuristic_disclaimer}",
                ev_ids,
                support_class="R",
            )
        elif is_sensitive:
            return _factor(
                "thermal_heat_stress",
                "Heat Stress Days",
                "thermal",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                50.0,
                f"High seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C); presents elevated thermal stress risk under macro-climatic reanalysis. {heuristic_disclaimer}",
                ev_ids,
                support_class="R",
            )
        else:
            return _factor(
                "thermal_heat_stress",
                "Heat Stress Days",
                "thermal",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                60.0,
                f"High seasonal heat exposure ({days} days with Tmax >= {climate_tcrit:0.0f}°C); presents a moderate thermal constraint under macro-climatic reanalysis. {heuristic_disclaimer}",
                ev_ids,
                support_class="R",
            )


def evaluate_water_precipitation(crop: CropProfile, climate: ClimateProfile | None) -> SuitabilityFactorAssessment:
    p_min = _get_crop_attr(crop.rainfall_requirements, "seasonal_precipitation_min_mm", "value")
    p_max = _get_crop_attr(crop.rainfall_requirements, "seasonal_precipitation_max_mm", "value")
    d_tol = _get_crop_attr(crop.water_demand_and_tolerance, "drought_tolerance", "rating") or "moderate"
    ev_ids = _get_crop_attr(crop.rainfall_requirements, "seasonal_precipitation_min_mm", "evidence_ids") or []
    req_str = f"Seasonal rainfall requirement: {p_min:0.0f}–{p_max:0.0f} mm (drought tolerance: {d_tol})" if p_min and p_max else None

    p_ind = next((i for i in climate.indicators if i.key == "precip_total_season"), None) if climate and climate.indicators else None
    observed_q = p_ind.value if p_ind else Quantity(value=None, unit="mm", missing_reason="NOT_COMPUTED")

    if observed_q.value is None or p_min is None:
        status = "missing" if observed_q.value is None else "not_integrated"
        interp = (
            "Seasonal precipitation observation unavailable."
            if observed_q.value is None
            else "Crop seasonal precipitation requirement not documented in knowledge base."
        )
        return _factor(
            "water_precipitation",
            "Seasonal Precipitation",
            "water_climate",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            interp,
            ev_ids,
            status,
            support_class="R",
        )

    val = float(observed_q.value)
    is_drought_tolerant = d_tol in {"tolerant", "very_tolerant", "high", "high_avoidance", "tolerant_escaping"}

    if p_min <= val <= p_max:
        return _factor(
            "water_precipitation",
            "Seasonal Precipitation",
            "water_climate",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Observed precipitation ({val:0.0f} mm) is within documented range ({p_min:0.0f}–{p_max:0.0f} mm). Note: regional rainfall is not field-level soil water.",
            ev_ids,
            support_class="R",
        )
    elif val > p_max:
        return _factor(
            "water_precipitation",
            "Seasonal Precipitation",
            "water_climate",
            observed_q,
            req_str,
            "compatible",
            "none",
            80.0,
            f"Observed precipitation ({val:0.0f} mm) exceeds upper range ({p_max:0.0f} mm); monitor for fungal disease and waterlogging on poorly drained soils.",
            ev_ids,
            support_class="R",
        )
    else:  # val < p_min
        deficit_pct = (p_min - val) / p_min
        if deficit_pct <= 0.25 and is_drought_tolerant:
            return _factor(
                "water_precipitation",
                "Seasonal Precipitation",
                "water_climate",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                65.0,
                f"Rainfall ({val:0.0f} mm) is below optimal minimum ({p_min:0.0f} mm), but within drought-tolerant adaptation envelope.",
                ev_ids,
                support_class="R",
            )
        elif deficit_pct <= 0.35:
            return _factor(
                "water_precipitation",
                "Seasonal Precipitation",
                "water_climate",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                50.0,
                f"Seasonal moisture deficit: observed {val:0.0f} mm vs minimum required {p_min:0.0f} mm. Supplemental irrigation or fallow moisture required.",
                ev_ids,
                support_class="R",
            )
        else:
            return _factor(
                "water_precipitation",
                "Seasonal Precipitation",
                "water_climate",
                observed_q,
                req_str,
                "critical_limitation",
                "critical",
                25.0,
                f"Severe moisture limitation: observed {val:0.0f} mm is well below rainfed minimum ({p_min:0.0f} mm). Unsuitable for dryland production without full irrigation.",
                ev_ids,
                support_class="R",
            )


def evaluate_soil_ph(crop: CropProfile, soil: SoilProfile | None) -> SuitabilityFactorAssessment:
    ph_opt_min = _get_crop_attr(crop.soil_preferences, "soil_ph_optimal_min", "value")
    ph_opt_max = _get_crop_attr(crop.soil_preferences, "soil_ph_optimal_max", "value")
    ph_tol_min = _get_crop_attr(crop.soil_preferences, "soil_ph_tolerated_min", "value")
    ph_tol_max = _get_crop_attr(crop.soil_preferences, "soil_ph_tolerated_max", "value")
    ev_ids = _get_crop_attr(crop.soil_preferences, "soil_ph_optimal_min", "evidence_ids") or []
    req_str = f"Optimal pH: {ph_opt_min}–{ph_opt_max}; Tolerated: {ph_tol_min}–{ph_tol_max}" if ph_opt_min else None

    top_layer = soil.layers[0] if soil and soil.layers else None
    observed_q = top_layer.ph_h2o if top_layer else Quantity(value=None, unit="pH", missing_reason="NO_DATA_SOURCE")

    if observed_q.value is None or ph_opt_min is None:
        status = "missing" if observed_q.value is None else "not_integrated"
        interp = (
            "Topsoil pH estimate unavailable from SSURGO survey records."
            if observed_q.value is None
            else "Crop pH preference not documented in knowledge base."
        )
        return _factor(
            "soil_ph",
            "Soil pH (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            interp,
            ev_ids,
            status,
            support_class="F",
        )

    ph = float(observed_q.value)

    if ph_opt_min <= ph <= ph_opt_max:
        return _factor(
            "soil_ph",
            "Soil pH (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            98.0,
            f"Survey-derived topsoil pH estimate ({ph:0.2f}) is in the optimal agronomic range ({ph_opt_min:0.1f}–{ph_opt_max:0.1f}) for nutrient availability and rhizobial activity.",
            ev_ids,
            support_class="F",
        )
    elif ph_tol_min <= ph <= ph_tol_max:
        return _factor(
            "soil_ph",
            "Soil pH (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            65.0,
            f"Survey-derived topsoil pH estimate ({ph:0.2f}) is outside optimal ({ph_opt_min:0.1f}–{ph_opt_max:0.1f}) but within tolerated limits ({ph_tol_min:0.1f}–{ph_tol_max:0.1f}); consider lime/gypsum management.",
            ev_ids,
            support_class="F",
        )
    else:
        return _factor(
            "soil_ph",
            "Soil pH (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "critical_limitation",
            "critical",
            15.0,
            f"Survey-derived topsoil pH estimate ({ph:0.2f}) exceeds biological tolerance boundaries ({ph_tol_min:0.1f}–{ph_tol_max:0.1f}); severe nutrient tie-up or aluminum toxicity hazard.",
            ev_ids,
            support_class="F",
        )


DRAINAGE_CLASS_CODES: dict[str, float] = {
    "excessively_drained": 1.0,
    "somewhat_excessively_drained": 2.0,
    "well_drained": 3.0,
    "moderately_well_drained": 4.0,
    "somewhat_poorly_drained": 5.0,
    "poorly_drained": 6.0,
    "very_poorly_drained": 7.0,
}

TEXTURE_CLASS_CODES: dict[str, float] = {
    "sand": 1.0,
    "loamy_sand": 2.0,
    "sandy_loam": 3.0,
    "loam": 4.0,
    "silt_loam": 5.0,
    "silt": 6.0,
    "sandy_clay_loam": 7.0,
    "clay_loam": 8.0,
    "silty_clay_loam": 9.0,
    "sandy_clay": 10.0,
    "silty_clay": 11.0,
    "clay": 12.0,
}


def evaluate_soil_drainage(crop: CropProfile, soil: SoilProfile | None) -> SuitabilityFactorAssessment:
    prefs = _get_crop_attr(crop.soil_preferences, "soil_drainage_class_preferences") or []
    pref_map = {item.get("drainage_class"): item.get("suitability_rating") for item in prefs if isinstance(item, dict)}
    ev_ids = [eid for item in prefs if isinstance(item, dict) for eid in item.get("evidence_ids", [])]
    req_str = f"Preferred drainage: {', '.join([k for k, v in pref_map.items() if v == 'ideal'])}" if pref_map else None

    drainage_val = soil.drainage_class.value if soil and soil.drainage_class else None
    clean_drain = drainage_val.lower().replace(" ", "_") if drainage_val else ""

    if not drainage_val:
        observed_q = Quantity(value=None, unit="unitless", missing_reason="NO_DATA_SOURCE")
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Survey-derived drainage class unavailable from SSURGO.",
            ev_ids,
            "missing",
            support_class="F",
        )

    drain_code = DRAINAGE_CLASS_CODES.get(clean_drain, 3.0)
    observed_q = Quantity(value=drain_code, unit="unitless", missing_reason=None)
    rating = pref_map.get(clean_drain)

    if rating == "ideal":
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Survey-derived drainage class estimate ({drainage_val}) is ideal for root aeration and disease prevention.",
            ev_ids,
            support_class="F",
        )
    elif rating == "acceptable":
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "compatible",
            "none",
            80.0,
            f"Survey-derived drainage class estimate ({drainage_val}) is acceptable for commercial production.",
            ev_ids,
            support_class="F",
        )
    elif rating == "marginal":
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            55.0,
            f"Survey-derived drainage class estimate ({drainage_val}) is marginal; requires enhanced drainage management or waterlogging risk mitigation.",
            ev_ids,
            support_class="F",
        )
    elif rating == "unsuitable" or (not rating and clean_drain in ("poorly_drained", "very_poorly_drained") and crop.crop_id in ("CRP011", "CRP005")):
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "critical_limitation",
            "critical",
            20.0,
            f"Survey-derived drainage class estimate ({drainage_val}) is unsuitable; severe crown/root rot or anoxia hazard.",
            ev_ids,
            support_class="F",
        )
    else:
        # Default fallback if drainage class not explicitly keyed
        return _factor(
            "soil_drainage",
            "Soil Drainage Class",
            "soil",
            observed_q,
            req_str,
            "compatible",
            "none",
            75.0,
            f"Survey-derived drainage class estimate ({drainage_val}) is conditionally compatible.",
            ev_ids,
            support_class="F",
        )


def evaluate_soil_texture(crop: CropProfile, soil: SoilProfile | None) -> SuitabilityFactorAssessment:
    prefs = _get_crop_attr(crop.soil_preferences, "soil_texture_preferences") or []
    pref_map = {item.get("texture_class"): item.get("suitability_rating") for item in prefs if isinstance(item, dict)}
    ev_ids = [eid for item in prefs if isinstance(item, dict) for eid in item.get("evidence_ids", [])]
    req_str = f"Preferred textures: {', '.join([k for k, v in pref_map.items() if v in {'ideal', 'acceptable'}])}" if pref_map else None

    top_layer = soil.layers[0] if soil and soil.layers else None
    texture_val = top_layer.texture_class if top_layer else None
    clean_tex = texture_val.lower().replace(" ", "_") if texture_val else ""

    if not texture_val:
        observed_q = Quantity(value=None, unit="unitless", missing_reason="NO_DATA_SOURCE")
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Topsoil texture class estimate unavailable from SSURGO.",
            ev_ids,
            "missing",
            support_class="F",
        )

    tex_code = TEXTURE_CLASS_CODES.get(clean_tex, 4.0)
    observed_q = Quantity(value=tex_code, unit="unitless", missing_reason=None)
    rating = pref_map.get(clean_tex)

    if rating == "ideal":
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Survey-derived topsoil texture estimate ({texture_val}) provides ideal physical structure and tilth.",
            ev_ids,
            support_class="F",
        )
    elif rating == "acceptable":
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "compatible",
            "none",
            80.0,
            f"Survey-derived topsoil texture estimate ({texture_val}) is compatible with standard agronomic practices.",
            ev_ids,
            support_class="F",
        )
    elif rating == "marginal":
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            55.0,
            f"Survey-derived topsoil texture estimate ({texture_val}) presents physical management challenges (e.g. low water holding or crusting).",
            ev_ids,
            support_class="F",
        )
    elif rating == "unsuitable":
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "critical_limitation",
            "critical",
            20.0,
            f"Survey-derived topsoil texture estimate ({texture_val}) is unsuited for this crop species.",
            ev_ids,
            support_class="F",
        )
    else:
        return _factor(
            "soil_texture",
            "Soil Texture (0–30 cm)",
            "soil",
            observed_q,
            req_str,
            "compatible",
            "none",
            75.0,
            f"Survey-derived topsoil texture estimate ({texture_val}) is compatible.",
            ev_ids,
            support_class="F",
        )


def evaluate_available_water(crop: CropProfile, soil: SoilProfile | None) -> SuitabilityFactorAssessment:
    root_eff = _get_crop_attr(crop.root_and_nutrients, "effective_water_extraction_depth_cm") or {}
    eff_min = root_eff.get("min_value")
    eff_max = root_eff.get("max_value")
    d_tol = _get_crop_attr(crop.water_demand_and_tolerance, "drought_tolerance", "rating") or "moderate"
    ev_ids = root_eff.get("evidence_ids") or []
    req_str = f"Effective water extraction depth: {eff_min}–{eff_max} cm; drought tolerance: {d_tol}" if eff_min else None

    observed_q = soil.aws_0_150 if soil and soil.aws_0_150 else Quantity(value=None, unit="cm", missing_reason="NO_DATA_SOURCE")

    if observed_q.value is None:
        return _factor(
            "available_water",
            "Available Water Storage (0–150 cm)",
            "soil",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Available water storage estimate unavailable from SSURGO.",
            ev_ids,
            "missing",
            support_class="F",
        )

    aws = float(observed_q.value)
    is_drought_tolerant = d_tol in {"tolerant", "very_tolerant", "high", "high_avoidance", "tolerant_escaping"}

    if aws >= 20.0:
        return _factor(
            "available_water",
            "Available Water Storage (0–150 cm)",
            "soil",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Survey-derived available water storage estimate ({aws:0.1f} cm) buffers against seasonal dry spells across active root zone ({eff_min}–{eff_max} cm).",
            ev_ids,
            support_class="F",
        )
    elif aws >= 15.0:
        return _factor(
            "available_water",
            "Available Water Storage (0–150 cm)",
            "soil",
            observed_q,
            req_str,
            "compatible",
            "none",
            80.0,
            f"Survey-derived available water storage estimate ({aws:0.1f} cm) provides adequate profile moisture buffer.",
            ev_ids,
            support_class="F",
        )
    elif aws >= 10.0:
        if is_drought_tolerant:
            return _factor(
                "available_water",
                "Available Water Storage (0–150 cm)",
                "soil",
                observed_q,
                req_str,
                "compatible",
                "none",
                70.0,
                f"Marginal water buffer estimate ({aws:0.1f} cm), but tolerated due to crop drought-tolerance mechanisms.",
                ev_ids,
                support_class="F",
            )
        else:
            return _factor(
                "available_water",
                "Available Water Storage (0–150 cm)",
                "soil",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                55.0,
                f"Marginal water storage estimate ({aws:0.1f} cm) elevates drought vulnerability for sensitive root systems.",
                ev_ids,
                support_class="F",
            )
    else:  # < 10.0 cm
        if is_drought_tolerant:
            return _factor(
                "available_water",
                "Available Water Storage (0–150 cm)",
                "soil",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                50.0,
                f"Low soil water capacity estimate ({aws:0.1f} cm); presents significant drought risk during grain fill.",
                ev_ids,
                support_class="F",
            )
        else:
            return _factor(
                "available_water",
                "Available Water Storage (0–150 cm)",
                "soil",
                observed_q,
                req_str,
                "critical_limitation",
                "critical",
                25.0,
                f"Severe drought vulnerability: survey-derived available water storage estimate ({aws:0.1f} cm) is insufficient for rainfed cultivation of this sensitive crop.",
                ev_ids,
                support_class="F",
            )


def evaluate_rooting(crop: CropProfile, soil: SoilProfile | None) -> SuitabilityFactorAssessment:
    root_eff = _get_crop_attr(crop.root_and_nutrients, "effective_water_extraction_depth_cm") or {}
    root_max = _get_crop_attr(crop.root_and_nutrients, "maximum_anatomical_root_depth_cm") or {}
    eff_min = root_eff.get("min_value")
    eff_max = root_eff.get("max_value")
    max_min = root_max.get("min_value")
    max_max = root_max.get("max_value")
    alleviation = _get_crop_attr(crop.root_and_nutrients, "compaction_alleviation_potential", "rating") or "moderate"
    ev_ids = (root_eff.get("evidence_ids") or []) + (root_max.get("evidence_ids") or [])

    req_str = f"Effective extraction: {eff_min}–{eff_max} cm; Max anatomical depth: {max_min}–{max_max} cm"

    # Soil surveyed profile depth context from layers (bottom of described horizons)
    depth_val = max(l.bottom_cm for l in soil.layers) if soil and soil.layers else None
    observed_q = Quantity(value=depth_val, unit="cm", missing_reason=None if depth_val else "NO_DATA_SOURCE")

    if not depth_val:
        return _factor(
            "rooting_depth",
            "Surveyed Profile Depth & Rooting Depth",
            "rooting",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Surveyed soil horizon depth data unavailable from SSURGO.",
            ev_ids,
            "missing",
            support_class="F",
        )

    if eff_min and depth_val < eff_min:
        return _factor(
            "rooting_depth",
            "Surveyed Profile Depth & Rooting Depth",
            "rooting",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            50.0,
            f"Surveyed soil profile depth ({depth_val:0.0f} cm) is less than the crop effective water extraction zone ({eff_min}–{eff_max} cm); anatomical maximum ({max_min}–{max_max} cm) cannot be accommodated within described horizons. Note: represents bottom of described SSURGO horizons, not confirmed depth to bedrock or root barrier.",
            ev_ids,
            support_class="F",
        )

    drain_val = (
        soil.drainage_class.value.lower().replace(" ", "_")
        if soil and soil.drainage_class and soil.drainage_class.value
        else ""
    )
    is_waterlogged = drain_val in {"poorly_drained", "very_poorly_drained"}

    if alleviation == "exceptional_bio_drilling":
        if is_waterlogged:
            return _factor(
                "rooting_depth",
                "Surveyed Profile Depth & Rooting Depth",
                "rooting",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                55.0,
                f"Bio-drilling taproot penetration is severely compromised by anaerobic / waterlogged soil conditions in {soil.drainage_class.value} soil.",
                ev_ids,
                support_class="F",
            )
        elif depth_val < 30.0:
            return _factor(
                "rooting_depth",
                "Surveyed Profile Depth & Rooting Depth",
                "rooting",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                50.0,
                f"Very shallow surveyed soil depth ({depth_val:0.0f} cm) physically prevents development of taproot bio-drilling architecture.",
                ev_ids,
                support_class="F",
            )
        else:
            return _factor(
                "rooting_depth",
                "Surveyed Profile Depth & Rooting Depth",
                "rooting",
                observed_q,
                req_str,
                "optimal",
                "favorable",
                95.0,
                f"Exceptional taproot bio-drilling capacity (penetrates dense subsoil plow pans to {max_max} cm; creates biopores for subsequent crops) within surveyed profile depth ({depth_val:0.0f} cm).",
                ev_ids,
                support_class="F",
            )
    elif eff_min and eff_min >= 90:
        return _factor(
            "rooting_depth",
            "Surveyed Profile Depth & Rooting Depth",
            "rooting",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            90.0,
            f"Deep effective water extraction zone ({eff_min}–{eff_max} cm) enables subsoil moisture foraging (max anatomical depth {max_min}–{max_max} cm) within surveyed profile depth ({depth_val:0.0f} cm). Note: describes described horizon boundary, not confirmed depth to bedrock.",
            ev_ids,
            support_class="F",
        )
    else:
        return _factor(
            "rooting_depth",
            "Surveyed Profile Depth & Rooting Depth",
            "rooting",
            observed_q,
            req_str,
            "compatible",
            "none",
            80.0,
            f"Effective extraction depth ({eff_min}–{eff_max} cm) is distinct from maximum anatomical depth ({max_min}–{max_max} cm), evaluated against surveyed horizon depth ({depth_val:0.0f} cm). Note: describes described horizon boundary, not confirmed depth to bedrock.",
            ev_ids,
            support_class="F",
        )


def evaluate_terrain_slope(crop: CropProfile, terrain: TerrainProfile | None) -> SuitabilityFactorAssessment:
    observed_q = terrain.slope_p90_pct if terrain and terrain.slope_p90_pct else Quantity(value=None, unit="percent", missing_reason="NO_DATA_SOURCE")
    is_cover = crop.is_cover_crop or crop.portfolio_role == "forage_perennial"
    req_str = "Slope <= 6.0% for row crops; cover crops/forages tolerate steep slopes"

    if observed_q.value is None:
        return _factor(
            "terrain_slope",
            "Terrain Slope (90th percentile)",
            "terrain",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "Terrain slope observation unavailable from SRTM.",
            [],
            "missing",
        )

    slope = float(observed_q.value)

    if slope <= 2.0:
        return _factor(
            "terrain_slope",
            "Terrain Slope (90th percentile)",
            "terrain",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            98.0,
            f"Flat to gently sloping terrain ({slope:0.1f}%) presents negligible sheet or rill erosion risk.",
            [],
        )
    elif slope <= 6.0:
        return _factor(
            "terrain_slope",
            "Terrain Slope (90th percentile)",
            "terrain",
            observed_q,
            req_str,
            "compatible",
            "none",
            85.0,
            f"Gentle to moderate slope ({slope:0.1f}%); compatible with standard contour or minimum-tillage management.",
            [],
        )
    elif slope <= 10.0:
        if is_cover:
            return _factor(
                "terrain_slope",
                "Terrain Slope (90th percentile)",
                "terrain",
                observed_q,
                req_str,
                "optimal",
                "favorable",
                90.0,
                f"Moderate slope ({slope:0.1f}%); highly suitable for soil-holding cover crops and perennial sod.",
                [],
            )
        else:
            return _factor(
                "terrain_slope",
                "Terrain Slope (90th percentile)",
                "terrain",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                55.0,
                f"Moderate slope ({slope:0.1f}%) increases erosion hazard for clean-tilled row crops; requires terrace or cover-crop protection.",
                [],
            )
    else:  # > 10.0%
        if is_cover:
            return _factor(
                "terrain_slope",
                "Terrain Slope (90th percentile)",
                "terrain",
                observed_q,
                req_str,
                "compatible",
                "none",
                75.0,
                f"Steep slope ({slope:0.1f}%); excellent candidate for continuous vegetative cover to prevent erosion.",
                [],
            )
        else:
            return _factor(
                "terrain_slope",
                "Terrain Slope (90th percentile)",
                "terrain",
                observed_q,
                req_str,
                "critical_limitation",
                "critical",
                20.0,
                f"Steep terrain ({slope:0.1f}%) exceeds conservation tillage thresholds for row crops (high erosion hazard).",
                [],
            )


def evaluate_crop_history(crop: CropProfile, history: CropHistory | None) -> SuitabilityFactorAssessment:
    observed_q = Quantity(value=None, unit="count", missing_reason="NO_DATA_SOURCE")
    req_str = f"Botanical family: {crop.botanical_family}; avoid immediate monoculture and repeated family cycles"

    if not history or not history.years:
        return _factor(
            "crop_history_context",
            "Historical Agronomic Context",
            "historical",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            "CDL crop history sequence unavailable for this field.",
            [],
            "missing",
            support_class="F",
        )

    # Sort history chronologically
    sorted_years = sorted(history.years, key=lambda y: y.year)
    last_year = sorted_years[-1]
    prev_code = last_year.majority.crop_code
    prev_name = last_year.majority.crop_name or "Unknown"

    if prev_code is None:
        return _factor(
            "crop_history_context",
            "Historical Agronomic Context",
            "historical",
            observed_q,
            req_str,
            "unknown",
            "unknown",
            None,
            f"Preceding crop observation for {last_year.year} has missing classification data.",
            [],
            "missing",
            support_class="F",
        )

    observed_q = Quantity(value=float(prev_code), unit="count", missing_reason=None)

    # Count consecutive years of the same crop code immediately preceding,
    # ensuring no gap in calendar years.
    consecutive_run = 0
    expected_year = last_year.year
    for y in reversed(sorted_years):
        if y.year != expected_year:
            # Missing calendar year breaks consecutive run
            break
        if y.majority.crop_code == crop.cdl_code and crop.cdl_code is not None:
            consecutive_run += 1
            expected_year -= 1
        else:
            break

    # 1. Monoculture / Autotoxicity check
    if crop.cdl_code is not None and prev_code == crop.cdl_code:
        if crop.crop_id == "CRP011":
            return _factor(
                "crop_history_context",
                "Historical Agronomic Context",
                "historical",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                50.0,
                f"Consecutive alfalfa cultivation ({consecutive_run} consecutive year(s)): re-seeding immediately into an existing stand is prohibited by medicarpin autotoxicity (EV0167); requires 1–2 year crop break.",
                ["EV0167"],
                support_class="F",
            )
        else:
            return _factor(
                "crop_history_context",
                "Historical Agronomic Context",
                "historical",
                observed_q,
                req_str,
                "moderate_limitation",
                "moderate",
                55.0,
                f"Consecutive monoculture warning: preceding crop was {prev_name} ({last_year.year}, {consecutive_run} consecutive year(s)). Continuous monoculture elevates disease, weed, and insect pressure.",
                [],
                support_class="F",
            )

    # 2. Rotational diversification check
    return _factor(
        "crop_history_context",
        "Historical Agronomic Context",
        "historical",
        observed_q,
        req_str,
        "optimal",
        "favorable",
        90.0,
        f"Preceding crop was {prev_name} ({last_year.year}); introduces rotational diversification from {crop.common_name}.",
        [],
        support_class="F",
    )


def evaluate_regional_suitability(crop: CropProfile, state_code: str = "KS") -> SuitabilityFactorAssessment:
    regions = crop.regional_suitability or []
    matching_reg = next(
        (r for r in regions if isinstance(r, dict) and state_code in (r.get("states_included") or [])),
        None,
    )
    observed_q = (
        Quantity(value=20.0 if state_code == "KS" else 1.0, unit="unitless", missing_reason=None)
        if state_code
        else Quantity(value=None, unit="unitless", missing_reason="NO_DATA_SOURCE")
    )
    req_str = "Documented regional adaptation and state inclusion"

    if not matching_reg:
        return _factor(
            "regional_adaptation",
            "Regional Climatic Adaptation",
            "regional",
            observed_q,
            req_str,
            "compatible",
            "none",
            75.0,
            f"State {state_code} is outside primary regional dossiers; verify local trial performance.",
            [],
            support_class="R",
        )

    tier = matching_reg.get("adaptation_tier")
    reg_name = matching_reg.get("region_name", "Regional Zone")
    limitations = matching_reg.get("regional_limitations") or "Standard regional management required."
    ev_ids = matching_reg.get("evidence_ids") or []

    if tier == "primary_core":
        return _factor(
            "regional_adaptation",
            "Regional Climatic Adaptation",
            "regional",
            observed_q,
            req_str,
            "optimal",
            "favorable",
            95.0,
            f"Primary core adaptation zone ({reg_name}). Regional suitability provides macro-climatic context; local soil and terrain govern field-level suitability.",
            ev_ids,
            support_class="R",
        )
    elif tier == "secondary_adapted":
        return _factor(
            "regional_adaptation",
            "Regional Climatic Adaptation",
            "regional",
            observed_q,
            req_str,
            "compatible",
            "none",
            85.0,
            f"Secondary adapted zone ({reg_name}): {limitations}",
            ev_ids,
            support_class="R",
        )
    elif tier == "marginal":
        return _factor(
            "regional_adaptation",
            "Regional Climatic Adaptation",
            "regional",
            observed_q,
            req_str,
            "moderate_limitation",
            "moderate",
            60.0,
            f"Marginally adapted in {reg_name}: {limitations}",
            ev_ids,
            support_class="R",
        )
    else:
        return _factor(
            "regional_adaptation",
            "Regional Climatic Adaptation",
            "regional",
            observed_q,
            req_str,
            "compatible",
            "none",
            75.0,
            f"Evaluated in {reg_name}. Regional suitability provides broad context.",
            ev_ids,
            support_class="R",
        )
