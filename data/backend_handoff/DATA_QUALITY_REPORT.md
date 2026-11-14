# SOILSTICE — Data Quality & Integrity Report

**Dataset Version:** `1.4.1-REMEDIATED`  
**Evaluation Target:** Canonical 14-Crop Agricultural Intelligence Knowledge Base  
**Audit Harness:** `backend_handoff/validation/validate_handoff.py`  
**Execution Timestamp:** 2026-11-14T15:20:00Z  
**Overall Structural Quality Score:** **100% (10/10 Verification Checks Passed)**  
**Overall Readiness Verdict:** **READY WITH DOCUMENTED LIMITATIONS**  

---

## 1. Executive Summary & Epistemological Framework

This data quality report provides an exhaustive, multi-dimensional audit of the **SOILSTICE Crop Knowledge Base** packaged for backend production integration.

### Fundamental Epistemological Distinction:
In agricultural intelligence systems, **structural completeness** must never be conflated with **zero scientific uncertainty**:
1. **Structural Completeness (100%):** Every required domain, schema property, crop ID, evidence reference, and rotation pair is structurally present, type-safe, and valid against Draft-07 JSON Schema specifications.
2. **Evidence Traceability (100%):** Every single claim and quantitative range across all 14 crops maps directly to a peer-reviewed journal article, USDA monograph, or university extension bulletin (212 authoritative records, 0 orphaned references).
3. **Scientific Uncertainty & Environmental Conditionality (Documented & Preserved):** Biological crop performance is inherently variable. Where primary scientific literature lacks standardized field measurements (e.g. whole-system net soil organic N accumulation under green manures), the dataset preserves **legitimate `null` values** and detailed limitation strings rather than generating speculative pseudo-data.

---

## 2. Crop Portfolio Coverage Summary

The knowledge base achieves 100% portfolio coverage across the 14 canonical agricultural crops of the United States. Zero skeleton or unresearched crop entities exist.

| Crop ID | Common Name | Scientific Name | Botanical Family | Production Category | Researched Domains | Schema Conformance |
|---|---|---|---|---|---|---|
| **CRP001** | Corn (Maize) | *Zea mays* L. | Poaceae | Primary Cash Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP002** | Soybean | *Glycine max* (L.) Merr. | Fabaceae | Primary Cash Oilseed | 11 / 11 (100%) | Valid Draft-07 |
| **CRP003** | Winter Wheat | *Triticum aestivum* L. | Poaceae | Cool-Season Cash Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP004** | Spring Wheat | *Triticum aestivum* L. | Poaceae | Cool-Season Cash Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP005** | Grain Sorghum | *Sorghum bicolor* (L.) Moench | Poaceae | Summer Drought Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP006** | Cotton | *Gossypium hirsutum* L. | Malvaceae | Primary Cash Fiber | 11 / 11 (100%) | Valid Draft-07 |
| **CRP007** | Rice | *Oryza sativa* L. | Poaceae | Wetland Cash Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP008** | Barley | *Hordeum vulgare* L. | Poaceae | Cool-Season Cash Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP009** | Cereal Rye | *Secale cereale* L. | Poaceae | Overwintering Cover / Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP010** | Oats | *Avena sativa* L. | Poaceae | Spring Nurse / Grain | 11 / 11 (100%) | Valid Draft-07 |
| **CRP011** | Alfalfa | *Medicago sativa* L. | Fabaceae | Perennial Forage Legume | 11 / 11 (100%) | Valid Draft-07 |
| **CRP012** | Hairy Vetch | *Vicia villosa* Roth | Fabaceae | Winter Legume Cover | 11 / 11 (100%) | Valid Draft-07 |
| **CRP013** | Crimson Clover | *Trifolium incarnatum* L. | Fabaceae | Winter Legume Cover | 11 / 11 (100%) | Valid Draft-07 |
| **CRP014** | Oilseed Radish | *Raphanus sativus* L. | Brassicaceae | Bio-Drilling Catch Crop | 11 / 11 (100%) | Valid Draft-07 |

- **Total Canonical Crops:** Exactly 14.
- **Top-Level Domains per Crop:** Exactly 11 uniform domains across all 14 profiles.
- **Unexpected Extra Entities:** 0.

---

## 3. Evidence Registry Coverage & Traceability

The evidence registry spans **exactly 212 authoritative records** (`EV0001` through `EV0212`), strictly sequential with zero gaps or duplicates.

