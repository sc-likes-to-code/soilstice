# SOILSTICE — Scientific Limitations & Backend Safeguards

**Target Audience:** Backend Developers, ML Engineers, Agronomic Modelers, Algorithm Authors  
**Dataset Version:** `1.4.1-REMEDIATED`  
**Purpose:** Mandatory agronomic rules, boundary conditions, and computation safeguards for backend software systems  

---

## 1. Executive Warning & Guiding Principle

The **SOILSTICE Crop Knowledge Base** reflects rigorous, peer-reviewed agronomic science and empirical field trials from U.S. land-grant universities and the USDA-ARS. However, agricultural biological systems are fundamentally complex, open-ended, and sensitive to local weather, soil physical structure, microbiological ecology, and grower management.

> [!WARNING]
> **AGRONOMIC MODELS ARE CONDITIONAL, NOT DETERMINISTIC.**  
> Backend algorithms, suitability scoring pipelines, and rotation recommendation engines must **never treat empirical experimental findings as universal farm guarantees**. All backend calculations must respect the boundaries, distinctions, and safeguard rules established in this document.

---

## 2. Null Value Semantics & Arithmetic Safeguards

### The Core Invariant
**A `null` value in this dataset indicates that an attribute is scientifically unmeasured, unverified under standardized field conditions, or deliberately decoupled to prevent inaccurate environmental accounting.**

### Developer Safeguard Rules:
1. **Never coerce `null` to `0.0`:**
   - In SQL databases, pandas DataFrames, or backend DTOs, never use `.fillna(0)` or `COALESCE(field, 0.0)` for biological balances.
   - Setting a `null` nitrogen balance or water requirement to `0.0` causes recommendation engines to misinterpret an unknown or unmeasured balance as a proven zero balance.
2. **Distinguish `0.0` from `null`:**
   - `0.0 kg N/ha BNF`: Proven physiological lack of rhizobial symbiosis (e.g. Corn, Oilseed Radish).
   - `null net_soil_nitrogen_balance_kg_ha`: Whole-system net soil organic nitrogen change is unmeasured.
3. **Propagate Nulls in Scoring Algorithms:**
   - When calculating composite soil fertility indices or nitrogen credits, if a component value is `null`, the algorithm must flag the result as *partially quantified* and surface the limitation string rather than computing an erroneous sum.

---

## 3. Nitrogen Accounting Architecture & Distinctions

Nitrogen is dynamic, mobile, and subject to multiple gaseous and aqueous loss pathways. The dataset maintains strict separation between eight distinct nitrogen metrics. Backend developers must never conflate them:

```text
 atmospheric N2
       │
       ▼ (1. Biological N Fixation - Legumes Only)
  Plant Biomass ◄─── (2. Soil N Uptake / Scavenging - Catch Crops)
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
 (3. Harvest Export)            (4. Residue N Returned)
  Leaves field with grain/hay    Decomposes on/in soil
                                         │
                                         ▼ (Mineralization: NH4+ -> NO3-)
                                 ┌───────┴───────┐
                                 ▼               ▼
                        (Crop Available)   (Environmental Losses:
                        (5. Successor      Volatilization NH3,
                         Fertilizer        Denitrification N2O,
                         Credit)           Leaching NO3-)
                                                 │
                                                 ▼
                                        (6. Net Soil Organic N:
                                         Humified recalcitrant pool)
```

### Critical Nitrogen Safeguard Rules:
1. **Gross Biological Nitrogen Fixation (`total_gross_n_fixed_kg_ha`) IS NOT Net Soil Enrichment:**
   - *Crimson Clover (`CRP013`):* Fixes 70–150 kg N/ha of atmospheric $N_2$ into plant tissue at full bloom (`EV0191`).
   - *Hairy Vetch (`CRP012`):* Fixes 90–200 kg N/ha (`EV0172`).
   - *The Trap:* A backend developer must **not** assume the soil organic nitrogen pool increases by +70 to +200 kg N/ha. Upon termination, rapid mineralization of low C:N succulent residue releases mineral ammonium and nitrate, substantial fractions of which are lost via ammonia volatilization, microbial denitrification, or leaching before succeeding cash crop roots take it up.
   - *Enforcement:* `net_soil_nitrogen_balance_kg_ha` is populated as **`null`** with explicit calculation boundary limitations.
