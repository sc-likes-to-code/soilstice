# SOILSTICE: Phase 0 Decisions and Closure Report

**Original date:** 2026-11-13 · **Closure audit:** 2026-11-14
**Status:** Phase 0 complete pending team sign-off (§D12 exit checklist).

**Document set:**
- [SOILSTICE_DATA_ARCHITECTURE.md](SOILSTICE_DATA_ARCHITECTURE.md)
- [DATASET_INTEGRATION_GUIDE.md](DATASET_INTEGRATION_GUIDE.md)
- [DATASET_SOURCE_REGISTER.md](DATASET_SOURCE_REGISTER.md)
- [SOILSTICE_API_CONTRACTS.md](SOILSTICE_API_CONTRACTS.md) (new)
- [SOILSTICE_UI_ARCHITECTURE.md](SOILSTICE_UI_ARCHITECTURE.md) (new)

**Labels:**

| Label | Meaning |
|---|---|
| **[LIVE]** | Tested against the real endpoint |
| **[CMR]** | NASA catalog record |
| **[DOC]** | Official documentation |
| **[UNVERIFIED]** | Must be confirmed before relying on it |
| **[REC]** | Decision or recommendation |

---

## D1. Final dataset priority list (unchanged by the audit)

| Priority | Datasets |
|---|---|
| **P0** | NASA POWER (Daily, AG) · SSURGO via Soil Data Access · USDA NASS CDL (CropScape) · USDA NASS Crop Sequence Boundaries 2018–2025 · NASA HLS v2.0 + HLS-VI v2.0 · NASA SMAP L4 `SPL4SMGP` v008 · NASA SRTM `SRTMGL1` v003 |
| **P1** | PRISM daily (4 km/800 m) · OpenET (Collection 2.1) · NASS Quick Stats · SMAP L3 `SPL3SMP_E` v006 |
| **P2** | GPM IMERG V07 · MODIS `MOD13Q1` v061 / VIIRS `VNP13A1` v002 · ECOSTRESS `ECO_L3T_JET` · NAIP · FAO GAEZ v5 · NLDAS-2 · CoCoRaHS · USGS 3DEP |
| **Excluded** | ERA5/ERA5-Land · GLDAS · NLCD · LANDFIRE · GEDI · USGS NWIS · AMS Market News · Web Soil Survey (UI) · Ag Data Commons (catalog) · stand-alone Landsat/Sentinel-2 (via HLS) · MODIS MOD16 · STATSGO2 (fallback only) |

Reasons for each exclusion are unchanged from the 2026-11-13 version; see DATA_ARCHITECTURE §2.2–2.3.

## D2. Demonstration region (unchanged)

**Central Kansas.** Primary AOI: Reno County (20155). Contrast AOI: Finney County (20055).

- **Evidence [LIVE]:** 2024 CDL crop-diversity Shannon index is 1.72 for Reno and 1.73 for Finney, against 0.63–1.14 for the other candidates. CDL is available 2006–2025.
- **Fallback:** Story County, IA (19169), with only an AOI code change.

---

## D3. Final approved architecture (summary)

```
 Next.js (App Router, TS)  ──typed services──▶  FastAPI /api/v1  ──▶  Supabase Postgres + PostGIS
   │  mock services (Phase 1)                     │  Pydantic contracts      (vectors, stats, indicators,
   │  http services (Phase 6)                     │                           provenance, KB, scenarios)
   └─ MapLibre GL · Recharts · TanStack Query      ├─▶ batch ingestion workers ──▶ object storage (raw cache, COGs)
                                                  │     earthaccess · pystac-client · rasterio · rioxarray
                                                  │     xarray/h5py · geopandas · shapely · pyproj · exactextract · httpx
                                                  └─▶ analytics: indicators → resilience (§5.10) → KB + rotation engine (§5.11)
```

- **One contract surface:** the frontend calls only FastAPI (contract rule R10).
- **Precompute the demo:** 20–50 CSB fields per AOI are processed in batch.
- **User-drawn fields:** POWER, SDA, CDL (from cached county files) and SRTM (from the cached mosaic) run on demand. HLS and SMAP run as a background job.

