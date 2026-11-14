# SOILSTICE — Backend Developer Integration Guide

**Target Audience:** Backend Software Engineers, Data Engineers, API Developers, and ML/Algorithm Engineers  
**Dataset Version:** `1.4.1-REMEDIATED`  
**Authoritative Source:** `data/crop_knowledge_base.json`  
**Schema Specification:** `data/schema.json` (Draft-07)  

---

## 1. Introduction & Architecture Overview

The **SOILSTICE Crop Knowledge Base** provides a structured, evidence-backed agronomic dataset designed to power:
- Farm-scale multi-year crop rotation planning.
- Regional and soil-specific crop suitability scoring.
- Environmental constraint validation (frost, heat, drought, salinity, and waterlogging).
- Preceding/following crop compatibility evaluations.
- Nitrogen dynamics and cover crop management recommendations.

This guide is written specifically for backend developers who did not participate in the agronomic research phases. It defines how to ingest, parse, validate, and navigate the dataset safely without misinterpreting scientific boundaries.

---

## 2. File Organization & Authority

| File Path | Format | Role & Purpose | Authoritative? |
|---|---|---|---|
| `data/crop_knowledge_base.json` | JSON (UTF-8) | Complete canonical dataset: 14 crops, 11 domains, 212 evidence records. | **PRIMARY AUTHORITATIVE SOURCE** |
| `data/schema.json` | JSON Schema (Draft-07) | Strict schema definitions and validation rules for all entities. | **AUTHORITATIVE VALIDATOR** |
| `data/crop_attributes.csv` | CSV | Flattened projection of core crop attributes (1 header + 14 crop rows). | Secondary projection (bulk ingest/BI) |
| `data/crop_rotation_compatibility.csv` | CSV | Directed pairwise rotation transitions (1 header + 196 rows). | Synchronized rotation projection |
| `data/crop_evidence.csv` | CSV | Tabular projection of evidence registry (1 header + 212 records). | Synchronized evidence projection |
| `documentation/SOURCE_REGISTER.md` | Markdown | Bibliographic source index, author affiliations, and citation registry. | Reference & provenance audit |
| `documentation/DATA_DICTIONARY.md` | Markdown | Comprehensive field definitions, measurement semantics, and units. | Reference specification |

---

## 3. Canonical Crop Registry & Identification

The knowledge base enforces a strict, immutable 14-crop canonical registry. Crops are identified by primary alphanumeric keys matching the regular expression `^CRP[0-9]{3}$`:

```json
[
  {"crop_id": "CRP001", "common_name": "Corn (Maize)",   "scientific_name": "Zea mays L."},
  {"crop_id": "CRP002", "common_name": "Soybean",        "scientific_name": "Glycine max (L.) Merr."},
  {"crop_id": "CRP003", "common_name": "Winter Wheat",   "scientific_name": "Triticum aestivum L."},
  {"crop_id": "CRP004", "common_name": "Spring Wheat",   "scientific_name": "Triticum aestivum L."},
  {"crop_id": "CRP005", "common_name": "Grain Sorghum",  "scientific_name": "Sorghum bicolor (L.) Moench"},
  {"crop_id": "CRP006", "common_name": "Cotton",         "scientific_name": "Gossypium hirsutum L."},
  {"crop_id": "CRP007", "common_name": "Rice",           "scientific_name": "Oryza sativa L."},
  {"crop_id": "CRP008", "common_name": "Barley",         "scientific_name": "Hordeum vulgare L."},
  {"crop_id": "CRP009", "common_name": "Cereal Rye",     "scientific_name": "Secale cereale L."},
  {"crop_id": "CRP010", "common_name": "Oats",           "scientific_name": "Avena sativa L."},
  {"crop_id": "CRP011", "common_name": "Alfalfa",        "scientific_name": "Medicago sativa L."},
  {"crop_id": "CRP012", "common_name": "Hairy Vetch",    "scientific_name": "Vicia villosa Roth"},
  {"crop_id": "CRP013", "common_name": "Crimson Clover", "scientific_name": "Trifolium incarnatum L."},
  {"crop_id": "CRP014", "common_name": "Oilseed Radish", "scientific_name": "Raphanus sativus L."}
]
```

