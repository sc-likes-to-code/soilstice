# SOILSTICE — Meteomatics Migration Architecture Audit

## 1. Executive Summary

This audit establishes the baseline technical architecture of the SOILSTICE repository before executing the Meteomatics-first environmental pipeline migration.

The migration replaces repeatedly failing and blocked download integrations (NASA HLS, SMAP, and SRTM download pipelines) with direct, reliable Meteomatics API queries for:
1. Volumetric soil moisture at 4 depths (`-5cm`, `-15cm`, `-50cm`, `-150cm`) and historical time series
2. Digital elevation (`elevation:m`)
3. Conditional slope & slope P90 derivation (with spatial adequacy gating)
4. Regional NDVI (`sat_ndvi:idx`) with explicit regional-context labelling

Critically, **NASA POWER** (climate) and **USDA NRCS SSURGO** (soil properties) remain fully preserved. Downstream consumers—including the independently audited **Phase 6 Crop Suitability Engine** and **Phase 7 Rotation Engine**—remain intact with zero alteration to their scientific scoring formulas, weights, or thresholds.

---

## 2. Repository Architecture & Runtimes

### 2.1 Backend
- **Language / Runtime:** Python 3.13.0
- **Framework:** FastAPI `0.162.7`, Starlette `1.10.0`, Uvicorn `0.54.0`
- **Configuration & Validation:** Pydantic `2.14.3`, Pydantic-Settings `2.16.3`
- **HTTP Client & Resiliency:** HTTPX `0.28.1` with custom `HttpAcquirer` (retries with exponential backoff, jitter, secret redaction, and SHA-256 raw request caching)
- **Geospatial & Numerical Stack:** Shapely `2.2.0`, Pyproj `3.8.0`, Rasterio `1.5.2`, NumPy `2.5.4`
- **Data Persistence:** SQLite document store (`SqliteDocumentStore`) at `backend/.data/soilstice.sqlite3` with ACID operations, WAL mode, and repository pattern (`Repositories`)
- **Testing:** Pytest `9.2.0`, Respx `0.23.1` (mock HTTP transport), Anyio `4.16.0`

### 2.2 Frontend
- **Framework:** Next.js `16.4.6` (App Router), React `19.3.0`, React DOM `19.3.0`
- **Language:** TypeScript 5.x (`strict: true`)
- **Styling:** Tailwind CSS `4.3.3` with custom agricultural theme palette (`forest`, `wheat`, `soil`, `paper`, `ink`)
- **State & Data Fetching:** TanStack React Query `v5.107.1`
- **Mapping & Charts:** MapLibre GL `v5.24.1`, Recharts `v3.10.1`
- **Icons:** Lucide React `v1.72.0`
- **Testing:** Vitest `v5.1.0`

---

## 3. Environment & Credential Loading Audit

### 3.1 Existing Loading Mechanism
- `backend/app/config.py` defines `Settings(BaseSettings)` with:
  ```python
  model_config = SettingsConfigDict(
      env_prefix="SOILSTICE_",
      env_file=BACKEND_ROOT / ".env",
      env_file_encoding="utf-8",
      extra="ignore",
  )
  ```
- Backend environment file location: `backend/.env`.
- Root `.gitignore` explicitly excludes `.env*` from git tracking (`git check-ignore -v backend/.env` confirmed).
- Previously required `SOILSTICE_EARTHDATA_TOKEN` / `SOILSTICE_EARTHDATA_USERNAME` / `SOILSTICE_EARTHDATA_PASSWORD` for SRTM.

### 3.2 Meteomatics Configuration Target
- Exact file path for credentials: **`backend/.env`**
- Variable names:
  - `METEOMATICS_USERNAME`
  - `METEOMATICS_PASSWORD`
  - (Also supporting `SOILSTICE_METEOMATICS_USERNAME` / `SOILSTICE_METEOMATICS_PASSWORD` via Pydantic `AliasChoices`)
- Template file: `backend/.env.example`
- Security invariants:
  - No secrets printed to console or logs.
  - No exposure in frontend bundle or `NEXT_PUBLIC_*` variables.
  - Clear startup and diagnostic validation reporting missing configuration without crashing or fabricating fake data.

---

## 4. Current Provider & Metric Ownership

