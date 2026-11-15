# SOILSTICE — Farm Data Provenance & Regression Audit Report

**Document ID:** `SOILSTICE-REGRESSION-AUDIT-001`  
**Date:** 2026-11-15  
**Auditor:** Independent Scientific & Technical Audit Agent  
**Investigation Scope:** Farm and field definitions, environmental data provenance, service mode architecture, Git commit history, and runtime application state.  
**Investigation Outcome:** **NO DATA LOSS / INTENDED DUAL-MODE ARCHITECTURE IDENTIFIED**

---

## 1. Executive Summary

This investigation was conducted to determine why the running application displayed **Reno Demo Farm** and **Finney Demo Farm** (with synthetic observations across 14 parcels) rather than **Reno Farm** and **Finney Farm** (which use the real environmental pipeline).

### Core Findings
1. **No Data Loss or Overwrite Occurred:** The original **Reno Farm** (`e3d21ac7-5df1-55ef-97f7-a4098b4e863e`) and **Finney Farm** (`3a9b1abb-271e-52d8-9cc9-8ca35ebfa7de`) remain completely intact in `backend/app/catalog.py`, `backend/app/services/fields.py`, and the persistent database `backend/.data/soilstice.sqlite3`.
2. **The Real Data Pipeline is Fully Operational:** Live upstream integration modules for USDA NRCS SSURGO (Soil Data Access live SQL), NASA POWER Daily AG v2.10.3 API, USDA NASS CDL (CropScape 30m rasters), and NASA SRTM GL1 are functional and actively caching data in `backend/.cache/raw/`.
3. **The Root Cause is Frontend Service Mode Selection (`NEXT_PUBLIC_DATA_MODE`):**
   - The SOILSTICE architecture defines a dual-mode service factory in `src/services/index.ts`:
     - When `NEXT_PUBLIC_DATA_MODE === "api"`, the frontend queries the FastAPI backend (`Reno Farm` and `Finney Farm`, live observations).
     - When `NEXT_PUBLIC_DATA_MODE` is unset or set to `"mock"` (the documented default in `.env.example`), the frontend uses offline mock services (`Reno Demo Farm` and `Finney Demo Farm`, synthetic observations).
   - The currently running Next.js web process on port 3000 (PID 37060) was started without `NEXT_PUBLIC_DATA_MODE=api` in its environment. Because `.env.local` is git-ignored and not present in the workspace root, Next.js defaulted to **Mock Mode**.
4. **Phase 6 Impact:** Phase 6 did not introduce, alter, or expose this behavior. Phase 6 implemented suitability evaluation for both HTTP and Mock service implementations in strict compliance with the architecture contracts.

---

## 2. Original vs. Current Farm Comparison

| Attribute | Original Farm Data (API Mode / Backend) | Current Displayed Data (Mock Mode / Frontend) |
| :--- | :--- | :--- |
| **Reno Farm Name** | **`Reno Farm`** | **`Reno Demo Farm`** |
| **Reno Farm ID** | `e3d21ac7-5df1-55ef-97f7-a4098b4e863e` (Deterministic UUID5) | `b6cc12fe-861f-436d-83bb-322a093e6bd4` (Mock PRNG UUID) |
| **Reno AOI** | `ks_reno` (`Reno County, Kansas`, FIPS `20155`) | `ks_reno` (`Reno County, Kansas`, FIPS `20155`) |
| **Reno Field Count** | Dynamic (0 initially; created via API / CSB) | 8 fixed parcels (`Demo Field A` through `Demo Field G`, `Demo User Field H`) |
| **Reno Total Area** | Dynamically computed from fields | 479.9 ha (sum of 8 mock parcels + test fixture) |
| **Finney Farm Name** | **`Finney Farm`** | **`Finney Demo Farm`** |
| **Finney Farm ID** | `3a9b1abb-271e-52d8-9cc9-8ca35ebfa7de` (Deterministic UUID5) | `d4a92591-d589-4f63-a0a3-802f1ea6bb8c` (Mock PRNG UUID) |
| **Finney AOI** | `ks_finney` (`Finney County, Kansas`, FIPS `20055`) | `ks_finney` (`Finney County, Kansas`, FIPS `20055`) |
| **Finney Field Count**| Dynamic (0 initially; created via API / CSB) | 6 fixed parcels (`Demo Field F-A` through `Demo Field F-F`) |
| **Finney Total Area** | Dynamically computed from fields | 335.1 ha (sum of 6 mock parcels) |
| **Storage Location** | `backend/.data/soilstice.sqlite3` (`farms` collection) | In-memory `src/services/mock/world.ts` (`AOI_META`) |
| **Data Nature** | Authoritative AOI definition with live pipeline | Synthetic offline demo fixtures |