2. **Oilseed Radish (`CRP014`) Nitrate Scavenging IS NOT Newly Added Nitrogen:**
   - Oilseed radish is a non-legume brassica (`has_symbiotic_fixation_capacity: False`; `0.0 kg N/ha BNF`; `EV0199`).
   - It captures **100–220 kg N/ha (100–200 lb N/ac)** of residual mineral nitrate from the upper 1.5 m soil profile (`EV0206`).
   - *The Trap:* This 100–220 kg N/ha is **internal profile nutrient recycling**, NOT newly added biological nitrogen. The radish took it from the soil; it did not fix it from the air.
   - *Enforcement:* Additive biological fertilizer credit is strictly **`0.0 lb N/ac`**.
   - *Effective Rotational Credit:* Rapid spring mineralization of recycled radish tissue provides an effective rotational benefit of **20–40 lb N/ac** to subsequent corn *if and only if* captured by corn roots before spring leaching occurs.
3. **Partial Accounting Cannot Serve as Complete Fertilizer Recommendations:**
   - Values in `net_soil_nitrogen_balance_kg_ha` (such as $-150\text{ to }-220\text{ kg N/ha}$ in corn grain export) reflect only the partial aboveground harvest removal boundary ($0.0\text{ BNF} - \text{harvest export}$). They **exclude** soil organic matter mineralization, atmospheric deposition, and fertilizer applications.
   - Recommendation engines must not use partial harvest removal figures as direct farm fertilizer prescriptions.

---

## 4. Root Architecture & Depth Boundaries

The dataset provides two distinct root metrics:
1. **Effective Water Extraction Depth (`effective_water_extraction_depth_cm`):**
   - The primary soil horizon containing $>70\text{--}80\%$ of active root surface area where the majority of transpiration water is extracted (typically 40–100 cm).
   - Use this metric for routine soil water balance, daily irrigation scheduling, and topsoil drought vulnerability modeling.
2. **Maximum Anatomical Root Depth (`maximum_anatomical_root_depth_cm`):**
   - The deepest vertical penetration reached by pioneering secondary taproots under optimal, unconstrained, deep permeable loess or silt loam soils (e.g. 150–240 cm in radish or corn; Weaver 1926).
   - Use this metric for evaluating deep subsoil moisture access during severe summer terminal drought.

### Developer Safeguard:
**Do not assume maximum anatomical root depth is achieved under every soil condition.**  
Anatomical penetration is severely truncated by:
- Dense subsoil plow pans or fragipans ($>2.5\text{--}3.5\text{ MPa}$).
- Shallow bedrock or petrocalcic horizons.
- High water tables or waterlogged anaerobic subsoils.
- Acidic subsoils ($\text{pH} < 5.0$ with toxic soluble aluminum).

---

## 5. Hydrological & Water Requirement Boundaries

Backend irrigation and suitability engines must distinguish five independent water domains:
1. **Seasonal Consumptive Water Use ($ET_c$):** Total crop evapotranspiration under non-stressed, well-watered conditions.
2. **Seasonal Precipitation Requirements:** Natural rainfall required for rainfed commercial production.
3. **Net Irrigation Requirement:** Net supplemental depth required beyond effective rainfall and soil storage.
4. **Drought Tolerance:** Categorical ability to survive temporary soil moisture deficits without mortality.
5. **Waterlogging Tolerance:** Physiological susceptibility to crown rot and anoxia in saturated/ponded soils.

### Developer Safeguard:
**Never substitute rainfall requirements for irrigation requirements.**  
Rainfall distribution efficiency is significantly lower than micro-irrigation; rainfed crops in sub-humid regions require 500–800 mm of annual rainfall to supply 400 mm of $ET_c$ due to runoff and deep drainage losses.

---

## 6. Temperature Thresholds & Physiological Context

Temperature parameters in `temperature_requirements` must be interpreted with growth-stage, exposure-duration, and insulation caveats:

1. **Exposure Duration Matters:**
   - *Example: Oilseed Radish Winter-Kill (`EV0201`):* Complete root collapse occurs at $-6.0^\circ\text{C}\text{ to }-9.0^\circ\text{C}$ ($21\text{ to }15^\circ\text{F}$), but requires **sustained exposure for $\ge 4\text{ to }6\text{ hours}$**. Brief radiation dips to $-5^\circ\text{C}$ burn leaves but leave fleshy roots alive.
