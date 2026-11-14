# SOILSTICE: Phase 2 Handover (Backend Foundation)

**Last updated:** 2026-11-14, session 2 (Claude Code, Opus 5.5) · **For:** the next coding agent
**Git:** branch `main`, HEAD `f31a501`. **Nothing from Phase 2 is committed.** No branch, remote or push was created (as the brief instructed).

---

## LIVE PROGRESS (authoritative)

| Item | Value |
|---|---|
| Overall completion | **~95% of Phase 2.** All 8 definition-of-done items are met, except that SRTM has not been verified live (it needs Earthdata credentials). |
| Current task | None. Phase 2 is complete pending review and commit. |
| Completed | Tasks 1–5 (§10 of session 1) · B1–B4 · backend starts · 27 endpoints · 4 provider integrations · OpenAPI export · TS drift check · frontend fixture validation · frontend running in `api` mode against the backend |
| In progress | — |
| Pending (next phases) | See §10 |
| Blockers | **D4:** no NASA Earthdata token, so the SRTM live download is untested (code and offline tests pass). **D5:** crop KB (teammate). **D6:** resilience breakpoints (Phase 4). |
| Exact next action | Team reviews the PROVISIONAL soil rule (§9 D1), supplies an Earthdata token and runs `pytest -m live`, then commits on a feature branch. |

---

## 1. Objectives and status

| # | Phase 2 objective | Status | Evidence |
|---|---|---|---|
| 1 | FastAPI backend in `backend/` | **COMPLETED** | `uvicorn app.main:app` serves `/api/v1` (verified live, §8) |
| 2 | Pydantic models matching `src/types/contracts.ts` | **COMPLETED + VALIDATED** | 57 exact-type TS assertions (`npm run contract:check`); 194 frontend fixtures validate |
| 3 | Endpoints E1–E27 | **COMPLETED** (behaviour per §4; E19/E21/E23–E24 evaluations are honest "pending" outputs) | `tests/test_api.py` |
| 4 | Service / repository / processing / API layers | **COMPLETED** | §3 |
| 5 | Config, env vars, structured logging, typed errors | **COMPLETED** | `app/config.py`, `app/logging.py`, `app/errors.py`, `app/main.py` |
| 6 | Automated tests + contract validation | **COMPLETED** | 266 offline tests + 4 live tests |
| 7 | OpenAPI export compatible with the frontend | **COMPLETED** | `backend/openapi.json`; drift check proven with injected drift |
| — | Real-data slice: SSURGO, CDL, POWER, SRTM | SSURGO/POWER/CDL **COMPLETED + LIVE-VERIFIED**; SRTM **IMPLEMENTED + OFFLINE-TESTED, NOT LIVE-VERIFIED** | §5 |
| — | Frontend consumes the backend through its service interfaces | **COMPLETED** | Dashboard, Environment (climate, soil) verified in the browser in api mode (§6) |

---

## 2. Files

