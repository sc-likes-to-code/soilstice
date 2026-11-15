# SOILSTICE — Phase 7: Multi-Year Crop Rotation Implementation Report
**Document Version:** 1.0.0  
**Phase:** 7 (Multi-Year Crop Rotation Recommendation & Scenario Comparison Engine)  
**Status:** Complete & Production Ready  
**Effective Date:** 2026-11-15  

---

## 1. Executive Summary

Phase 7 delivers the **Multi-Year Crop Rotation Recommendation and Scenario Comparison Engine** for SOILSTICE, extending the Phase 4 environmental observation pipelines, Phase 5 cited Crop Knowledge Base (`EV0001`–`EV0212`), and Phase 6 biophysical crop suitability engine.

The engine provides:
1. **Factor-by-Factor Multi-Year Sequence Evaluation:** Evaluates 2- to 5-year crop sequences across four orthogonal agronomic dimensions (`agronomic_fit`, `rotation_benefit`, `water_risk`, `diversity`) and synthesizes an overall qualitative interpretation label (`supported`, `conditional`, `exploratory`, `not_recommended`, `insufficient_data`).
2. **Directed Rotation Compatibility & Pathogen Cycle Modeling:** Enforces asymmetric directed transitions $T(A \rightarrow B) \neq T(B \rightarrow A)$ across all 196 combinations in the Phase 5 KB, penalizes consecutive monocultures, and tracks botanical family accumulation across all 14 canonical crops (`CRP001`–`CRP014`).
3. **Antecedent CDL History Linkage:** Seamlessly incorporates the parcel's verified USDA Cropland Data Layer history (e.g. 2025 verified majority crop) as the antecedent condition for Year 1 of prospective rotation scenarios.
4. **Bounded Beam Search Candidate Generation:** Deterministically generates Pareto-optimal candidate crop sequences over horizons of 2, 3, 4, or 5 years using beam width $W=50$, early constraint pruning of environmentally unsuitable crops or prolonged monocultures, and multi-objective ranking.
5. **Multi-Scenario Comparison & Trade-off Synthesis:** Enables side-by-side comparison of 2 or 3 scenarios, displaying a dimension-by-dimension matrix and automated agronomic trade-offs across taxonomic diversity, soil moisture risk, and environmental suitability.
6. **Complete Frontend & Dual-Mode Integration:** Section 4 of Rotation Lab (`rotation-view.tsx`) provides interactive candidate generation, scenario authoring, and side-by-side comparison, fully supported in both FastAPI Live API and Next.js Mock Data modes.

---

## 2. Architecture & Implementation Details

### 2.1. Backend Architecture (`backend/app/rotation/`)

| Module | Core Responsibilities |
| :--- | :--- |
| `backend/app/rotation/evaluator.py` | Implements `MultiYearEvaluator`. Evaluates directed transitions, monoculture penalties, botanical family runs (Poaceae, Fabaceae, Brassicaceae, Malvaceae), and water risk sequencing. Computes the 4 orthogonal dimensions and overall qualitative interpretation label. |
| `backend/app/rotation/search.py` | Implements `BoundedBeamSearchGenerator`. Executes deterministic bounded beam search ($W=50$) over planning horizons 2–5 years. Prunes branches violating Liebig limitations or 3+ monoculture runs. Formats top $K=10$ non-dominated candidates. |
| `backend/app/rotation/comparison.py` | Implements `ScenarioComparator`. Compares 2 or 3 scenarios, evaluating taxonomic diversity differences, water depletion profiles, and suitability bands. Synthesizes categorized `TradeoffFinding`s. |
| `backend/app/rotation/engine.py` | Implements `MultiYearRotationEngine` (replacing `PendingRotationEngine`). Exposes `evaluate`, `generate_candidates`, and `compare_scenarios`. Preserves `PendingRotationEngine` as a backward-compatible alias. |

### 2.2. Contracts & API Endpoints

#### Pydantic Contracts (`backend/app/contracts/entities.py` & `vocab.py`)
- `ScenarioInterpretation`: `Literal["supported", "conditional", "exploratory", "not_recommended", "insufficient_data"]`.
- `ScenarioEvaluation`: Extended to include `interpretation: ScenarioInterpretation`.
- `GenerateRotationsRequest`: `horizon` (2–5, default 3), `start_year` (default 2026), `include_cover_crops` (bool), `max_candidates` (1–20, default 10).
- `GenerateCandidate`: `rank`, `name`, `sequence`, `evaluation`.
- `GenerateRotationsResponse`: `field_id`, `horizon`, `start_year`, `antecedent_crop`, `candidates`, `generated_at`.
- `CompareScenariosRequest`: `scenario_ids: list[UUID]` (2 or 3 IDs).
- `TradeoffFinding`: `category`, `summary`.
- `CompareScenariosResponse`: `field_id`, `scenarios`, `tradeoffs`.

