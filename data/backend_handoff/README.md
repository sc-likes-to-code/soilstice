# SOILSTICE — Backend Crop Knowledge Base Handoff Package

**Canonical Dataset Version:** `1.4.1-REMEDIATED`  
**Dataset Name:** SOILSTICE U.S. Agricultural Intelligence & Crop Rotation Knowledge Base  
**Status:** **FROZEN & VERIFIED FOR BACKEND INTEGRATION**  
**Readiness Verdict:** **READY WITH DOCUMENTED LIMITATIONS**  
**Package Generation Date:** 2026-11-14  

---

## 1. Overview & Handoff Purpose

This directory (`backend_handoff/`) contains the complete, self-contained, scientifically vetted agricultural crop knowledge base for the **SOILSTICE** platform. Developed across four iterative research, targeted verification, and controlled remediation phases, this dataset provides the definitive agronomic foundation for backend suitability scoring, rotational compatibility evaluations, environmental constraint checking, and multi-year crop planning.

The dataset covers **exactly 14 canonical agricultural crops** across the contiguous United States, backed by **exactly 212 peer-reviewed and land-grant university evidence records** (`EV0001`–`EV0212`), with **all 196 directed rotation compatibility transitions** ($14 \times 14$) fully populated.

---

## 2. Directory Structure & File Manifest

```text
backend_handoff/
│
├── README.md                     # Package orientation, quickstart, and file index (this file)
├── HANDOFF_MANIFEST.json         # Machine-readable provenance, file inventory, and SHA-256 hashes
├── INTEGRATION_GUIDE.md          # Comprehensive integration manual for backend software engineers
├── API_DATA_CONTRACT.md          # Proposed read-only API contracts, endpoints, and response models
├── SCIENTIFIC_LIMITATIONS.md     # Critical agronomic boundaries, calculations, and safeguard rules
├── DATA_QUALITY_REPORT.md        # Comprehensive data audit, missingness profile, and validation results
├── INTEGRATION_CHECKLIST.md      # Actionable implementation checklist for backend developers
│
├── data/                         # Authoritative data files (frozen)
│   ├── crop_knowledge_base.json  # Primary authoritative JSON master dataset
│   ├── schema.json               # JSON Schema Draft-07 specification
│   ├── crop_attributes.csv       # Flat CSV projection of crop attributes (15 lines: 1 header + 14 crops)
│   ├── crop_rotation_compatibility.csv # Directed rotation pairs (197 lines: 1 header + 196 transitions)
│   └── crop_evidence.csv         # Complete evidence registry projection (213 lines: 1 header + 212 records)
│
├── documentation/                # Evidentiary and dictionary documentation
│   ├── SOURCE_REGISTER.md        # Bibliographic source registry and publication metadata
│   └── DATA_DICTIONARY.md        # Domain definitions, attribute schemas, and measurement types
│
└── validation/                   # Self-contained portability and validation test harness
    ├── validate_handoff.py       # Standalone validation script (zero external dependencies)
    ├── validation_results.json   # Machine-readable output of validation checks
    └── file_hashes.sha256        # Cryptographic checksums of all source files
```

---

## 3. Authoritative Source Hierarchy

When integrating into backend services, microservices, databases, or API caches:

1. **`data/crop_knowledge_base.json` is the SOLE AUTHORITATIVE SOURCE OF TRUTH.**  
   All nested attributes, measurement types, confidence ratings, qualitative descriptions, regional profiles, and attribute-level evidence associations are defined canonically in this JSON file.
2. **`data/schema.json` is the authoritative structural validator.**  
   Enforces Draft-07 JSON Schema conformance across all entities, preventing invalid types, missing keys, or rogue attributes.
3. **CSV files in `data/*.csv` are synchronized projections.**  
   These are provided for relational database bulk imports, tabular BI reporting, and quick inspection. If an attribute is `null` in the JSON master, it is projected as an empty string (`""`) in CSV projections.
