# SOILSTICE: UI Architecture (Phase 1 specification)

**Status:** Implementation-ready specification for Phase 1 (frontend skeleton with typed mock data). No code has been written.
**Date:** 2026-11-14
**Contracts:** [SOILSTICE_API_CONTRACTS.md](SOILSTICE_API_CONTRACTS.md). Endpoint IDs (E1–E27) and type names refer to that document.

---

## 1. UI-first strategy: compatibility verdict

**Compatible, with three conditions.**

1. **Contracts are frozen first.** SOILSTICE_API_CONTRACTS v1.0.0-phase0 is the boundary. Components render only contract types, and nothing in the UI depends on how a value is computed.
2. **Analytical outputs are opaque to the UI.**
   - Resilience scores, bands, recommendation rankings and scenario evaluations are displayed exactly as returned, with their `explanation`, `confidence`, `support_class` and `evidence_ids`.
   - The UI never computes a score, band or threshold. That keeps Phase 4/5 methodology changes from forcing UI rewrites.
3. **Synthetic data is visibly synthetic.** In mock mode a non-dismissable banner reads "Synthetic demo data: not observations", and each value whose `SourceRef.dataset_id === "synthetic"` carries a badge.

### 1.1 What must exist before Phase 1 code

All of the following are in SOILSTICE_API_CONTRACTS:
- Controlled vocabularies (§2).
- Shared building blocks (§3).
- Envelope and errors (§4).
- All entity contracts (§5).
- Endpoint list (§6).
- Service interfaces (§7).
- Mock rules (§8).

**Status: done.**

### 1.2 What depends on unresolved analytical decisions

These need no UI change when the decisions land, because the contract already carries their output.

| UI element | Depends on | Phase | UI handling until then |
|---|---|---|---|
| Resilience composite and component scores | Breakpoint tables (DATA_ARCHITECTURE §5.10) | 4 | Render the returned `score`/`band`; mocks are labelled synthetic |
| Recommendation ranking and factor bands | Crop KB thresholds and citations (PHASE_0_DECISIONS D5.6; DATA_ARCHITECTURE §5.11) | 5 | Render returned candidates; show `kb_version` |
| Scenario evaluation messages | Rotation rules | 5 | Render `year_findings` and `warnings` |
| Season window shown on climate charts | Crop calendar in the KB | 5 (defaults in 4) | Render `ClimateProfile.season` as returned |
| GDD values | GDD base/cap per crop | 4 | Display only |

### 1.3 Interactions that need real backend functionality

Mocks only simulate these:

| Interaction | Why it needs the backend |
|---|---|
| Create user field (E8) and job progress (E27) | Geometry validation against the AOI; on-demand POWER, SDA and CDL processing |
| Scenario create/update evaluation (E23/E24) | Rules engine (Phase 5) |
| Any "live" `meta.data_mode` | Real ingestion (Phase 3) |

Everything else is read-only `GET`s over precomputed data and can be built fully against mocks.

### 1.4 Preventing coupling to mock data

| Rule | Mechanism |
|---|---|
| Components never import fixtures or mock modules | Only `services/index.ts` (the factory) imports `services/mock/*`. A lint rule (`no-restricted-imports`) blocks `**/mock/**` everywhere else. |
| Components receive contract types only | Page-level hooks call services; components take typed props (`SoilProfile`, `EnvironmentalIndicator`, …). |
| No assumptions about array length, ordering or presence | Components handle empty arrays, `null` profiles and `value: null` with `missing_reason` (contract rule R5). |
| No hard-coded labels or units from fixtures | Labels come from `label` fields; units come from `Quantity.unit` through one `formatQuantity()` utility. |
| No hidden IDs | Routes use `field_id` from list responses. The mock generator creates random UUIDs per seed, so hard-coded IDs break immediately. |
| Mode switch is a single env flag | `NEXT_PUBLIC_DATA_MODE=mock\|api`; there are no `if (mock)` branches in components. |
| Errors and latency are exercised | Mock services honour `?mock_error=<ApiErrorCode>` and `?mock_latency=<ms>` (mock mode only). |

---

## 2. Frontend stack (minimal)

| Concern | Choice | Status |
|---|---|---|
| Framework | Next.js (App Router) + TypeScript (strict) | Established in brief |
| Map | MapLibre GL JS | Established (DATA_ARCHITECTURE §7) |
| Basemap tiles | **Open question U-UI-1.** Phase 1 uses a blank style or a key-free vector style. NAIP imagery tiles are P2. | Unresolved, non-blocking |
| Charts | **Recharts**: one library for time series, bars and timeline strips | Recommended |
| Data fetching / cache | **TanStack Query**: standard loading/error/retry states over the service interfaces | Recommended |
| Styling | **Tailwind CSS** | Recommended; team may substitute an existing preference |
| Validation | None at runtime in Phase 1 (TS types). From Phase 2, `openapi-typescript` (dev-only) diffs generated types against hand-written ones. | Recommended |
| Auth | None (single demo workspace; PHASE_0_DECISIONS D8) | Decided |
| PDF export | Browser print stylesheet on the report route; no PDF library | Decided |

