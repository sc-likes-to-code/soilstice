# SOILSTICE Environmental Pipeline Health Report

**Generated:** 2026-11-15T14:50:43.140656+00:00  
**Summary:** Total: 9 | PASS: 8 | FAIL: 0 | WARN: 1 | SKIPPED: 0

## Diagnostic Checks

| Capability | Check Name | Status | HTTP | Details |
|---|---|:---:|:---:|---|
| Configuration | Meteomatics Credentials Check | **PASS** | — | Credentials found in environment (Username: ha***, Password: [REDACTED]). |
| Provider Connectivity | Meteomatics Authentication & Reachability | **PASS** | 200 | HTTP Basic Authentication succeeded against https://api.meteomatics.com. |
| Provider Core | Minimal Valid Provider Request | **PASS** | 200 | Minimal valid request (elevation:m) succeeded and returned valid data. |
| Soil Hydrology | Multi-Depth Soil Moisture Pipeline | **PASS** | — | All 4 depth parameters successfully retrieved with valid volumetric water values. |
| Terrain Processing | Elevation & Conditional Slope Pipeline | **PASS** | — | Elevation successfully retrieved (482.0 m). Conditional slope derivation validated. |
| Vegetation Monitoring | Regional NDVI Pipeline | **WARN** | — | Meteomatics sat_ndvi:idx is geographically restricted to Himawari satellite domain (90°E–180°E). Kansas is outside footprint; pipeline handles as UNAVAILABLE. |
| Climate Monitoring | NASA POWER Climate Integration | **PASS** | — | NASA POWER Daily AG client initialized; endpoints & community parameters validated. |
| Soil Properties | USDA NRCS SSURGO Soil Integration | **PASS** | — | SSURGO Tabular SDA client initialized; component/horizon SQL templates verified. |
| API Governance | API Contract & Schema Validation | **PASS** | — | All unified environmental metrics, vocabularies, and schemas are strictly aligned. |

## Credential Instructions

To enable live Meteomatics queries for real farm fields:
1. Open `backend/.env` (created from `backend/.env.example`).
2. Add your credentials:
   ```bash
   METEOMATICS_USERNAME=your_username_here
   METEOMATICS_PASSWORD=your_password_here
   ```
3. Re-run `npm run diagnostics:environment` to verify live authentication.

*(Note: Real credentials are never logged or exposed in client bundles).* 
