# SOILSTICE — Proposed Backend API Data Contract

**Specification Type:** Read-Only RESTful Agronomic Data Contract  
**Document Version:** `1.0.0` (Targeting Canonical Dataset `1.4.1-REMEDIATED`)  
**Status:** **PROPOSED ARCHITECTURAL SPECIFICATION**  
**Data Source:** `data/crop_knowledge_base.json`  

---

## 1. Specification Scope & Philosophy

This document defines the proposed backend API contract for exposing the **SOILSTICE Crop Knowledge Base** to internal microservices, suitability scoring pipelines, rotation recommendation engines, and frontend clients.

### Architectural Principles:
1. **Strictly Read-Only:** All operations are idempotent `GET` endpoints.
2. **Deterministic Provenance:** Every returned agronomic claim carries its associated `evidence_ids` and `limitations`.
3. **Explicit Null Representation:** Attributes with unavailable, unmeasured, or decoupled data return explicit JSON `null`, preserving scientific integrity.
4. **No Server-Side Side-Effects:** The API serves immutable, frozen agricultural intelligence.

---

## 2. Global Standards & Types

### Identifier Formats
- **Crop IDs:** `^CRP[0-9]{3}$` (e.g. `CRP001`, `CRP014`).
- **Evidence IDs:** `^EV[0-9]{4}$` (e.g. `EV0001`, `EV0212`).

### Standard Response Envelope
All endpoints return responses wrapped in a standard JSON metadata envelope:
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "timestamp": "2026-11-14T15:20:00Z",
  "status": "success",
  "data": { ... }
}
```

### Standard Error Envelope
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "timestamp": "2026-11-14T15:20:00Z",
  "status": "error",
  "error": {
    "code": "CROP_NOT_FOUND",
    "message": "Crop identifier 'CRP999' is not registered in the canonical 14-crop portfolio.",
    "details": {
      "valid_range": "CRP001 to CRP014"
    }
  }
}
```

---

## 3. Proposed Read-Only Endpoints

### 1. List Canonical Crops
- **Endpoint:** `GET /api/crops`
- **Description:** Returns the complete 14-crop canonical registry with basic identities and functional roles.
- **Query Parameters:**
  - `role` *(optional, string)*: Filter by `cash_crop`, `cover_crop`, or `forage`.
  - `family` *(optional, string)*: Filter by botanical family (e.g. `Poaceae`, `Fabaceae`, `Brassicaceae`).

#### Sample Response:
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "status": "success",
  "data": {
    "total_crops": 14,
    "crops": [
      {
        "crop_id": "CRP001",
        "common_name": "Corn (Maize)",
        "scientific_name": "Zea mays L.",
        "botanical_family": "Poaceae",
        "lifecycle_class": "warm_season_annual",
        "portfolio_role": "primary_cash_grain",
        "is_cover_crop": false
      },
      {
        "crop_id": "CRP014",
        "common_name": "Oilseed Radish",
        "scientific_name": "Raphanus sativus L.",
        "botanical_family": "Brassicaceae",
        "lifecycle_class": "cool_season_annual",
        "portfolio_role": "specialty_cover_crop",
        "is_cover_crop": true
      }
    ]
  }
}
```

---

### 2. Retrieve Complete Crop Profile
- **Endpoint:** `GET /api/crops/{crop_id}`
- **Description:** Returns the full, unflattened 11-domain agronomic profile for a specific crop.
- **Path Parameters:**
  - `crop_id` *(required, string)*: Canonical ID (e.g., `CRP014`).

#### Sample Response:
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "status": "success",
  "data": {
    "crop_id": "CRP014",
    "crop_identity": {
      "common_name": "Oilseed Radish",
      "scientific_name": "Raphanus sativus L.",
      "taxonomic_authority": "L.",
      "botanical_family": "Brassicaceae",
      "usda_plants_symbol": "RASA2",
      "lifecycle_class": "cool_season_annual",
      "is_cover_crop": true
    },
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
}
```

---

### 3. Query Specific Crop Domain or Attribute
- **Endpoint:** `GET /api/crops/{crop_id}/attributes`
- **Description:** Retrieves filtered subsets of a crop's attributes.
- **Query Parameters:**
  - `domain` *(optional, string)*: e.g., `nitrogen_and_biomass`, `temperature_requirements`, `root_and_nutrients`.
  - `attribute` *(optional, string)*: Specific attribute path (e.g. `nitrogen_and_biomass.successor_nitrogen_credit`).