#### FastAPI Endpoints (`backend/app/api/routes.py`)
- `POST /api/v1/fields/{field_id}/rotations/generate`: Generates candidate rotations using bounded beam search.
- `POST /api/v1/fields/{field_id}/rotations/compare`: Compares 2 or 3 scenarios side by side with synthesized trade-offs.
- `POST /api/v1/fields/{field_id}/scenarios`: Evaluates and persists custom scenarios using the real Phase 7 engine.
- `PUT /api/v1/scenarios/{scenario_id}`: Re-evaluates and updates existing scenarios.

### 2.3. Frontend Rotation Lab Integration (`src/components/views/rotation-view.tsx`)
- **Active Engine Badge:** Declares Phase 7 Multi-Year Rotation Intelligence Engine active (v1.0.0).
- **Candidate Generator Panel:**
  - Interactive horizon selector pills: 2, 3, 4, 5 Years (default 3).
  - Start year selector: 2026–2035.
  - "Generate Candidates" action with loading feedback.
  - Candidate cards displaying rank, visual sequence timeline with crop colors, overall band, qualitative interpretation pill (`supported`, `conditional`, etc.), 4 dimension bands, "Edit in Builder", and "Save directly" actions.
- **Scenario Builder:** Author custom multi-year sequences with crop selector, year add/remove controls, and live evaluation upon saving.
- **Side-by-Side Comparison Matrix:**
  - Supports comparing 2 or 3 scenarios simultaneously.
  - Displays sequence chips, overall fit, and the 4 dimensions side-by-side.
  - Displays automated Agronomic Trade-off Synthesis box (diversity, water risk, agronomic fit).
  - Fully responsive across mobile (375px), tablet (768px), desktop (1024px), and wide monitors (1440px).

### 2.4. Dual-Mode Support
- **Live API Mode:** Directly calls FastAPI backend endpoints via `src/services/http/services.ts`. Evaluates real field environmental data and CDL crop history.
- **Mock Data Mode:** Deterministic in-memory generation and comparison via `mockGenerateRotations` and `mockCompareScenarios` in `src/services/mock/`.

---

## 3. Verification & Test Results

### 3.1. Verification Matrix Across the 25 Formal Criteria