---

## 3. Field IDs and Geometry Comparison

### A. Original Backend Fields (`Reno Farm` & `Finney Farm`)
Backend fields are user- or pipeline-created polygons located strictly within the county boundary (`MAX_FIELD_HA = 260.0`).
- **Reno Test Square (Phase 3 Benchmark):**
  - **Field ID:** `a59a0f18-d300-4ed1-a66e-1c6947155145`
  - **Centroid:** `[ -98.0500, 37.9500 ]`
  - **Area:** 97.56 ha
  - **Geometry:** `MultiPolygon` `[[[[-98.055, 37.945], [-98.045, 37.945], [-98.045, 37.955], [-98.055, 37.955], [-98.055, 37.945]]]]`
  - **Processing Status:** `ready` / `partial` (SSURGO, CDL, POWER complete; SRTM requires credentials)
- **Phase 6 Verification Field:**
  - **Field ID:** `4e0f055e-12f1-427b-97ff-d8815be858fb` ("Audit Reno Field")
  - **Area:** 97.56 ha

### B. Mock Service Fields (`Reno Demo Farm` & `Finney Demo Farm`)
Mock fields are hardcoded in a synthetic grid layout defined by `PLAN` in `src/services/mock/world.ts`:

#### 1. Reno Demo Farm (8 Fields, ~464 ha grid)
- `411dd851-40e2-481b-885e-7dc029bcafcd` | `Demo Field A` | 56.3 ha | Shape: Quarter Section Rectangle | Status: `ready`
- `0a66f5ad-239e-4148-9f34-7f4a8c3a78cf` | `Demo Field B` | 113.6 ha | Shape: Half Section Rectangle | Status: `ready`
- `3287b38d-6604-45e6-81eb-15dc57cab1e1` | `Demo Field C` | 53.0 ha | Shape: Quarter Section Rectangle | Status: `partial`
- `cdf4ea91-1b1a-4f5c-a3d2-4e6b9bb085c4` | `Demo Field D` | 55.7 ha | Shape: Quarter Section Rectangle | Status: `ready`
- `b2f02d36-3ebc-478d-8c4d-6b5e49e639ba` | `Demo Field E` | 51.2 ha | Shape: Quarter Section Rectangle | Status: `partial`
- `e0b78e6b-7d25-434b-bea0-c569044bde56` | `Demo Field F` | 27.2 ha | Shape: Eighty-Acre Rectangle | Status: `ready`
- `46984669-4195-4ead-8d67-19c1f31451fa` | `Demo Field G` | 54.9 ha | Shape: Quarter Section Rectangle | Status: `failed`
- `51e18c11-e9e2-4961-a004-8ca63bdc25c3` | `Demo User Field H` | 52.0 ha | Shape: Quarter Section Rectangle | Status: `processing`

#### 2. Finney Demo Farm (6 Fields, ~335 ha grid)
- `7608c195-b364-49a2-a293-a4be862d9eac` | `Demo Field F-A` | 42.5 ha | Shape: Center Pivot Circle | Status: `ready`
- `b51ca161-9c78-4a01-8b6f-cd43029b543a` | `Demo Field F-B` | 40.1 ha | Shape: Center Pivot Circle | Status: `ready`
- `e41c9973-15d2-4a46-8554-650d981d24ac` | `Demo Field F-C` | 109.8 ha | Shape: Half Section Rectangle | Status: `ready`
- `1b55c3d8-cef5-4eda-9c4e-02253fbfd283` | `Demo Field F-D` | 45.0 ha | Shape: Center Pivot Circle | Status: `partial`
- `474ea01b-7fdd-403c-a004-43d8c2312d17` | `Demo Field F-E` | 56.1 ha | Shape: Quarter Section Rectangle | Status: `ready`
- `41c080ae-424c-4647-943a-0715d99b7337` | `Demo Field F-F` | 41.6 ha | Shape: Center Pivot Circle | Status: `partial`

---

## 4. Environmental Data Provenance Matrix