Nothing is installed in Phase 0.

---

## 3. Information architecture

### 3.1 Route map

```
/                                   Landing
/dashboard                          Main Dashboard (active farm)
/fields                             Field Explorer: map + list
/fields/[fieldId]                   Field overview            ┐
/fields/[fieldId]/environment       Environmental Intelligence │ shared FieldLayout:
/fields/[fieldId]/resilience        Resilience Analysis        │ field header + tab bar +
/fields/[fieldId]/rotation          Rotation Lab               │ field switcher
/fields/[fieldId]/report            Field report (printable)   ┘
/evidence                           Evidence & data sources (global)
/settings                           Farm & Settings
```

**Evaluation of the proposed pages:**
- All eight proposed pages are kept, with no new pages.
- Three of them (Environmental Intelligence, Resilience Analysis, Rotation Lab) are **field-scoped tabs**, because each one analyses one field. This avoids duplicate field pickers.
- "Reports & Evidence" is split across two routes: the per-field printable **report** and the global **evidence** registry. They are two views of one area under one nav item.
- The active farm comes from E3 (MVP: exactly one farm per AOI; the farm switcher lists the two AOIs).

### 3.2 Global shell

| Component | Contents |
|---|---|
| `AppShell` | Top bar: product name, farm switcher (E3), primary nav (Dashboard, Fields, Evidence, Settings) |
| `DataModeBanner` | Shown when `meta.data_mode === "synthetic"`. Not dismissable. |
| `FieldLayout` | Field header (name, area, source badge, processing status, coverage completeness), tab bar (Overview, Environment, Resilience, Rotation, Report), field switcher |

### 3.3 Shared components (contract-typed)

| Component | Props (contract types) | Notes |
|---|---|---|
| `QuantityValue` | `Quantity` | Formats value plus unit. If `value === null`, shows "—" with a tooltip from `missing_reason`. Shows ± from `uncertainty`. |
| `SupportBadge` | `SpatialSupport` | F = "Field", S = "Local grid (≈4 km)", R = "Regional context (≈9–50 km): not a field measurement". Resolution comes from `native_resolution_m`. |
| `SourceChip` | `SourceRef` | Product + version, link to the evidence item. "Synthetic" variant. |
| `QualityIndicator` | `QualityInfo` | Status dot + flags list + completeness |
| `IndicatorCard` | `EnvironmentalIndicator` | Label, `QuantityValue`, `reference_value` delta, `SupportBadge`, `SourceChip`, method popover |
| `TimeSeriesChart` | `TimeSeries` | Line or bar, optional `reference` overlay. Null points render as gaps, never zeros. |
| `CoverageTable` | `DataCoverage` | Per-dataset status, support, resolution, period, version |
| `ScoreBandPill` | `ScoreBand` / `FitBand` + `Confidence` | Never shown without confidence |
| `CropTimeline` | `CropYear[]` | Year strip coloured by crop; low-purity hatch; CSB disagreement marker |
| `FieldMap` | `FieldSummary[]` + selection | MapLibre GeoJSON layer; colour by `resilience_band` or `latest_crop` |
| `EvidenceList` | `EvidenceItem[]` | Grouped by `kind`; shows `verification_status` |
| `StateBoundary` | — | Uniform loading skeleton / error (with retry if `retryable`) / empty patterns |

### 3.4 Uniform state rules

| State | Rule |
|---|---|
| Loading | Skeletons matching final layout. Never spinners alone. A card loads independently of its siblings. |
| Error | Message from `ApiError.message` + `code`. Retry button only if `retryable`. A page-level error appears only when the primary resource fails, such as E9 `Field` 404, which shows "Field not found". |
| Empty | A specific message per component, e.g. "No accepted HLS scenes for 2025 (cloud cover)" derived from `missing_reason`, not a generic "No data". |
| Partial | `quality.status === "partial"` shows an inline warning listing `flags`. |
| Processing | `processing_status === "processing"` shows the job steps (E27, polled every 3 s while running, stopped on terminal status). |

---

## 4. Page specifications

### 4.1 Landing (`/`)

| Aspect | Specification |
|---|---|
| Purpose | Explain SOILSTICE in under one minute and route judges or users into the dashboard |
| Sections | Hero (value statement + "Open demo farm" CTA) · How it works (fields → NASA/USDA data → indicators → resilience & rotation) · Data sources strip (from E2, grouped by priority, NASA products first) · Scientific honesty note (field vs regional support) · Team/challenge footer |
| Data | E2 `DatasetDescriptor[]` (optional; the static copy can stand alone) |
| States | Loading: data strip skeleton · Error: hide the strip, keep the page · Empty: n/a |
| Phase 1 mock | Fully static plus mocked E2 |

