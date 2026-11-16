# SOILSTICE — Phase 4 Analytical Methodology

**Project:** `E:\MY PROJECTS\Soilstice`  
**Date:** 2026-11-14  
**Scope:** Scientific definitions, mathematical formulas, quality-control thresholds, and authoritative citations for environmental and resilience indicators.  
**Governing Documents:**
- `docs/SOILSTICE_DATA_ARCHITECTURE.md` §5 (Processing & analytics architecture)
- `docs/SOILSTICE_API_CONTRACTS.md` §2 & §5 (Pydantic contracts & enums)
- `docs/PHASE_0_DECISIONS.md` §8 & T18 (Resilience framework rules)

---

## 1. Audit of Phase 3 Baseline GDD (2024: 2,577 °C-days) vs Grounded Modified GDD (2,862.0 °C-days)

During Phase 3 manual browser QA, the frontend display reported **2,577 °C-days** for the 2024 season. An independent audit of this value reveals:

### Audit Findings
1. **Source & Nature:** The value **2,577 °C-days** did **not** originate from actual daily NASA POWER integration in the backend. Instead, it was computed by the synthetic client generator (`src/services/mock/generators.ts:79`):
   ```typescript
   const gddMonthly = tmax.map((hi, i) => Math.max(0, (Math.min(hi, 30) + Math.max(tmin[i], 10)) / 2 - 10) * DAYS[i]);
   ```
2. **Methodological Deficiencies in Mock Generator:**
   - **Monthly Averaging Error:** The mock used monthly mean $T_{\max}$ and $T_{\min}$ multiplied by days per month. Because GDD is a non-linear truncation function, monthly averaging severely underestimates heat accumulation during early spring and autumn and fails to capture daily threshold crossings.
   - **Crop Agnosticism:** It applied a single hardcoded base temperature ($10^\circ\text{C}$) and upper cutoff ($30^\circ\text{C}$) across all 365 calendar days without accounting for the actual crop planted or its phenological window.
3. **Backend Live API Status:** In the Phase 3 FastAPI backend (`backend/app/processing/climate.py`), `gdd_season` was properly configured with:
   ```python
   ("gdd_season", "Growing degree days", "climate", "degC_day", ("pending",))
   ```
   and returned `value: null` with `missing_reason: "NOT_COMPUTED"`, adhering strictly to scientific honesty.
4. **Independent Reproduction for Phase 4:** Consuming the 366 daily $(T_{\max}, T_{\min})$ observations from NASA POWER MERRA-2 for Reno County (centroid -98.05°, 37.95°) using the standard McMaster & Wilhelm (1997) Method 2 (Modified GDD) parameterized with standard warm-season baseline thresholds ($T_{\text{base}} = 10.0^\circ\text{C}, T_{\text{cap}} = 30.0^\circ\text{C}$) over the 2024 leap year yields exactly **2,861.99 °C·d** (rounding to **2,862.0 °C·d**).

---

## 2. Climate Intelligence Methodology

All climate calculations consume stored `PowerDaily` records (`backend/app/providers/power.py`) queried at field centroids with spatial support class **`R`** (~50 km meteorology / ~110 km solar radiation).

### 2.1 Growing Degree Days (`gdd_season`)
- **Scientific Definition:** Heat accumulation above a crop-specific developmental threshold temperature ($T_{\text{base}}$) up to an optional developmental ceiling ($T_{\text{cap}}$).
- **Required Inputs:** Daily maximum temperature ($T_{\max}$, °C) and daily minimum temperature ($T_{\min}$, °C) from NASA POWER `T2M_MAX` and `T2M_MIN`.
- **Formula (Modified GDD / Method 2, McMaster & Wilhelm 1997; Barger 1969):**
  For each day $d$ in the season window:
  $$T_{\max}^* = \min(\max(T_{\max}, T_{\text{base}}), T_{\text{cap}})$$
  $$T_{\min}^* = \min(\max(T_{\min}, T_{\text{base}}), T_{\text{cap}})$$
  $$\text{GDD}_d = \max\left(0, \frac{T_{\max}^* + T_{\min}^*}{2} - T_{\text{base}}\right)$$
  $$\text{GDD}_{\text{season}} = \sum_{d \in \text{season}} \text{GDD}_d$$