### Created
| Path | Purpose |
|---|---|
| `backend/pyproject.toml` | Package, dependencies, pytest (`live` marker deselected by default), ruff (line length 125) |
| `backend/README.md`, `backend/.env.example` | Run/test instructions; every env var |
| `backend/app/config.py` | `Settings` (prefix `SOILSTICE_`, reads `backend/.env`), credentials as `SecretStr` |
| `backend/app/logging.py` | JSON-lines logs with `request_id` context |
| `backend/app/errors.py` | Typed `ApiException` hierarchy → code/HTTP status/retryable |
| `backend/app/contracts/{vocab,common,envelope,entities}.py` | Pydantic v2 wire contracts (API_CONTRACTS §2–5) |
| `backend/app/catalog.py` | Dataset register (14), integrated set, spatial supports, AOIs, CDL candidate crop names |
| `backend/app/repositories/{store,records,__init__}.py` | `DocumentStore` Protocol, `SqliteDocumentStore`, typed repositories, internal records |
| `backend/app/providers/http.py` | Retries/backoff, sha256 raw cache, acquisition records, redaction, Earthdata auth |
| `backend/app/providers/{power,ssurgo,cdl,srtm}.py` | One acquisition + parsing module per dataset |
| `backend/app/processing/{geometry,climate,soil,texture,crop_history,terrain,placeholders}.py` | Pure transformations |
| `backend/app/analytics/{indicators,resilience}.py` | Environmental engine: indicator assembly; `PendingResilienceEngine` |
| `backend/app/rotation/{kb,engine}.py` | Crop-KB loader (citation-enforcing); `PendingRotationEngine` |
| `backend/app/services/{container,pipeline,fields,environment,rotation,evidence}.py` | Application services, job runner |
| `backend/app/api/{envelope,routes}.py`, `backend/app/main.py` | FastAPI app, middleware, handlers, 27 operations |
| `backend/scripts/export_openapi.py`, `backend/openapi.json` | Deterministic OpenAPI export (`--check`) |
| `backend/db/schema.sql` | PostGIS target DDL, **design only, not applied** |
| `backend/tests/*.py` | conftest (synthetic fakes), contracts, api, providers, processing, kb, frontend contract, live |
| `backend/tests/fixtures/frontend_mock/*.json` + `README.md` | 194 **SYNTHETIC** mock responses exported from the frontend |
| `contract/{compat.ts,openapi.gen.ts,tsconfig.json,export-openapi.mjs,export-fixtures.mjs}` | TS↔OpenAPI drift check and helper launchers |
| `src/services/mock/export-fixtures.test.ts` | New vitest file; writes fixtures only when `EXPORT_FIXTURES_DIR` is set |
| `docs/PHASE_2_HANDOVER.md` | This document |

### Modified
| Path | Change |
|---|---|
| `.gitignore` | Ignore `backend/.venv/`, `.cache/`, `.data/`, `__pycache__`, `*.sqlite3`, pytest/ruff caches, egg-info |
| `.claude/launch.json` | `soilstice-web` no longer uses the non-existent `web/` prefix. New `soilstice-web-api` (port 3100, `NEXT_PUBLIC_DATA_MODE=api`) and `soilstice-api` (uvicorn, port 8000). |
| `package.json` / `package-lock.json` | devDependency `openapi-typescript@7.13.0` (exact). Scripts `contract:openapi`, `contract:gen`, `contract:check`, `contract:fixtures`. |
| `src/components/layout/app-shell.tsx`, `layout/field-layout.tsx`, `views/dashboard-view.tsx`, `views/field-explorer-view.tsx`, `views/rotation-view.tsx`, `views/settings-view.tsx` | **Minimal honesty fix (13 lines):** "Synthetic" badges and "synthetic geometry" captions were unconditional, so they would have labelled real API data as synthetic. They now render only when `DATA_MODE === "mock"`. Mock-mode output is unchanged. No other frontend change. |

The frontend was **not** moved; it stays at the repo root, and its contracts are at `src/types/contracts.ts`.

---

## 3. Architecture and decisions

```
Next.js (repo root, unchanged service interfaces) ──HTTP /api/v1──▶ app/api (routes, envelope, errors, request-id, rate limit)
                                                                       │
                                                         app/services (container, pipeline/job runner, coverage, evidence)
                                     ┌─────────────────────────────────┼──────────────────────────────┐
                              app/repositories                 app/providers (+ http.py)        app/analytics · app/rotation
                         (SQLite doc store; PostGIS later)   power · ssurgo · cdl · srtm      (indicators; resilience "pending";
                                                                    │                             KB loader; engine "pending")
                                                              app/processing (pure functions)
```

Layer mapping (four approved layers): Presentation = Next.js. Data services and acquisition = api/services/repositories/providers/processing. Environmental analytical engine = `app/analytics`. Rotation engine = `app/rotation`. The engines read only stored profiles, never upstream APIs (PHASE_0 D7).

Decisions H1–H19 from session 1 (below in §11) were all implemented as written, with these session-2 additions:

| # | Decision |
|---|---|
| H20 | **CropScape is called sequentially** (`SOILSTICE_CDL_PARALLEL_REQUESTS=1`). Four parallel `GetCDLFile` calls all hit the 120 s timeout. Single calls took 1.3 s (2025) and 37 s (2006: the server builds older files on demand). |
| H21 | **One `SourceRef` per acquisition.** SSURGO profiles carry 4 (clip, components, muaggatt, survey); terrain carries one per tile; CDL carries one per year. |
| H22 | **Climate on demand:** E13 serves a stored profile if one exists. Otherwise it fetches POWER synchronously. It stores only complete past seasons without `crop_code`; the current year is never cached, so it is refetched. Future years return `OUT_OF_TEMPORAL_RANGE` without a network call. |
| H23 | **Job steps** run in the order SSURGO → CDL → POWER → SRTM. Each step is wrapped so that a `ProviderError` or an unexpected exception fails only that step. On startup, jobs left `queued`/`running` are marked failed ("Interrupted by a server restart."). |
| H24 | Pixel inclusion for CDL and SRTM uses the **pixel centre** (rasterio `geometry_mask`, `all_touched=False`). This is the documented fallback; `exactextract` is not a dependency. Every crop history carries the `PIXEL_CENTRE_RULE` flag. |
| H25 | Farms get deterministic ids: `uuid5(namespace, aoi_id)`. Reno Farm = `e3d21ac7-5df1-55ef-97f7-a4098b4e863e`, Finney Farm = `3a9b1abb-271e-52d8-9cc9-8ca35ebfa7de`. |
| H26 | `/crops` without a KB returns the 8 CDL candidate codes with `family: "unassigned (crop knowledge base pending)"` and `kb_version: "none"`. These are names only, no thresholds. Scenario validation accepts only these codes. |

---

## 4. Endpoints (all implemented and tested)

| # | Endpoint | Behaviour in this build |
|---|---|---|
| E1 | `GET /health` | `{status:"ok", contract_version}` |
| E2 | `GET /datasets` | 14 descriptors; POWER, SSURGO, CDL and SRTM have `integration_status: "integrated"` |
| E3–E5 | farms | 2 seeded farms; `field_count`/`total_area` computed; PATCH rename (1–80 chars) |
| E6 | overview | Summaries, coverage counts, alerts (`FIELDS_FAILED/PARTIAL/PROCESSING`, `EARTHDATA_NOT_CONFIGURED`, `NO_FIELDS`); `regional_context: []` |
| E7/E8 | list / create field | Filters; 202 with job; 422 `GEOMETRY_INVALID` / `OUTSIDE_AOI` / `FIELD_TOO_LARGE` / `VALIDATION_ERROR` |
| E9/E10 | get / delete field | 409 `NOT_EDITABLE` unless `source=="user"`; cascade deletes jobs, profiles, states, scenarios |
| E11 | profile | soil/terrain/crop_history `null` until available; climate summary for the default season; vegetation `NO_DATA_SOURCE`; resilience `pending` |
| E12 | coverage | 12 rows (P0 + P1). Completeness = available-or-partial / applicable P0 rows (**max 4/7 for a user field**) |
| E13 | climate | §5 POWER. 3 computed indicators; others `NOT_COMPUTED` or `NO_DATA_SOURCE` |
| E14/E15 | soil / terrain | Stored profile, or a contract-valid null profile carrying the step's reason (`PENDING_PROCESSING`, `NO_DATA_SOURCE`, `NOT_COMPUTED`, …) |
| E16 | vegetation | HLS not integrated: empty scenes, `NO_DATA_SOURCE` |
| E17 | crop history | §5 CDL; rotation metrics `NOT_COMPUTED` |
| E18 | indicators | Climate + soil + terrain + vegetation + rotation; `category` / `season_year` filters |
| E19 | resilience | `status: "pending"`, 5 components with null scores, band `unknown` |
| E20 | crops | H26 |
| E21 | recommendations | `status: "insufficient_data"`, no candidates, disclaimers incl. "Not a yield or profit forecast." |
| E22–E25 | scenarios | Real CRUD; 422 on unknown crop codes or non-consecutive years; evaluation `overall: "unknown"` with warning `ENGINE_PENDING_KB` |
| E26 | evidence | Global dataset and method items, plus per-field acquisition items (LIVE) and computed-indicator items; `kind` / `related_id` filters |
| E27 | jobs | Live step progression |