### Crop Portfolio Roles
Never assume all crops are harvested cash crops. The dataset categorizes crops into distinct functional roles:
- **Cash Grain / Fiber Crops (`CRP001`–`CRP008`):** Grown for commercial grain or lint harvest. Aboveground biomass is exported from the field.
- **Forage Perennials (`CRP011` — Alfalfa):** Multi-year perennial legume harvested repeatedly for high-protein hay or baleage.
- **Cool-Season Annual Cover Crops (`CRP009`, `CRP010`, `CRP012`, `CRP013`, `CRP014`):** Managed primarily for soil health, erosion control, weed suppression, nutrient scavenging, or green manure. Commercial harvest is either secondary (forage/grain oats or rye) or unfeasible (vetch, radish).

---

## 4. Uniform Schema Domains & Nested Attribute Structures

Each crop entity in `crops[]` contains **exactly 11 uniform top-level domain keys**:

```json
{
  "crop_id": "CRP014",
  "crop_identity": { ... },
  "growing_duration": { ... },
  "temperature_requirements": { ... },
  "rainfall_requirements": { ... },
  "water_demand_and_tolerance": { ... },
  "soil_preferences": { ... },
  "root_and_nutrients": { ... },
  "nitrogen_and_biomass": { ... },
  "rotation_compatibility": { ... },
  "regional_suitability": { ... }
}
```

### Standard Attribute Data Models

Attributes are modeled as structured objects rather than raw primitives:

#### 1. Quantitative Attribute (`QuantitativeAttribute`)
Used for physical, biological, or chemical measurements:
```json
{
  "value": null,
  "min_value": 150.0,
  "max_value": 300.0,
  "unit": "mm",
  "measurement_type": "reported_range",
  "growth_stage": null,
  "region_scope": null,
  "confidence": "high",
  "evidence_ids": ["EV0203"],
  "limitations": null
}
```
- **Rules for interpretation:**
  - If `value` is present, it is a single point estimate (e.g. base temperature $3.5^\circ\text{C}$).
  - If `value` is `null` and `min_value` / `max_value` are present, the attribute represents a biological range (e.g., ETc 150–300 mm).
  - `measurement_type` specifies provenance: `measured`, `reported_range`, `derived`, `expert_consensus`, or `qualitative`.
  - Always preserve the `unit` field during API serialization and unit conversion.

#### 2. Qualitative Attribute (`QualitativeAttribute`)
Used for categorical agronomic ratings:
```json
{
  "rating": "exceptional_bio_drilling",
  "description": "Punches through dense subsoil plow pans (>2.0 MPa); leaves open 2-5 cm macropores upon winter decay.",
  "measurement_type": "qualitative",
  "growth_stage": null,
  "region_scope": null,
  "confidence": "high",
  "evidence_ids": ["EV0202"],
  "limitations": "Measured in Maryland coastal plain silt loam and sandy loam soils with traffic pans (Chen & Weil 2010); bio-drilling efficacy is conditional on early autumn establishment (>=6-8 weeks prior to freeze) and fails in waterlogged, smeared, or severely rutted soils."
}
```

---

## 5. Handling Null Values (Critical Developer Rule)

> [!CAUTION]
> **NEVER COERCE `null` TO `0.0`.**  
> In this dataset, `null` indicates that an attribute is **unmeasured, scientifically unverified, or deliberately decoupled** to prevent inaccurate environmental accounting. Converting `null` to `0.0` introduces severe scientific errors into backend calculation engines.

### Key Examples of Legitimate Nulls:
1. **Green Manure Net Soil Nitrogen Balance (`net_soil_nitrogen_balance_kg_ha`):**
   - In `CRP012` (Hairy Vetch), `CRP013` (Crimson Clover), and `CRP014` (Oilseed Radish), `value`, `min_value`, and `max_value` are `null`.
   - **Why:** While unharvested biomass contains fixed or scavenged nitrogen, whole-system net soil organic nitrogen accumulation is unmeasured. Rapid mineralization exposes mineral N to leaching and volatilization.
   - **Backend Action:** Do not compute a net N balance. Query `total_gross_n_fixed_kg_ha` for gross biological fixation and `successor_nitrogen_credit` for empirical synthetic fertilizer replacement credits.
2. **Irrigation Requirements on Rainfed Cover Crops:**
   - For winter cover crops grown during humid winter months, `net_irrigation_requirement_mm` is `0.0` or `null`.
   - Distinguish `0.0 mm` (no irrigation applied) from `null` (not evaluated for irrigated commercial production).