- **Crop-Specific Thermal Thresholds:**
  | Crop | $T_{\text{base}}$ (°C) | $T_{\text{cap}}$ (°C) | Authoritative Reference |
  |---|---|---|---|
  | **Corn (Maize)** | 10.0 (50 °F) | 30.0 (86 °F) | Barger (1969); Gilmore & Rogers (1958); USDA-ARS |
  | **Winter Wheat** | 0.0 (32 °F) | 25.0 (77 °F) | McMaster & Wilhelm (1997); K-State Research & Extension MF-2475 |
  | **Grain Sorghum** | 10.0 (50 °F) | 35.0 (95 °F) | Vanderlip & Reeves (1972); K-State Research & Extension MF-1085 |
  | **Soybeans** | 10.0 (50 °F) | 30.0 (86 °F) | Fehr & Caviness (1977); Major et al. (1975) |
  | **Alfalfa** | 5.0 (41 °F) | 30.0 (86 °F) | Fick et al. (1988); K-State Research & Extension MF-1058 |
  | **Unspecified / Baseline** | 10.0 (50 °F) | 30.0 (86 °F) | Standard warm-season crop baseline |
- **Crop Determination & Unknown Crop Disclosure:**
  - If caller provides an explicit `crop_code`, the corresponding thresholds are applied.
  - If `crop_code` is unspecified (`None`), the engine applies the standard warm-season baseline thresholds ($10.0^\circ\text{C} / 30.0^\circ\text{C}$) and explicitly emits `QualityFlag(code="GDD_DEFAULT_PARAMETERS")` disclosing that standard baseline thresholds were applied.
- **Season Window & Missing-Day Handling:**
  - Plausibility check: $T_{\min} \le T_{\max}$. If violated, day is flagged.
  - Completeness requirement: At least 90% of days in the season window must have valid $T_{\max}$ and $T_{\min}$. If completeness $< 0.90$, $\text{GDD}_{\text{season}}$ is `null` with `missing_reason: "INSUFFICIENT_COVERAGE"`.
  - Missing days within valid windows ($\ge 90\%$) are omitted from the sum (not filled or scaled), and flagged with `MISSING_DAYS_OMITTED`.
  - Currently evaluated over the calendar year pending crop-specific planting/harvest dates from the crop knowledge base.
- **Spatial Support:** Support class **`R`**, native resolution ~55,000 m, `api_point_query`.

### 2.2 Seasonal Precipitation Total (`precip_total_season`)
- **Scientific Definition:** Cumulative liquid water equivalent delivered over the defined season window.
- **Input:** Daily precipitation (`PRECTOTCORR`, mm/day) from NASA POWER.
- **Formula:**
  $$P_{\text{season}} = \sum_{d \in \text{season}} P_d$$
- **Quality Control:** $P_d \ge 0.0\text{ mm}$. If completeness $< 0.90$, `value: null` with `INSUFFICIENT_COVERAGE`. Missing days are not filled with zero.
- **Units:** mm. Support class **`R`**.

### 2.3 Precipitation Anomaly vs Baseline (`precip_anomaly_pct`)
- **Scientific Definition:** Percentage departure of season precipitation from the 30-year climatological normal (1991–2020).
- **Formula:**
  $$\Delta P_{\%} = \frac{P_{\text{season}} - P_{\text{normal}}}{P_{\text{normal}}} \times 100$$
- **Baseline Source:** NOAA NCEI 1991–2020 Climate Normals for Kansas Climate Division 8 / Hutchinson 10 SW (USC00143930: normal annual precipitation $760.5\text{ mm}$ / 29.94 inches).
- **Spatial Disparity Disclosure:** The baseline is a ground rain-gauge measurement serving as a local Reno County benchmark. The indicator carries `QualityFlag(code="POINT_STATION_BASELINE")` disclosing that station point normals differ in spatial support from MERRA-2 gridded areal precipitation.
- **Units:** percent (%). Directionality: negative indicates drought deficit; positive indicates surplus.

### 2.4 Heat-Stress Days (`heat_stress_days`)
- **Scientific Definition:** Number of calendar days during the analyzed period exceeding critical maximum temperature thresholds.
- **Thresholds:**
  - Warm-season crops (corn, sorghum, soybean, default): $T_{\max} \ge 35.0^\circ\text{C}$ (95 °F) (Schlenker & Roberts 2009; K-State Agronomy).
  - Cool-season wheat: $T_{\max} \ge 30.0^\circ\text{C}$ (86 °F) (Paulsen 1994).