---

## D4. Technical decisions

T1–T10 from 2026-11-13 still stand:
- spatial-support labelling
- no coarse-to-fine resampling
- EPSG:4326 storage / EPSG:5070 computation
- missing values as `null` + reason
- no PostGIS raster
- Python stack
- no Earth Engine
- precomputed demo
- one authoritative source per variable
- request caching with provenance
- secrets outside the repository

Decisions added by the closure audit:

| # | Decision |
|---|---|
| T11 | **UI-first is approved.** The frontend is built against SOILSTICE_API_CONTRACTS v1.0.0-phase0 through service interfaces with mock implementations. Components never import mocks. |
| T12 | **Wire format:** JSON `snake_case`, metric canonical units, the `Quantity` wrapper for every measured or derived number, and the `ApiResponse` envelope with `meta.data_mode`. |
| T13 | **Contract source of truth:** the contracts doc in Phase 1. From Phase 2, Pydantic is the source, OpenAPI is exported, and `openapi-typescript` is diffed against the TS types in CI. |
| T14 | **Frontend libraries:** MapLibre GL (established), Recharts, TanStack Query, Tailwind CSS. No runtime schema validator. No PDF library (browser print). |
| T15 | **No authentication in the MVP (D8).** It runs as a single demo workspace. All writes (farm rename, user fields, scenarios) go through FastAPI. |
| T16 | **CropScape is acquired by county fips only** and clipped locally. Never by bbox, never per request. |
| T17 | **SSURGO aggregation** follows DATA_ARCHITECTURE §5.3.1. Area fractions come from the SDA `GetClippedMapunits` macro, with areas computed locally in EPSG:5070. |
| T18 | **Resilience methodology framework** is frozen (DATA_ARCHITECTURE §5.10). Breakpoint values are set and cited in Phase 4. |
| T19 | **Rotation recommendation** uses the limiting-factor method plus rotation rules (DATA_ARCHITECTURE §5.11). Every KB threshold must be cited. No yield or profit forecasts. |
| T20 | **User-drawn fields** must lie inside the AOI counties and be ≤ 260 ha. |

---

## D5. Resolution of remaining Phase 0 questions

### D5.1 Crop Sequence Boundaries: eligibility and reliability

| Type | Content |
|---|---|
| Verified facts [DOC] | NASS product, public domain, free to redistribute, no access constraints. National FileGDB zip `NationalCSB_2018-2025_rev23.zip`, layer `national1825`. Attributes `CSBID`, `CSBACRES`, `CDL2018…CDL2025`, `STATEFIPS`, `CNTYFIPS`. Built automatically from CDL resampled to 10 m, with roads and rails imposed, a ≥ ~1 ha minimum and 60 m simplification. These are crop segments, not ownership boundaries. Crop accuracy inherits the CDL's (~85–95% for major crops). CRS: NAD83 Albers, equivalent to EPSG:5070. |
| Unresolved | (a) Whether the challenge rules permit datasets outside the supplied list; the team must check the Space Apps rules. (b) The file size. (c) `CNTYFIPS` digit width. |
| Recommended decision | **Use CSB as P0**, with the reliability filter in INTEGRATION_GUIDE §4.1 (≥ 6 of 8 crop years, ≥ 10 acres) and a NAIP visual spot-check of every demo field. Cite it as supplementary USDA data. **Non-blocking:** the manual polygon fallback (D5.2) gives the same pipeline if CSB is ruled out. |

### D5.2 Manual field polygon fallback

| Type | Content |
|---|---|
| Verified facts | FSA Common Land Units are not public (established in Phase 0). The UI can capture polygons with MapLibre. |
| Recommended decision | **Decided:** user polygons go through Settings → Add field, using the E8 `POST /farms/{farm_id}/fields` endpoint. Validation: valid ring, inside AOI counties, ≤ 260 ha. They are stored as `source='user'` and run through the same pipeline. Coverage shows `pending` until processing finishes. The team can also use this path to replace a visibly wrong CSB polygon. |