Every response uses the `ApiResponse` envelope with `meta.data_mode: "live"`. Errors use `ApiErrorResponse`, including unknown routes (404 `NOT_FOUND`) and unhandled exceptions (500 `INTERNAL`). Each response carries an `X-Request-ID` header. Writes are rate-limited per IP (429 `RATE_LIMITED`). Docs are at `/api/v1/docs`; the schema is at `/api/v1/openapi.json`.

---

## 5. Dataset integrations

### NASA POWER: COMPLETED, LIVE-VERIFIED
- **Endpoint:** `GET https://power.larc.nasa.gov/api/temporal/daily/point`, `community=AG`. Parameters: `PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,ALLSKY_SFC_SW_DWN`. Point query at the field centroid. No auth.
- **Parsing:**
  - Fill value −999 becomes `null` with `FILL_VALUE`. A true 0 stays 0.
  - Days after the request window become `NOT_YET_PUBLISHED`.
  - Days absent from the response become `UPSTREAM_ERROR`.
  - Units are checked against the expected strings (`mm/day`, `C`, `%`, `MJ/m^2/day`). On a mismatch the series is **withheld** with a `UNIT_MISMATCH` critical flag; it is never converted on an assumption.
  - Range checks (RH 0–100, precipitation and solar ≥ 0, Tmin ≤ T ≤ Tmax) **flag** points; they never drop them.
- **Units:** mm (daily total), degC, percent, MJ_m-2_day-1.
- **Resolution:**
  - Spatial: **support R**, `api_point_query`, EPSG:4326, 55 000 m (MERRA-2) or 111 000 m (solar, CERES). No claim is made about POWER's internal interpolation.
  - Temporal: P1D, LST.
- **Indicators:** `precip_total_season` (sum), `solar_total_season` (sum, MJ_m-2) and `rh_mean_season` (mean), each only when ≥ 90% of days are present (§5.5). Season = calendar year (KB pending).
- **Provenance:** product "POWER Daily API (community=AG; sources: …)", version from `header.api.version`, acquisition id, `retrieved_at`.
- **Limitations:**
  - No 1991–2020 normals, so the anomaly is not computed.
  - GDD, heat stress and ET₀ are pending Phase 4.

### USDA SSURGO (Soil Data Access): COMPLETED, LIVE-VERIFIED
- **Endpoint:** `POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` (`JSON+COLUMNNAME`). 4 queries: `GetClippedMapunits` per polygon part, then components/horizons (major only), `muaggatt`, and `legend`/`sacatalog`.
- **Parsing:**
  - All values are strings; `to_float` treats `''`/null as null.
  - `saverest` is in `M/D/YYYY h:mm:ss AM/PM` format.
  - Mukeys are digit-validated before being placed in SQL.
  - An HTTP 500 is not retried (it means a query bug).
- **Aggregation:** DATA_ARCHITECTURE §5.3.1, `ssurgo_area_comppct_weighting` v1:
  - Areas are measured locally in EPSG:5070.
  - Fixed intervals 0–30, 30–100 and 100–150 cm, with the 80% coverage rule.
  - `_l`/`_h` become uncertainty ranges.
  - USDA texture triangle; categorical classes by the largest weight.
  - AWS comes from `muaggatt`.
- **Units:** percent, pH, cm_cm-1, cm.
- **Resolution:** spatial support F, `vector_intersection`; temporal static (survey vintage in `product_version`).
- **Limitations:** see §9 D1 (PROVISIONAL rules).