2. **Insulation & Snow Cover Conditioning:**
   - *Example: Crimson Clover Hardiness (`EV0187`):* Absolute minimum survival of $-12^\circ\text{C}\text{ to }-15^\circ\text{C}$ requires **continuous insulating snow cover**. On bare soil, lethal crown mortality occurs at $-10^\circ\text{C}$ to $-12^\circ\text{C}$.
   - *Example: Cereal Rye (`EV0135`):* Survives $-35^\circ\text{C}$ air temperatures under deep snow, but bare crown $LT_{50}$ is $-24^\circ\text{C}$ to $-25.5^\circ\text{C}$.
3. **Regional Adaptation & Non-Extrapolation:**
   - In USDA Hardiness Zones 8b–9 (Deep South, coastal California), radish **does not reliably winter-kill**, requiring growers to plan mechanical mowing or chemical burndown.

---

## 7. Rotational Compatibility & Legal vs. Biological Boundaries

### Rating Definitions
- `highly_compatible`: High biological synergy; recommended sequence.
- `compatible`: Standard agronomic sequence with standard pest/weed management.
- `caution_conditional`: Feasible sequence requiring specific conditional management.
- `incompatible`: Severe disease/autotoxicity/rotational penalty.
- `prohibited`: **Strictly reserved for legal quarantine or herbicide-label plant-back mandates.**
- `unknown`: Unstudied or non-standard combination lacking primary field evidence.

### Developer Safeguard:
**Do not assign `prohibited` based on biological disease risk alone.**  
- *Clubroot (*Plasmodiophora brassicae*) in Oilseed Radish:* Radish is a susceptible host. Rotating radish with canola or cabbage in fields with a history of Clubroot or low soil pH ($\text{pH} < 6.8$) carries high disease risk (`EV0210`).
- *The Distinction:* This is an **agronomic epidemiological risk**, not a statutory prohibition. It is managed via 3–4 year crop breaks and liming ($\text{pH} > 7.0$). It must be rated `caution_conditional`, not `prohibited`.

---

## 8. Cover-Crop Mixtures vs. Sequential Crop Rotations

> [!IMPORTANT]
> **SIMULTANEOUS POLYCULTURE MIXTURES ARE NOT SEQUENTIAL ROTATIONS.**  
> A multi-species cover crop mixture sown together on the same day occupies the **same seasonal window**, whereas a rotation transition implies one crop harvested or terminated before the next is planted.

### The Crimson Clover + Oilseed Radish Case (`CRP013` & `CRP014`):
1. **In Mixtures (`highly_compatible`):** Sowing clover and radish simultaneously in late August is a premier cover crop biculture. Radish bio-drills and scavenges autumn nitrate before winter-killing in January; clover survives winter, fixes 70–150 kg N/ha in spring, and provides erosion control.
2. **In Sequential Monocultures (`caution_conditional`):**
   - `CRP013 -> CRP014`: Crimson clover terminated in May leaves an unmanaged summer fallow gap before radish can be planted in August (May-seeded radish bolts into woody stalks; EV0200).
   - `CRP014 -> CRP013`: Winter-killed radish in December leaves bare soil from January until late-summer clover seeding.
   - **Backend Action:** Rotations between these two crops are classified as `caution_conditional` for sequential monocultures, with mixture synergies preserved under `[MIXTURE NOTE]` tags.

---

## 9. Non-Extrapolation of Conditional Agronomic Outcomes

Backend recommendation engines must not present experimental premiums as universal farm guarantees:
1. **Radish 2–3× Infiltration Enhancement (`EV0203`):** Observed in Maryland silt loam soils with dense plow pans where open decay biopores bridged the impermeable layer (Chen & Weil 2011). On loose sands or well-aggregated virgin prairie soils, infiltration increases are negligible.
2. **Corn 5–10% Yield Bump Following Radish (`EV0203`, `EV0211`):** Measured in compacted no-till soils where corn roots utilized radish biopores to access subsoil water during summer drought. On uncompacted soils or in seasons with abundant rainfall, yield premiums are negligible or absent.
3. **Biofumigation (`EV0209`):** Volatile isothiocyanate (ITC) suppression of soil fungi (*Rhizoctonia*, *Pythium*, *Verticillium*) is strong in laboratory and closed microplots, but highly diffuse and variable under field winter-kill conditions. Biofumigation cannot substitute for commercial fungicides or nematicides.
4. **Early Spring Nitrate Leaching Asynchrony (`EV0208`):** Radish releases 70–80% of captured nitrogen in March–April upon winter-kill thaw. On coarse sandy soils, this mineral nitrate leaches into groundwater before May corn roots can reach it unless paired with an overwintering grass like Cereal Rye (`CRP009`).
