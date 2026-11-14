# SOILSTICE — Phase 5 Crop Knowledge Base Architecture
**Document Version:** 1.0.0  
**Phase:** 5 (Production-Ready Crop Knowledge Layer & Backend Integration)  
**Status:** Completed & Verified  
**Date:** 2026-11-14  

---

## 1. Executive Summary & Purpose

Phase 5 establishes a centralized, evidence-backed, schema-validated **Crop Knowledge Base (KB)** within the SOILSTICE backend platform. This knowledge layer ingests the agronomic knowledge handoff (`data/backend_handoff/v1.4.1-REMEDIATED`), encapsulating 14 canonical agricultural crops, 11 uniform scientific domains per crop, 212 distinct evidence records, and a directed 14 × 14 crop rotation compatibility matrix (196 pairwise transitions).

The architecture bridges USDA NASS Cropland Data Layer (CDL) integer identifiers with canonical crop profiles, integrates authoritative base/cutoff thermal parameters into the Phase 4 Environmental Analytical Engine, enforces strict scientific null semantics (particularly regarding soil nitrogen accounting), and exposes typed REST API endpoints for downstream utilization by Phase 6 (Crop Suitability Engine) and Phase 7 (Crop Rotation Recommendation Engine).

---

## 2. High-Level Architectural Diagram

```
+---------------------------------------------------------------------------------------------------------+
|                                    SOILSTICE AGRO-ECOLOGICAL PLATFORM                                   |
+---------------------------------------------------------------------------------------------------------+
                                                     |
                                   +-----------------+-----------------+
                                   |                                   |
                                   v                                   v
             +-----------------------------------+   +-----------------------------------+
             |    NASA Earth Science & USDA      |   |  Teammate Crop Knowledge Package  |
             |  (POWER, SMAP, HLS, CDL, SSURGO)  |   |    (v1.4.1-REMEDIATED Master KB)  |
             +-----------------------------------+   +-----------------------------------+
                                   |                                   |
                                   v                                   v
             +-----------------------------------+   +-----------------------------------+
             |   Phase 4: Environmental Engine   |   |   Phase 5: Crop Knowledge Base    |
             | - Daily Modified GDD              |<--| - 14 Canonical Profiles (11 dom.) |
             | - Climatic Water Balance (P-ET0)  |   | - 212 Evidence Registry Items     |
             | - 5-Component Soil Resilience     |   | - 196 Directed Rotation Matrix    |
             | - Shannon Crop Diversity          |   | - Authoritative Thermal Params    |
             +-----------------------------------+   +-----------------------------------+
                                   \                                   /
                                    \                                 /
                                     v                               v
                        +---------------------------------------------------------+
                        |                 Unified FastAPI Backend                 |
                        | - Schema-conforming REST Endpoints (/api/v1/...)        |
                        | - Strict Pydantic Models & OpenAPI Generation           |
                        | - Dual Indexing: CDL Integer (11) & Canonical ID (14)   |
                        +---------------------------------------------------------+
                                                     |
                                                     v
                        +---------------------------------------------------------+
                        |             TypeScript / Next.js Frontend               |
                        | - Strict Contract Parity (contract/compat.ts)           |
                        | - HttpRotationService & MockRotationService             |
                        +---------------------------------------------------------+
                                                     |
                                                     v
                                    +---------------------------------+
                                    | Future Phase 6 & Phase 7 Target |
                                    | - Phase 6: Suitability Engine   |
                                    | - Phase 7: Rotation Optimizer   |
                                    +---------------------------------+
```

---

## 3. Knowledge Package Composition & Data Ingestion

The canonical knowledge package is located at `data/backend_handoff/data/` and loaded upon application startup:

1. **Master Knowledge Base:** `crop_knowledge_base.json`  
   - Format: JSON Schema Draft-07 compliant document.
   - Version: `1.4.1-REMEDIATED`.
   - Metadata: Schema version, release timestamp, total entity counts, geographic/institutional provenance.
