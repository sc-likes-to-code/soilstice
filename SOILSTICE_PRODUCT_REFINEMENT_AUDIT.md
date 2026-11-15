# SOILSTICE — Product Refinement, Data Coverage & Crop Ranking Audit

**Date:** November 15, 2026  
**Status:** Complete & Verified  
**Branch:** `main`  
**Application Architecture:** FastAPI (Python 3.13) backend + Next.js 16 (Turbopack, TypeScript) frontend  

---

## 1. Executive Summary

This audit report documents the comprehensive execution of the **SOILSTICE Dashboard Cleanup, Data Coverage Refinement & Crop Ranking** mission. All 10 tasks requested have been implemented, tested across both Live API and Mock Data execution modes, and validated with complete test suites, type checking, linting, and production builds.

Key architectural and scientific outcomes:
1. **Data Coverage Purified:** Removed all unavailable (`not_applicable`, `not_integrated`) datasets and globally eliminated all NDVI/NDMI (`nasa_hls_vi`, `nasa_hls`) entries from the Data Coverage / Essential Datasets interface across every field, farm, season, and mode. Completeness calculations are now strictly grounded in the 5 operational P0 datasets (`meteomatics`, `nasa_power_daily_ag`, `usda_nrcs_ssurgo_sda`, `usda_nass_cdl`, `nasa_srtm_gl1`).
2. **Actual ET & Root-Zone Percentile Cleanly Removed:** Deprecated `et_actual_season` and `sm_rootzone_percentile` across indicators, metric cards, summaries, and charts without destabilizing ET0, precipitation, water balance, or the 4-depth Meteomatics soil moisture profile (-5, -15, -50, -150 cm).
3. **Vegetation Section Deprecated:** Eliminated the standalone Vegetation tab, cards, and charts from Environmental Intelligence while retaining climate, soil, and moisture analytics.
4. **Resilience Engine Reweighted & Recalibrated:** Removed `vegetation_stability` from the resilience composite. The 4 remaining components (`soil_water_buffer`, `terrain_erosion_risk`, `climate_exposure`, `rotation_diversity`) now each carry an equal base weight of 0.25 ($25\%$), with proportional dynamic normalization ($1/k$) when optional components are withheld. The minimum valid evidence quorum is updated to $\ge 3$ of 4 components ($75\%$).
5. **Authoritative Agronomic Descriptions:** Established definitive, scientifically grounded agronomic descriptions for all 14 canonical crops across both backend explainer and frontend presentation layers.
6. **Deterministic Crop Ranking:** Fully integrated Phase 6 suitability score ranking with multi-tier deterministic tie-breaking (`score` DESC $\to$ `confidence` DESC $\to$ `limiting_factors_count` ASC $\to$ non-repeat before repeat $\to$ `crop_name` ASC). Top ranks are visually distinguished with Gold (Rank #1 Top Match), Silver (Rank #2), Bronze (Rank #3), and Neutral badges, with disqualified/unsuitable crops isolated in a dedicated section.

---

## 2. Detailed Task Breakdown & Implementation Matrix

| Task | Scope | Files Modified | Verification Status |
| :--- | :--- | :--- | :--- |
| **Task 1: Data Coverage — Remove Unavailable Entries** | Filter out `not_applicable` and `not_integrated` entries across backend and frontend. Rebase P0 completeness. | `backend/app/services/fields.py`, `src/components/shared/data-display.tsx`, `src/services/mock/generators.ts` | Tested & Verified |
| **Task 2: Data Coverage — Globally Remove NDVI/NDMI** | Globally purge `nasa_hls_vi` / `nasa_hls` and NDVI/NDMI badges/rows across all fields, farms, seasons, and modes. | `backend/app/services/fields.py`, `src/components/shared/data-display.tsx`, `src/services/mock/generators.ts` | Tested & Verified |
| **Task 3: Remove Actual ET** | Remove `et_actual_season` from climate indicators and summaries; preserve ET0, precip, and water balance. | `backend/app/processing/climate.py`, `src/services/mock/generators.ts` | Tested & Verified |
| **Task 4: Remove Root-Zone Soil Moisture Percentile** | Remove `sm_rootzone_percentile` from indicators, cards, and summaries; retain 4 depths, composite, and dry days. | `backend/app/processing/climate.py`, `src/services/mock/generators.ts`, `src/services/mock/services.ts` | Tested & Verified |
| **Task 5: Remove Standalone Vegetation Section** | Remove Vegetation tab, views, and cards from Environmental Intelligence views. | `src/components/views/environment-view.tsx`, `src/components/views/field-overview-view.tsx` | Tested & Verified |
| **Task 6: Resilience — Remove Vegetation & Reweight** | Remove `vegetation_stability`. Base weight 0.25 each across 4 components. Quorum $\ge 3$ of 4. | `backend/app/analytics/resilience.py`, `backend/app/contracts/entities.py`, `src/types/contracts.ts`, `src/components/views/resilience-view.tsx`, `src/components/views/field-overview-view.tsx` | Tested & Verified |
| **Task 7: Rotation Lab — Fix All Crop Descriptions** | Provide scientifically grounded descriptions for all 14 canonical crops. | `backend/app/suitability/explainer.py`, `src/components/views/suitability-section.tsx`, `src/services/mock/generators.ts` | Tested & Verified |
| **Task 8: Implement Crop Ranking & Tie-Breaking** | Deterministic sorting by score, confidence, limitations, repeat status, and name. Visual rank badges and isolation of disqualified crops. | `backend/app/services/rotation.py`, `src/components/views/suitability-section.tsx`, `src/components/views/rotation-view.tsx`, `backend/tests/test_crop_ranking.py`, `src/lib/lib.test.ts` | Tested & Verified |
| **Task 9: Application-Wide Consistency Audit** | Check routes, views, contracts, and export integrity. Update OpenAPI definitions. | `contract/openapi.gen.ts`, `backend/openapi.json`, `backend/tests/test_frontend_contract.py` | Tested & Verified |
| **Task 10: Comprehensive Test & Build Verification** | Run backend pytest suite, vitest suite, TypeScript typecheck, ESLint, Next.js production build. | Complete repository | All Passed (100%) |

---

## 3. Data Coverage Catalog: Before vs. After

### Before
```json
[
  { "id": "meteomatics", "priority": "P0", "status": "available" },
  { "id": "nasa_power_daily_ag", "priority": "P0", "status": "available" },
  { "id": "usda_nrcs_ssurgo_sda", "priority": "P0", "status": "available" },
  { "id": "usda_nass_cdl", "priority": "P0", "status": "available" },
  { "id": "nasa_srtm_gl1", "priority": "P0", "status": "available" },
  { "id": "usda_nass_csb", "priority": "P0", "status": "not_applicable" },
  { "id": "nasa_hls_vi", "priority": "P0", "status": "missing" },
  { "id": "nasa_smap_spl4smgp", "priority": "P0", "status": "not_integrated" }
]
```
- **Denominator:** 8 datasets.
- **Completeness:** $5 / 8 = 0.625$ ($62.5\%$), triggering false "Missing" badges for operational fields.

### After
```json
[
  { "id": "meteomatics", "label": "Meteomatics Weather & Soil Moisture", "priority": "P0", "status": "available" },
  { "id": "nasa_power_daily_ag", "label": "NASA POWER Daily Agrometeorology", "priority": "P0", "status": "available" },
  { "id": "usda_nrcs_ssurgo_sda", "label": "USDA NRCS SSURGO Soil Survey", "priority": "P0", "status": "available" },
  { "id": "usda_nass_cdl", "label": "USDA NASS Cropland Data Layer", "priority": "P0", "status": "available" },
  { "id": "nasa_srtm_gl1", "label": "NASA SRTM 30m Global Elevation", "priority": "P0", "status": "available" }
]
```
- **Operational P0 Denominator:** Exactly 5 integrated datasets.
- **Unavailable / Not Integrated:** Completely omitted from standard displays.
- **NDVI / NDMI:** Globally purged from coverage tables and summaries across all fields.
- **Completeness Calculation:**
  $$\text{Completeness} = \frac{|\{d \in \text{P0} \mid \text{status}(d) \in \{\text{available}, \text{partial}\}\}|}{|\text{P0}|} = \frac{5}{5} = 1.0 \; (100\%)$$

---

## 4. Resilience Engine Mathematical Adjustments

### Component Structure & Weighting
The resilience composite formerly evaluated 5 components with base weights of 0.20 each ($20\%$). Following the deprecation of HLS satellite vegetation time series, `vegetation_stability` has been eliminated from the composite calculation.

The 4 remaining components and their calibrated base weights:
1. **`soil_water_buffer`** ($w_1 = 0.25$): Available water capacity (AWC), root-zone depth, drainage class, and clay content.
2. **`terrain_erosion_risk`** ($w_2 = 0.25$): Mean slope, 90th percentile slope ($P_{90}$), and RUSLE K-factor erodibility.
3. **`climate_exposure`** ($w_3 = 0.25$): 10-year drought frequency, heat stress days ($T_{\max} \ge 35^\circ\text{C}$), precipitation anomaly coefficient of variation, and freeze-thaw cycles.
4. **`rotation_diversity`** ($w_4 = 0.25$): 5-year Shannon crop diversity index, legume frequency, consecutive monoculture penalty, and cover crop presence.

### Quorum and Normalization Logic
Let $C_i$ represent the evaluated score for component $i \in \{1, 2, 3, 4\}$, and $M_i \in \{0, 1\}$ indicate whether component $i$ has sufficient evidence.

$$\text{Valid Components Count } k = \sum_{i=1}^{4} M_i$$

- **Evidence Quorum Threshold:** $k \ge 3$ of 4 ($75\%$ minimum component coverage).
- If $k < 3$: Status is set to `"insufficient_data"`, composite score is `null`, and band is `"withheld"`.
- If $k \ge 3$: Composite score is computed using proportional re-normalization:
  $$\text{Composite Score} = \sum_{i=1}^{4} \left( \frac{M_i}{k} \times C_i \right) = \frac{1}{k} \sum_{i \in \text{Available}} C_i$$

### Resilience Rating Bands
Scores are mapped deterministically into four calibrated agronomic resilience bands:
- **High Resilience:** $\text{Score} \ge 75$
- **Moderate Resilience:** $55 \le \text{Score} < 75$
- **Low Resilience:** $35 \le \text{Score} < 55$
- **Vulnerable:** $\text{Score} < 35$

---

## 5. Canonical Crops Agronomic Descriptions (14 Crops)

All 14 canonical crops supported by the Phase 6 Suitability Engine have been enriched with authoritative, scientifically rigorous descriptions:

1. **Corn (Zea mays):** High-yielding warm-season C4 grain demanding deep fertile soils (pH 5.8–7.0), significant nitrogen, and 500–800 mm water. Highly sensitive to moisture and heat stress during pollination and silking.
2. **Soybeans (Glycine max):** Nitrogen-fixing warm-season legume ideal for rotation with grain cereals. Thrives in well-drained loams (pH 6.0–6.8); sensitive to severe drought during pod development and pod-fill.
3. **Winter Wheat (Triticum aestivum):** Cool-season small grain seeded in autumn requiring winter vernalization. Highly cold-hardy; well-adapted to moderate-rainfall plains with good drainage (pH 6.0–7.5).
4. **Spring Wheat (Triticum aestivum):** Fast-maturing cool-season cereal planted in early spring. Avoids harsh winterkill but vulnerable to late-season high heat and moisture stress during grain fill.
5. **Grain Sorghum / Milo (Sorghum bicolor):** Exceptional drought- and heat-resilient C4 cereal with an extensive fibrous root system. Highly suitable for semi-arid dryland rotations where corn faces high stress.
6. **Sunflowers (Helianthus annuus):** Deep-taproot oilseed capable of scavenging moisture and subsoil nutrients down to 2 m depth. Moderately drought-tolerant; susceptible to sclerotinia and lodging in high winds.
7. **Canola / Rapeseed (Brassica napus):** Cool-season brassica oilseed providing an effective disease break in cereal rotations. Requires well-drained fertile soil; highly vulnerable to heat stress during flowering and pod development.
8. **Alfalfa (Medicago sativa):** Deep-rooted perennial legume offering high-protein forage and substantial biological nitrogen fixation. Improves soil structure; demands high water availability and well-drained, non-acidic soils (pH 6.5–7.5).
9. **Barley (Hordeum vulgare):** Early-maturing, cool-season small grain with superior drought and salinity tolerance relative to other cereals. Performs reliably in light to medium well-drained soils.
10. **Oats (Avena sativa):** Cool-season grain and cover crop well-adapted to cooler, moist climates and acidic or marginal soils (pH 5.0–7.0). Excellent nutrient scavenger with low pest and disease pressure.
11. **Rye (Secale cereale):** Hardiest cool-season cereal and winter cover crop with extreme cold tolerance and low nutrient requirements. Suppresses weeds through allelopathy and protects against erosion.
12. **Cotton (Gossypium hirsutum):** Warm-season taproot fiber crop requiring high heat units (GDD > 2200), a long frost-free growing period (>180 days), and warm loamy soils (pH 5.8–8.0). Highly vulnerable to early cold stress.
13. **Peanuts (Arachis hypogaea):** Warm-season annual legume that flowers aboveground and matures seed pods underground. Demands loose, friable sandy loams (pH 5.8–6.5) with low clay content for successful pegging and digging.
14. **Dry Edible Beans (Phaseolus vulgaris):** Fast-maturing pulse legume requiring moderate temperatures and well-drained loams. Highly sensitive to waterlogging, saline soils, and extreme heat during flowering.

---

## 6. Crop Ranking & Multi-Tier Tie-Breaking Methodology

In both Next Season recommendation candidates and the complete Suitability section:
1. **Primary Key:** Suitability Score descending ($\text{Score} \in [0, 100]$).
2. **Secondary Key:** Confidence Rating descending (`"high"` $>$ `"medium"` $>$ `"low"`).
3. **Tertiary Key:** Limiting Factors count ascending (fewer Liebig limiting factors ranks higher).
4. **Quaternary Key:** Rotational diversity preference (non-consecutive repeat crops preferred before monoculture repeats).
5. **Quinary Key:** Deterministic alphabetical tie-breaker by `crop_name` ascending.

### Visual Distinctions & Disqualification Handling
- **Rank #1:** High-prominence Gold/Amber badge (`Rank #1 Top Match`), with special highlight styling in candidate cards.
- **Rank #2:** Silver badge (`Rank #2`).
- **Rank #3:** Bronze badge (`Rank #3`).
- **Rank #4+:** Slate/Neutral numbered rank badge.
- **Disqualified / Unsuitable Crops:** Any crop with a suitability score $< 25$ or disqualified by hard agronomic constraints (e.g. soil texture mismatch, extreme pH restriction, severe heat limit) is partitioned into a dedicated collapsible section labeled *"Crops Outside Agronomic Window (Disqualified)"*, preventing unviable options from competing with actionable rotation candidates.

---

## 7. Automated Test & Build Verification Results

### Backend Pytest Suite
- **Command:** `backend\.venv\Scripts\pytest.exe backend/tests`
- **Results:** **364 passed, 10 deselected, 103 warnings in 10.66s**
- **Test Modules Covered:**
  - `backend\tests\test_crop_ranking.py`: 2 passed (All 14 crop descriptions tested, multi-tier tie-breaking tested).
  - `backend\tests\test_phase4_analytics.py`: 11 passed (Resilience 4-component quorum $\ge 3$, normalization $1/k$).
  - `backend\tests\test_phase6_suitability.py`: 31 passed (Phase 6 Suitability Engine scoring logic, Liebig's law, constraint checks).
  - `backend\tests\test_phase7_rotation.py`: 17 passed (Rotation sequencing, penalty scoring, multi-year evaluations).
  - `backend\tests\test_api.py`: 17 passed (Field profile endpoints, coverage completeness = 1.0).
  - `backend\tests\test_contracts.py` & `test_frontend_contract.py`: 134 passed (Contract schema compliance).
  - `backend\tests\test_processing.py`: 23 passed (Environmental indicator processing without actual ET or root-zone percentile).
  - `backend\tests\test_meteomatics.py`: 10 passed (Live & mock Meteomatics provider endpoints).

### Frontend Vitest Suite
- **Command:** `npm test`
- **Results:** **5 test files passed, 27 tests passed in 837ms**
  - `src/lib/lib.test.ts`: Passed (Crop descriptions present for all 14 crops, tie-breaking deterministic sorting).
  - `src/services/mock/mock-services.test.ts`: Passed (Coverage filtering, resilience 4-component quorum).
  - `src/services/mock/export-fixtures.test.ts`: Passed (Snapshot regression).
  - `src/services/http/client.test.ts`: Passed (HTTP handling).
  - `src/services/data-mode.test.ts`: Passed (Runtime data mode controller).

### TypeScript Compilation
- **Command:** `npm run typecheck`
- **Results:** **0 errors (Exit code 0)**

### Code Style & ESLint
- **Command:** `npm run lint`
- **Results:** **0 errors, 0 warnings (Exit code 0)**

### Contract Schema Check
- **Command:** `npm run contract:check`
- **Results:** **0 mismatches (Generated `contract/openapi.gen.ts` matches `backend/openapi.json`)**

### Production Build
- **Command:** `npm run build`
- **Results:** **Compiled successfully in 1464ms, TypeScript finished in 5.3s, 13 static/PPR routes generated successfully.**

---

## 8. Residual Risks & Operational Recommendations

1. **User Cache Eviction:** Users who loaded previous field profiles before the coverage filter update should perform a browser reload so cached profiles re-fetch the updated P0 coverage array.
2. **Phase 6 Rule Base Integrity:** No modification was made to Phase 6 crop scoring weights or thresholds. Future crop additions should define their agronomic description in `backend/app/suitability/explainer.py` to maintain synchronization across backend explainers and the frontend UI.
3. **Meteomatics Upstream Rate Limits:** With Meteomatics serving as the primary multi-depth soil moisture and elevation provider, ensure backend disk-cache (`SQLITE_DB_PATH` / file cache) remains enabled in high-throughput environments to stay comfortably within subscription API concurrency limits.
