"""Phase 6: Suitability Explainer.

Generates evidence-backed agronomic explanations and extracts
limiting, favorable, and unknown factors.
"""

from __future__ import annotations

from app.contracts import (
    CropProfile,
    SuitabilityClass,
    SuitabilityFactorAssessment,
)

CROP_AGRONOMIC_DESCRIPTIONS: dict[str, str] = {
    "CRP001": (
        "Corn (Zea mays L.) is a warm-season annual C4 cereal grain requiring 1,167–1,556 GDD (Tbase 10°C, Tcap 30°C) "
        "and 500–800 mm water. Highly productive on fertile, well-drained loams with pH 6.0–6.8. Serves as a primary "
        "cash grain in rotation with soybeans or small grains; heavy user of nitrogen and soil moisture, with high "
        "vulnerability to mid-season heat and drought stress during silking."
    ),
    "CRP002": (
        "Soybean (Glycine max (L.) Merr.) is a warm-season annual legume requiring 1,000–1,450 GDD (Tbase 10°C) "
        "and 450–700 mm water. Fixes atmospheric nitrogen via Bradyrhizobium symbiosis (70–140 kg N/ha) on soils with "
        "pH 6.0–6.8. Critical cash oilseed and rotational break crop following corn or winter wheat, breaking cereal "
        "pathogen cycles; sensitive to iron-deficiency chlorosis in high-pH calcareous soils and waterlogging."
    ),
    "CRP003": (
        "Winter Wheat (Triticum aestivum L.) is a cool-season annual cereal requiring vernalization (4–8 weeks at 0–7°C), "
        "1,800–2,400 GDD (Tbase 0°C), and 350–550 mm water. Excellent winter ground cover and erosion barrier on soils "
        "with pH 6.0–7.0. Foundational high-plains cash cereal and dual-purpose graze-grain crop; breaks summer weed "
        "cycles, possessing moderate drought and cold tolerance with vulnerability to wet foot and fungal root rots."
    ),
    "CRP004": (
        "Spring Wheat (Triticum aestivum L.) is a cool-season non-vernalizing annual cereal requiring 1,150–1,400 GDD "
        "(Tbase 0°C) and 250–500 mm water on well-drained soils with pH 6.0–7.0. Fast-maturing spring cash grain and "
        "flexible replant option following winter-kill; lower total moisture demand than summer grains, but highly "
        "sensitive to high ambient temperatures (>32°C) during flowering and grain fill."
    ),
    "CRP005": (
        "Grain Sorghum (Sorghum bicolor (L.) Moench) is a warm-season C4 grain requiring 944–1,333 GDD (Tbase 10°C) "
        "and 350–500 mm water, thriving on diverse soils with pH 5.5–7.8. Exemplary dryland cash crop with exceptional "
        "drought and heat tolerance through osmotic adjustment and waxy leaf epicuticle; ideal low-moisture break "
        "crop following wheat, but sensitive to cold soils (<15°C) at planting and early autumn frost."
    ),
    "CRP006": (
        "Cotton (Gossypium hirsutum L.) is a warm-season perennial grown as an annual fiber crop requiring 1,167–1,444 GDD "
        "(Tbase 15.6°C, Tcap 32°C) and 500–750 mm water. Requires deep, well-drained loam to sandy loam with pH 6.0–7.0 "
        "and >180 frost-free days. Deep taproot aids subsoil moisture capture and breaks grass disease cycles; highly "
        "sensitive to chilling injury, seedling damping-off, and waterlogged anaerobic root zones."
    ),
    "CRP007": (
        "Rice (Oryza sativa L.) is a semi-aquatic warm-season annual cereal requiring 1,167–1,556 GDD (Tbase 10°C) "
        "and 900–1,200 mm seasonal water. Specifically adapted to poorly drained lowlands and claypan soils with "
        "pH 5.5–6.8 under continuous flooding or furrow irrigation. Unique wetland cash crop breaking terrestrial disease "
        "cycles; agronomically unsuitable on well-drained, permeable upland fields without impoundment infrastructure."
    ),
    "CRP008": (
        "Barley (Hordeum vulgare L.) is a cool-season annual small grain requiring 1,100–1,600 GDD (Tbase 0°C) and "
        "300–450 mm water on well-drained loams with pH 6.0–7.5. Short growing cycle allows early harvest and double-cropping; "
        "exhibits the highest salinity and drought tolerance among small grains, but poor tolerance to waterlogged "
        "soils, acidic conditions (pH < 5.8), and high humidity during heading."
    ),
    "CRP009": (
        "Cereal Rye (Secale cereale L.) is an exceptionally cold-hardy cool-season annual grass germinating near 1°C, "
        "requiring 900–1,400 GDD and 300–450 mm water. Thrives across marginal, acidic (pH 4.5–7.5), sandy soils. "
        "Premier cover crop and late-season forage; provides massive biomass, allelopathic weed suppression, and "
        "aggressive nitrate scavenging before summer legumes, but termination must be managed to preserve corn soil moisture."
    ),
    "CRP010": (
        "Oats (Avena sativa L.) is a cool-season annual cereal requiring 1,300–1,700 GDD (Tbase 4.4°C) and 350–500 mm "
        "water on soils with pH 6.0–7.0. Non-winterhardy cover and companion nurse crop that reliably winter-kills in "
        "colder latitudes; rapid autumn biomass establishment and effective surface nutrient scavenging, though sensitive "
        "to hot, dry weather during grain fill."
    ),
    "CRP011": (
        "Alfalfa (Medicago sativa L.) is a perennial deep-rooted legume forage requiring 2,200–3,500 GDD across multiple "
        "cuts and 600–1,000 mm water on deep, well-drained soils with pH 6.5–7.5. Exceptional biological nitrogen "
        "fixation (150–250 kg N/ha/yr) and subsoil biopores via 2–4 m taproots; medicarpin autotoxicity prevents immediate "
        "re-seeding into existing stands (mandating a 1–2 year rotational break)."
    ),
    "CRP012": (
        "Hairy Vetch (Vicia villosa Roth) is a winter-hardy annual legume cover crop requiring 1,100–1,600 GDD and "
        "350–600 mm water on moderately fertile soils with pH 5.5–7.5. Fixes substantial atmospheric nitrogen (90–180 kg N/ha) "
        "released quickly to subsequent corn or sorghum crops; outstanding winter-survival among annual legumes, but "
        "vining habit requires proper spring termination to prevent hard-seed volunteer contamination."
    ),
    "CRP013": (
        "Crimson Clover (Trifolium incarnatum L.) is a cool-season annual legume cover crop requiring 1,000–1,500 GDD "
        "and 500–800 mm water on well-drained sandy loams and loams with pH 6.0–7.0. Rapid spring biomass development, "
        "moderate nitrogen fixation (70–140 kg N/ha), and prolific early pollinator forage; easily terminated mechanically "
        "or chemically before summer planting, but vulnerable to severe freeze without snow cover."
    ),
    "CRP014": (
        "Oilseed Radish (Raphanus sativus L. var. oleiferus) is a specialty brassica cover crop requiring 600–1,000 GDD "
        "and 300–500 mm water on medium soils with pH 6.0–7.5. Aggressive tuberous taproot performs biological subsoiling "
        "to alleviate plow pan compaction and scavenges up to 150–220 kg N/ha of residual profile nitrate; reliably "
        "winter-kills at temperatures below -6°C to -9°C, facilitating spring no-till seeding without herbicide burndown."
    ),
}