### D5.3 HLS product and cloud-mask details

| Type | Content |
|---|---|
| Verified facts | STAC collections `HLSL30_2.0`, `HLSS30_2.0`, `HLSL30_VI_2.0`, `HLSS30_VI_2.0` **[LIVE]**. VI granules include `Fmask` plus nine index COGs **[LIVE]**. SR/VI int16, scale 0.0001, fill −9999; Fmask uint8, fill 255 **[DOC]**. Fmask bits 1 cloud, 2 adjacent, 3 shadow **[DOC, secondary: NASA-IMPACT `hls-vi` code citing User Guide v2 Table 9]**. S30 NIR narrow = `B8A` **[DOC]**. |
| Unresolved | Fmask bits 0 and 4–7; L30 NIR band name (`B05` expected); VI back-processing completeness 2013–2019. |
| Recommended decision | Use **HLS-VI as primary**, with its bundled Fmask. Mask bits 1–3 now; enable 4–5 after Test H-5. Fall back to SR-computed indices only where VI is missing (Test H-3). |

### D5.4 SSURGO aggregation methodology

| Type | Content |
|---|---|
| Verified facts [LIVE] | `GetClippedMapunits` returns clipped map-unit geometries per mukey, with several rows per mukey possible. `STArea()` returns degree². Direct geography intersection fails with a type clash. `muaggatt` provides `aws0100wta`, `aws0150wta`, `drclassdcd`, `hydgrpdcd`. Component and horizon columns, including `_l`/`_h`, are available. |
| Recommended decision | **Decided:** DATA_ARCHITECTURE §5.3.1. Major components only; weight = area_fraction × comppct_r/100; fixed depth intervals 0–30/30–100/100–150 cm with an 80% horizon-coverage rule; texture class from aggregated fractions; categorical values by maximum weight; AWS from `muaggatt`; quality thresholds by null weight. |

### D5.5 CropScape coordinate transformation and response parsing

| Type | Content |
|---|---|
| Verified facts [LIVE] | `GetCDLValue` needs EPSG:5070 x/y; lon/lat fails. The responses are XML wrapping non-JSON object literals. `GetCDLStat` files have unquoted keys. Errors arrive as `<faultstring>` with HTTP 200. Fips requests answer in ~1–1.5 s. Bbox requests timed out twice. One value call hung for more than 100 s, then succeeded on retry. |
| Recommended decision | **Decided:** use `pyproj` with `always_xy=True` to EPSG:5070; regex/XML parsing per INTEGRATION_GUIDE §3; county-fips GeoTIFFs only; local clipping; 30 s / 120 s timeouts with 3 retries; responses cached. |

### D5.6 Agronomic thresholds and growing-season assumptions

| Type | Content |
|---|---|
| Verified facts | None yet. No agronomic threshold has been verified against a primary source in Phase 0. |
| Recommended *starting points* | Every value below is **[UNVERIFIED]** and must be replaced by a cited KB value in Phase 4/5. |

| Crop | Season window | GDD base/cap |
|---|---|---|
| Winter wheat | ~Sep/Oct → Jun/Jul | base 0 °C |
| Corn | ~Apr → Sep | base 10 °C / cap 30 °C (the "50/86 °F" convention) |
| Grain sorghum | ~May/Jun → Oct | base 10 °C |
| Soybeans | ~May → Oct | base 10 °C |

- The heat-stress day threshold (Tmax > 35 °C) is a heuristic and must be labelled as such or cited.
- pH, drainage and AWS thresholds per crop: to be sourced from K-State Research and Extension / NRCS in Phase 5.

**Blocking status:** blocks Phase 4/5 calculations only. **Does not block Phase 1–3**, because the contract carries the season window and thresholds as data.

### D5.7 Resilience score methodology