### Evidence Breakdown by Crop Allocation:
- **CRP001 (Corn):** EV0001–EV0018 (18 records)
- **CRP002 (Soybean):** EV0019–EV0036 (18 records)
- **CRP003 (Winter Wheat):** EV0037–EV0054 (18 records)
- **CRP004 (Spring Wheat):** EV0055–EV0072 (18 records)
- **CRP005 (Grain Sorghum):** EV0073–EV0086 (14 records)
- **CRP006 (Cotton):** EV0087–EV0100 (14 records)
- **CRP007 (Rice):** EV0101–EV0114 (14 records)
- **CRP008 (Barley):** EV0115–EV0128 (14 records)
- **CRP009 (Cereal Rye):** EV0129–EV0142 (14 records)
- **CRP010 (Oats):** EV0143–EV0156 (14 records)
- **CRP011 (Alfalfa):** EV0157–EV0170 (14 records)
- **CRP012 (Hairy Vetch):** EV0171–EV0184 (14 records)
- **CRP013 (Crimson Clover):** EV0185–EV0198 (14 records)
- **CRP014 (Oilseed Radish):** EV0199–EV0212 (14 records)

### Traceability Metrics:
- **Total Registered Evidence Records:** 212.
- **Attribute Cross-References Checked:** 194 unique evidence associations in crop profiles.
- **Unresolved Cross-References:** **0 (0.0% failure rate)**.
- **Orphaned Evidence Records:** 0 (all 212 records are referenced in crop profiles or rotation matrices).
- **Primary Source Quality:** 100% peer-reviewed journals, USDA-ARS/NRCS publications, and university extension research bulletins.

---

## 4. Rotation Matrix Completeness & Directional Integrity

The directed crop rotation compatibility matrix comprises **all 196 possible transitions ($14 \times 14$)**:

- **Total Directed Transitions:** 196 rows in `data/crop_rotation_compatibility.csv`.
- **Predecessor Coverage:** All 14 crops appear exactly 14 times as preceding crop.
- **Successor Coverage:** All 14 crops appear exactly 14 times as following crop.
- **Continuous Monocultures:** Exactly 14 transitions where predecessor equals successor (`is_monoculture: true`).

### Distribution of Compatibility Ratings:
| Compatibility State | Count | Percentage | Agronomic Meaning |
|---|---|---|---|
| `highly_compatible` | 38 | 19.4% | High positive synergy (e.g. Legume $\rightarrow$ Corn, Radish $\rightarrow$ Corn). |
| `compatible` | 96 | 49.0% | Standard agronomic rotation with normal management. |
| `caution_conditional` | 58 | 29.6% | Feasible sequence requiring specific conditional management (e.g. Alfalfa replanting autotoxicity, continuous monocultures, or cover crop mixture/sequential distinctions). |
| `unknown` | 4 | 2.0% | Non-standard sequences lacking empirical field documentation (e.g. Rice following dryland cover crops). |
| `incompatible` | 0 | 0.0% | No absolute universal biological impossibilities (all severe risks carry conditional management). |
| `prohibited` | 0 | 0.0% | No statutory quarantine prohibitions exist across the 14-crop canonical matrix. |
| **Total** | **196** | **100.0%** | Full directed coverage. |

### Directional Non-Reciprocity Audited:
Confirmed that asymmetric transitions (such as Radish $\rightarrow$ Corn vs Corn $\rightarrow$ Radish) preserve directional differences without erroneous reciprocal mirroring.

---

## 5. Missing-Value & Null Profile Analysis

Null values in the knowledge base are **strictly intentional and semantically informative**:

### Intentional Null Patterns:
1. **Net Soil Nitrogen Balance in Green Manures & Catch Crops (`CRP012`, `CRP013`, `CRP014`):**
   - Populated as `null` with comprehensive boundary notes.
   - *Epistemological Rationale:* Decouples unmeasured whole-system net soil organic nitrogen change from gross biological fixation ($70\text{--}200\text{ kg N/ha}$) and mineral nitrate profile recycling ($100\text{--}220\text{ kg N/ha}$).
2. **Point Estimates on Biologically Variable Ranges:**
   - In attributes such as `seasonal_consumptive_water_use_etc_mm`, `effective_water_extraction_depth_cm`, and `active_growth_duration_days`, the `value` field is `null` while `min_value` and `max_value` define the empirical range.
   - *Epistemological Rationale:* Plants are biological organisms, not static machine parts; forcing a single point estimate obscures true phenotypic plasticity.
3. **Irrigation on Purely Rainfed Systems:**
   - `net_irrigation_requirement_mm` is `null` or `0.0` for non-irrigated cover crops.

---

## 6. Unit Validation & Quantitative Consistency

All quantitative attributes comply with the standard units specified in `data/schema.json` and `documentation/DATA_DICTIONARY.md`:

- **Thermal Units:** Degrees Celsius (`celsius`).
- **Hydrological Depths:** Millimeters (`mm`) and Millimeters per day (`mm_per_day`).
- **Soil & Root Depths:** Centimeters (`cm`).
- **Nutrient Application & Removal:** Kilograms per hectare (`kg_per_ha`), Kilograms of nitrogen per hectare (`kg_n_per_ha`), Kilograms of $P_2O_5$ per hectare, Kilograms of $K_2O$ per hectare.
- **Fertilizer Customary Equivalents:** Pounds of nitrogen per acre (`lb_n_per_acre`).
- **Salinity:** Decisiemens per meter (`ds_m` / `dS/m`).
- **Mechanical Pressure:** Megapascals (`MPa`).

