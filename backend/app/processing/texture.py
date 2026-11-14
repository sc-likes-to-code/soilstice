"""USDA soil texture class from sand/silt/clay percentages (USDA texture triangle).

Class boundaries follow the USDA-NRCS Soil Survey Manual (Handbook 18) texture triangle definitions, the
standard published rule set (also implemented in NRCS tools). Inputs are renormalised to sum to 100.
"""

from __future__ import annotations


def usda_texture_class(sand: float | None, silt: float | None, clay: float | None) -> str | None:
    if sand is None or silt is None or clay is None:
        return None
    total = sand + silt + clay
    if total <= 0:
        return None
    sand, silt, clay = (100 * sand / total, 100 * silt / total, 100 * clay / total)

    if silt + 1.5 * clay < 15:
        return "Sand"
    if silt + 1.5 * clay >= 15 and silt + 2 * clay < 30:
        return "Loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "Sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "Loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "Silt loam"
    if silt >= 80 and clay < 12:
        return "Silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "Sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "Clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "Silty clay loam"
    if clay >= 35 and sand > 45:
        return "Sandy clay"
    if clay >= 40 and silt >= 40:
        return "Silty clay"
    if clay >= 40 and sand <= 45 and silt < 40:
        return "Clay"
    return None