**Recommended decision (frozen framework, DATA_ARCHITECTURE §5.10):**
- Five components with absolute, cited-or-labelled breakpoints mapped to 0–100.
- Bands: < 40 low, 40–70 moderate, > 70 high.
- Equal-weight composite, computed only if ≥ 4 of 5 components are available.
- Confidence from support class and completeness.
- No cross-field ranking.

**Unresolved:** breakpoint values (Phase 4). This does not block the UI.

### D5.8 Dataset credentials and rate limits

| Dataset | Credential | Limits |
|---|---|---|
| POWER | None **[LIVE]** | ≤ 20 parameters per point request **[DOC, client docs]**; throttles rapid requests; no numeric limit published |
| SDA | None **[LIVE]** | Row/time limits exist; values **[UNVERIFIED]**. Batch ≤ 50 fields. |
| CropScape | None **[LIVE]** | Not published; intermittent slowness observed **[LIVE]**. Cache county files. |
| CSB | None **[DOC]** | One-time download |
| PRISM | None **[LIVE]** | Not published; one file per variable-day |
| HLS / SMAP / SRTM | NASA Earthdata Login (`.netrc`) | Not published for HTTPS downloads **[UNVERIFIED]** |
| OpenET (P1) | API key (`Authorization` header) **[DOC]** | Tier 1: 100 queries/month, 50,000 acres/request, 20/min, 500/h; multipolygon endpoints temporarily disabled (changelog v3.2.2) |
| Quick Stats (P1) | API key **[LIVE: unauthorized without]** | 50,000 records/request **[DOC]** |

**Owner:** one team service account per provider (Q3 below). Secrets live in `.env` / `.netrc` only.

### D5.9 Remaining open questions (non-blocking for Phase 1)

| ID | Question | Default |
|---|---|---|
| Q1 | Do Space Apps rules allow CSB and 3DEP, which are not on the supplied list? | Use them; manual fallback exists |
| Q2 | Where is the official challenge resource document? It was not in the project folder. | Proceed on the brief's list |
| Q3 | Which team account owns Earthdata, OpenET and Quick Stats credentials? | One shared service account |
| Q5 | Do judges want resilience component weights other than equal? | Equal, labelled "prototype" |
| U-UI-1 | Basemap tile provider (key-free) | Blank/simple style in Phase 1 |
| U-UI-2 | Styling preference (Tailwind assumed) | Tailwind |

Earlier questions closed by this audit:
- Q4 thresholds → D5.6.
- Q6 user-drawn fields → D5.2.
- Q7 CDL smoke test → D5.5.
- Q8 → Source Register §3.

---

## D6. Consistency audit (2026-11-14): findings and corrections

| # | Finding | Type | Resolution |
|---|---|---|---|
| A1 | The architecture said the 15 m inward buffer was a CSB convention. It is the Crop Frequency Layers' convention. | Error | Corrected (ARCH §5.2) and given a small-field rule |
| A2 | POWER extraction claimed "bilinear interpolation, the API's own behaviour". This is unverified and contradicted the containing-cell rule. | Contradiction | Now `api_point_query`, with no claim about POWER's interpolation (ARCH §5.4) |
| A3 | SSURGO area fractions depended on an unverified macro; the aggregation rule was under-specified. | Missing decision | Verified the `GetClippedMapunits` macro; normative §5.3.1 added |
| A4 | HLS-VI IDs, Fmask presence and scale factors were unverified. | Gap | Verified (LIVE/DOC); masking policy defined; Test H-5 added |
| A5 | CropScape bbox was documented as usable. It times out live. | Risk | Fips-only decision (T16); parsing rules documented |
| A6 | CSB format, attributes and CRS were unknown; the guide used a WGS84 bbox on an Albers layer. | Gap / error | Documented; attribute filter plus reliability filter added (GUIDE §4) |
| A7 | No resilience methodology beyond component names. | Missing decision | Framework frozen (ARCH §5.10) |
| A8 | No crop recommendation methodology at all. | Missing decision | Framework frozen (ARCH §5.11); KB citation rule |
| A9 | The DB design lacked farms, jobs, indicators, KB, scenarios, recommendations and evidence tables. | Gap | Added (ARCH §6.9) |
| A10 | The resilience example used an invalid UUID (`…p1`). | Error | Fixed |
| A11 | Missing-reason vocabulary lacked API states (not computed, outside AOI, pending). | Gap | Added; the API contract is authoritative |
| A12 | Storage contracts (ARCH §6) and API contracts could drift. | Risk | Scope note added; one-to-one mapping via shared blocks |
| A13 | The "precompute demo" decision conflicted with letting users add fields. | Contradiction | User fields restricted to the AOI; on-demand subset defined (T20, ARCH §7) |
| A14 | OpenET quotas were unknown; its own docs conflict on the v2.1 start year. | Gap | Quotas documented; start year left as UNVERIFIED |
| A15 | SMAP climatology covers only 2015 onward (~10 years). Percentiles are weak. | Scientific risk | `sm_rootzone_percentile` is labelled R and low confidence; the resilience framework uses dry-day counts alongside it |
| A16 | Temporal standards mix: POWER is LST, SMAP is UTC. | Consistency | Carried in `TemporalSupport.time_standard`; daily SMAP means stay in UTC days |

