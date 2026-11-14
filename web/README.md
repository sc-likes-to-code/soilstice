# SOILSTICE web (Phase 1: UI skeleton)

Next.js frontend for SOILSTICE. Specifications live in `../docs/`, in particular:
- `SOILSTICE_UI_ARCHITECTURE.md`
- `SOILSTICE_API_CONTRACTS.md`

**Phase 1 runs entirely on synthetic data behind typed service interfaces.** Every value is labelled as synthetic, and a banner that cannot be dismissed says so on every page.

## Commands

```bash
npm install
npm run dev        # http://localhost:3000
npm run typecheck  # tsc --noEmit
npm run lint       # eslint, including the "no mock imports outside the factory" rule
npm test           # vitest: contract invariants, mock behaviour, formatting, geometry, HTTP client
npm run build      # production build (Cache Components + Partial Prefetching)
```

## Configuration

Copy `.env.example` to `.env.local`.

| Variable | Values | Purpose |
|---|---|---|
| `NEXT_PUBLIC_DATA_MODE` | `mock` (default) / `api` | Selects the service implementation in `src/services/index.ts` |
| `NEXT_PUBLIC_API_BASE_URL` | e.g. `http://localhost:8000/api/v1` | FastAPI base URL, used only when the mode is `api` |

The mock services can simulate errors and latency through query-string parameters:

| Parameter | Effect |
|---|---|
| `?mock_error=<ApiErrorCode>` | Makes service calls fail with that error code |
| `&mock_error_on=<method>` | Restricts the simulated error to methods whose name contains this text, e.g. `getClimate` |
| `?mock_latency=<ms>` | Sets the simulated response latency |

## Architecture

```
src/
  app/                    routes (thin server components; client views below)
    page.tsx              Landing
    (app)/dashboard       Dashboard
    (app)/fields          Field Explorer, plus [fieldId]/ Overview, environment, resilience, rotation, report
    (app)/evidence        Evidence & data sources
    (app)/settings        Farm & Settings (draw a field, units, data mode)
  components/
    ui/                   primitives (Card, Button, Tip, Segmented, Select, …)
    shared/               contract-typed components (QuantityValue, SupportBadge, SourceChip, IndicatorCard,
                          TimeSeriesChart, CoverageTable, CropTimeline, FieldMap, EvidenceList, StateBoundary)
    layout/               app shell, field layout, synthetic-data banner, brand
    views/                one client view per page
  hooks/                  TanStack Query hooks over the service interfaces; viewer preferences
  services/
    types.ts              service interfaces (API_CONTRACTS §7)
    index.ts              factory: the ONLY importer of services/mock (enforced by ESLint)
    http/                 fetch implementations for Phase 6
    mock/                 seeded synthetic world and generators (not the analytics engines)
  types/contracts.ts      wire contracts v1.0.0-phase0 (API_CONTRACTS §2–5)
  lib/                    formatting (display-only unit conversion), geometry helpers, vocabularies, AOI extents
```

### Layer separation
- **Presentation:** `app/`, `components/`, `hooks/`. These render contract types only. They never compute scores, bands or thresholds.
- **Data services:** `services/`. This layer swaps between mock and HTTP with no UI change.
- **Environmental analytics** (Phase 4) and **the rotation engine** (Phase 5) live in the backend. Mock generators only produce visibly synthetic outputs that are consistent enough to chart.

### Next.js 16 notes
- Cache Components is on.
- Routes under `/fields/[fieldId]` read params in client components wrapped in `<Suspense>`. Navigation reads the pathname inside a Suspense boundary.

### Maps
- MapLibre GL 5 with no basemap tiles (open item U-UI-1). A schematic one-mile section grid stands in.
- All geometry is synthetic in Phase 1.
