# SOILSTICE — Phase 6: Crop Suitability Analytical Methodology
**Document Version:** 1.0.0  
**Phase:** 6 (Crop Suitability Engine)  
**Status:** Canonical Analytical Specification  
**Effective Date:** 2026-11-14  

---

## 1. Executive Summary & Objective

The **SOILSTICE Crop Suitability Engine** answers the foundational agronomic query:
> *"Given the multi-layered environmental characteristics of this field, how suitable is each supported crop for cultivation here, and what evidence supports that assessment?"*

Operating across all **14 canonical crops** (`CRP001` through `CRP014`) integrated in the Phase 5 Crop Knowledge Base (`data/crop_knowledge_base.json`), the Phase 6 engine delivers transparent, factor-by-factor environmental suitability assessments. It evaluates local climate, topsoil and subsoil physical and chemical properties, terrain dynamics, rooting depth constraints, and historical field management.

Crucially, the engine is architected as an **explainable decision-support system**, not an empirical yield prediction model or commercial financial guarantee. Every factor evaluation is grounded in documented agronomic literature, traceable to the Phase 5 Evidence Registry (`EV0001`–`EV0212`), and bounded by fundamental biophysical principles.

---

## 2. Core Scientific Principles

### 2.1. Liebig's Law of the Minimum (Limiting-Factor Principle)
In biological and agronomic systems, plant growth and crop survival are governed not by the total abundance of available resources, but by the **scarcest resource or the most severe environmental constraint** (Justus von Liebig, 1840).

The SOILSTICE suitability engine strictly adheres to this principle:
1. **Critical Limitation Primacy:** A single critical environmental violation (such as topsoil pH falling outside physiological tolerance limits, or saturated anoxic soil for a legume susceptible to root rot) **strictly classifies the crop as `unsuitable`**.
2. **Non-Compensation Rule:** Favorable or optimal environmental factors (e.g., abundant GDD or optimal precipitation) **cannot silently compensate for, average out, or mask a critical limiting factor**.
3. **Score Bounding (Liebig Cap):** When a critical limitation exists, the numerical suitability score is strictly capped at $\le 35.0$ (or withheld), regardless of how high the unweighted arithmetic mean would otherwise be.

### 2.2. Scientific Null Preservation & Uncertainty Integrity
Missing environmental data represents uncertainty, not zero resources:
- **Null Value Integrity:** Missing environmental indicators (such as uncomputed GDD or absent radar soil moisture) **must never be converted to zero** ($0.0$). A temperature of $0.0^\circ\text{C-days}$ or $0.0\text{ mm}$ precipitation would represent catastrophic freeze or absolute drought.
- **Explicit Unknown Compatibility:** When an environmental variable is missing from upstream providers, the corresponding factor compatibility is recorded as `"unknown"` with a data status of `"missing"`.
- **Provisional Status & Withholding:** If critical baseline environmental factors are missing, the assessment is marked `"provisional"` or `"insufficient_data"`, and the numerical score is explicitly withheld (`null`), with a documented methodological rationale.
- **No Invented Thresholds:** Where attributes in the Phase 5 Knowledge Base are unpopulated (`null`), the engine preserves the missing state rather than fabricating unverified agronomic cutoffs.

---

## 3. Evaluated Environmental Dimensions & Factor Formulations

The engine evaluates 11 distinct environmental factors across 7 disciplinary domains:

### 3.1. Thermal Suitability (`thermal_gdd` & `thermal_heat_stress`)
- **Growing Degree Days (GDD):** Compares field-level seasonal heat unit accumulation ($\text{GDD} = \sum \max(0, \frac{T_{\max} + T_{\min}}{2} - T_{\text{base}})$) against crop developmental thresholds ($GDD_{\min}$, $GDD_{\max}$ in $^\circ\text{C-days}$) to physiological maturity.
  - *Optimal:* $GDD_{\min} \le \text{GDD}_{\text{obs}} \le 1.4 \times GDD_{\max}$.
  - *Compatible:* $\text{GDD}_{\text{obs}} > 1.4 \times GDD_{\max}$ (accelerated phenology warning).
  - *Moderate Limitation:* $0.85 \times GDD_{\min} \le \text{GDD}_{\text{obs}} < GDD_{\min}$ (requires short-season hybrids/varieties).
  - *Critical Limitation:* $\text{GDD}_{\text{obs}} < 0.85 \times GDD_{\min}$ (maturity cannot be attained before autumn frost).
- **Heat Stress Extremity:** Evaluates the count of days exceeding the crop's critical reproductive temperature threshold (e.g., $32^\circ\text{C}$ for maize pollen desiccation, $35^\circ\text{C}$ for sorghum).
  - Evaluated against crop-specific heat tolerance ratings (`tolerant`, `moderate`, `sensitive`).