---

## 6. Evidence Resolution & Traceability

Every quantitative and qualitative attribute contains an `evidence_ids` array:
```json
"evidence_ids": ["EV0206", "EV0207"]
```

To resolve evidence in backend services:
1. Index `evidence_registry[]` by `evidence_id` upon application startup.
2. An evidence record contains full bibliographic metadata:
   ```json
   {
     "evidence_id": "EV0206",
     "crop_ids": ["CRP014"],
     "related_domain": "nitrogen_and_biomass",
     "attribute_or_claim": "Oilseed Radish Residual Nitrate Scavenging Capacity & Profile Recovery",
     "recorded_value_or_summary": "Exceptional autumn nitrate scavenger, capturing 100-220 kg N/ha (100-200 lb N/ac) from soil profile; reduces nitrate leaching to groundwater by 60-90%.",
     "source_organization": "American Society of Agronomy / Soil Science Society of America",
     "source_title": "Brassica Cover Crops for Nitrogen Scavenging in the Mid-Atlantic Coastal Plain",
     "author_or_institution": "Dean, J.E. and Weil, R.R.",
     "publication_year": 2009,
     "publication_date": "2009-01-01",
     "access_date": "2026-11-14",
     "source_url_or_doi": "https://doi.org/10.2134/jeq2008.0107",
     "citation_location": "J. Environ. Qual. 38(1):253-261",
     "exact_supporting_context": "Evaluated N uptake by forage radish, showing it accumulated 110 to 220 kg N/ha in aboveground and belowground biomass...",
     "geographic_scope": "Mid-Atlantic Coastal Plain",
     "variety_scope": "Forage radish",
     "source_quality": "high",
     "data_availability": "Open Access",
     "conditions_and_assumptions": "Planted in late August following heavily fertilized sweet corn and field corn.",
     "limitations": "Total N scavenged depends strictly on available soil residual mineral N."
   }
   ```
3. Surface `evidence_ids`, `source_title`, and `limitations` in API payloads so frontend applications can render provenance badges and tooltip warnings.

---

## 7. Navigating the Directed Rotation Compatibility Matrix

The rotation matrix consists of **exactly 196 directed transitions ($14 \times 14$)**, stored in `data/crop_rotation_compatibility.csv` and partially reflected in each crop's `rotation_compatibility` domain.

### Directional Non-Reciprocity
> [!IMPORTANT]
> **ROTATION TRANSITIONS ARE DIRECTED AND ASYMMETRIC.**  
> Transition $A \rightarrow B$ DOES NOT equal transition $B \rightarrow A$.

- **Example 1: Radish & Corn**
  - `CRP014 -> CRP001` (Radish $\rightarrow$ Corn): **`highly_compatible`**. Radish bio-drills subsoil plow pans, creating vertical biopores that enhance corn rooting and drought tolerance (+5–10% yield bump on compacted soils).
  - `CRP001 -> CRP014` (Corn $\rightarrow$ Radish): **`compatible`**. October corn harvest leaves a very narrow, late planting window in the northern Midwest, reducing radish taproot fleshing before freezing.
- **Example 2: Cover Crop Mixtures vs. Sequential Monocultures**
  - `CRP013 -> CRP014` (Crimson Clover $\rightarrow$ Oilseed Radish): **`caution_conditional`**.
  - `CRP014 -> CRP013` (Oilseed Radish $\rightarrow$ Crimson Clover): **`caution_conditional`**.
  - **Why:** Both are cool-season annual covers. Direct back-to-back sequential monoculture leaves severe summer or winter fallow gaps.
  - **Mixture Exception:** Sowing them **simultaneously in polyculture mixtures** is highly synergistic. Look for the `[MIXTURE NOTE]` prefix in `synergy_mechanisms`.

### Compatibility Rating Vocabulary
Backend services must handle all six standardized rating states:
1. `highly_compatible`: Strong biological and agronomic synergy (yield enhancement, pest break, nitrogen contribution).
2. `compatible`: Standard agronomic rotation with manageable disease/weed dynamics.
3. `caution_conditional`: Feasible rotation requiring specific management (e.g. pH control, multi-year interval, starter fertilizer, or cultivar selection).
4. `incompatible`: Severe agronomic penalty (disease buildup, extreme autotoxicity, complete season conflict).
5. `prohibited`: Enforces a **statutory legal restriction or pesticide-label plant-back quarantine**. (Not used for biological disease risks alone).
6. `unknown`: Unstudied or agronomically non-viable combination lacking primary empirical field trials.