#### Sample Response (`domain=nitrogen_and_biomass` for `CRP014`):
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "status": "success",
  "data": {
    "crop_id": "CRP014",
    "domain": "nitrogen_and_biomass",
    "attributes": {
      "biological_nitrogen_fixation": {
        "has_symbiotic_fixation_capacity": {
          "value": false,
          "measurement_type": "qualitative",
          "confidence": "high",
          "evidence_ids": ["EV0199"],
          "limitations": null
        },
        "total_gross_n_fixed_kg_ha": {
          "value": 0.0,
          "min_value": 0.0,
          "max_value": 0.0,
          "unit": "kg_n_per_ha",
          "measurement_type": "measured",
          "confidence": "high",
          "evidence_ids": ["EV0199"]
        }
      },
      "residue_and_harvest_nitrogen_dynamics": {
        "harvested_biomass_nitrogen_export_kg_ha": {
          "value": 0.0,
          "unit": "kg_n_per_ha",
          "evidence_ids": ["EV0199"]
        },
        "net_soil_nitrogen_balance_kg_ha": {
          "value": null,
          "min_value": null,
          "max_value": null,
          "unit": "kg_n_per_ha",
          "measurement_type": "derived",
          "confidence": "high",
          "evidence_ids": ["EV0199", "EV0206"],
          "limitations": "Calculation boundary: Set to null because 0.0 kg N/ha derived solely from zero biological fixation minus zero harvest export does not represent a measured whole-system net soil nitrogen balance..."
        }
      },
      "successor_nitrogen_credit": {
        "fertilizer_equivalent_n_credit_lb_ac": {
          "value": 0.0,
          "min_value": 0.0,
          "max_value": 0.0,
          "unit": "lb_n_per_acre",
          "evidence_ids": ["EV0199", "EV0206"],
          "limitations": "Oilseed radish does not provide an additive biological nitrogen fertilizer credit (0.0 lb N/ac biological addition). However, recycling and rapid mineralization of 100-200 lb N/ac of scavenged profile nitrogen provides an effective rotational N benefit of 20-40 lb N/ac on subsequent corn if captured by crop roots before leaching."
        }
      }
    }
  }
}
```

---

### 4. Directed Rotation Compatibility Lookup
- **Endpoint:** `GET /api/rotations`
- **Description:** Evaluates the directed transition from a preceding crop to a following crop.
- **Query Parameters:**
  - `previous_crop` *(required, string)*: Preceding crop ID (e.g. `CRP014`).
  - `next_crop` *(required, string)*: Succeeding crop ID (e.g. `CRP001`).

#### Sample Request:
`GET /api/rotations?previous_crop=CRP014&next_crop=CRP001`

#### Sample Response:
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "status": "success",
  "data": {
    "preceding_crop": {
      "crop_id": "CRP014",
      "common_name": "Oilseed Radish"
    },
    "following_crop": {
      "crop_id": "CRP001",
      "common_name": "Corn (Maize)"
    },
    "transition": {
      "compatibility_rating": "highly_compatible",
      "is_monoculture": false,
      "synergy_mechanisms": "Corn roots utilize open radish biopores to bypass dense plow pans to access subsoil water; field studies in Maryland and Michigan observed a 5-10% corn yield increase on compacted no-till soils (Chen & Weil 2011; MSU E-3165).",
      "disease_break_potential": "Non-host broadleaf cover crop provides complete biological break for Corn Rootworm (Diabrotica spp.).",
      "shared_pest_disease_risks": "None.",
      "herbicide_carryover_risks": "Atrazine applied to previous corn can injure radish seedlings if plant-back interval (<10-12 months) is not respected.",
      "evidence_ids": ["EV0202", "EV0206", "EV0211"],
      "limitations": "Corn yield benefit is conditional on soil compaction and late-summer water stress; no yield increase is observed on uncompacted soils or in well-watered seasons. On coarse sands, early nitrate release can leach before late-spring corn uptake unless companion rye is used."
    }
  }
}
```

---

### 5. Evidence Reference Lookup
- **Endpoint:** `GET /api/evidence/{evidence_id}`
- **Description:** Retrieves primary citation, DOI, supporting context, and empirical conditions for any evidence record.
- **Path Parameters:**
  - `evidence_id` *(required, string)*: Range `EV0001` to `EV0212`.

#### Sample Response:
```json
{
  "api_version": "1.0.0",
  "dataset_version": "1.4.1-REMEDIATED",
  "status": "success",
  "data": {
    "evidence_id": "EV0202",
    "crop_ids": ["CRP014"],
    "related_domain": "root_and_nutrients",
    "attribute_or_claim": "Oilseed Radish Subsoil Compaction Alleviation & Bio-Drilling Macropore Formation",
    "source_organization": "Elsevier / University of Maryland",
    "source_title": "Penetration of Compact Subsoils by Diverse Cover Crop Roots",
    "author_or_institution": "Chen, G. and Weil, R.R.",
    "publication_year": 2010,
    "source_url_or_doi": "https://doi.org/10.1016/j.still.2010.03.003",
    "citation_location": "Soil & Tillage Research 108(1-2):31-40",
    "exact_supporting_context": "Evaluated root growth of forage radish, rye, and rapeseed in compacted soils, demonstrating radish roots had significantly higher penetration density in compacted subsoils (>2.0 MPa) than rye or rapeseed, creating biopores used by subsequent corn roots.",
    "geographic_scope": "Maryland / Mid-Atlantic",
    "source_quality": "high",
    "data_availability": "Open Access",
    "conditions_and_assumptions": "Field and rhizotron experiments across silt loam and sandy loam soils with induced plow pans.",
    "limitations": "Compaction alleviation fails if soil is severely smeared, waterlogged, or if planting is delayed (<40 days of growth before freeze)."
  }
}
```

---

## 4. HTTP Status Codes & Error Handling Matrix

| HTTP Status | Error Code | Trigger Condition | Recommended Client Action |
|---|---|---|---|
| `200 OK` | — | Successful data retrieval. | Render / process payload. |
| `400 Bad Request` | `INVALID_PARAMETER` | Malformed crop ID or missing query param (e.g. `previous_crop` without `next_crop`). | Validate parameter schema. |
| `404 Not Found` | `CROP_NOT_FOUND` | Requested crop ID is outside `CRP001`–`CRP014`. | Check canonical crop list. |
| `404 Not Found` | `EVIDENCE_NOT_FOUND` | Requested evidence ID is outside `EV0001`–`EV0212`. | Check evidence registry. |
| `422 Unprocessable` | `INVALID_TRANSITION` | Preceding or following crop not recognized. | Correct rotation query. |
| `500 Server Error` | `DATASET_LOAD_ERROR` | Knowledge base JSON corrupt or schema invalid. | Verify file hashes via `validate_handoff.py`. |