No contradiction was found in dataset priorities, region selection, or spatial and temporal resolutions, beyond the items above.

---

## D7. Revised phase plan and implementation dependency graph

**Phases:**

| Phase | Scope |
|---|---|
| 0 | Contract freeze (this document) |
| 1 | UI skeleton with mocks |
| 2 | Backend, database and API foundation |
| 3 | Dataset ingestion |
| 4 | Indicators and resilience |
| 5 | Crop KB and rotation engine |
| 6 | Frontend–backend integration |
| 7 | Testing, deployment and submission |

```
P0 Contracts frozen (API_CONTRACTS v1.0.0-phase0, UI_ARCHITECTURE)
 ├──▶ P1 UI skeleton (mock services) ─────────────────────────────────────────────┐
 ├──▶ P2 Backend foundation: Pydantic models ▸ FastAPI routes (serving fixtures)   │
 │        ▸ PostGIS schema ▸ OpenAPI export + TS diff (contract test)              │
 │          │                                                                      │
 │          ├──▶ P3 Ingestion (independent tracks):                                │
 │          │      CSB fields ─┬─▶ SDA soil ─┐                                     │
 │          │                  ├─▶ CDL history ─┐                                  │
 │          │                  ├─▶ SRTM terrain ┤                                  │
 │          │                  └─▶ HLS-VI veg ──┤                                  │
 │          │      POWER climate (centroids) ───┤                                  │
 │          │      SMAP L4 cells ───────────────┤                                  │
 │          │                                   ▼                                  │
 │          │      P4 Indicators ─▶ Resilience (needs breakpoints, D5.7)           │
 │          │                         │                                            │
 │          │      P5 Crop KB (cited thresholds, D5.6) ─▶ Rotation engine          │
 │          │                         │          (needs P4 indicators + CDL)       │
 │          ▼                         ▼                                            ▼
 └────────────────────────────▶ P6 Integration: swap mock → http services ◀───────┘
                                       ▼
                                P7 Testing · deployment · submission
```

| Task | Can start when | Independent of |
|---|---|---|
| P1 UI skeleton | Now (contracts frozen) | All backend work |
| P2 Pydantic models + routes | Now | P1 (both follow the contract doc) |
| P2 PostGIS schema | Now | P1 |
| P3 POWER, SMAP, SRTM AOI mosaic, CSB download, Earthdata/OpenET/Quick Stats accounts | P2 storage tables exist (or local files first) | Each other |
| P3 SDA, CDL, HLS zonal stats | CSB demo fields selected | Each other |
| P4 indicators | Their input datasets are ingested | P5 KB research |
| P4 resilience scoring | P4 indicators + breakpoint table | — |
| P5 KB research and citation | **Now** (research only; no dependency on data) | Everything else |
| P5 rotation engine | KB + P4 indicators + CDL history | — |
| P6 integration | P2 routes return real data for an endpoint | Can proceed endpoint by endpoint |