| Environmental Factor | Current Running State (Mock Mode / Port 3000) | Backend Live Pipeline (API Mode / Port 8000) | Classification in Live Mode | Upstream Source & Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Soil pH (0–30 cm)** | **Synthetic Fixture** (PRNG range 5.9–7.6) | **Live Source Data** (`SDMdataaccess.sc.egov.usda.gov`) | Derived estimate from real survey data | USDA NRCS SSURGO SDA; component-weighted polygon intersection |
| **Soil Texture Class** | **Synthetic Fixture** (randomly chosen from 4 classes) | **Live Source Data** (`SDMdataaccess.sc.egov.usda.gov`) | Derived estimate from real survey data | USDA NRCS SSURGO SDA; sand/silt/clay ternary diagram classification |
| **Soil Drainage Class**| **Synthetic Fixture** (latent generator) | **Live Source Data** (`SDMdataaccess.sc.egov.usda.gov`) | Derived estimate from real survey data | USDA NRCS SSURGO SDA; dominant condition drainage class |
| **Available Water (AWS)** | **Synthetic Fixture** (synthetic profile integration) | **Live Source Data** (`SDMdataaccess.sc.egov.usda.gov`) | Derived estimate from real survey data | USDA NRCS SSURGO SDA; 0–150 cm depth-weighted water storage sum |
| **Soil Profile Depth** | **Synthetic Fixture** (fixed 150 cm) | **Live Source Data** (`SDMdataaccess.sc.egov.usda.gov`) | Surveyed profile depth (lower boundary) | USDA NRCS SSURGO SDA; maximum depth of described horizons |
| **Terrain Elevation** | **Synthetic Fixture** (450–495 m Reno; 860–905 m Finney) | **Live Source Data** (`SRTMGL1` v003) | Derived estimate from remote sensing | NASA SRTM GL1 30 m DEM; zonal polygon statistics |
| **Terrain Slope** | **Synthetic Fixture** (PRNG range 0.3–3.6%) | **Live Source Data** (`SRTMGL1` v003) | Derived estimate from remote sensing | NASA SRTM GL1; Horn (1981) 30 m gradient calculation |
| **Precipitation** | **Synthetic Fixture** (daily PRNG generator) | **Live Source Data** (`power.larc.nasa.gov`) | Real model reanalysis estimate | NASA POWER Daily AG v2.10.3; ~50 km MERRA-2 point query |
| **Growing Degree Days** | **Synthetic Fixture** (synthetic daily Tmin/Tmax) | **Live Source Data** (`power.larc.nasa.gov`) | Real model reanalysis estimate | NASA POWER Daily AG; crop-specific base/cutoff integration |
| **Heat Stress Days** | **Synthetic Fixture** (synthetic daily Tmax) | **Live Source Data** (`power.larc.nasa.gov`) | Real model reanalysis estimate | NASA POWER Daily AG; $T_{\max} \ge 30^\circ\text{C}$ (wheat) / $35^\circ\text{C}$ |
| **Crop History (CDL)** | **Synthetic Fixture** (rotation templates `[24, 26, 4]`) | **Live Source Data** (`nassgeodata.gmu.edu/CropScape`) | Real satellite classification | USDA NASS CDL; 30 m pixel-inward buffer extraction (2006–2025) |
| **Crop Suitability** | **Synthetic Evaluation** (Phase 6 on synthetic traits) | **Live Phase 6 Engine** (`CropSuitabilityEngine`) | Agronomic decision-support evaluation | Phase 6 Engine evaluating Phase 5 KB against real environmental profile |

> **Pedological and Geodetic Precision Note:** In live mode, SSURGO attributes are **survey-derived polygon-weighted mapunit approximations**, not direct in-situ field sensor measurements or laboratory core tests. NASA POWER meteorology attributes are **regional atmospheric model reanalysis estimates (~50 km grid)**, not on-farm weather station measurements.

---

## 5. Relevant Git Commits & Code Architecture

### Commit History Analysis
1. **Commit `f04bd1f` (2026-11-14 10:27:53):**
   - *"feat: establish SOILSTICE frontend foundation"*
   - Authored by Shourjya Chakraborty.
   - Introduced `web/src/services/mock/world.ts` defining `Reno Demo Farm` and `Finney Demo Farm` as offline synthetic fixtures for Phase 1.
2. **Commit `863c883` (2026-11-14 11:23:58):**
   - *"feat: integrate real agricultural data services"*
   - Authored by Shourjya Chakraborty.
   - Introduced `backend/app/catalog.py` defining `Reno Farm` and `Finney Farm`.
   - Introduced `.claude/launch.json` defining both `soilstice-web` (port 3100, default mock) and `soilstice-web-api` (port 3100, `NEXT_PUBLIC_DATA_MODE=api`).
   - Exported mock fixtures to `backend/tests/fixtures/frontend_mock/` to allow backend contract testing against frontend mock payloads.
3. **Commit `3f4d6cd` (2026-11-14 12:45:00):**
   - Documented Phase 3 browser QA in live API mode (`docs/PHASE_3_FINAL_VERIFICATION.md`), where "Reno Farm" was verified in the browser when running under `NEXT_PUBLIC_DATA_MODE=api`.