### 4.2 Main Dashboard (`/dashboard`)

| Aspect | Specification |
|---|---|
| Purpose | Farm-level situation at a glance: which fields need attention, and how complete the data is |
| Sections | KPI row (field count, total area, average coverage, fields by resilience band) · `FieldMap` coloured by resilience band · Field table (name, area, latest crop, band, coverage, status; sortable; row → field overview) · Alerts (`FarmOverview.alerts`) · Regional context panel (`regional_context` indicators, always R-badged) · Data coverage summary (`coverage_summary`) |
| Data | E6 `FarmOverview` (single call; no N+1) |
| States | Loading: KPI + map + table skeletons · Error: page-level (primary resource) · Empty: "No fields yet. Add a field in Settings" + link |
| Phase 1 mock | Fully mockable |

### 4.3 Field Explorer (`/fields`) and Field overview (`/fields/[fieldId]`)

| Aspect | `/fields` | `/fields/[fieldId]` (Overview tab) |
|---|---|---|
| Purpose | Find and select fields spatially | One-screen summary of a field |
| Sections | Full-height `FieldMap` + side list with filters (source, status, latest crop, band) + search by name | Header (FieldLayout) · Coverage card (`CoverageTable` condensed) · Crop history strip (`CropTimeline`) · Soil summary (texture class, AWS 0–150, drainage, pH, OM with `SupportBadge` F) · Terrain summary · Key climate indicators (R-badged) · Vegetation summary (peak NDVI, peak date) · Resilience band + "View analysis" |
| Data | E7 | E11 `FieldProfile` |
| States | Empty: "No fields match filters" / "No fields" | Profile sections are individually nullable; a null section shows its coverage `missing_reason` |
| Phase 1 mock | Fully mockable | Fully mockable |

### 4.4 Environmental Intelligence (`/fields/[fieldId]/environment`)

| Aspect | Specification |
|---|---|
| Purpose | Inspect the environmental evidence for one field and season, with explicit resolution and quality |
| Sections (sub-tabs) | **Climate:** season selector (year), precipitation monthly bars + normal overlay, Tmax/Tmin lines, cumulative GDD, indicator cards (precip anomaly, GDD, heat-stress days, ET₀, water balance). Banner shows the authoritative source (POWER→PRISM). **Soil moisture:** SMAP root-zone daily series with a permanent "Regional context: 9 km" badge; percentile and dry-day cards. **Vegetation:** index selector (NDVI default, EVI, NDMI), scene scatter + accepted-scene line, phenology markers, scene table (date, product, clear fraction, accepted, mask counts). **Soil & terrain:** layer table (0–30/30–100/100–150 cm) with ranges, map-unit shares, drainage/hydro group, terrain stats. |
| Data | E13 `ClimateProfile`, E16 `VegetationProfile`, E14 `SoilProfile`, E15 `TerrainProfile`, E18 (optional, for cards) |
| States | Each sub-tab loads independently. Vegetation empty → reason (e.g., `INSUFFICIENT_COVERAGE`). SMAP before 2015-03-31 → `OUT_OF_TEMPORAL_RANGE` message. OpenET cards show "Not yet integrated (P1)" from coverage `not_integrated`. |
| Phase 1 mock | Fully mockable (synthetic series) |

### 4.5 Resilience Analysis (`/fields/[fieldId]/resilience`)

| Aspect | Specification |
|---|---|
| Purpose | Show *why* a field is more or less resilient, component by component, with confidence and support class |
| Sections | Composite card (band, score, confidence, "n of 5 components used") · Component list (5 rows: band pill, score, support badge, confidence, explanation, inputs → links to indicator cards/evidence) · Limitations panel (`limitations` flags) · Disclaimers · Method summary (model_version, link to evidence `method` items) |
| Data | E19 `ResilienceProfile`; E26 filtered by `related_id` for drill-down |
| States | `status: "insufficient_data"` → composite hidden; show which components are missing and why · `pending` → "Analysis not yet computed" |
| Not allowed | Radar charts or a single unexplained number. No ranking of fields against each other. |
| Phase 1 mock | Mockable (synthetic, banner). Methodology-dependent values are never hard-coded in components. |

### 4.6 Rotation Lab (`/fields/[fieldId]/rotation`)