- **Phenology Limitation Disclosure:** Because satellite phenological dates (flowering, silking, grain filling) are uncomputed (pending Earthdata Login credentials for HLS), heat-stress days represent calendar-window thermal extremity. The indicator explicitly carries `QualityFlag(code="PHENOLOGY_UNAVAILABLE")` stating that reproductive-stage-specific heat stress is not claimed.
- **Formula:**
  $$\text{Days}_{\text{heat}} = \sum_{d \in \text{season}} \mathbf{1}(T_{\max, d} \ge T_{\text{crit}})$$
- **Units:** days. Support class **`R`**.

### 2.5 Frost-Free Days (`frost_free_days`)
- **Scientific Definition:** Total count of individual days in the analyzed calendar window with minimum temperature strictly above freezing ($T_{\min} > 0.0^\circ\text{C}$).
- **Formula:**
  $$\text{Days}_{\text{frost\_free}} = \sum_{d \in \text{season}} \mathbf{1}(T_{\min, d} > 0.0^\circ\text{C})$$
- **Agronomic Distinction:** This metric counts total non-freezing days across the full calendar year. It is explicitly distinguished from the continuous freeze-free season length (the consecutive interval between the last spring freeze and the first autumn freeze, which was 237 days in Reno County in 2024 vs 287 total non-freezing days). Carries `QualityFlag(code="CALENDAR_DAYS_COUNT")`.
- **Units:** days. Support class **`R`**.

### 2.6 Reference Evapotranspiration (`et0_total_season`) & Climatic Water Balance (`water_balance_season`)
- **Scientific Definition:**
  - $\text{ET}_0$: Atmospheric evaporative demand from a hypothetical well-watered reference grass canopy ($h = 0.12\text{ m}$, albedo $0.23$, surface resistance $70\text{ s/m}$).
  - Climatic water balance: Net meteorological moisture surplus or deficit ($P - \text{ET}_0$).
- **Formula (FAO-56 Penman-Monteith, Allen et al. 1998):**
  $$\text{ET}_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$
  $$\text{Climatic Water Balance} = P_{\text{season}} - \text{ET}_{0, \text{season}}$$
- **Engineering Approximations Disclosed:**
  - Wind speed: Assumed neutral $u_2 = 2.0\text{ m/s}$ (FAO-56 standard default when measured wind data is unavailable).
  - Elevation: Parameterized to local Reno County elevation ($470.0\text{ m}$).
  - Net longwave radiation ($R_{nl}$): Scaled by regional growing-season clear-sky radiation ratio approximation.
- **Boundary Distinction vs Crop Water Demand:**
  - Climatic water balance is purely meteorological ($P - \text{ET}_0$).
  - It is **NOT** crop water demand ($ET_c = K_c \times \text{ET}_0$, which requires crop coefficients $K_c$ and phenological stage dates).
  - It is **NOT** actual evapotranspiration ($ET_a$, which requires surface energy balance models such as OpenET or root-zone soil water stress coefficients $K_s$).
  - It is **NOT** irrigation requirement (which requires root-zone water depletion accounting, effective rainfall, and leaching fraction).
- **Units:** mm. Support class **`R`**.

---

## 3. Soil & Water Intelligence Methodology

Consumes stored `SoilProfile` records (`backend/app/providers/ssurgo.py`) derived from USDA NRCS SSURGO via Soil Data Access (SDA) with spatial support class **`F`** (`vector_intersection`).

### 3.1 Available Water Storage (`aws_0_150`, `aws_0_100`)
- **Definition:** Water volume retained between field capacity (1/3 bar) and permanent wilting point (15 bar) in profile.
- **Source:** SSURGO `muaggatt.aws0150wta` and `aws0100wta` (area-weighted average of map units intersecting field polygon).
- **Units:** cm of water. Support class **`F`**.
- **Agronomic Ranges (K-State Extension MF-2980):**
  - $< 10.0\text{ cm}$: Low storage; acute drought hazard.
  - $10.0$–$18.0\text{ cm}$: Moderate capacity.
  - $18.0$–$25.0\text{ cm}$: High capacity (characteristic of Nalim and Harney silt loams).
  - $> 25.0\text{ cm}$: Exceptional water-buffering capacity.