---

## 8. Python Ingestion & Querying Example

```python
import json
import os
from typing import Dict, Any, Optional, List

class SoilSticeKnowledgeBase:
    def __init__(self, data_dir: str):
        self.kb_path = os.path.join(data_dir, "crop_knowledge_base.json")
        with open(self.kb_path, "r", encoding="utf-8") as f:
            self.data: Dict[str, Any] = json.load(f)
            
        self.crops: Dict[str, Any] = {c["crop_id"]: c for c in self.data["crops"]}
        self.evidence: Dict[str, Any] = {e["evidence_id"]: e for e in self.data["evidence_registry"]}
        
    def get_crop(self, crop_id: str) -> Optional[Dict[str, Any]]:
        return self.crops.get(crop_id)
        
    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        return self.evidence.get(evidence_id)
        
    def get_nitrogen_credits(self, crop_id: str) -> Dict[str, Any]:
        crop = self.get_crop(crop_id)
        if not crop:
            raise KeyError(f"Crop {crop_id} not found")
            
        nb = crop["nitrogen_and_biomass"]
        bnf = nb["biological_nitrogen_fixation"]["total_gross_n_fixed_kg_ha"]
        credit = nb["successor_nitrogen_credit"]["fertilizer_equivalent_n_credit_lb_ac"]
        net_soil = nb["residue_and_harvest_nitrogen_dynamics"]["net_soil_nitrogen_balance_kg_ha"]
        
        return {
            "crop_id": crop_id,
            "has_bnf": nb["biological_nitrogen_fixation"]["has_symbiotic_fixation_capacity"]["value"],
            "gross_bnf_min_kg_ha": bnf.get("min_value"),
            "gross_bnf_max_kg_ha": bnf.get("max_value"),
            "fertilizer_credit_min_lb_ac": credit.get("min_value") or credit.get("value"),
            "fertilizer_credit_max_lb_ac": credit.get("max_value"),
            "net_soil_nitrogen_balance": net_soil.get("value"),  # Legitimate None for cover crops
            "balance_limitations": net_soil.get("limitations")
        }

# Usage:
# kb = SoilSticeKnowledgeBase("data/processed/crop_knowledge_base/backend_handoff/data")
# info = kb.get_nitrogen_credits("CRP014")
# print(info)
```

---

## 9. Units & Engineering Conversions

Always respect the canonical units defined in `data/schema.json` and `DATA_DICTIONARY.md`:

| Dimension | Canonical Metric Unit | Standard U.S. Customary Equivalent | Conversion Factor |
|---|---|---|---|
| Temperature | Celsius ($^\circ\text{C}$) | Fahrenheit ($^\circ\text{F}$) | $^\circ\text{F} = (^\circ\text{C} \times 9/5) + 32$ |
| Water Depth / ETc | Millimeters ($\text{mm}$) | Inches ($\text{in}$) | $1\text{ in} = 25.4\text{ mm}$ |
| Root Depth | Centimeters ($\text{cm}$) | Feet ($\text{ft}$) | $1\text{ ft} = 30.48\text{ cm}$ |
| Fertilizer / Nutrient Mass | $\text{kg/ha}$ | $\text{lb/ac}$ | $1\text{ lb/ac} = 1.12085\text{ kg/ha}$ |
| Electrical Conductivity | $\text{dS/m}$ | $\text{mmhos/cm}$ | $1\text{ dS/m} = 1\text{ mmhos/cm}$ |
| Soil Pressure / Resistance | $\text{MPa}$ | $\text{psi}$ | $1\text{ MPa} \approx 145.038\text{ psi}$ |

---

## 10. Summary Integration Rules for Backend Developers

1. **Verify Draft-07 schema compliance** on every dataset update.
2. **Never convert `null` to `0.0`.**
3. **Always index rotations as directed pairs `(preceding, following)`.**
4. **Never treat gross biological fixation as net soil organic nitrogen.**
5. **Never treat nitrate scavenging as newly fixed biological nitrogen.**
6. **Pass through limitation strings** to the API client to prevent algorithmic overconfidence.
7. **Distinguish cover crop mixtures from sequential rotations** using the `[MIXTURE NOTE]` tag.
