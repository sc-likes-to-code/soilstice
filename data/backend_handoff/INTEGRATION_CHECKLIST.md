# SOILSTICE — Backend Integration Checklist

**Document Version:** `1.0.0`  
**Dataset Target:** `1.4.1-REMEDIATED`  
**Audience:** Backend Software Engineers, DevOps Engineers, QA Automation Engineers  

---

## 1. Overview & Separation of Concerns

This checklist cleanly delineates:
- **Phase A: Handoff Deliverables (COMPLETED by Data Engineering & Science Teams).**
- **Phase B: Backend Engineering Implementation Tasks (PENDING execution by Backend Platform Team).**

---

## Phase A: Handoff Verification Checklist (COMPLETED)

- [x] **Canonical Crop Scope:** Exactly 14 canonical crops (`CRP001` to `CRP014`) in immutable canonical order.
- [x] **Schema Completeness:** All 14 crops possess the uniform 11 top-level domains.
- [x] **Schema Validation:** `data/crop_knowledge_base.json` validated 100% against `data/schema.json` (Draft-07).
- [x] **Evidence Continuity:** Exactly 212 evidence records (`EV0001` through `EV0212`) with 0 gaps and 0 duplicates.
- [x] **Cross-Reference Integrity:** 0 orphaned or unresolved evidence references in any crop profile.
- [x] **Rotation Completeness:** All 196 directed pairwise transitions ($14 \times 14$) populated in `crop_rotation_compatibility.csv`.
- [x] **Asymmetric Directionality:** Directional logic enforced; non-reciprocal transitions preserved.
- [x] **CSV Synchronization:** `crop_attributes.csv` (15 lines), `crop_rotation_compatibility.csv` (197 lines), and `crop_evidence.csv` (213 lines) synchronized with the JSON master.
- [x] **Nitrogen Accounting Discipline:** Cover crop net soil nitrogen balances set to `null` with boundary notes; BNF decoupled from net organic N; radish recycling kept separate from new N addition.
- [x] **De-escalation of Brassica Prohibitions:** Replaced absolute prohibitions with conditional epidemiological management (Clubroot).
- [x] **Mixture vs. Sequential Disconnect:** Clarified mixture polycultures vs. sequential monocultures (`CRP013 <-> CRP014` rated `caution_conditional` with `[MIXTURE NOTE]` tags).
- [x] **Outcome Qualifications:** Infiltration (2–3×), corn yield bump (5–10%), deep root penetration, and biofumigation qualified with environmental boundaries.
- [x] **Cryptographic Hash Manifest:** `validation/file_hashes.sha256` generated and verified.
- [x] **Standalone Test Harness:** `validation/validate_handoff.py` authored and tested (10/10 checks passing).

---

## Phase B: Backend Implementation Checklist (PENDING BACKEND TEAM)

### 1. Ingestion & Storage Pipeline
- [ ] **Master File Loader:** Implement JSON loader for `data/crop_knowledge_base.json` upon application initialization.
- [ ] **Schema Pre-Flight Check:** Integrate `data/schema.json` into application startup or CI/CD pre-deployment test suite.
- [ ] **Database / In-Memory Indexing:**
  - [ ] Primary index on `crop_id` (`CRP001`–`CRP014`).
  - [ ] Primary index on `evidence_id` (`EV0001`–`EV0212`).
  - [ ] Composite primary index on `(preceding_crop_id, following_crop_id)` for the 196 rotation pairs.
- [ ] **Hash Verification on Deployment:** Execute `validation/validate_handoff.py` as a pre-boot container health check or build step.

---

### 2. Data Interpretation & Safeguard Enforcement
- [ ] **Strict Null Preservation:**
  - [ ] Verify that ORM models (SQLAlchemy, Prisma, Hibernate) preserve `null` as `None` / `null` / `nil`.
  - [ ] Ensure serialization to JSON does not omit null fields or coerce them to `0` or `""`.
  - [ ] Verify that `net_soil_nitrogen_balance_kg_ha` is returned as `null` for `CRP012`, `CRP013`, and `CRP014`.
