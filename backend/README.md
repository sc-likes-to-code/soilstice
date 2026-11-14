# SOILSTICE backend (Phase 2)

FastAPI implementation of contract **v1.0.0-phase0** (`docs/SOILSTICE_API_CONTRACTS.md`), with the first real-data
integrations: **USDA SSURGO (Soil Data Access), USDA NASS CDL (CropScape), NASA POWER and NASA SRTM**.
Progress, decisions and limitations: `docs/PHASE_2_HANDOVER.md`.

## Run

```bash
cd backend
py -3.13 -m venv .venv                       # Python >= 3.11
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000/api/v1` · interactive docs: `http://localhost:8000/api/v1/docs`
- Configuration: `.env.example` (copy to `backend/.env`). SRTM needs NASA Earthdata credentials.

## Test

```bash
.venv/Scripts/python -m pytest              # offline: synthetic fakes, no network
.venv/Scripts/python -m pytest -m live      # real upstream calls (SSURGO, POWER, CDL; SRTM if a token is set)
.venv/Scripts/ruff check app tests scripts
```

Contract checks (from the repo root): `npm run contract:openapi`, `npm run contract:fixtures`, `npm run contract:check`.

## Layout (four approved layers)

| Path | Layer / role |
|---|---|
| `app/contracts/` | Pydantic wire contracts (mirror `src/types/contracts.ts`) |
| `app/api/`, `app/main.py` | HTTP API: routes, envelope, errors, request IDs, rate limit |
| `app/services/` | Data services: orchestration, field pipeline, coverage, evidence |
| `app/repositories/` | Storage interfaces + SQLite document store (PostGIS design in `db/schema.sql`) |
| `app/providers/` | Acquisition: one module per dataset + shared HTTP (retry, raw cache, provenance) |
| `app/processing/` | Pure transforms: geometry, SSURGO aggregation, CDL zonal stats, SRTM slope, POWER aggregation |
| `app/analytics/` | Environmental analytical engine (indicators; resilience pending Phase 4 breakpoints) |
| `app/rotation/` | Rotation engine + crop-KB integration point (pending the cited KB) |

## Honesty rules enforced in code

- Missing values are `null` + `missing_reason` (validator on `Quantity`); never 0.
- POWER values are support class **R** (`api_point_query`, ~55 km / ~110 km grids), never field observations.
- No thresholds or scores are invented: resilience is `pending`, recommendations `insufficient_data`, and
  methodology-dependent indicators are `NOT_COMPUTED`.
- The backend only serves real acquisitions (`meta.data_mode: "live"`). Synthetic data exists only in tests.