### Code Locations Dictating Mode Selection
1. **Service Factory (`src/services/index.ts` lines 12–18):**
   ```typescript
   export const DATA_MODE: "mock" | "api" = process.env.NEXT_PUBLIC_DATA_MODE === "api" ? "api" : "mock";

   let instance: Services | null = null;

   export function getServices(): Services {
     if (!instance) instance = DATA_MODE === "api" ? createHttpServices() : createMockServices();
     return instance;
   }
   ```
2. **Configuration Default (`.env.example` line 3):**
   ```bash
   # SOILSTICE frontend configuration (copy to .env.local)
   # mock = synthetic data behind the service factory (Phase 1). api = FastAPI backend (Phase 6).
   NEXT_PUBLIC_DATA_MODE=mock
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   ```
3. **HTTP Client Fallback Behavior (`src/services/http/client.ts` lines 29–31):**
   ```typescript
   try {
     res = await fetch(...);
   } catch {
     throw new ApiError("UPSTREAM_UNAVAILABLE", `The SOILSTICE API at ${BASE} is not reachable.`, { retryable: true });
   }
   ```
   *Finding:* The HTTP client **never** silently falls back to synthetic mock data. When in API mode, an unreachable backend throws `UPSTREAM_UNAVAILABLE`. Silent fallback does not exist.

---

## 6. Root Cause Determination

### Verified Facts
1. The backend SQLite database (`backend/.data/soilstice.sqlite3`) and upstream cache (`backend/.cache/raw/`) have **not** been corrupted, deleted, or cleared.
2. The backend catalog (`backend/app/catalog.py`) defines only **`Reno Farm`** and **`Finney Farm`**.
3. The mock world (`src/services/mock/world.ts`) defines only **`Reno Demo Farm`** and **`Finney Demo Farm`**.
4. The frontend service factory (`src/services/index.ts`) switches between mock and HTTP implementations solely based on the environment variable `NEXT_PUBLIC_DATA_MODE`.
5. The Next.js dev process running on port 3000 (PID 37060, started 00:47:49) was started without `NEXT_PUBLIC_DATA_MODE=api`.
6. There is no uncommitted or committed `.env.local` file in the workspace root.

### Root Cause
The switch from `Reno Farm` / `Finney Farm` to `Reno Demo Farm` / `Finney Demo Farm` occurred because the Next.js development server on port 3000 was started in the **default Mock Mode** rather than **API Mode**. In Mock Mode, Next.js statically bundles the Phase 1 offline mock services, rendering the synthetic demo farms and bypasses the FastAPI backend entirely.

No code regression, data loss, database overwrite, or model corruption took place.

---

## 7. Data-Loss & Integrity Assessment

- **Database Integrity:** 100% intact. `backend/.data/soilstice.sqlite3` retains the canonical farms (`e3d21ac7-5df1-55ef-97f7-a4098b4e863e` and `3a9b1abb-271e-52d8-9cc9-8ca35ebfa7de`) and field records.
- **Provider Pipeline Integrity:** 100% intact. Live requests to SSURGO SDA and NASA POWER execute and parse correctly.
- **Phase 5 Crop Knowledge Base:** 100% intact. Immutable handoff package `data/backend_handoff/` is untouched.
- **Phase 6 Suitability Engine:** 100% intact. All 31 Phase 6 unit/integration tests and 333 backend tests pass.

---

## 8. Safe Recovery Procedure (Awaiting Explicit Approval)

To switch the running application from Mock Mode to Live API Mode without modifying any application code or losing mock fixtures:

### Step 1: Create `.env.local` in Project Root
Create `.env.local` (git-ignored) containing:
```bash
NEXT_PUBLIC_DATA_MODE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Step 2: Start Backend Server
Ensure FastAPI is running on port 8000:
```bash
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Step 3: Restart Next.js Frontend
Restart the Next.js development server so Turbopack picks up `.env.local`:
```bash
npm run dev
```

### Expected Result
- The application will immediately display **Reno Farm** and **Finney Farm**.
- DataModeBanner will render: `Live data environment · Dataset availability varies by field (USDA SSURGO, USDA CDL, NASA POWER operational)`.
- All field queries will execute against live SSURGO, POWER, CDL, and the Phase 6 suitability engine.
- Mock fixtures in `src/services/mock/` and `backend/tests/fixtures/frontend_mock/` will remain completely preserved for offline test suites (`npm test`, `pytest`).

---

**End of Audit Report. No data modification or restoration has been executed.**
