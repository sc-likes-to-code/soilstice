"""Phase 6: Crop Suitability Engine package."""

from .engine import CropSuitabilityEngine, ENGINE_VERSION
from .evaluators import (
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
from .explainer import build_explanation, build_limitations_list, extract_factor_lists
from .scorer import calculate_suitability_score, classify_crop

__all__ = [
    "CropSuitabilityEngine",
    "ENGINE_VERSION",
    "evaluate_thermal_gdd",
    "evaluate_heat_stress",
    "evaluate_water_precipitation",
    "evaluate_soil_ph",
    "evaluate_soil_drainage",
    "evaluate_soil_texture",
    "evaluate_available_water",
    "evaluate_rooting",
    "evaluate_terrain_slope",
    "evaluate_crop_history",
    "evaluate_regional_suitability",
    "classify_crop",
    "calculate_suitability_score",
    "extract_factor_lists",
    "build_explanation",
    "build_limitations_list",
]