2. **Directed Rotation Compatibility Matrix:** `crop_rotation_compatibility.csv`  
   - 196 rows representing directed pairs $(P_i, F_j)$ for $i, j \in \{1, \dots, 14\}$.
   - Enforces non-reciprocal rotation dynamics (e.g. Radish $\rightarrow$ Corn vs Corn $\rightarrow$ Radish).
3. **Draft-07 Validation:**  
   - Implemented via `validate_draft07_schema()` in `app.rotation.kb` using standard library Python (zero third-party validation dependencies).
   - Validates root structure, metadata attributes, evidence records, and crop definitions without schema drift.

---

## 4. Dual-Index Resolution & CDL Mapping Strategy

A fundamental architectural requirement is bridging historical remote sensing land-cover classifications (CDL) with physiological crop models:

### 4.1. Mapping Roster

| Canonical ID | Common Name | CDL Code | Botanical Family | Crop Group | Portfolio Role | Primary Lifecycle |
|---|---|---|---|---|---|---|
| `CRP001` | Corn (Maize) | **1** | Poaceae | Cereal / Grain | Primary Commercial | Summer Annual |
| `CRP002` | Soybean | **5** | Fabaceae | Legume / Oilseed | Primary Commercial | Summer Annual |
| `CRP003` | Winter Wheat | **24** | Poaceae | Small Grain | Primary Commercial | Winter Annual |
| `CRP004` | Spring Wheat | **23** | Poaceae | Small Grain | Primary Commercial | Spring Annual |
| `CRP005` | Grain Sorghum | **4** | Poaceae | Cereal / Grain | Primary Commercial | Summer Annual |
| `CRP006` | Cotton | **2** | Malvaceae | Fiber / Oilseed | Primary Commercial | Summer Annual |
| `CRP007` | Rice | **3** | Poaceae | Cereal / Grain | Primary Commercial | Summer Annual |
| `CRP008` | Barley | **21** | Poaceae | Small Grain | Primary Commercial | Winter/Spring Annual |
| `CRP009` | Cereal Rye | **27** | Poaceae | Small Grain | Rotation Cover | Winter Annual |
| `CRP010` | Oats | **28** | Poaceae | Small Grain | Small Grain / Cover | Spring/Winter Annual |
| `CRP011` | Alfalfa | **36** | Fabaceae | Perennial Legume | Perennial Forage | Perennial |
| `CRP012` | Hairy Vetch | **None** | Fabaceae | Legume Cover | Rotation Cover | Winter Annual |
| `CRP013` | Crimson Clover | **None** | Fabaceae | Legume Cover | Rotation Cover | Winter/Spring Annual |
| `CRP014` | Oilseed Radish | **None** | Brassicaceae | Brassica Cover | Rotation Cover | Cool-season Annual |

### 4.2. Dual Indexing Implementation

In `CropKnowledgeBase`:
- `crops_by_id: dict[str, CropProfile]`: Keyed by canonical ID (`CRP001` to `CRP014`).
- `crops_by_cdl: dict[int, CropProfile]`: Keyed by USDA CDL integer code (11 commercial/forage crops).
- Cover crops `CRP012`, `CRP013`, and `CRP014` have `cdl_code = None`. They are indexed canonically and never assigned synthetic CDL numbers.
- CDL Double-crop candidates (`26: Dbl Crop WinWht/Soybeans`, `236: Dbl Crop WinWht/Sorghum`) and `61: Fallow/Idle Cropland` remain accessible in `CropOption` rosters for historical rotation reconstruction.

---

## 5. Uniform Knowledge Domain Model

Every canonical crop profile contains 11 uniform, scientifically defined domains:

```
CropProfile
├── crop_identity
├── growing_duration
├── temperature_requirements
├── rainfall_requirements
├── water_demand_and_tolerance
├── soil_preferences
├── root_and_nutrients
├── nitrogen_and_biomass
├── rotation_compatibility
├── regional_suitability
└── evidence_ids (aggregated list of cross-cutting EV citations)
```