| # | Verification Criterion | Status | Evidence / Test Function |
| :---: | :--- | :---: | :--- |
| 1 | Canonical 14 crops supported (`CRP001`–`CRP014`) | **PASS** | `test_criterion_1_and_2_canonical_14_crops_and_cdl_mappings` |
| 2 | Correct USDA CDL code mapping for 11 crops, None for 3 cover crops | **PASS** | `test_criterion_1_and_2_canonical_14_crops_and_cdl_mappings` |
| 3 | Asymmetric directed transition evaluation $T(A \rightarrow B) \neq T(B \rightarrow A)$ | **PASS** | `test_criterion_3_asymmetric_transitions` |
| 4 | Retrieval of documented synergy mechanisms from Phase 5 KB | **PASS** | `test_criterion_4_5_6_7_synergies_risks_herbicide_citations` |
| 5 | Retrieval of documented pathogen/pest risks from Phase 5 KB | **PASS** | `test_criterion_4_5_6_7_synergies_risks_herbicide_citations` |
| 6 | Retrieval of documented herbicide carryover warnings from Phase 5 KB | **PASS** | `test_criterion_4_5_6_7_synergies_risks_herbicide_citations` |
| 7 | Citation linkages (`EV0001`–`EV0212`) on all transition findings | **PASS** | `test_criterion_4_5_6_7_synergies_risks_herbicide_citations` |
| 8 | Unknown preceding crop handling without fabricated synergies | **PASS** | `test_criterion_8_unknown_preceding_crop_handling` |
| 9 | Consecutive monoculture detection and penalty scoring | **PASS** | `test_criterion_9_consecutive_monoculture_penalized` |
| 10 | Botanical family repetition tracking across all 14 crops | **PASS** | `test_criterion_10_and_11_botanical_family_run_penalties` |
| 11 | Family run length penalties for runs $> 2$ years | **PASS** | `test_criterion_10_and_11_botanical_family_run_penalties` |
| 12 | Distinct crop count metric computation | **PASS** | `test_criterion_12_and_13_diversity_metrics` |
| 13 | Distinct botanical family count metric computation | **PASS** | `test_criterion_12_and_13_diversity_metrics` |
| 14 | Antecedent CDL history integration for prospective Year 1 | **PASS** | `test_criterion_14_antecedent_history_integration` |
| 15 | Environmental suitability baseline integration without score averaging | **PASS** | `test_criterion_15_and_16_environmental_suitability_baseline` |
| 16 | Quorum and data sufficiency enforcement | **PASS** | `test_criterion_15_and_16_environmental_suitability_baseline` |
| 17 | Bounded beam search operation across horizons 2, 3, 4, 5 years | **PASS** | `test_criterion_17_18_19_beam_search_generator` |
| 18 | Hard constraint rejection of unsuitable crops and fatal monocultures | **PASS** | `test_criterion_17_18_19_beam_search_generator` |
| 19 | Deterministic tie-breaking across generated candidates | **PASS** | `test_criterion_19_deterministic_tie_breaking` |
| 20 | Generation of exactly 4 dimensions (`agronomic_fit`, `rotation_benefit`, `water_risk`, `diversity`) | **PASS** | `test_criterion_20_and_21_dimensions_and_interpretation_labels` |
| 21 | Explicit qualitative interpretation labels (`supported`, `conditional`, `exploratory`, `not_recommended`, `insufficient_data`) | **PASS** | `test_criterion_20_and_21_dimensions_and_interpretation_labels` |
| 22 | Side-by-side scenario comparison supporting 2 and 3 scenarios | **PASS** | `test_criterion_22_scenario_comparison_2_and_3_scenarios` |
| 23 | Complete dual-mode support (FastAPI Live API & Next.js Mock Data) | **PASS** | `test_criterion_23_generate_rotations_api_endpoint` & Mock suite |
| 24 | Zero yield predictions, profit forecasts, or unverified nitrogen credits | **PASS** | `test_criterion_24_no_yield_or_profit_claims` |
| 25 | 100% test pass rate across all test suites | **PASS** | 348 backend pytest passed, 25 vitest passed, 0 failures |

### 3.2. Automated Test Execution Summary
- **Backend pytest:** 348 passed, 6 deselected, 0 failures (19.46s).
- **Frontend vitest:** 25 passed, 0 failures (3.29s).
- **Contract check (`npm run contract:check`):** OpenAPI export, schema generation, and TypeScript `Same<A, B>` type checks passed with 0 errors.
- **TypeScript typecheck (`npm run typecheck`):** Zero errors (`tsc --noEmit`).
- **ESLint (`npm run lint`):** Zero errors, zero warnings.
- **Production Build (`npm run build`):** Compiled and generated 13 static/PPR routes in 3.5s with zero errors.

---

## 4. Live Verification on Running Backend

The engine was verified against the active FastAPI daemon running on port 8000:
1. **Candidate Generation for Audit Reno Field (`4e0f055e-12f1-427b-97ff-d8815be858fb`):**
   - Retrieved antecedent 2025 crop: `Corn` (`CRP001` / CDL code 1).
   - Generated 5 candidates for 3-year horizon ($2026 \rightarrow 2028$):
     - Candidate #1: `Soybean – Grain Sorghum – Cotton` $\rightarrow$ `suitable` (`supported`).
     - Candidate #2: `Soybean – Cereal Rye – Cotton` $\rightarrow$ `suitable` (`supported`).
     - Candidate #3: `Soybean – Winter Wheat – Cotton` $\rightarrow$ `suitable` (`supported`).
     - Candidate #4: `Cotton – Grain Sorghum – Soybean` $\rightarrow$ `suitable` (`supported`).
     - Candidate #5: `Cereal Rye – Cotton – Soybean` $\rightarrow$ `suitable` (`supported`).
2. **Scenario Comparison (Wheat-Sorghum-Soybean vs Continuous Corn):**
   - Scenario A (`Wheat – Sorghum – Soybean`): `suitable` (`supported`).
   - Scenario B (`Continuous Corn`): `unsuitable` (`not_recommended`).
   - Synthesized trade-offs:
     - `[diversity]`: Scenario A provides greater botanical family diversity (2 families: Fabaceae, Poaceae) than Scenario B (1 family).
     - `[water_risk]`: Scenario A poses lower moisture depletion risk (0 high-demand crop seasons vs 3 in Scenario B).
     - `[agronomic_fit]`: Scenario A is agronomically supported, whereas Scenario B contains critical monoculture and pest limitations.