### USDA NASS CDL (CropScape): COMPLETED, LIVE-VERIFIED (live test + full 20-year end-to-end field job)
- **Endpoint:** `GetCDLFile?year&fips` (county fips only, T16) returns a GeoTIFF (EPSG:5070, 30 m, uint8, 0 = background). `GetCDLStat` provides the per-year class-name legend.
- **Parsing:**
  - `<faultstring>` "not available" becomes `OUT_OF_TEMPORAL_RANGE`.
  - A response that is not a GeoTIFF is rejected.
  - A missing legend falls back to "CDL class N".
- **Processing:**
  - 15 m inward buffer, skipped below 50% remaining area (flag `INWARD_BUFFER_SKIPPED`).
  - Pixel-centre mask; background pixels excluded and flagged.
  - Histogram, majority, purity; `low_purity` < 0.6.
  - `class_accuracy` null, flagged `CLASS_ACCURACY_NOT_INGESTED`.
  - CSB cross-check fields stay null (no CSB yet).
- **Resolution:** spatial F, `zonal_polygon_inward_buffer`, 30 m (read from the raster); temporal P1Y, 2006–2025.
- **Cache:** ~4 MB per county-year; the first field in a county downloads all 20 years sequentially (~15 min observed).
- **Live finding (resolves an [UNVERIFIED] item in DATA_ARCHITECTURE §8.3 / Source Register §3):** the Reno County rasters for **2006 and 2007 are 56 m**; 2008 onward are 30 m. `native_resolution_m` is read per year from the raster, so the contract reports it correctly.
- **Note on the test result:** every year of the 97 ha test square has purity < 0.6. The square is an arbitrary 1 km box spanning several real fields, not a field boundary. 2025 majority = Corn, consistent with the Phase 0 point check (2025 = 1 Corn).

### NASA SRTM SRTMGL1 v003: IMPLEMENTED + OFFLINE-TESTED, **NOT LIVE-VERIFIED**
- **Endpoint:**
  - Discovery: CMR granule search (open; verified live in session 1).
  - Download: the `.hgt.zip` data link with Earthdata **bearer token**, or basic auth sent only to `urs.earthdata.nasa.gov` (manual redirect loop, tested with a mock transport).
- **Parsing:** 3601×3601 big-endian int16, void −32768, converted to a cached GeoTIFF (EPSG:4326, pixel-centre registration).
- **Processing:**
  - Elevation mean/min/max on the native grid.
  - Slope via bilinear reprojection to EPSG:5070 at 30 m, then a Horn kernel; mean and p90 in percent.
  - Voids are excluded and flagged; the `SRTM_SURFACE_MODEL` flag is always set.
- **Without credentials:** the step fails with `NOT_COMPUTED` and the message to configure Earthdata; the overview shows `EARTHDATA_NOT_CONFIGURED`.

### Not started (planned)
- CSB demo fields.
- HLS/HLS-VI and SMAP L4 (P0): shown as `not_integrated`.
- PRISM, OpenET, Quick Stats, SMAP L3 (P1).

---

## 6. Frontend–backend connection

- **Connected and verified** in the browser with `NEXT_PUBLIC_DATA_MODE=api` (launch entry `soilstice-web-api`, port 3100).
- The Dashboard shows the real farm, field and area.
- The Environment page shows real POWER climate indicators, with "Regional · 55 km / 111 km" support badges and POWER v2.10.3 source chips, and the real SSURGO soil profile with ranges and KS155 provenance.
- No console errors. No "synthetic" text remains in api mode.
- The service interfaces (`src/services/types.ts`, `http/services.ts`) are **unchanged**. All 26 frontend HTTP calls map to OpenAPI operations (test-enforced).
- The default mode is still `mock` (the `.env.example` default).

---

## 7. Setup

Backend:

```bash
cd backend
```

```bash
py -3.13 -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -e ".[dev]"
```

Frontend (repo root):