### Key Domain Principles:
1. **Quantitative vs Qualitative Attributes:**  
   Quantitative values expose standard structures: `{ "value": float | null, "min_value": float | null, "max_value": float | null, "unit": string, "source_id": string, "limitations": string | null }`.
2. **Root Depth Disaggregation:**  
   `effective_water_extraction_depth_cm` (depth of primary transpiration uptake) is strictly distinguished from `maximum_anatomical_root_depth_cm` (deepest observed taproot penetration). In all 14 crops, effective depth is strictly less than or equal to anatomical depth (e.g., Alfalfa effective 120–180 cm vs anatomical 300–600 cm).
3. **Thermal GDD Linkage:**  
   `temperature_requirements.growing_degree_days` provides standard base temperature $T_{\text{base}}$ and upper ceiling $T_{\text{cutoff}}$.

---

## 6. Scientific Limitations & Nitrogen Accounting Safeguards

Per `data/backend_handoff/SCIENTIFIC_LIMITATIONS.md`, the implementation enforces strict agronomic invariants:

### 6.1. Net Soil Nitrogen Balance vs. Gross Fixation
- Legume cover crops (`CRP012: Hairy Vetch`, `CRP013: Crimson Clover`) fix substantial atmospheric $N_2$ via symbiotic *Rhizobium* ($110$–$280\text{ kg N/ha}$).
- However, their `net_soil_nitrogen_balance_kg_ha.value` is strictly set to `None` (`null`) in the database.
- **Scientific Rationale:** As green manures, their net contribution to soil organic N depends entirely on termination method, termination timing, biomass incorporation vs surface mulching, soil microbial activity, and temperature-dependent mineralization kinetics. Coercing this to a fixed number or to gross fixation would overestimate plant-available nitrogen.

### 6.2. Non-Legume Scavenging vs. Fixation
- `CRP014: Oilseed Radish` is a non-legume Brassica.
- Symbiotic fixation capacity is strictly `False`, and gross $N_2$ fixed is `0.0 kg N/ha`.
- Successor fertilizer equivalent credit is `0.0 lb N/ac`.
- The knowledge base explicitly documents that radish scavenges $100$–$220\text{ kg N/ha}$ of residual nitrate from deep root zones ($>1.5\text{ m}$), preventing leaching and releasing it rapidly upon spring winterkill, but does not add *new* exogenous nitrogen to the biosphere.

### 6.3. Strict Null Preservation
- Missing or variable parameters (such as salinity tolerance for non-tested cultivars or specific regional yield potentials) remain `None` (`null`).
- In no case are missing values coerced to `0.0` or default estimates.

---

## 7. Directed Crop Rotation Matrix Architecture

The rotation engine utilizes a directed graph structure $G = (V, E)$ where $|V| = 14$ and $|E| = 196$:

1. **Directional Asymmetry:**  
   Transitions are directed: $(P \rightarrow F) \neq (F \rightarrow P)$.
   - *Example:* `CRP014 (Oilseed Radish)` $\rightarrow$ `CRP001 (Corn)` has compatibility rating `highly_compatible` (bio-drilling relieves compaction, rapid mineralization provides early-season N).
   - In reverse, `CRP001 (Corn)` $\rightarrow$ `CRP014 (Oilseed Radish)` has compatibility rating `compatible` (heavy corn stover and allelopathic residue require residue management and timely seeding).
2. **Monoculture Penalties:**  
   All 14 diagonal elements $(P_i \rightarrow P_i)$ carry `is_monoculture = True` and document specific agronomic penalties (e.g., Continuous Corn `CRP001 -> CRP001` incurs 5%–15% yield penalty supported by Morrow Plots research `EV0012`).
3. **Mixture vs. Sequential Distinctions:**  
   Transitions between cover crops (e.g., `CRP013 (Crimson Clover)` $\rightarrow$ `CRP014 (Oilseed Radish)`) document whether the cited compatibility applies to simultaneous polyculture mixtures or sequential rotations.

---

## 8. Thermal GDD Parameters & Phase 4 Climate Integration

Authoritative base and ceiling temperatures from the knowledge base are centralized in `app.rotation.kb` and consumed directly by `app.processing.climate`:

```python
CANONICAL_GDD_THRESHOLDS = {
    "CRP001": (10.0, 30.0),  # Corn
    "CRP002": (10.0, 30.0),  # Soybean
    "CRP003": (0.0, 26.0),   # Winter Wheat
    "CRP004": (0.0, 26.0),   # Spring Wheat
    "CRP005": (10.0, 35.0),  # Grain Sorghum
    "CRP006": (15.6, 37.8),  # Cotton
    "CRP007": (10.0, 35.0),  # Rice
    "CRP008": (0.0, 26.0),   # Barley
    "CRP009": (0.0, 25.0),   # Cereal Rye
    "CRP010": (4.4, 25.0),   # Oats
    "CRP011": (5.0, 30.0),   # Alfalfa
    "CRP012": (4.0, 25.0),   # Hairy Vetch
    "CRP013": (5.0, 25.0),   # Crimson Clover
    "CRP014": (4.0, 25.0),   # Oilseed Radish
}
```

The function `get_crop_gdd_thresholds(identifier)` dynamically resolves thresholds given either a canonical crop ID (`CRP001`), a CDL code (`1`), or crop name string, maintaining backwards compatibility with Phase 4 Modified GDD calculations.

---

## 9. API Surface & Data Contracts

Seven dedicated, read-only REST API endpoints expose the knowledge layer under `/api/v1/`:

| Method | Endpoint | Operation ID | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/canonical-crops` | `listCanonicalCrops` | Retrieve summaries of all 14 canonical crops; supports filtering by `role` and `family`. |
| `GET` | `/api/v1/crops/{crop_id}` | `getCropProfile` | Retrieve the complete 11-domain crop profile by canonical ID (`CRP001`) or CDL code (`1`). |
| `GET` | `/api/v1/crops/{crop_id}/attributes` | `getCropAttributes` | Retrieve filtered subsets of attributes by domain query (`?domain=nitrogen_and_biomass`). |
| `GET` | `/api/v1/rotations` | `getRotationCompatibility` | Query directed pairwise transition compatibility between preceding and following crops. |
| `GET` | `/api/v1/rotations/matrix` | `listRotationMatrix` | Retrieve the complete 196-transition directed compatibility matrix. |
| `GET` | `/api/v1/evidence/{evidence_id}` | `getCropEvidence` | Retrieve complete bibliographic provenance and supporting context for any evidence ID (`EV0001`–`EV0212`). |
| `GET` | `/api/v1/kb/metadata` | `getKbMetadata` | Retrieve knowledge base version, author institutional credentials, and entity counts. |

All responses conform to the standard `ApiResponse[T]` envelope with full OpenAPI documentation and strict TypeScript parity verified in `contract/compat.ts`.

---

## 10. Downstream Integration Strategy (Phase 6 & 7)

```
+-------------------------------------------------------------+
|                 CropKnowledgeBase Interface                 |
+-------------------------------------------------------------+
              |                                 |
              v                                 v
+-----------------------------+   +-----------------------------+
|    Phase 6 Suitability      |   |      Phase 7 Rotation       |
|    - Soil pH & Texture      |   |    - Compatibility Graph    |
|    - Water Deficit (P-ET0)  |   |    - Monoculture Penalties  |
|    - GDD Accumulation       |   |    - N Credit Carryover     |
|    - Drainage & Salinity    |   |    - Disease Break Scoring  |
+-----------------------------+   +-----------------------------+
```

1. **Phase 6 (Crop Suitability Engine):**  
   Will invoke `get_crop()` to evaluate environmental match factors between SSURGO soil characteristics, NASA POWER climate parameters, and the crop's `soil_preferences`, `temperature_requirements`, and `water_demand_and_tolerance`.
2. **Phase 7 (Crop Rotation Recommendation Engine):**  
   Will traverse `rotations[(P, F)]` to formulate multi-year rotation schedules, maximizing agronomic synergies (disease break, nitrogen credit) while penalizing consecutive monoculture sequences.