| Aspect | Specification |
|---|---|
| Purpose | Review crop history, see explained next-season options, and test alternative rotations |
| Sections | **History:** `CropTimeline` 2006–2025 + rotation metrics (distinct crops, max monoculture run, Shannon). **Next-season options:** ranked `RecommendationCandidate` cards (overall fit band + confidence, factor table with observed vs requirement and support badge, rotation effects, reasons, evidence links); excluded crops with reasons; disclaimers ("not a yield or profit forecast"). **Scenario builder:** start year + 2–8 year sequence of crop selects (E20), save → evaluated scenario (E23/E24); evaluation panel (overall, 4 dimensions, per-year findings, warnings); list of saved scenarios; compare two scenarios side by side (dimension bands only). |
| Data | E17, E21, E20, E22–E25 |
| States | Recommendation `pending`/`insufficient_data` → explanatory empty state · Scenario 422 → inline field errors · No scenarios → "Build your first rotation" |
| Phase 1 mock | History & recommendations: mockable. Scenario CRUD: mock in-memory with a canned evaluation, clearly labelled. **Real evaluation needs Phase 5.** |

### 4.7 Reports & Evidence

**Field report (`/fields/[fieldId]/report`).**

| Aspect | Specification |
|---|---|
| Purpose | A printable, citable one-to-three-page field summary for judges, advisors or farmers |
| Sections | Field identity + map snapshot · Data coverage table · Soil & terrain · Season climate (with R badges) · Vegetation summary · Resilience components · Next-season options · Source list (all `SourceRef`s, deduplicated, with versions and DOIs) · Generated timestamp, contract/model/KB versions, data mode |
| Data | E11 + E19 + E21 + E26 |
| Export | Browser print (`@media print` stylesheet). No server PDF in the MVP. |
| States | Sections omitted gracefully with a "not available: reason" line |
| Phase 1 mock | Fully mockable |

**Evidence registry (`/evidence`).**

| Aspect | Specification |
|---|---|
| Purpose | Global transparency: every dataset and method SOILSTICE uses, with verification status |
| Sections | Dataset table (E2: product, version, priority, support class, resolution, coverage, verification, integration status) · Methods & rules (evidence items of `kind` `method`/`kb_rule`) · Known limitations (static, from DATA_ARCHITECTURE §8) |
| Data | E2, E26 (global items, `field_id: null`) |
| Phase 1 mock | Fully mockable; the dataset rows can be real descriptors from the Source Register, since those are metadata, not observations |

### 4.8 Farm & Settings (`/settings`)

| Aspect | Specification |
|---|---|
| Purpose | Manage the demo farm and its fields; display preferences; data attribution |
| Sections | Farm name (E5) · AOI info (read-only) · Fields table with source; delete for `editable` fields only (E10) · **Add field:** draw a polygon on `FieldMap` (MapLibre draw interaction) → validate client-side (closed ring, inside AOI bbox, ≤ 260 ha) → E8 → job progress (E27) · Display preferences: units (metric/US customary, display-only, stored in `localStorage`) · Data mode indicator + API base URL (read-only) · Attribution and licences |
| States | 422 errors mapped to drawing hints (`OUTSIDE_AOI`, `FIELD_TOO_LARGE`, `GEOMETRY_INVALID`) · Job `partial` → per-dataset step list showing which datasets are unavailable for custom fields (HLS, SMAP, SRTM until processed) |
| Phase 1 mock | Farm rename and delete: in-memory. Add field: geometry validation real (client), job simulated. **Real processing needs Phase 2/3.** |

---

## 5. Frontend module layout (to be created in Phase 1, not now)

```
app/                      routes per §3.1 (page.tsx files compose hooks + components only)
components/shared/        §3.3 components
components/<page>/        page-specific components
services/types.ts         service interfaces (API_CONTRACTS §7)
services/index.ts         factory: NEXT_PUBLIC_DATA_MODE → mock | http   (only importer of mock/)
services/mock/            seeded generator + mock implementations (API_CONTRACTS §8)
services/http/            fetch implementations (Phase 6)
types/contracts.ts        hand-written contract types (API_CONTRACTS §2–5)
lib/format.ts             formatQuantity, unit display conversion, date formatting
hooks/                    TanStack Query hooks per service method
```

---

## 6. Phase 1 acceptance criteria

1. Every route in §3.1 renders in mock mode, including loading, error (each `ApiErrorCode` via `mock_error`), empty, partial and processing states.
2. No component imports from `services/mock/**` (lint passes).
3. Every displayed number goes through `QuantityValue` / `formatQuantity`, and every environmental value shows a `SupportBadge` and `SourceChip`.
4. The synthetic banner is visible on every page in mock mode.
5. `types/contracts.ts` matches SOILSTICE_API_CONTRACTS v1.0.0-phase0 exactly (reviewed field by field).
6. The print view of the report route fits on A4/Letter without clipped content.
7. Switching `NEXT_PUBLIC_DATA_MODE=api` compiles. It fails at runtime with a clear "API unavailable" state, not a crash.