```bash
npm install
```

- **Environment variables:** see `backend/.env.example`. Required only for SRTM: `SOILSTICE_EARTHDATA_TOKEN`, or `SOILSTICE_EARTHDATA_USERNAME` + `SOILSTICE_EARTHDATA_PASSWORD`.
- **Python packages:** fastapi, uvicorn, pydantic, pydantic-settings, httpx, shapely, pyproj, numpy, rasterio. Dev: pytest, respx, ruff.
- **npm devDependency:** openapi-typescript 7.13.0.
- No paid services or cloud resources are used.

---

## 8. Verification log (actual results)

| Command / action | Result |
|---|---|
| Live smoke script (SSURGO + POWER), Reno square box(−98.055, 37.945, −98.045, 37.955) | **PASS.** Nalim loam 85.3%; AWS 0–150 = 21.34 cm; Well drained; hydgrp C; 0–30 cm Loam; POWER 2025 precipitation 959.62 mm, completeness 1.0 |
| `backend: .venv/Scripts/python -m pytest` | **266 passed, 4 deselected** |
| `backend: .venv/Scripts/python -m pytest -m live` | **3 passed (SSURGO, POWER, CDL), 1 skipped (SRTM: no token)** |
| `backend: .venv/Scripts/ruff check app tests scripts` | **All checks passed** |
| `npm run contract:openapi && npm run contract:fixtures && npm run contract:check` | **PASS.** 22 paths / 95 schemas; 194 fixtures; `tsc -p contract` clean |
| Drift-detection proof: rename `Quantity.value` and make `DataCoverage.completeness` optional in the generated file | **23 TS errors**, then clean after restoring |
| `npm run lint` / `npm run typecheck` / `npm test` | **exit 0 / exit 0 / 4 files, 19 tests passed** |
| Server start + curl: health, farms, POST field (97.56 ha), OUTSIDE_AOI, 404 | **PASS** |
| Restart during a running job | **PASS:** interrupted steps marked failed; field `partial` |
| Browser, api mode: dashboard, environment climate + soil | **PASS:** real data, no console errors, no synthetic labels |
| Live E8 job on the Reno square (field `a59a0f18-…`, sequential CDL) | **PARTIAL as designed:** SSURGO, CDL (20/20 years, quality valid, completeness 1.0) and POWER succeeded; SRTM failed `NOT_COMPUTED` (no Earthdata credentials). Coverage completeness 3/7 = 0.4286. CDL took about 15 min (first acquisition of the county). |
| Browser, api mode: Rotation Lab | **PASS:** real 2006–2025 CDL sequence rendered; rotation metrics show "Not computed yet"; no console errors |
| Final re-run after all edits: pytest / ruff / `export_openapi.py --check` / npm test / typecheck / lint / `tsc -p contract` | **266 passed · clean · up to date · 19 passed · clean · clean · clean** |

---

## 9. Bugs, blockers and decisions needing approval

| # | Item | Status / action |
|---|---|---|
| D1 | **PROVISIONAL soil rules, NOT approved methodology:** (a) `null_weight_fraction` denominator: a null-comppct component gets nominal weight `area_fraction / n_major`; map units with no major components count as fully null; a component is null if it has no 0–30 cm value for any property. (b) AWS and SSURGO slope are null when map units with a value cover < 50% of the field. | Implemented, and visible as `PROVISIONAL_NULL_WEIGHT_RULE` on every soil profile and in the method description. **Team must approve or replace.** |
| D2 | AOI check uses county bounding boxes (as in `src/lib/aoi.ts`) | Accepted limitation; replace with TIGER county polygons |
| D3 | CDL class accuracy not ingested | `class_accuracy: null` plus a flag |
| D4 | No Earthdata credentials | **Blocks live SRTM verification.** Set the token, run `pytest -m live`, create a field |
| D5 | Crop KB (teammate) | `SOILSTICE_CROP_KB_DIR/kb.json`. The proposed shape is in `app/rotation/kb.py`; agree it with the KB author. |
| D6 | Resilience breakpoints (Phase 4) | E19 returns `pending` |
| D7 | Proposed `kb.json` format not yet agreed | — |
| D8 | CropScape is slow for older years (~37 s each, server-generated) | The first field per county takes several minutes for CDL. Precompute (DATA_ARCHITECTURE §7) or pre-warm the cache. |
| D9 | The frontend has no field-reprocess action; a field stuck after a restart stays `partial` | Delete and recreate it, or add a reprocess endpoint (a contract addition needs a §9 change-log entry) |
| D10 | Starlette emits a deprecation warning for `httpx` in `TestClient` | Harmless; tests pass |
| D11 | Duplicate-looking SSURGO source chips (one per acquisition, H21) | Cosmetic; could group by dataset in the UI |