**Rules:**
- **API contracts before services:** satisfied, since the contracts are frozen.
- **Ingestion before calculations:** P4 reads only stored observations, never upstream APIs.
- **Indicators before scoring:** the resilience engine consumes `indicators` rows only.
- **KB before recommendations:** the engine refuses to run on KB entries that lack citations (`status: "insufficient_data"`).

## D8. Authentication decision

No user accounts in the MVP. There is one demo workspace with two farms (one per AOI). All mutating endpoints (E5, E8, E10, E23–E25) are open but rate-limited at the API (implementation detail for Phase 2). Supabase is accessed only by FastAPI, using a server-side key.

---

## D9. Final page and component architecture (summary)

Full specification: SOILSTICE_UI_ARCHITECTURE §3–4.

| Page | Route | Primary endpoints | Phase 1 mock |
|---|---|---|---|
| Landing | `/` | E2 | Full |
| Main Dashboard | `/dashboard` | E6 | Full |
| Field Explorer | `/fields`, `/fields/[id]` | E7, E11 | Full |
| Environmental Intelligence | `/fields/[id]/environment` | E13–E16, E18 | Full |
| Resilience Analysis | `/fields/[id]/resilience` | E19, E26 | Full (synthetic scores) |
| Rotation Lab | `/fields/[id]/rotation` | E17, E20–E25 | History/recommendations full; scenario evaluation canned |
| Reports & Evidence | `/fields/[id]/report`, `/evidence` | E11, E19, E21, E26, E2 | Full |
| Farm & Settings | `/settings` | E3–E5, E8, E10, E27 | Rename/delete in memory; add-field validation real, job simulated |

Shared components:
- `QuantityValue`
- `SupportBadge`
- `SourceChip`
- `QualityIndicator`
- `IndicatorCard`
- `TimeSeriesChart`
- `CoverageTable`
- `ScoreBandPill`
- `CropTimeline`
- `FieldMap`
- `EvidenceList`
- `StateBoundary`

## D10. API contract overview

Full specification: SOILSTICE_API_CONTRACTS.

- Envelope `ApiResponse<T>` with `meta.data_mode`. Errors use `ApiErrorResponse` with stable codes.
- Building blocks: `Quantity`, `SourceRef` (product + version), `SpatialSupport` (support class + resolution + extraction), `TemporalSupport`, `QualityInfo` (status, flags, completeness, missing reason), `Uncertainty`, `MethodRef`, `TimeSeries`.
- Entities:
  - `Farm` / `FarmOverview`
  - `Field` / `FieldSummary`
  - `FieldProfile`
  - `ClimateProfile`
  - `SoilProfile`
  - `TerrainProfile` (added)
  - `VegetationProfile`
  - `CropHistory`
  - `EnvironmentalIndicator`
  - `DataCoverage`
  - `ResilienceProfile`
  - `RotationScenario`
  - `RotationRecommendation`
  - `EvidenceItem`
  - `DatasetDescriptor`
  - `CropOption`
  - `ProcessingJob`
- 27 endpoints under `/api/v1`, plus six frontend service interfaces.

## D11. Remaining risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CropScape (GMU host) slow or unavailable during ingestion | Medium (observed) | High for crop history | County files cached once; Source Cooperative / NASS bulk mirrors as fallback |
| CSB ruled ineligible by challenge rules | Low–medium | Medium | Manual polygon path (D5.2), same pipeline |
| HLS-VI archive incomplete before 2020 | Medium | Medium (vegetation stability component) | Test H-3; compute from SR; reduce the CV window and lower the confidence |
| Fmask bits 4–5 misassigned | Low | Medium | Mask only bits 1–3 until Test H-5 |
| SMAP L4 download volume (global granules) | Medium | Medium | Cell-only extraction; test Harmony subsetting; limit to the seasons shown |
| Agronomic thresholds not cited in time | Medium | High for credibility | Start KB research now in parallel (P5 has no data dependency); ship fewer crops with cited rules rather than more without |
| Resilience scores misread as field measurements | Medium | High (scientific honesty) | Support badges, confidence, R-component caps, disclaimers, no cross-field ranking |
| Contract drift between TS and Pydantic | Medium | Medium | OpenAPI → TS diff in CI from Phase 2 |
| OpenET quota (100/month) exhausted | Low | Low (P1) | One request per demo field, cached |
| Mock data mistaken for real | Low | High | Non-dismissable banner, `dataset_id: "synthetic"`, synthetic geometry |

