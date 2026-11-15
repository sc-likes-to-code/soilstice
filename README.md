# SOILSTICE

**Precision Environmental Intelligence, Agronomic Resilience & Crop Rotation Engine**

[![Next.js](https://img.shields.io/badge/Next.js-16.4.6-black?style=flat&logo=next.js)](https://nextjs.org/)
[![Turbopack](https://img.shields.io/badge/Turbopack-Ready-blueviolet?style=flat)](https://nextjs.org/docs/app/api-reference/turbopack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.13-3776AB?style=flat&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![Tests](https://img.shields.io/badge/Tests-364%20Pytest%20%7C%2027%20Vitest-success?style=flat)](https://github.com/sc-likes-to-code/soilstice)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)](LICENSE)

---

## Overview

**SOILSTICE** is an enterprise-grade agronomic intelligence and crop suitability platform designed for regenerative agriculture, soil health assessment, and long-term crop rotation planning. 

By unifying high-resolution multi-depth soil moisture data, federal soil surveys, satellite crop history, elevation modeling, and daily agrometeorology, SOILSTICE delivers auditable, transparent, evidence-backed decision support for farm operators, agronomists, and agricultural researchers.

The platform is built on strict scientific honesty: **no fabricated scores, no unstated interpolation, and no black-box outputs**. If data is absent or spatially uncalibrated, SOILSTICE withholds the composite score and cites the precise missing reason, adhering to Liebig’s Law of the Minimum and peer-reviewed agronomic benchmarks.

---

## Key Modules & Core Capabilities

```
                                 ┌────────────────────────────────────────┐
                                 │            SOILSTICE ENGINE            │
                                 └──────────────────┬─────────────────────┘
                                                    │
        ┌─────────────────────────┬─────────────────┴───────────────┬─────────────────────────┐
        ▼                         ▼                                 ▼                         ▼
┌───────────────┐       ┌───────────────────┐             ┌───────────────────┐     ┌───────────────────┐
│ Environmental │       │    Resilience     │             │ Crop Suitability  │     │   Rotation Lab    │
│ Intelligence  │       │     Composite     │             │   (Liebig's Law)  │     │  (Multi-Year Sim) │
├───────────────┤       ├───────────────────┤             ├───────────────────┤     ├───────────────────┤
│ • Meteomatics │       │ • Soil Water      │             │ • 14 Canonical    │     │ • Multi-tier Rank │
│   4-depth SM  │       │   Buffer (25%)    │             │   Crops           │     │ • 2-8 Year Plans  │
│ • NASA POWER  │       │ • Terrain Erosion │             │ • Hard Constraint │     │ • Shannon Index   │
│   ET0 / Precip│       │   Risk (25%)      │             │   Filtering       │     │ • Legume Balance  │
│ • SSURGO Soil │       │ • Climate         │             │ • Explanatory     │     │ • Nitrogen Budget │
│ • SRTM Slope  │       │   Exposure (25%)  │             │   Limitations     │     │ • Disease Breaks  │
│ • CDL History │       │ • Rotation        │             │ • Confidence      │     │ • Monoculture     │
│               │       │   Diversity (25%) │             │   Ratings         │     │   Penalties       │
└───────────────┘       └───────────────────┘             └───────────────────┘     └───────────────────┘
```

### 1. Meteomatics-First Environmental Intelligence
- **Multi-Depth Soil Moisture Profile:** Live and historical time series at four distinct depths:
  - Surface: `-5 cm` (seed germination & early emergence)
  - Active Root Zone: `-15 cm` (early vegetative growth)
  - Subsoil Moisture: `-50 cm` (mid-season root expansion)
  - Deep Water Storage: `-150 cm` (taproot buffer during drought stress)
- **Daily Agrometeorology (NASA POWER):** Precipitation totals, vapor pressure deficit, relative humidity, growing degree days (GDD), and Penman-Monteith reference evapotranspiration ($ET_0$) with seasonal water balance ($P - ET_0$).
- **Taxonomic Soil Characterization (USDA NRCS SSURGO SDA):** Available water capacity (AWC), soil texture classification, organic matter percentage, drainage class, pH profiles, and hydric status.
- **Topographic & Terrain Risk (NASA SRTM GL1 30m):** Digital elevation model, mean slope, 90th percentile slope ($P_{90}$), and RUSLE K-factor erodibility.
- **Cropland History (USDA NASS CDL):** 5-year automated satellite crop sequence classification.

### 2. 4-Component Agronomic Resilience Engine
Quantifies a field’s structural buffering capacity against climate and abiotic stress:
- **Equal-Weight Base Formulation:** Each of the 4 components carries an equal base weight of $25\%$ ($w_i = 0.25$):
  1. *Soil Water Buffer:* AWC, root-zone depth, drainage rating, and clay content.
  2. *Terrain Erosion Risk:* Topographic slope steepness, $P_{90}$, and soil erodibility.
  3. *Climate Exposure:* 10-year drought return intervals, extreme heat days ($T_{\max} \ge 35^\circ\text{C}$), and precipitation volatility.
  4. *Rotation Diversity:* 5-year historical crop rotational complexity and cover crop integration.
- **Strict Evidence Quorum:** A composite resilience score requires at least **3 of 4 components ($\ge 75\%$)** with valid data. If fewer than 3 components are present, the composite is honestly withheld (`insufficient_data`).
- **Dynamic Re-normalization:** When 3 components are valid, weights proportionally normalize ($1/k$ where $k = 3$) without penalizing the grower for missing optional data.
- **Calibrated Agronomic Bands:** High Resilience ($\ge 75$), Moderate Resilience ($55–74$), Low Resilience ($35–54$), and Vulnerable ($< 35$).

### 3. Phase 6 Crop Suitability Engine
- Evaluates **14 canonical agricultural crops** (Corn, Soybeans, Winter Wheat, Spring Wheat, Grain Sorghum, Sunflowers, Canola, Alfalfa, Barley, Oats, Cereal Rye, Cotton, Peanuts, and Dry Edible Beans).
- **Liebig’s Law of the Minimum:** The overall suitability score is bounded by the most limiting environmental or edaphic factor (e.g. soil pH, root depth, drainage, seasonal moisture deficit, or heat units).
- **Authoritative Agronomic Descriptions:** Every crop provides scientific nomenclature, water and thermal requirements, rotational niche, and vulnerability profiles.
- **Hard Constraints & Disqualifications:** Crops failing critical non-negotiable thresholds (e.g. extreme soil acidity or moisture deficit) are partitioned into an explicit *Outside Agronomic Window (Disqualified)* section.

### 4. Phase 7 Rotation Lab & Multi-Year Scenario Planner
- **Deterministic Multi-Tier Crop Ranking:**
  $$\text{Suitability Score (DESC)} \to \text{Confidence (DESC)} \to \text{Limiting Count (ASC)} \to \text{Non-repeat preference} \to \text{Crop Name (ASC)}$$
- **Prominent Visual Rank Badges:** Instant identification of top agronomic fits (Gold `Rank #1 Top Match`, Silver `Rank #2`, Bronze `Rank #3`, and Slate `Rank #4+`).
- **Multi-Year Scenario Simulator (2–8 Years):** Model custom multi-year sequences and instantly evaluate:
  - Shannon Crop Diversity Index ($H'$)
  - Legume Frequency & Biological Nitrogen Fixation ($N_2$ balance)
  - Continuous Monoculture Penalties & Disease Cycle Breaks
  - Ground Cover & Erosion Risk Trajectories

### 5. Interactive Field Explorer & Enterprise Mapping
- Draw, edit, and validate field polygons with automatic topology checks (self-intersection detection, minimum/maximum acreage limits, AOI bounding enforcement).
- Seamless satellite and vector basemaps with boundary inspection.
- Generate and export comprehensive field agronomic reports.

---

## Architectural Stack

| Layer | Technologies | Key Responsibilities |
| :--- | :--- | :--- |
| **Frontend** | **Next.js 16.4.6** (Turbopack, App Router, PPR), **React 19**, **TypeScript 5**, **Tailwind CSS 4** | Ultra-responsive UI, client-side caching via TanStack Query, SVG/Recharts data visualizations, MapLibre GL geospatial rendering. |
| **Backend** | **FastAPI 0.115+**, **Python 3.11 / 3.13**, **Pydantic v2**, **Pydantic Settings** | High-performance async REST API, spatial transformations (`shapely`, `pyproj`), data acquisition orchestrator, caching layer. |
| **Storage & Cache**| **SQLite (WAL mode)**, in-memory cache, file-based raw response caching | Sub-millisecond local response caching, field geometries, and job state management. |
| **Data Contracts** | **OpenAPI 3.1**, `openapi-typescript` | Strict type synchronization between backend Pydantic models and frontend TypeScript interfaces (`contract:check`). |
| **Upstream Providers**| **Meteomatics API**, **NASA POWER API**, **USDA NRCS SSURGO SDA**, **USDA NASS CDL**, **NASA SRTM GL1** | Authoritative multi-source agrometeorological and geospatial ingestion. |

---

## Repository Structure

```
soilstice/
├── backend/                         # FastAPI Python backend
│   ├── app/
│   │   ├── analytics/               # Resilience engine & agro-climatic scoring
│   │   ├── api/                     # REST routes, request handlers & middleware
│   │   ├── contracts/               # Pydantic wire contracts & entity definitions
│   │   ├── processing/              # Geometry transforms, climate & SSURGO aggregations
│   │   ├── providers/               # Upstream clients (Meteomatics, POWER, SSURGO, SRTM, CDL)
│   │   ├── repositories/            # SQLite storage & document persistence
│   │   ├── services/                # Field pipelines, coverage orchestration & rotation services
│   │   └── suitability/             # Phase 6 Crop Suitability engine & agronomic explainers
│   ├── tests/                       # Pytest test suite (364 automated tests)
│   ├── pyproject.toml               # Python project configuration & dependencies
│   └── openapi.json                 # Exported OpenAPI 3.1 specification
├── contract/                        # Contract-first synchronization tools
│   ├── export-openapi.mjs           # FastAPI OpenAPI exporter script
│   └── openapi.gen.ts               # Auto-generated TypeScript contract definitions
├── src/                             # Next.js 16 frontend application
│   ├── app/                         # App Router pages (Dashboard, Fields, Evidence, Settings)
│   ├── components/
│   │   ├── layout/                  # Navigation shell, app layout, banners
│   │   ├── shared/                  # Typed contract components (CoverageTable, IndicatorCard)
│   │   ├── ui/                      # Base design system primitives (Cards, Buttons, Modals)
│   │   └── views/                   # Client page views (FieldOverview, Environment, RotationLab)
│   ├── hooks/                       # TanStack Query data-fetching hooks
│   ├── lib/                         # Agronomic helpers, unit conversions, geometry validation
│   ├── services/                    # Data service abstraction (swappable Live API vs. Mock Data)
│   │   ├── http/                    # Live HTTP client implementation
│   │   └── mock/                    # Deterministic synthetic generators for offline mode
│   └── types/                       # Core TypeScript contracts and schemas
├── scripts/                         # Operational diagnostics & verification utilities
├── SOILSTICE_PRODUCT_REFINEMENT_AUDIT.md # Comprehensive engineering & scientific audit log
└── package.json                     # Frontend scripts & NPM workspace configuration
```

---

## Getting Started

### Prerequisites
- **Node.js**: `>= 20.x` (LTS recommended)
- **Python**: `>= 3.11` (Python 3.13 supported)
- **Git**

---

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory and set up a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - **Windows:**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

3. Install dependencies in editable mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Add your credentials in `backend/.env`:
   ```env
   METEOMATICS_USERNAME=your_username
   METEOMATICS_PASSWORD=your_password
   SOILSTICE_EARTHDATA_TOKEN=your_optional_nasa_token
   CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
   ```

5. Start the backend development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The backend API will be live at `http://localhost:8000/api/v1` (Interactive Swagger Docs at `http://localhost:8000/api/v1/docs`).

---

### 2. Frontend Setup (Next.js 16)

1. From the repository root, install dependencies:
   ```bash
   npm install
   ```

2. Configure frontend environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Configure `.env.local`:
   ```env
   # Toggle between "api" (Live FastAPI Backend) and "mock" (Offline Synthetic World)
   NEXT_PUBLIC_DATA_MODE=api
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   ```

3. Start the Next.js development server with Turbopack:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.

---

## Operating Modes

SOILSTICE features an architectural abstraction layer allowing the frontend to operate identically across two runtime modes:

| Mode | Configuration | Use Case |
| :--- | :--- | :--- |
| **Live API Mode** | `NEXT_PUBLIC_DATA_MODE=api` | Real-world production operation. Queries real upstream APIs (Meteomatics, NASA, USDA) via the FastAPI backend with local disk caching and database persistence. |
| **Mock Data Mode** | `NEXT_PUBLIC_DATA_MODE=mock` | Fully offline development, testing, and UI demonstrations. Provides a deterministic, geographically anchored synthetic agricultural world (Finney and Reno Counties, KS). |

*Note: In Mock Data mode, simulate network latency and API failure states directly in the URL using query parameters (e.g. `?mock_error=UPSTREAM_TIMEOUT` or `?mock_latency=800`).*

---

## Contract-First Synchronization

SOILSTICE enforces strict type parity between the Python backend and TypeScript frontend using automated OpenAPI contract generation:

```bash
# Export the latest OpenAPI 3.1 spec from the running FastAPI models
npm run contract:openapi

# Regenerate TypeScript interfaces from backend/openapi.json
npm run contract:gen

# Validate full contract typecheck and parity
npm run contract:check
```

---

## Testing & Quality Assurance

Every pull request and deployment is verified against an extensive automated test matrix:

```bash
# 1. Run all Backend Pytest Suites (364 tests)
cd backend && pytest

# 2. Run all Frontend Vitest Suites (27 tests)
npm test

# 3. TypeScript Static Typecheck
npm run typecheck

# 4. ESLint Code Quality Inspection
npm run lint

# 5. Production Next.js Build Verification
npm run build
```

---

## Environmental Data Coverage Catalog

The operational Data Coverage / Essential Datasets engine tracks the active acquisition and processing of 5 core P0 datasets:

| Dataset ID | Source Provider | Resolution | Update Frequency | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `meteomatics` | Meteomatics API | High resolution point / grid | Hourly / Daily | 4-depth soil moisture (-5, -15, -50, -150 cm), historical profile, elevation |
| `nasa_power_daily_ag` | NASA Langley Research Center | ~55 km ($0.5^\circ$) | Daily | Daily agrometeorology, solar radiation, temperature extremes, $ET_0$, precip |
| `usda_nrcs_ssurgo_sda` | USDA NRCS Soil Data Access | 1:24,000 mapunit polygons | Dynamic / Decennial | Soil taxonomy, AWC, pH, organic matter, drainage class, hydric status |
| `usda_nass_cdl` | USDA NASS (CropScape) | 30 m raster | Annual | 5-year historical crop rotation patterns and land cover |
| `nasa_srtm_gl1` | NASA JPL / USGS | 30 m raster | Static | Digital elevation, terrain slope, slope percentile ($P_{90}$), erosion susceptibility |

---

## Scientific Principles & Honesty Rules

1. **Liebig's Law of the Minimum:** Crop suitability cannot be inflated by averaging favorable parameters over a fatal limiting constraint.
2. **No Fabricated Data:** Missing values are rendered as explicit `null` quantities accompanied by a typed `missing_reason` (`UPSTREAM_ERROR`, `INSUFFICIENT_COVERAGE`, etc.). Missing values are never falsified as zero.
3. **Explicit Spatial Support Classes:** Every metric discloses its native observation support class:
   - `F` (Field polygon intersection)
   - `G` (Gridded raster cell, e.g. 30 m)
   - `R` (Regional point query, e.g. ~55 km climate grid)
4. **Transparent Quorum:** Multi-component indices (such as Agronomic Resilience) require an explicit quorum ($\ge 75\%$) to produce a composite rating; otherwise, they are conservatively withheld.

---

## Documentation & Audits

- [SOILSTICE_PRODUCT_REFINEMENT_AUDIT.md](SOILSTICE_PRODUCT_REFINEMENT_AUDIT.md) — Comprehensive technical audit of the Data Coverage cleanup, Resilience reweighting equations, and Crop Ranking methodology.
- [backend/README.md](backend/README.md) — Backend-specific architecture, layer layout, and local testing instructions.

---

## License

Copyright © 2026 SOILSTICE. All rights reserved.
Proprietary software. Unauthorized reproduction, distribution, or reverse engineering is strictly prohibited.