---

## 10. Next 5 tasks (priority order)

1. **Review and commit.** Create a feature branch, review the diff (backend, `contract/`, the 6 small frontend edits, the 194 fixtures) and commit. Approve or replace D1.
2. **Earthdata + SRTM live.** Set `SOILSTICE_EARTHDATA_TOKEN`, run `pytest -m live`, create a field, confirm the slope and elevation values against INTEGRATION_GUIDE T-2/T-3, and update §5.
3. **Persist to PostGIS (optional for the demo).** Implement `DocumentStore` (or typed repositories) against `db/schema.sql`. Keep SQLite for tests.
4. **Phase 3 ingestion:** CSB demo fields (INTEGRATION_GUIDE §4, with the reliability filter), then HLS-VI and SMAP L4 providers, following the same provider/processing split. Pre-warm the CDL cache for both AOI counties.
5. **Phase 4/5 hooks:** replace `PendingResilienceEngine` with the cited breakpoint table, and add rotation metrics once the class rules are decided. Wire the teammate's KB into `PendingRotationEngine`'s replacement. Contracts need no change.

---

## 11. Context not stored elsewhere

- The Phase 2 brief's restrictions:
  - Do not rewrite the frontend.
  - Do not invent thresholds or methods.
  - No fabricated observations.
  - No paid or cloud services.
  - Credentials only in env vars.
  - No deployment, commit, push or remote unless instructed.
- Live format facts: SDA string values and the `saverest` format; CDL `nodata=None` with 0 as background; the stat legend as the source of class names; CropScape latency (1.3 s for 2025, 37 s for 2006, timeouts under parallel load); the SRTM CMR link pattern.
- Session-1 decisions H1–H19 (all implemented):
  - H1: frontend stays at the root.
  - H2: Python 3.13.
  - H3: SQLite now, PostGIS later.
  - H4: always `data_mode: "live"`.
  - H5: start with user fields only.
  - H6: job runner.
  - H7: bbox AOI check.
  - H8: EPSG:5070 area, ≤ 260 ha, 3-digit `county_fips`.
  - H9: compute no invented method.
  - H10: calendar-year season.
  - H11: pending engines.
  - H12: KB integration point.
  - H13: coverage rules (corrected: maximum 4/7).
  - H14: `json_schema_serialization_defaults_required`.
  - H15: two contract checks.
  - H16: HTTP policy.
  - H17: Earthdata auth without `earthaccess`.
  - H18: write rate limit.
  - H19: no commits without approval.

---

## 12. Start commands

Backend (port 8000):

```bash
cd "E:/MY PROJECTS/Soilstice/backend" && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Frontend in mock mode (default, port 3000):

```bash
cd "E:/MY PROJECTS/Soilstice" && npm run dev
```

Frontend against the backend (api mode, port 3100). Put these two lines in `.env.local` at the repo root, then run the dev server:

```
NEXT_PUBLIC_DATA_MODE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

```bash
cd "E:/MY PROJECTS/Soilstice" && npm run dev -- --port 3100
```

In the Claude desktop app you can use the launch entries `soilstice-api` and `soilstice-web-api` instead.