- [ ] **Nitrogen Balance Logic:**
  - [ ] Ensure scoring algorithms do not treat `total_gross_n_fixed_kg_ha` as a direct soil organic nitrogen addition.
  - [ ] Ensure recommendation logic does not treat radish scavenged nitrate ($100\text{--}220\text{ kg N/ha}$) as newly fixed nitrogen.
  - [ ] Do not use partial nitrogen accounting as a commercial synthetic fertilizer recommendation without consulting soil test mineral N ($NO_3^-\text{--N}$).
- [ ] **Root Depth Modeling:**
  - [ ] Use `effective_water_extraction_depth_cm` for topsoil drought modeling and daily irrigation scheduling.
  - [ ] Use `maximum_anatomical_root_depth_cm` only when evaluating deep subsoil moisture access under unconstrained profiles.
- [ ] **Hydrological Distinctions:**
  - [ ] Keep `seasonal_consumptive_water_use_etc_mm` separate from `seasonal_precipitation_min_mm` and `net_irrigation_requirement_mm`.
- [ ] **Directed Rotation Lookup:**
  - [ ] Verify that rotation queries always enforce directionality: `query_rotation(preceding, following)` must NOT default to `query_rotation(following, preceding)`.
  - [ ] Implement query logic for `[MIXTURE NOTE]` tags when users plan simultaneous polycultures rather than sequential monocultures.
- [ ] **Surfacing Limitations:**
  - [ ] Include attribute `limitations` strings in API payloads to allow frontend display of scientific caveats and management advice.

---

### 3. API Endpoints & Contract Conformance
- [ ] Implement `GET /api/crops`: List all 14 crops with basic identity and role metadata.
- [ ] Implement `GET /api/crops/{crop_id}`: Return complete 11-domain crop entity.
- [ ] Implement `GET /api/crops/{crop_id}/attributes`: Query filtered domain or specific attribute.
- [ ] Implement `GET /api/rotations?previous_crop={id}&next_crop={id}`: Return directed transition record.
- [ ] Implement `GET /api/evidence/{evidence_id}`: Return authoritative bibliographic evidence record.

---

### 4. QA & Negative Testing Suite
- [ ] **Invalid Crop ID:** Test `GET /api/crops/CRP999` returns `404 Not Found` with structured error code `CROP_NOT_FOUND`.
- [ ] **Invalid Evidence ID:** Test `GET /api/evidence/EV9999` returns `404 Not Found` with structured error code `EVIDENCE_NOT_FOUND`.
- [ ] **Malformed Query:** Test `GET /api/rotations?previous_crop=CRP001` (missing `next_crop`) returns `400 Bad Request`.
- [ ] **Null Response Integrity:** Verify API output for `GET /api/crops/CRP014/attributes?domain=nitrogen_and_biomass` returns `"net_soil_nitrogen_balance_kg_ha": {"value": null}`.
- [ ] **Directional Test Case:** Assert `GET /api/rotations?previous_crop=CRP014&next_crop=CRP001` returns `highly_compatible`, while reverse query `previous_crop=CRP001&next_crop=CRP014` returns `compatible`.
- [ ] **Mixture Test Case:** Assert `GET /api/rotations?previous_crop=CRP013&next_crop=CRP014` returns `caution_conditional` with limitations explaining the sequential monoculture disconnect.

---

### 5. Version Governance & Future Updates
- [ ] **Dataset Version Header:** Ensure all API responses include `X-Dataset-Version: 1.4.1-REMEDIATED` or include it in the response body envelope.
- [ ] **Release Update Protocol:** When updating to a future dataset release:
  1. Validate incoming files with `validate_handoff.py`.
  2. Verify SHA-256 hashes against `file_hashes.sha256`.
  3. Deploy using zero-downtime database migrations or blue-green container updates.