| Metric / Domain | Current Provider | Status / Issues | Target Provider | Action in Migration |
|---|---|---|---|---|
| **Daily Climate** (precip, temp, GDD, solar, RH) | NASA POWER Daily AG (`nasa_power_daily_ag`) | Working reliably, tested live | NASA POWER | **Preserve completely** |
| **Soil Properties** (AWS, pH, texture, drainage, horizons) | USDA NRCS SSURGO (`usda_nrcs_ssurgo_sda`) | Working reliably, tested live | SSURGO | **Preserve completely** |
| **Crop History** (2006–2025 CDL sequence) | USDA NASS CDL (`usda_nass_cdl`) | Working reliably, tested live | USDA NASS CDL | **Preserve completely** |
| **Soil Moisture** (4 depths: 5, 15, 50, 150 cm & time series) | SMAP L4 (`nasa_smap_spl4smgp`) | Failing / blocked HDF5 download; marked unintegrated | Meteomatics (`volumetric_soil_water_-*cm:m3m3`) | **Primary replacement (P0)** |
| **Elevation** (mean, min, max) | NASA SRTM GL1 (`nasa_srtm_gl1`) | Requires Earthdata auth; download pipeline blocked | Meteomatics (`elevation:m`) | **Primary replacement (P0)** |
| **Slope & Slope P90** | NASA SRTM GL1 (Horn 3x3 on 30m DEM) | Blocked by SRTM | Meteomatics grid with conditional derivation | **Conditional derivation; gate if spatial evidence inadequate** |
| **Vegetation Index** (NDVI time series) | NASA HLS (`nasa_hls_vi`) | Blocked by NASA CMR/STAC downloads | Meteomatics (`sat_ndvi:idx`) | **Regional NDVI indicator (P1); label as coarse regional context** |
| **Canopy Stability Model** (interannual CV) | Derived from HLS 30m | Blocked by HLS | None | **Keep unavailable; do NOT feed coarse regional NDVI into 30m model** |
| **Terrain Erosion Hazard** (HEL proxy) | Slope P90 model | Blocked by SRTM | Conditionally derived slope P90 | **Withhold score (`insufficient_coverage`) if slope P90 inadequate** |

---

## 5. Trace of Environmental Metrics to Downstream Consumers

```
[Meteomatics API]
       │
       ├── volumetric_soil_water_-5cm:m3m3   ──┐
       ├── volumetric_soil_water_-15cm:m3m3  ──┼──> Soil Moisture Pipeline
       ├── volumetric_soil_water_-50cm:m3m3  ──┤     ├── Surface / Shallow / Mid / Deep metrics
       ├── volumetric_soil_water_-150cm:m3m3 ──┘     ├── Time-series & seasonal aggregations
       │                                             └── Composite root-zone moisture (weighted & model-identified)
       │
       ├── elevation:m                       ─────> Terrain Pipeline
       │                                             ├── Mean / Min / Max elevation
       │                                             └── Conditional Slope & Slope P90 (adequate grid required)
       │
       └── sat_ndvi:idx                      ─────> Regional Vegetation Pipeline
                                                     ├── Regional NDVI time-series & peak greenness
                                                     └── Clearly labeled as regional (support class R)

Downstream Consumers:
1. Environmental Indicators (`app.analytics.indicators.py`):
   - All indicators assembled with honest quality status and missing reasons.
2. Resilience Engine (`app.analytics.resilience.py`):
   - `terrain_erosion_risk`: scored from slope P90 if valid; withheld if inadequate.
   - `vegetation_stability`: withheld (`NOT_COMPUTED`) as regional NDVI is not 30m HLS.
   - Quorum rule (>= 4 of 5 components) faithfully enforced.
3. Crop Suitability Engine (`app.suitability.engine.py`):
   - Consumes `TerrainProfile.slope_p90_pct` and `SoilProfile.aws_0_150`.
   - Scoring formulas, weights, thresholds remain 100% unchanged.
4. Frontend (`src/components/views/environment-view.tsx`):
   - Soil moisture tab displays Meteomatics 4-depth values and time-series.
   - Terrain card displays elevation statistics and conditional slope.
   - Regional NDVI clearly distinguished from field-scale HLS.
```

---

## 6. Migration Risks & Mitigations

1. **Risk:** Overstating coarse grid elevation as native high-resolution DEM.
   - **Mitigation:** Track effective spatial resolution and coordinate spacing; require minimum valid cells before computing slope; gate slope P90 and mark unavailable if inadequate.
2. **Risk:** Conflating regional NDVI (`sat_ndvi:idx`) with 30m field-level HLS canopy stability.
   - **Mitigation:** Attribute regional NDVI as support class `R`, keep `Canopy Temporal Stability Model v1` unavailable, and display explicit regional caveats in UI.
3. **Risk:** Disrupting audited Phase 6 suitability scoring.
   - **Mitigation:** Keep all Phase 6 scoring contracts and evaluator functions untouched; write dedicated regression tests asserting identical outputs for given inputs.
4. **Risk:** Test suite hanging or failing when credentials are not configured.
   - **Mitigation:** Offline unit and integration tests use realistic cached response fixtures via `respx`. Live tests detect missing credentials and report `SKIPPED` rather than failing or silently mocking.

---

## 7. Baseline Test Results

Prior to code changes:
- **Backend (pytest):**
  - Total items: 356
  - Deselected (live tests): 6
  - Selected: 350
  - Passed: 350 (100% of selected offline tests)
  - Time: ~10.6s
- **Frontend (vitest):**
  - Test files: 5 passed
  - Tests: 25 passed (100%)
  - Time: ~1.35s
- **OpenAPI Schema Check:** Verified synced with FastAPI application definition.

Baseline recorded. Proceeding to implementation.