def extract_factor_lists(
    factors: list[SuitabilityFactorAssessment],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Extract limiting, favorable, unknown factor summaries and collected evidence IDs."""
    limiting: list[str] = []
    favorable: list[str] = []
    unknown: list[str] = []
    ev_ids_set: set[str] = set()

    for f in factors:
        for eid in f.evidence_ids:
            if eid and eid.startswith("EV"):
                ev_ids_set.add(eid)

        if f.is_limiting:
            severity_tag = "[CRITICAL] " if f.severity == "critical" else "[MODERATE] "
            limiting.append(f"{severity_tag}{f.factor_name}: {f.interpretation}")
        elif f.is_favorable:
            favorable.append(f"{f.factor_name}: {f.interpretation}")
        elif f.data_status in {"missing", "not_integrated"} or f.compatibility == "unknown":
            unknown.append(f"{f.factor_name}: Data unavailable or requirement not documented.")

    return limiting, favorable, unknown, sorted(list(ev_ids_set))


def build_explanation(
    crop: CropProfile,
    suitability_class: SuitabilityClass,
    limiting: list[str],
    favorable: list[str],
    unknown: list[str],
    class_reason: str,
) -> str:
    """Compose an evidence-backed narrative explanation of the suitability assessment."""
    agronomic_desc = CROP_AGRONOMIC_DESCRIPTIONS.get(crop.crop_id)
    class_label = suitability_class.replace('_', ' ').title()
    header = f"{crop.common_name} ({crop.scientific_name}) is classified as '{class_label}'. {class_reason}"
    if agronomic_desc:
        header = f"{header}\n\n{agronomic_desc}"
    lines = [header]

    if limiting:
        lines.append(f"Identified limitations ({len(limiting)}):")
        for lim in limiting:
            lines.append(f"• {lim}")

    if favorable:
        lines.append(f"Favorable conditions ({len(favorable)}):")
        for fav in favorable:
            lines.append(f"• {fav}")

    if unknown:
        lines.append(f"Uncertainty / Missing data ({len(unknown)}):")
        for unk in unknown:
            lines.append(f"• {unk}")

    return "\n\n".join(lines)


def build_limitations_list(
    factors: list[SuitabilityFactorAssessment],
    crop: CropProfile,
) -> list[str]:
    """Collect scientific limitations and guardrails for this crop evaluation."""
    limits = [
        "Decision-support advisory only: does not constitute a guaranteed crop emergence, yield, or commercial return.",
        "Regional climate observations (NASA POWER, ~50 km spatial grid) do not substitute for in-situ field weather monitoring.",
        "SSURGO soil indicators represent survey-derived polygon-weighted mapunit approximations rather than direct laboratory soil core tests or in-situ field sensor measurements.",
        "SSURGO profile depth reflects the lower boundary of described soil horizons (typically 100–150 cm), not confirmed depth to restrictive bedrock layers or in-situ root penetration resistance.",
    ]

    # Crop-specific limitations from Phase 5 KB
    if crop.crop_id == "CRP014":
        limits.append("Oilseed radish scavenging captures up to 100–220 kg N/ha of residual soil nitrate; this is recycled profile N, NOT newly fixed biological N.")
        limits.append("Radish winter-kill efficacy requires sustained temperatures <= -6°C to -9°C for >= 4–6 continuous hours.")
    elif crop.crop_id in {"CRP012", "CRP013"}:
        limits.append("Legume gross biological nitrogen fixation is not net soil organic nitrogen addition due to mineralization and potential leaching losses upon termination.")
    elif crop.crop_id == "CRP011":
        limits.append("Alfalfa stand re-establishment into preceding alfalfa is inhibited by medicarpin autotoxicity; requires a 1–2 year rotational break.")
    elif crop.crop_id == "CRP001":
        limits.append("Corn yield benefits following taproot cover crops are conditional on compacted subsoils and summer water stress; premiums are negligible in uncompacted soils.")

    return limits