4. **Documentation in `documentation/*.md` provides legal and scientific traceability.**  
   Use `SOURCE_REGISTER.md` for primary publication metadata and `DATA_DICTIONARY.md` for attribute definitions and calculation boundaries.

---

## 4. Quickstart for Backend Developers

### Running the Standalone Validation Suite
The handoff package contains a fully self-contained test suite that validates the dataset without requiring connection to the parent repository:

```bash
# From within the backend_handoff/ directory:
python validation/validate_handoff.py

# Or directly from the validation/ directory:
cd validation
python validate_handoff.py
```

Expected output:
```text
================================================================================
SOILSTICE BACKEND HANDOFF VALIDATION SUITE
================================================================================
[CHECK_1_FILE_EXISTENCE] All 8 Required Handoff Source Files Present: PASS
[CHECK_2_SHA256_INTEGRITY] SHA-256 File Hash Integrity Verification: PASS
[CHECK_3_JSON_SCHEMA] JSON Schema Draft-07 Recursive Validation: PASS
[CHECK_4_CANONICAL_CROPS] Canonical 14 Crops & 11 Uniform Domains Integrity: PASS
[CHECK_5_EVIDENCE_REGISTRY] Evidence Registry Continuity EV0001–EV0212 (212 Records): PASS
[CHECK_6_EVIDENCE_RESOLVABILITY] Attribute Evidence Cross-Reference Resolvability (0 Orphaned Refs): PASS
[CHECK_7_ROTATION_MATRIX] Directed Rotation Matrix (196 Transitions, Directional Logic Enforced): PASS
[CHECK_8_QUANTITATIVE_RANGES_AND_NULLS] Quantitative Range Ordering (min <= max) & Legitimate Null Preservation: PASS
[CHECK_9_CSV_SYNCHRONIZATION] CSV Projections Synchronization (Attributes: 15, Rotations: 197, Evidence: 213): PASS
[CHECK_10_DOCUMENTATION] Documentation Governance (Source Register & Data Dictionary Synchronized): PASS
--------------------------------------------------------------------------------
VERIFICATION SUMMARY: 10/10 CHECKS PASSED.
OVERALL STATUS:      PASS
READINESS VERDICT:   READY WITH DOCUMENTED LIMITATIONS
================================================================================
```

---

## 5. Essential Integration Reading Order

Before writing backend code, database loaders, or API endpoints, read the following handoff documents in order:

1. [`SCIENTIFIC_LIMITATIONS.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/SCIENTIFIC_LIMITATIONS.md)  
   **MANDATORY READING:** Critical agronomic guardrails. Explains why `null` must never be coerced to `0.0`, why biological N fixation is not net soil N accumulation, why radish nitrate scavenging is internal recycling rather than newly added N, and why cover crop mixtures must not be conflated with sequential rotations.
2. [`INTEGRATION_GUIDE.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/INTEGRATION_GUIDE.md)  
   Engineering handbook detailing data structures, object typing, unit conversions, directional rotation lookup, and Python/TypeScript parsing patterns.
3. [`API_DATA_CONTRACT.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/API_DATA_CONTRACT.md)  
   Proposed RESTful API specifications, route parameters, response payloads, and error codes for backend service implementation.
4. [`INTEGRATION_CHECKLIST.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/INTEGRATION_CHECKLIST.md)  
   Step-by-step checklist separating completed dataset deliverables from pending backend engineering tasks.
5. [`DATA_QUALITY_REPORT.md`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/DATA_QUALITY_REPORT.md)  
   Detailed data auditing results, missingness statistics, and cryptographic integrity verifications.
6. [`HANDOFF_MANIFEST.json`](file:///c:/My%20D%20Drive/My_Projects/Soilstice/data/processed/crop_knowledge_base/backend_handoff/HANDOFF_MANIFEST.json)  
   Machine-readable metadata, freeze timestamps, and authoritative SHA-256 file hashes.