### 3.2 Fixed-Depth Texture & Chemical Properties
- Standardized depth intervals: 0–30 cm, 30–100 cm, 100–150 cm. Area $\times$ component percentage weighting.

---

## 4. Vegetation Intelligence Framework

Consumes stored `VegetationProfile` records (`backend/app/providers/hls.py`) with spatial support class **`F`** (native 30 m grid, inward buffer).
- When raw HLS COGs are unretrieved due to Earthdata credentials, phenology returns `value: null` with `missing_reason: "INSUFFICIENT_COVERAGE"`. Zero synthetic curves are published.

---

## 5. Crop History & CDL Rotation Intelligence Methodology

Consumes stored `CropHistory` records (`backend/app/providers/cdl.py`) across 2006–2025 sequence (20 consecutive seasons) with spatial support class **`F`** (30 m / 56 m native GeoTIFFs, 15 m inward buffer).

### 5.1 Land Cover vs Crop Species Separation
Classes are strictly partitioned into:
1. **Non-Agricultural Land Cover:** Open Water (111), Developed (121–124), Barren (131), Deciduous/Evergreen/Mixed Forest (141–143), Shrubland (152), Wetlands (190, 195).
2. **Agricultural Non-Crop Land Use / Management States:** Fallow/Idle Cropland (61), Grassland/Pasture (176). These represent management conditions or perennial forage, NOT cultivated annual crop species.
3. **Cultivated Crop Species:** Corn (1), Sorghum (4), Soybeans (5), Sunflower (6), Winter Wheat (24), Double-crop Winter Wheat/Soybeans (26), Rye (27), Oats (28), Millet (29), Alfalfa (36), Other Hay (37), Double-crop Winter Wheat/Sorghum (236).

### 5.2 Distinct Crop Species (`distinct_crops`)
- **Scientific Definition:** Number of distinct cultivated agricultural crop species over the observation record.
- **Formula:**
  $$\text{Distinct Crops} = |\{ \text{crop\_code}_y : y \in [2006, 2025] \land \text{is\_cultivated\_species}(\text{crop\_code}_y) \}|$$
- **Units:** count.

### 5.3 Longest Monoculture Run (`max_monoculture_run`)
- **Scientific Definition:** Maximum number of consecutive calendar years the identical cultivated crop species was planted.
- **Temporal Continuity Rule:** Intervening fallow (61), pasture (176), non-agricultural land cover, or missing years interrupt the run ($y_k = y_{k-1} + 1$). Separated years are never concatenated.
- **Units:** years.

### 5.4 Shannon Rotation Diversity Index (`rotation_shannon`)
- **Scientific Definition:** Information-theoretic diversity index capturing temporal richness and evenness of the dominant cultivated crop species sequence across observation years.
- **Formula (Shannon 1948; Magurran 1988):**
  $$p_i = \frac{n_i}{N_{\text{cultivated\_years}}}$$
  $$H' = -\sum_{i=1}^{S} p_i \ln(p_i)$$
- **Units:** unitless.

---

## 6. Field Resilience Scoring Methodology (Expert-Informed Breakpoint Model)

Governed by `DATA_ARCHITECTURE.md` §5.10. The resilience framework evaluates 5 distinct environmental dimensions using absolute agronomic breakpoints and engineering scoring heuristics. Fields are **never** ranked against each other.
> [!NOTE]
> This model is an **expert-informed decision-support heuristic**, NOT an empirically calibrated regression or outcome model. Numeric breakpoints and weights are engineering scoring choices informed by published agronomic ranges.

### 6.1 Component Definitions & Breakpoint Tables

#### Component 1: Soil Water Buffer (`soil_water_buffer`)
- **Input:** Profile available water storage (`aws_0_150`, cm) from SSURGO. Support class **`F`**.
- **Scoring Direction:** Higher AWS $\to$ Higher resilience.
- **Breakpoint Table (Informed by NRCS Soil Quality Tech Note 2; K-State Extension MF-2980):**
  | `aws_0_150` (cm) | Score (0–100) | Agronomic Justification |
  |---|---|---|
  | $\le 6.0$ | 0 | Severely shallow/sandy; acute drought vulnerability |
  | $10.0$ | 30 | Marginal water holding |
  | $15.0$ | 55 | Moderate buffer |
  | $20.0$ | 80 | High buffer capacity (Central KS Nalim/Harney loam benchmark) |
  | $\ge 25.0$ | 100 | Deep silt loam; exceptional drought resilience |