### 3.2. Water & Climate Suitability (`water_precipitation`)
- Compares seasonal cumulative precipitation ($P_{\text{obs}}$ in $\text{mm}$) against documented minimum and maximum rainfed precipitation requirements ($P_{\min}, P_{\max}$).
- Evaluates moisture deficits against documented drought tolerance classifications (`tolerant`, `moderate`, `sensitive`).
- *Important Distinction:* The engine explicitly clarifies that coarse-grid climatic precipitation and climatic water balance ($P - ET_0$) reflect **regional atmospheric evaporative demand and water balance**, not direct field-level soil root-zone moisture or irrigation water duty.

### 3.3. Soil Edaphic Suitability (`soil_ph`, `soil_drainage`, `soil_texture`, `available_water`)
- **Topsoil Reaction (pH 1:1 $\text{H}_2\text{O}$, 0–30 cm):**
  - Evaluates observed SSURGO topsoil pH against documented optimal range $[pH_{\text{opt\_min}}, pH_{\text{opt\_max}}]$ and absolute physiological tolerance limits $[pH_{\text{tol\_min}}, pH_{\text{tol\_max}}]$.
  - $pH < pH_{\text{tol\_min}}$ or $pH > pH_{\text{tol\_max}}$ constitutes a **critical limitation** due to aluminum/manganese toxicity, calcium binding, or severe micronutrient lockout.
- **Soil Drainage Class:**
  - Evaluates SSURGO drainage classes (`poorly_drained` to `excessively_drained`) against documented drainage preferences.
  - Alfalfa (`CRP011`) and sensitive legumes in `poorly_drained` soils incur a **critical limitation** due to *Phytophthora* root rot and crown anoxia.
  - Paddy Rice (`CRP007`) conversely requires `poorly_drained` or dense subsoil claypans to minimize irrigation percolation losses.
- **Soil Texture Class:**
  - Evaluates USDA topsoil texture classes against documented preferences (`ideal`, `acceptable`, `marginal`, `unsuitable`).
- **Available Water Storage (AWS, 0–150 cm):**
  - Evaluates weighted multi-horizon profile water storage against crop drought avoidance strategies.

### 3.4. Rooting & Physical Soil Constraints (`rooting_depth`)
- **Extraction Depth vs. Anatomical Maximum Depth:**
  - The engine strictly distinguishes **effective water extraction depth** (40–120 cm, the active root zone where $\ge 85\%$ of moisture uptake occurs) from **maximum anatomical root depth** (60–350 cm, deep taproots or adventitious anchor roots).
  - These values are never conflated. Shallow restrictive layers (e.g., lithic contacts or dense plow pans at $< 40\text{ cm}$) restrict water extraction regardless of nominal genetic potential.
- **Compaction Alleviation Potential:**
  - Recognizes exceptional bio-drilling taproot capabilities (e.g., Oilseed Radish `CRP014` with root taproots penetrating dense subsoils to 180–240 cm).

### 3.5. Terrain Constraints (`terrain_slope`)
- Compares SRTM 90th percentile slope gradients against soil conservation and machinery limits:
  - $\le 6\%$: Optimal for clean-tilled row crops.
  - $6\% - 10\%$: Moderate limitation; requires contour farming, terraces, or cover-crop protection.
  - $> 10\%$: Critical limitation for conventional mechanized row crops; compatible with perennial forages (`CRP011`) or continuous cover crops (`CRP012`, `CRP013`).

### 3.6. Agronomic & Historical Context (`crop_history_context`)
- Evaluates recent Cropland Data Layer (CDL) majority crop history on the field:
  - **Consecutive Monoculture:** Flags multi-year monoculture of the same crop code, penalizing weed, insect, and soil-borne pathogen cycles.
  - **Alfalfa Medicarpin Autotoxicity:** Enforces strict autotoxicity limitations for continuous alfalfa (`CRP011`), which requires a 1–2 year rotational break (EV0162).
  - **Botanical Family Rotation:** Identifies family-level breaks (e.g., rotating Poaceae cereals with Fabaceae legumes or Brassicaceae covers).

### 3.7. Regional Climatic Adaptation (`regional_adaptation`)
- Evaluates documented regional adaptation tiers (e.g., CONUS central plains, eastern corn belt, southern plains).
- *Strict Principle:* Regional suitability cannot override local environmental incompatibility, nor does regional presence guarantee field-level success.

---

## 4. Suitability Classification System

The engine assigns every crop into one of five transparent, mutually exclusive classes:

| Suitability Class | Definition & Decision Criteria | Agronomic Interpretation |
| :--- | :--- | :--- |
| **`suitable`** | Zero critical limitations, zero moderate limitations. All evaluated parameters meet optimal or compatible requirements. | Highly compatible; environmental conditions support standard commercial yields under typical regional management. |
| **`conditionally_suitable`** | Zero critical limitations, $\le 2$ moderate limitations. No physiological thresholds violated. | Moderately compatible; manageable constraints exist (e.g., slight pH deviation, moderate rainfall deficit) requiring specific agronomic interventions (liming, hybrid selection, supplemental irrigation). |
| **`limited_suitability`** | Zero critical limitations, $\ge 3$ compounding moderate limitations. | Substantial constraints; multiple compounding environmental stresses will restrict yield potential or require intensive conservation inputs. |
| **`unsuitable`** | $\ge 1$ critical environmental limitation (physiological pH bounds violated, severe thermal deficiency, extreme waterlogging, or severe slope). | Not recommended; fundamental biophysical constraints preclude standard cultivation. |
| **`insufficient_data`** | Fewer than 2 valid environmental factor observations available for the field. | Assessment withheld; insufficient observed data to form a scientifically defensible evaluation. |

---

## 5. Bounded Numerical Scoring Methodology

### 5.1. Engineering Factor Weights
To prevent arbitrary averaging, numerical scoring is applied only across core biophysical factors with published agronomic response functions:

$$\text{Weighting Scheme } (W_i):$$
- Thermal GDD: $0.20$
- Seasonal Precipitation: $0.20$
- Topsoil pH: $0.20$
- Soil Drainage: $0.15$
- Available Water Storage: $0.15$
- Terrain Slope: $0.10$

### 5.2. Mathematical Calculation
1. **Raw Weighted Average:**
   $$\text{Raw Score} = \frac{\sum_{i \in \text{Available}} S_i \times W_i}{\sum_{i \in \text{Available}} W_i}$$
   where $S_i \in [0, 100]$ is the individual factor compatibility score.

2. **Liebig Limiting-Factor Bounding:**
   - If $\text{Class} == \text{"unsuitable"}$:
     $$\text{Final Score} = \min(\text{Raw Score}, \min(S_i), 35.0)$$
   - If $\text{Class} == \text{"limited\_suitability"}$:
     $$\text{Final Score} = \text{clamp}(\text{Raw Score}, 35.0, 59.9)$$
   - If $\text{Class} == \text{"conditionally\_suitable"}$:
     $$\text{Final Score} = \text{clamp}(\text{Raw Score}, 55.0, 74.9)$$
   - If $\text{Class} == \text{"suitable"}$:
     $$\text{Final Score} = \text{clamp}(\text{Raw Score}, 75.0, 100.0)$$

3. **Score Withholding Rules:**
   - Numerical scores are **strictly withheld** (`null`) if:
     - The classification is `"insufficient_data"`.
     - Fewer than 3 core weighted factors have valid observations.
   - When a score is withheld, `score_methodology` provides an explicit narrative explanation.

---

## 6. Mandatory Scientific Constraints

1. **Oilseed Radish Nitrogen Accounting:**
   - Oilseed Radish (`CRP014`) scavenges $100\text{--}220\text{ kg N/ha}$ from deep soil horizons (EV0028, EV0203).
   - This constitutes **internal soil profile recycling and leached nitrate retrieval**, **NOT biological nitrogen fixation**.
   - BNF is strictly accounted as $0.0\text{ kg N/ha}$, and fertilizer replacement credits are null unless validated by synchronized mineralization studies.

2. **Effective Extraction Depth vs. Anatomical Maximum:**
   - Corn (`CRP001`): Effective extraction $40\text{--}90\text{ cm}$; Anatomical max $120\text{--}180\text{ cm}$.
   - Alfalfa (`CRP011`): Effective extraction $90\text{--}180\text{ cm}$; Anatomical max $250\text{--}350\text{ cm}$.
   - Evaluators must never evaluate effective moisture buffering using the anatomical maximum depth.

3. **No Phase 7 Rotation Sequencing:**
   - The engine strictly assesses individual crop-to-field compatibility and pairwise historical context.
   - It does not generate forward multi-year rotation recommendations, rotation sequence optimization, or scenario alternatives (strictly reserved for Phase 7).

---

## 7. Traceability to Evidence Registry

Every factor assessment explicitly lists the `evidence_ids` corresponding to the underlying peer-reviewed literature and USDA/FAO publications in `data/crop_knowledge_base.json`. When an assessment is delivered via the API or displayed in the UI, users can trace any threshold directly to its publication author, year, title, and geographic scope.