### Range Ordering Audit:
Every quantitative attribute containing `min_value` and `max_value` across all 14 crops was evaluated:
$$\text{min\_value} \le \text{max\_value}$$
- **Range Ordering Violations:** **0** across all 14 crop profiles.

---

## 7. CSV Projection Synchronization

All three CSV projections were audited against the authoritative JSON master:

| File Name | Projected Entity | Header Lines | Data Rows | JSON Master Source | Sync Status |
|---|---|---|---|---|---|
| `data/crop_attributes.csv` | Core Crop Attributes | 1 | 14 | `kb["crops"]` | **100% SYNCHRONIZED** |
| `data/crop_rotation_compatibility.csv` | Directed Transitions | 1 | 196 | Rotation Matrix Engine | **100% SYNCHRONIZED** |
| `data/crop_evidence.csv` | Evidence Registry | 1 | 212 | `kb["evidence_registry"]` | **100% SYNCHRONIZED** |

- In `data/crop_attributes.csv`, null values (such as `CRP012`, `CRP013`, and `CRP014` net soil N balance) are consistently projected as empty strings (`""`).
- Row counts, column names, and field values correspond perfectly across formats.

---

## 8. Cryptographic Hash Integrity Verification

Cryptographic SHA-256 hashes were computed for all packaged source files and verified against `validation/file_hashes.sha256`:

| Packaged File Path | File Size (Bytes) | SHA-256 Digest | Original Source Match |
|---|---|---|---|
| `data/crop_knowledge_base.json` | 1,160,056 | `907e95e3e7769bb28b68bcd9ff7812c8a71f7e527aa38c19d6f821302bb0aaf4` | **IDENTICAL** |
| `data/schema.json` | 45,492 | `94ffbde1a8a2f9ac64617a4763f2ea390ab14b6b47e0675ddb3603106b6cedc3` | **IDENTICAL** |
| `data/crop_attributes.csv` | 13,960 | `51bb1d2f652e532c47b6820a37a62cf12e2c7201fa82f5fe8f2a343e1abe0280` | **IDENTICAL** |
| `data/crop_rotation_compatibility.csv` | 87,672 | `866193f114bd6ea34b265a55952c15650eb5ac64f884ddeca73c18060dcd92ca` | **IDENTICAL** |
| `data/crop_evidence.csv` | 140,910 | `70d37b00cd352c5809e1f8d94ac0d7ae910bd6569887450beccca949e5f66aaa` | **IDENTICAL** |
| `documentation/SOURCE_REGISTER.md` | 16,423 | `cdc5e69d0f798cdd883a04978930fe6c09ba88440b8e8c8d2834b54b4650446c` | **IDENTICAL** |
| `documentation/DATA_DICTIONARY.md` | 30,050 | `3c91e12d3c78709d074f42ecfc5c5a39a0d7df1e184bb70ca8daae038e599073` | **IDENTICAL** |

Zero bytes were altered during packaging and handoff staging.

---

## 9. Unresolved Scientific Limitations & Known Boundaries

The following known agronomic boundaries must be respected during backend application design:

1. **Cover Crop Nitrogen Leaching Asynchrony:** Rapid mineralization of winter-killed radish releases nitrate in March–April, creating leaching vulnerability on coarse sandy soils if subsequent corn is not planted until May. Recommendation engines should pair radish with cereal rye on well-drained sands.
2. **Compaction Alleviation Operational Constraints:** Radish taproot bio-drilling penetrates plow pans exceeding 2.0 MPa, but fails in waterlogged, smeared, or severely rutted soils. Seeding must occur $\ge 6\text{--}8\text{ weeks}$ before the first killing freeze.
3. **Root-Knot Nematode Host Risks:** Crimson clover is a susceptible host to Southern Root-Knot Nematode (*Meloidogyne incognita*; `EV0196`), requiring advisory alerts ahead of susceptible cotton or vegetable crops on Coastal Plain sands.
4. **Mixture vs. Sequential Disconnect:** Cover crop polycultures (clover + radish) are highly synergistic when sown together, but direct sequential monoculture rotations leave severe seasonal fallow gaps.

---

## 10. Final Verification Verdict

### **VERDICT: READY WITH DOCUMENTED LIMITATIONS**

The dataset meets all criteria for structural completeness, schema compliance, cryptographic integrity, and bibliographic traceability. Backend engineers may proceed with integration, adhering strictly to the safeguards detailed in [`SCIENTIFIC_LIMITATIONS.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/SCIENTIFIC_LIMITATIONS.md).