#### Component 2: Terrain Erosion Risk (`terrain_erosion_risk`)
- **Input:** 90th percentile slope (`slope_p90_pct`, %) from SRTM. Support class **`F`**.
- **Scoring Direction:** Flatter terrain $\to$ Lower erosion hazard $\to$ Higher resilience.
- **Breakpoint Table (Informed by NRCS Highly Erodible Land criteria; RUSLE):**
  | `slope_p90_pct` (%) | Base Score (0–100) | Agronomic Justification |
  |---|---|---|
  | $\le 0.5$ | 100 | Flat, negligible runoff velocity |
  | $1.5$ | 85 | Minimal slope, low sheet erosion potential |
  | $3.0$ | 65 | Gentle slope, moderate runoff velocity |
  | $6.0$ | 35 | Moderate slope, erosion control practices required |
  | $\ge 10.0$ | 10 | Steep slope, high erodibility index |

#### Component 3: Climate Exposure (`climate_exposure`)
- **Inputs:** Seasonal heat-stress days ($T_{\max} \ge 35^\circ\text{C}$, count) and precipitation anomaly ($\Delta P_{\%}$, %) from NASA POWER. Support class **`R`**.
- **Scoring Direction:** Lower climatic extremity $\to$ Higher score.
- **Heuristic Scoring (Informed by Schlenker & Roberts 2009):**
  - Heat sub-score: $\le 5\text{ d} \to 100$; $15\text{ d} \to 75$; $30\text{ d} \to 45$; $\ge 50\text{ d} \to 10$.
  - Precip sub-score: 100 at normal, drops linearly to 20 at $-50\%$ deficit; drops to 60 above $+50\%$ excess.
  - Heuristic weighting: $0.60 \times \text{Heat} + 0.40 \times \text{Precip}$.

#### Component 4: Rotation Diversity (`rotation_diversity`)
- **Inputs:** `distinct_crops`, `max_monoculture_run`, `rotation_shannon` ($H'$). Support class **`F`**.
- **Scoring Direction:** Higher diversity, shorter monoculture runs $\to$ Higher resilience.
- **Heuristic Algorithm (Informed by Davis et al. 2012; Liebman & Dyck 1993):**
  - $\text{Sub}_1 = \max(0, 100 - (\text{max\_run} - 1) \times 20)$
  - $\text{Sub}_2 = \min(100, \text{distinct\_crops} \times 25)$
  - $\text{Sub}_3 = \min(100, \frac{H'}{1.386} \times 100)$
  - Heuristic weighting: $0.40 \times \text{Sub}_1 + 0.30 \times \text{Sub}_2 + 0.30 \times \text{Sub}_3$.

#### Component 5: Vegetation Stability (`vegetation_stability`)
- **Input:** Peak NDVI interannual CV (`ndvi_peak_cv`). Support class **`F`**.
- **Scoring Direction:** Lower CV $\to$ Higher buffering $\to$ Higher score.
- **Breakpoint Table (Heuristic thresholds informed by Pettorelli et al. 2005):**
  $\le 0.08 \to 100$; $0.15 \to 75$; $0.25 \to 45$; $\ge 0.40 \to 10$.
- Missing Data: Evaluates to `score: null` with `INSUFFICIENT_COVERAGE` when HLS credentials are unconfigured.

### 6.2 Composite Resilience Calculation Rules
1. **Minimum Component Quorum:** The composite score is computed **if and only if at least 4 of the 5 components are valid**. If fewer than 4 components are available, `composite.score` is `null`, `band` is `"unknown"`, and `status = "insufficient_data"`.
2. **Aggregation:**
   $$\text{Score}_{\text{composite}} = \frac{1}{N_{\text{valid}}} \sum_{i \in \text{valid}} \text{Score}_i$$
3. **Resilience Bands:**
   - $\text{Score} < 40$: `"low"`
   - $40 \le \text{Score} \le 70$: `"moderate"`
   - $\text{Score} > 70$: `"high"`
   - Insufficient quorum: `"unknown"`
4. **Confidence Bounding:**
   - Component confidence is `"high"` for Support Class `F` with completeness $\ge 0.90$.
   - Component confidence is `"low"` for Support Class `R` (e.g. Climate Exposure).
   - Composite confidence is the lowest confidence of any valid component used (regional data explicitly bounds composite certainty).