---

## D12. Phase 0 exit checklist

| # | Item | Status |
|---|---|---|
| 1 | Dataset research, priorities and exclusions documented with verification labels | ✅ |
| 2 | Demonstration region selected with live evidence | ✅ |
| 3 | Variable-to-dataset matrix and processing pipeline specified | ✅ |
| 4 | SSURGO aggregation methodology normative | ✅ (§5.3.1) |
| 5 | CropScape transformation, parsing and acquisition strategy decided | ✅ (T16) |
| 6 | HLS product, assets and masking policy decided (bits 4–5 pending Test H-5) | ✅ with a tracked test |
| 7 | CSB access, attributes, reliability filter and fallback decided | ✅ (eligibility: Q1, non-blocking) |
| 8 | Resilience methodology framework frozen | ✅ (breakpoints in Phase 4) |
| 9 | Rotation recommendation methodology framework frozen | ✅ (KB content in Phase 5) |
| 10 | Credentials and rate limits documented | ✅ |
| 11 | API contracts frozen (TS + Pydantic, envelope, errors, endpoints, services) | ✅ v1.0.0-phase0 |
| 12 | UI architecture: routes, pages, components, states, mock rules | ✅ |
| 13 | Dependency graph and phase plan | ✅ (D7) |
| 14 | No application code, dependencies, config or git operations | ✅ |
| 15 | **Team sign-off** on D1–D10 and answers or defaults for Q1, Q3 | ☐ **Pending: team** |

## D13. Recommended Phase 1 implementation sequence

1. **Scaffold** the Next.js (App Router, TS strict) project with Tailwind, MapLibre GL, Recharts and TanStack Query, plus the lint rule blocking `services/mock` imports (UI_ARCHITECTURE §1.4).
2. **`types/contracts.ts`:** transcribe API_CONTRACTS §2–5 exactly.
3. **Service interfaces and factory:** `services/types.ts` and `services/index.ts` (`NEXT_PUBLIC_DATA_MODE`).
4. **Seeded mock generator and mock services** per API_CONTRACTS §8: all coverage, partial, processing, failed and insufficient-data states, plus `mock_error` / `mock_latency` support.
5. **Shared components:** `QuantityValue`, `SupportBadge`, `SourceChip`, `QualityIndicator`, `StateBoundary`, `IndicatorCard`, `TimeSeriesChart`, `CoverageTable`, `ScoreBandPill`, `CropTimeline`, `FieldMap`, `EvidenceList`.
6. **App shell** with `DataModeBanner`, the farm switcher and `FieldLayout`.
7. **Pages, in demo-critical order:** Dashboard → Field Explorer/Overview → Environmental Intelligence → Resilience → Rotation Lab → Report & Evidence → Settings → Landing.
8. **Phase 1 acceptance check** (UI_ARCHITECTURE §6).

In parallel, without waiting for Phase 1:
- Phase 2 Pydantic models and fixture-serving routes.
- Creation of the three provider accounts.
- CSB download.
- Phase 5 KB literature research.

## D14. Process constraints honoured in Phase 0

- No git repository, commits, branches, remotes or pushes.
- No dependencies installed and no configuration changed.
- No application code; code blocks in the docs are specifications.
- Live checks wrote only to a scratch directory outside the project.
- The only project files written are the six documents in `docs/`.
- No sample data that could pass for observations: every example is marked `_example`, and mock rules require a synthetic flag.
