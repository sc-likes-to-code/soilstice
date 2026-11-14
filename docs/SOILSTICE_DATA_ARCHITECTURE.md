# SOILSTICE: Data Architecture (Phase 0)

**Project:** SOILSTICE, NASA Space Apps Challenge 2026 (Field Shift)
**Document status:** Phase 0 research deliverable. Nothing in this document has been implemented.
**Research date:** 2026-11-13
**Companion documents:** [DATASET_SOURCE_REGISTER.md](DATASET_SOURCE_REGISTER.md) · [DATASET_INTEGRATION_GUIDE.md](DATASET_INTEGRATION_GUIDE.md) · [PHASE_0_DECISIONS.md](PHASE_0_DECISIONS.md)

---

## 0. How to read this document

Every factual claim carries one of these verification labels:

| Label | Meaning |
|---|---|
| **[LIVE]** | We tested it ourselves on 2026-11-13 with a live HTTP request against the official endpoint. It returned the stated result. |
| **[CMR]** | Confirmed in NASA's Common Metadata Repository (`cmr.earthdata.nasa.gov`) on 2026-11-13: short name, version, archive center and temporal range. |
| **[DOC]** | Stated in official documentation or an official announcement from the publisher. The URL is cited in the Source Register. |
| **[UNVERIFIED]** | Believed true but not confirmed from a primary source during Phase 0. It must be checked before we depend on it. |
| **[REC]** | A recommendation or design decision, not a fact. |

> **Note on challenge resources:** The brief says the official challenge resources are "available in the project documentation". On 2026-11-13 the project folder was empty, so we found no challenge resource file. This research uses the dataset list in the Phase 0 brief and the publishers' own documentation. If a challenge resource file exists, add it to `docs/` and reconcile it against this document.

---

## 1. Executive summary

1. **Demonstration region [REC]:** Central Kansas. The primary area of interest (AOI) is **Reno County, KS (FIPS 20155)**. **Finney County, KS (FIPS 20055)** is a semi-arid, irrigated contrast AOI.
   - 2024 CDL statistics, retrieved live, show these counties have more than twice the crop diversity of the Iowa/Illinois and Mississippi Delta candidates (§3).
2. **P0 datasets (7) [REC]:**
   - NASA POWER: meteorology and solar radiation.
   - SMAP L4 `SPL4SMGP` v008: surface and root-zone soil moisture.
   - HLS v2.0 `HLSL30`/`HLSS30` and the HLS-VI products: 30 m vegetation indices.
   - SRTM `SRTMGL1` v003: elevation and slope.
   - SSURGO via Soil Data Access: soil properties.
   - USDA NASS Cropland Data Layer via CropScape: crop history.
   - USDA NASS Crop Sequence Boundaries: field polygons and 8-year crop sequences. This dataset is not in the supplied list (see §2.3).
3. **P1 datasets:**
   - PRISM: higher-resolution precipitation and temperature.
   - OpenET: 30 m evapotranspiration.
   - NASS Quick Stats: county statistics.
   - SMAP L3 `SPL3SMP_E`: observation-based check on the L4 model output.
4. **P2 datasets:** IMERG, MODIS/VIIRS vegetation indices, ECOSTRESS, NAIP, FAO GAEZ v5, NLDAS-2, CoCoRaHS, and USGS 3DEP as a terrain upgrade.
5. **Excluded datasets:** ERA5/ERA5-Land, GLDAS, NLCD, LANDFIRE, GEDI, USGS NWIS, AMS Market News, Web Soil Survey (UI only), Ag Data Commons (a catalog, not a dataset), stand-alone Landsat and Sentinel-2 (used through HLS instead), and STATSGO2 (fallback only).
6. **Scientific honesty rule [REC]:**
   - A field profile has three kinds of numbers, and each is labelled by **spatial support**:
     - **field-resolved:** SSURGO, CDL, HLS, SRTM, OpenET.
     - **sub-regional:** PRISM.
     - **regional context:** POWER, SMAP, IMERG, NLDAS, GAEZ.
   - Coarse-grid values are never presented as field measurements (§5.4).

---

## 2. Dataset research summary and prioritization

Full per-dataset details, including identifiers, URLs, variables, resolution, coverage, formats, authentication, limits and libraries, are in [DATASET_SOURCE_REGISTER.md](DATASET_SOURCE_REGISTER.md). This section records the evaluation and the priority given to each dataset.

### 2.1 Evaluation criteria

| Criterion | Question |
|---|---|
| Field relevance | Does the native resolution resolve a typical ~16–65 ha (40–160 ac) field? |
| Accessibility | Is there a programmatic API? What authentication does it need? What are the quotas? |
| Integration cost | What format, what grid, and how hard is quality filtering? |
| Scientific value | Does it feed an indicator that the resilience or rotation model needs? |
| Redundancy | Does another selected dataset already provide the same variable at equal or better quality? |

### 2.2 Classification

| # | Dataset | Priority | Rationale |
|---|---|---|---|
| 1 | **NASA POWER** (Daily API, `community=AG`) | **P0** | **[LIVE]** No authentication. One call returns T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN and GWETROOT. The sources are MERRA-2 and CERES SYN1deg. It is the backbone for climate normals, growing degree days and solar radiation. Its coarse grid (~0.5°×0.625° meteorology, 1° solar) makes it **regional context**. |
| 2 | **SSURGO via Soil Data Access (SDA)** | **P0** | **[LIVE]** SQL over REST with no authentication. Returns texture, pH, OM, AWC, drainage class, hydrologic group and slope per map unit, component and horizon. The ~1:12,000–1:24,000 survey scale is the only true sub-field soil source. |
| 3 | **USDA NASS Cropland Data Layer (CropScape)** | **P0** | **[LIVE]** Values, county files and statistics for 2006–2025 in Kansas and 2000–2025 in Iowa. 30 m. This is the core historical crop classification. |
| 4 | **USDA NASS Crop Sequence Boundaries (CSB) 2018–2025** | **P0** | **[DOC]** Public-domain field-like polygons, each with its crop sequence. Released 2026-03-27. It solves the field-geometry problem, because FSA Common Land Units are not public. **This dataset is not on the supplied list.** It comes from the same publisher as the CDL and is derived from it. The team must confirm it can be used (see PHASE_0_DECISIONS Q1). |
| 5 | **HLS v2.0 (`HLSL30`, `HLSS30`) + HLS-VI (`HLSL30_VI`, `HLSS30_VI`)** | **P0** | **[CMR]** 30 m with Landsat 8/9 and Sentinel-2A/B/C harmonized, revisiting every ~2–3 days. Cloud Optimized GeoTIFFs (COGs) are served through the CMR-STAC API **[LIVE]**. The VI products provide NDVI, EVI, SAVI, MSAVI, NDMI, NDWI, NBR, NBR2 and TVI **[DOC]**. This is the only field-resolving vegetation source that needs no tasking. **It replaces separate Landsat and Sentinel-2 integrations.** |
| 6 | **SMAP L4 `SPL4SMGP` v008** | **P0** | **[CMR]** 9 km EASE-Grid 2.0, 3-hourly, gap-free surface (0–5 cm) and root-zone (0–100 cm) soil moisture from 2015-03-31 to the present. It is the NASA soil-moisture headline for the challenge. Label it **regional context** (one 9 km cell is about 8,100 ha). |
| 7 | **SRTM `SRTMGL1` v003** | **P0** | **[CMR]** 1 arc-second (~30 m) DEM from LP DAAC. Used for field elevation, slope and aspect. It is NASA's own dataset and simple to use. USGS 3DEP 10 m is more accurate over the US but is not on the supplied list (P2 upgrade). |
| 8 | **PRISM** (daily, 4 km and 800 m) | **P1** | **[LIVE]** No-authentication web service. Returns zipped COGs. 800 m data has been free since March 2025 **[DOC]**. It is gauge-informed and terrain-aware, and better than POWER for CONUS precipitation and temperature at sub-county scale. Once integrated it **replaces POWER for precipitation and temperature only**, not for solar radiation or RH. |
| 9 | **OpenET** (API) | **P1** | **[DOC]** 30 m ensemble ET, now covering CONUS (December 2025 expansion). Kansas falls in the original western coverage, which has the longest validation record. The API key is free, but quotas apply. |
| 10 | **NASS Quick Stats API** | **P1** | **[LIVE]** The endpoint responds and requires a key (it returns `unauthorized` without one). Used for county yields and planted/harvested acres, as regional benchmarks. 50,000 records per request **[DOC]**. |
| 11 | **SMAP L3 `SPL3SMP_E` v006** | **P1** | **[CMR]** 9 km daily retrievals. Used as an observation-based check on the model-assimilated L4 product, and for quality-flag transparency. |
| 12 | **GPM IMERG** (`GPM_3IMERGDF` V07 Final; `GPM_3IMERGDL` Late) | **P2** | **[CMR]** 0.1° (~11 km). Over CONUS, PRISM is the better precipitation product. The Final run lags ~3.5 months; CMR shows its end date as 2025-09-30. Keep it as a NASA satellite cross-check only. |
| 13 | **MODIS `MOD13Q1` v061 / VIIRS `VNP13A1` v002** | **P2** | **[CMR]** 250 m / 500 m, 16-day. Useful only for a 2000–2012 vegetation baseline before HLS. MODIS science collection ends in 2027 **[DOC]**. |
| 14 | **ECOSTRESS `ECO_L3T_JET` v002/v003** | **P2** | **[CMR]** 70 m ET, but the ISS orbit samples irregularly. OpenET is the operational choice. |
| 15 | **NAIP** | **P2** | **[DOC]** 0.5–1 m aerial imagery, flown every ~2–3 years. Visual basemap and boundary QA only, not used for analytics. |
| 16 | **FAO GAEZ v5** | **P2** | **[DOC]** Global crop suitability at 30 arc-seconds (~1 km), launched April 2025. A **regional proxy** for agro-climatic suitability, not field-level. |
| 17 | **NLDAS-2** (`NLDAS_FORA0125_H`, `NLDAS_NOAH0125_H` v2.0) | **P2** | **[CMR]** 0.125°, hourly, 1979 to present. Redundant with POWER plus PRISM for the MVP. Possible later use: Noah model soil moisture before 2015. |
| 18 | **CoCoRaHS** | **P2** | Volunteer rain-gauge points. Could validate PRISM and POWER. **[UNVERIFIED]** We could not confirm a programmatic export API. |
| 19 | **USGS 3DEP 1/3 arc-second** | **P2 (upgrade)** | **[DOC]** 10 m seamless DEM. Not on the supplied list. Drop-in upgrade for SRTM. |
| — | **ERA5 / ERA5-Land** | **Excluded** | Redundant with POWER, PRISM and NLDAS over CONUS. Needs a Copernicus CDS account, licence acceptance and queued requests **[DOC]**. |
| — | **GLDAS** | **Excluded** | 0.25° global. NLDAS is the CONUS-specific counterpart. Redundant. |
| — | **NLCD (Annual NLCD Collection 1.1)** | **Excluded** | The CDL already provides annual 30 m land cover, including non-crop classes, and is crop-specific. Revisit only if pre-2006 land-use change matters. |
| — | **LANDFIRE** | **Excluded** | Wildland vegetation and fuel products. Not designed for cropland. |
| — | **GEDI** | **Excluded** | Footprint lidar for canopy structure. Row-crop height is not a target, and sampling is sparse. |
| — | **USGS NWIS** | **Excluded** | Stream gauges are not field-relevant for the MVP. The legacy `waterservices.usgs.gov` is scheduled for decommissioning in Q1 2027 **[DOC]**, so any integration would need the new OGC API. |
| — | **USDA AMS Market News** | **Excluded** | Market prices fall outside field-condition and rotation suitability. Needs a key. |
| — | **USDA Web Soil Survey** | **Excluded (as integration)** | An interactive UI over the same SSURGO database that SDA serves programmatically. Cite it as a user-facing reference link. |
| — | **USDA Ag Data Commons** | **Excluded (as integration)** | A repository and catalog, not a dataset. No specific asset was identified that adds value over the selected sources. |
| — | **Landsat Collection 2 (stand-alone)** | **Excluded (covered by HLS)** | HLS is NASA's harmonized, BRDF-normalized derivative. Use Landsat C2 L2 only if pre-2013 30 m history is later required. |
| — | **ESA Sentinel-2 (stand-alone)** | **Excluded (covered by HLS)** | Consumed through `HLSS30`. |
| — | **STATSGO2** | **Fallback only** | 1:250,000 scale. Use only where SSURGO has no data (SSURGO is complete across our AOIs; see §3). |

### 2.3 Redundancy decisions

| Variable family | Selected | Rejected or demoted | Justification |
|---|---|---|---|
| Precipitation and temperature | POWER (P0), then PRISM (P1) | IMERG (P2), NLDAS (P2), ERA5 (X) | POWER gets us working on day 1 with no authentication. PRISM then adds resolution: 4 km/800 m against ~50 km. Only one source is "authoritative" per variable at a time; the others are recorded as cross-checks. |
| Soil moisture | SMAP L4 (P0), SMAP L3 (P1) | POWER GWETROOT (kept as metadata only), NLDAS Noah (P2), GLDAS (X) | SMAP is the NASA soil-moisture mission. L4 is gap-free with root zone. L3 is observation-based. |
| Vegetation | HLS + HLS-VI (P0) | Landsat and Sentinel-2 stand-alone (X), MODIS/VIIRS (P2) | HLS already harmonizes Landsat and Sentinel-2 at 30 m. |
| ET | OpenET (P1) | MODIS MOD16 (X), ECOSTRESS (P2) | 30 m daily/monthly ensemble against 500 m or irregular sampling. |
| Land cover / crops | CDL (P0) | NLCD (X) | CDL is crop-specific, annual and 30 m. |
| Field geometry | NASS CSB (P0) | User-drawn polygons (fallback) | Public-domain, field-scale, and already attached to the CDL crop sequence. |

---

## 3. Demonstration region

### 3.1 Evidence

**Crop diversity [LIVE].** We pulled 2024 CDL county statistics through CropScape `GetCDLStat` on 2026-11-13. Diversity is the Shannon index over crop classes (CDL codes 1–61, 66–77 and 204–254), weighted by acreage.

| Candidate region | County (FIPS) | Crop acres (2024 CDL) | Shannon H | Top crops (share of crop acres) |
|---|---|---|---|---|
| Iowa / Illinois | Story, IA (19169) | 273,176 | 0.74 | Corn 56%, Soybeans 43% |
| Iowa / Illinois | McLean, IL (17113) | 633,746 | 0.76 | Soybeans 50%, Corn 49% |
| Kansas / Nebraska | **Reno, KS (20155)** | 389,423 | **1.72** | Winter wheat 43%, Corn 15%, Sorghum 14%, Soybeans 14%, Alfalfa 4%, Dbl-crop WW/Soy 4% |
| Kansas / Nebraska | **Finney, KS (20055)** | 529,450 | **1.73** | Winter wheat 29%, Corn 22%, Sorghum 19%, Fallow/idle 18%, Alfalfa 8% |
| Kansas / Nebraska | Hamilton, NE (31081) | 291,054 | 0.72 | Corn 72%, Soybeans 26% |
| Mississippi Delta | Sunflower, MS (28133) | 343,448 | 0.63 | Soybeans 84%, Corn 10%, Rice 3% |
| Mississippi Delta | Phillips, AR (05107) | 310,468 | 1.14 | Soybeans 66%, Cotton 14%, Rice 11% |

> These are acreage summaries computed from the CDL classification. They are not survey statistics. CDL class accuracy varies by crop and state.

**CDL history depth [LIVE]** (CropScape `GetCDLFile`):
- Reno County, KS: available **2006** onward. The service reports 2005 as not available.
- Story County, IA: available **2000** onward.
- Nationwide coverage: 2008 onward **[DOC]**.

**SSURGO coverage:**
- **[LIVE]** SDA returned complete component and horizon data for a Reno County point (Nalim loam, mukey 1443836) and for a Story County point.
- **[UNVERIFIED]** Whether every map unit in every candidate county has complete pH, OM and AWC is not yet checked. A county-wide null-check query is Phase 1 Test S-3.

**NASA dataset coverage:**
- **[CMR]** SMAP, HLS, SRTM, IMERG and NLDAS are CONUS-wide or global, so all three candidate regions are covered equally.
- **[DOC]** OpenET covered Kansas and Nebraska first, in the original western coverage. The East was added only in December 2025, and eastern field boundaries were reported as pending.

**Climate data:** POWER and PRISM cover all of CONUS **[LIVE]**.

### 3.2 Assessment

| Criterion | Iowa / Illinois | Kansas / Nebraska (central KS) | Mississippi Delta |
|---|---|---|---|
| SSURGO coverage | Complete (spot-checked) | Complete (spot-checked) | Assumed complete; not checked |
| CDL depth | 2000+ (deepest) | 2006+ (KS) | Not checked |
| NASA coverage | Equal | Equal; longest OpenET record | Equal; more cloud for optical |
| Climate data | Equal | Equal; strong east–west precipitation gradient | Equal |
| **Crop diversity and rotation relevance** | **Low**: corn–soy only | **High**: wheat, sorghum, corn, soy, alfalfa, fallow, double-crop | Medium (AR) / low (MS) |
| Ease of sample field data | Good | **Good**: CSB polygons; center pivots visible in NAIP | Good |
| Water-stress signal for SMAP/ET | Weak (humid, tile-drained) | **Strong**: dryland vs irrigated, semi-arid west | Confounded by flood irrigation and rice |

### 3.3 Recommendation [REC]

**Central Kansas.** Primary AOI: **Reno County (20155)**. Contrast AOI: **Finney County (20055)**.

- Rotation-suitability analysis only means something where farmers actually choose among several crops. Reno County has five or more major crop classes, including wheat followed by double-crop soybeans. Iowa's two-crop system makes "rotation suitability" nearly trivial.
- Kansas has a precipitation and irrigation gradient, so SMAP soil moisture, PRISM precipitation and OpenET ET carry real signal. That supports a resilience narrative.
- The trade-off is shorter CDL history (2006+ against 2000+ in Iowa). That still gives 20 seasons (2006–2025), which is plenty for rotation statistics.
- If the judges value corn/soy recognition, Iowa is the fallback: the same pipeline works unchanged with only a change to the AOI FIPS code.

---

## 4. Dataset integration matrix

Abbreviations:
- **Nature:** O = direct observation; M = model or reanalysis; D = derived indicator; P = regional proxy or statistic.
- **Support:** F = field-resolved (≤ 100 m); S = sub-regional (≤ 5 km); R = regional context (> 5 km).

| Required variable | Dataset | Exact product | Resolution | Temporal res. | API / access | Extraction method | Intended calculation | Nature / Support |
|---|---|---|---|---|---|---|---|---|
| Precipitation | NASA POWER | Daily API, `PRECTOTCORR` (mm/day), `community=AG` | ~0.5°×0.625° (MERRA-2) | Daily, 1981→ | `GET power.larc.nasa.gov/api/temporal/daily/point` (no auth) **[LIVE]** | Point query at field centroid; record grid-cell support | Seasonal totals, 30-yr normals (1991–2020), anomaly (% of normal), dry-spell length | M / R |
| Precipitation (upgrade) | PRISM | `ppt` daily, 4 km (`25m` in file names) or 800 m (`30s`) | 4 km / 800 m | Daily, 1981→ | `GET services.nacse.org/prism/data/get/us/{4km\|800m}/ppt/{YYYYMMDD}` → zip containing COG **[LIVE]** | Area-weighted zonal mean over field polygon (800 m) or containing cell (4 km) | Same as above, at higher resolution | M (gauge-interpolated) / S |
| Temperature | NASA POWER → PRISM | POWER `T2M`, `T2M_MAX`, `T2M_MIN` (°C); PRISM `tmean`, `tmax`, `tmin` | As above | Daily | As above | As above | GDD (crop-specific base and cap), heat-stress days (Tmax > 35 °C), frost dates | M / R→S |
| Humidity | NASA POWER | `RH2M` (%), optional `QV2M` | ~0.5°×0.625° | Daily | POWER API | Point at centroid | Mean RH, VPD (with T2M) | M / R |
| Solar radiation | NASA POWER | `ALLSKY_SFC_SW_DWN` (MJ/m²/day) | 1°×1° (CERES SYN1deg) | Daily | POWER API | Point at centroid | Seasonal radiation total; reference ET₀ input | M (satellite-derived) / R |
| Soil moisture | SMAP L4 | `SPL4SMGP` v008: `sm_surface`, `sm_rootzone` (m³/m³) | 9 km EASE-Grid 2.0 | 3-hourly, 2015-03-31→ | NSIDC DAAC via `earthaccess` (Earthdata Login) **[CMR]** | Value of the 9 km cell containing the centroid; store field fraction of cell | Daily mean; percentile versus the 2015→ climatology for that cell; drought-stress days | M (assimilated) / R |
| Soil moisture (check) | SMAP L3 | `SPL3SMP_E` v006: `soil_moisture` (AM/PM), `retrieval_qual_flag` | 9 km EASE-Grid 2.0 | Daily (gappy) | NSIDC via `earthaccess` **[CMR]** | Containing cell; keep only recommended-quality retrievals | Consistency check against L4 | O (retrieval) / R |
| Soil texture | SSURGO | `chorizon.sandtotal_r`, `silttotal_r`, `claytotal_r` (%) | Map-unit polygons (1:12k–1:24k) | Static (survey vintage) | SDA `POST sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` **[LIVE]** | Polygon intersection → map units → major components → horizons; depth-weight 0–30 cm and 0–100 cm; area- and comppct-weight | USDA texture class, dominant texture | O (survey) + expert estimate / F |
| Soil pH | SSURGO | `chorizon.ph1to1h2o_r` | As above | Static | SDA | As above (0–30 cm) | Crop pH suitability windows | O + estimate / F |
| Organic matter | SSURGO | `chorizon.om_r` (%) | As above | Static | SDA | As above (0–30 cm) | Fertility indicator | O + estimate / F |
| Drainage | SSURGO | `component.drainagecl`, `component.hydgrp`; `muaggatt.drclassdcd` | As above | Static | SDA | Dominant class by area × comppct | Waterlogging and droughtiness risk | O (classed) / F |
| Available water capacity | SSURGO | `chorizon.awc_r` (cm/cm); `muaggatt.aws0100wta`, `aws0150wta` (cm) | As above | Static | SDA **[LIVE]** | Area-weighted AWS 0–100 / 0–150 cm | Plant-available water storage; drought buffer | Derived from survey / F |
| Elevation | SRTM | `SRTMGL1` v003 (m, EGM96) | 1″ (~30 m) | Static (Feb 2000) | LP DAAC via `earthaccess` **[CMR]** | Zonal mean/min/max over field | Relief; low-spot detection | O (radar) / F |
| Slope | SRTM (+ SSURGO cross-check) | Derived from `SRTMGL1`; SSURGO `muaggatt.slopegradwta` | ~30 m | Static | As above | Compute slope (degrees and %) in EPSG:5070 with a Horn kernel, then zonal mean/p90 | Erosion and trafficability risk | D / F |
| Vegetation indices | HLS-VI (P0); HLS SR fallback | `HLSL30_VI` / `HLSS30_VI` v2.0 (NDVI, EVI, NDMI, …); else `HLSL30`/`HLSS30` bands | 30 m | ~2–3 day combined revisit; L30 2013-04→, S30 2015-11→ | CMR-STAC `cmr.earthdata.nasa.gov/stac/LPCLOUD` + Earthdata Login **[LIVE]** | Fmask-filtered zonal median per scene; reject scenes with < 70% clear field pixels | Seasonal NDVI curve, peak NDVI, green-up/senescence timing, NDMI moisture stress | D (from observed SR) / F |
| Evapotranspiration | OpenET (P1) | Ensemble ET (mm), monthly/daily | 30 m | Daily/monthly | `openet-api.org` with API key **[DOC]** | Field polygon request (API-side zonal) | Seasonal ET, ET/P ratio, irrigation signal | M (satellite-driven ensemble) / F |
| Evapotranspiration (proxy, P0) | NASA POWER | Derived ET₀ from T, RH, wind, radiation | ~0.5° | Daily | POWER API | Point | FAO-56 Penman–Monteith reference ET₀; water balance P − ET₀ | D / R |
| Historical crop classification | USDA NASS CDL | CDL 30 m (2006–2025 in KS) | 30 m | Annual | CropScape `GetCDLFile` / `GetCDLValue` / `GetCDLStat` **[LIVE]** | Clip county GeoTIFF to field; class histogram; majority class + purity | Crop sequence, rotation frequency, monoculture run length | D (classification) / F |
| Field polygons + crop sequence | USDA NASS CSB | CSB 2018–2025 | Vector (field-like) | Annual sequence | Bulk download (NASS) **[DOC]** | Spatial filter to AOI; store as `fields` | Field geometry; 8-year sequence cross-check | D / F |
| Crop suitability | FAO GAEZ v5 (P2) + SOILSTICE rules | GAEZ v5 suitability index | 30″ (~1 km) | Climatology / scenario | GAEZ v5 data portal **[DOC]**; API **[UNVERIFIED]** | Containing cell | Regional agro-climatic prior | P / R |
| Crop suitability (primary) | SOILSTICE derived | Rule-based score from SSURGO + climate + CDL history | Field | Per season | Internal | n/a | Transparent per-crop suitability score with component breakdown | D / F (inputs mixed) |
| Regional agricultural statistics | NASS Quick Stats (P1) | County yield, planted/harvested acres | County | Annual | `quickstats.nass.usda.gov/api/api_GET` with key **[LIVE: auth required]** | Join by state/county FIPS | Field context: county yield trend and variability | P (survey statistic) / County |

---

## 5. Processing architecture

### 5.1 Pipeline stages

```
 Raw acquisition ─▶ Validation ─▶ Quality filtering ─▶ Spatial extraction ─▶ Temporal aggregation
        │                                                                          │
        ▼                                                                          ▼
 raw cache (immutable,                      Unit normalization ─▶ Derived indicators ─▶ Storage (PostGIS)
 hashed, provenance)                                                                   + provenance rows
```

| Stage | What happens | Output |
|---|---|---|
| 1. Raw acquisition | Adapter calls the official endpoint (§DATASET_INTEGRATION_GUIDE). Requests are bounded to the AOI bbox and date window. Responses are cached as files keyed by `sha256(request)`. | Raw files + `acquisition_log` row (URL, params minus secrets, HTTP status, bytes, sha256, retrieved_at, product version) |
| 2. Validation | Check schema and format: CRS present, expected variables or bands, dimensions and dtype, value ranges, temporal coverage, fill values identified (POWER `-999`, HLS `-9999`, SMAP `-9999`). | Pass/fail + `validation_report` JSON |
| 3. Quality filtering | Apply product QA: HLS Fmask bits, SMAP `retrieval_qual_flag` (L3), SSURGO `majcompflag`, CDL class purity, POWER fill values. **Masked values become `null`, not zero.** | Masked arrays + QA summary (n_total, n_valid, reasons) |
| 4. Spatial extraction | Reproject polygon (not the raster, where possible) to the raster CRS; extract (§5.2–5.4). | Per-field, per-timestep statistics + coverage metrics |
| 5. Temporal aggregation | Roll up to daily → dekad/month → growing season → multi-year (§5.5). | Aggregates with `n_obs` and completeness |
| 6. Unit normalization | Convert to canonical SI-like units (§5.6). Keep the original unit in provenance. | Normalized values |
| 7. Derived indicators | GDD, ET₀, water balance, NDVI phenology, rotation metrics, soil suitability, resilience components. | Indicator rows with `inputs[]` lineage |
| 8. Storage | Upsert into PostGIS tables per data contract (§6). Raw rasters stay in object storage, never in Postgres. | DB rows + object-store URIs |

### 5.2 Clipping and intersecting rasters with field polygons [REC]

- **Canonical vector CRS:** fields are stored in EPSG:4326, and area calculations are done in **EPSG:5070** (CONUS Albers Equal Area).
- **Per raster:**
  1. Read only the window covering the polygon bbox plus a one-pixel buffer. Use `rasterio` windowed reads over COG `/vsicurl/` or authenticated HTTPS. Use `rioxarray.clip_box` for NetCDF/HDF5 via `xarray`.
  2. Reproject the **polygon** into the raster's native CRS. Rasters stay on their native grids to avoid resampling artifacts:
     - HLS: UTM zone of its MGRS tile.
     - CDL: EPSG:5070.
     - SRTM: EPSG:4326.
     - SMAP: EPSG:6933, the EASE-Grid 2.0 global grid.
  3. Compute **coverage-weighted zonal statistics** with `exactextract`, which uses the fractional pixel coverage of the polygon. This matters for 30 m pixels on small or irregular fields. `rasterstats` with `all_touched=False` is an acceptable fallback, but it is biased on field edges.
  4. Apply an **inward buffer of 15 m** to field polygons for HLS and CDL, to reduce mixed edge pixels **[REC]**.
     - *Correction (2026-11-14):* the 15 m inward buffer is the convention of the NASS **Crop Frequency Layers** (since the 2019 products) **[DOC]**. It is **not** a CSB convention.
     - CSB polygons are built by segmenting CDL resampled to 10 m and simplified at a 60 m tolerance **[DOC]**, so their edges are approximate. That is the reason we buffer.
     - If the buffered polygon keeps < 50% of the original area (small or narrow fields), use the unbuffered polygon and add the flag `INWARD_BUFFER_SKIPPED`.
     - Store both buffered and unbuffered pixel counts.

### 5.3 Polygon-level statistics [REC]

| Data type | Statistics stored |
|---|---|
| Continuous (NDVI, elevation, slope, PRISM) | `mean`, `median`, `std`, `min`, `p10`, `p90`, `valid_pixel_count`, `total_pixel_count`, `coverage_fraction` |
| Categorical (CDL) | Class histogram (area fraction per class), `majority_class`, `purity` (= majority fraction), `n_classes` |
| Soil (SSURGO vector) | See §5.3.1 (normative). |

#### 5.3.1 SSURGO aggregation methodology (normative, method id `ssurgo_area_comppct_weighting` v1)

1. **Map-unit area fractions:**
   - Call SDA with the `~GetClippedMapunits(@aoi,polygon,geo,@int)~` macro, which returns clipped map-unit geometries per `mukey` **[LIVE 2026-11-14]**.
   - Request the geometry as WKT, reproject it to EPSG:5070 and compute areas locally.
   - Do **not** use the returned `STArea()`: it is in degree² for this geometry type **[LIVE]**.
   - Several rows can share one `mukey`; sum them.
   - `area_fraction = area(mukey) / Σ area`.
2. **Components:** major components only (`majcompflag = 'Yes'`).
   - Component weight `w = area_fraction × comppct_r / 100`.
   - Components with `comppct_r` null get weight 0 and are counted in `null_weight_fraction`.
3. **Depth intervals:** fixed at 0–30, 30–100 and 100–150 cm. Each horizon contributes in proportion to its overlap thickness with the interval. An interval value for a component exists only if horizons cover ≥ 80% of the interval thickness; otherwise it is `null`.
4. **Continuous properties** (sand, silt, clay, OM, pH, AWC):
   - Value = Σ(w × interval value) / Σ(w over non-null).
   - The `_l`/`_h` columns are aggregated the same way and reported as `uncertainty.kind = "range"`.
   - pH is averaged arithmetically, as SSURGO's own aggregations are. This is a documented simplification, not a chemical mean.
5. **Texture class:** derived from the aggregated sand/silt/clay with the USDA texture triangle. It is not a majority of component classes.
6. **Categorical properties** (drainage class, hydrologic group): the class with the largest summed `w`, reported with its `weight_share`.
7. **Available water storage:** `aws0100wta` and `aws0150wta` from `muaggatt`, area-weighted across map units. These are NRCS's own component-weighted values **[LIVE]**. The horizon-derived AWC is shown per layer only.
8. **Quality:**
   - `null_weight_fraction > 0.2` → status `partial`.
   - `> 0.5` → `missing` with `INSUFFICIENT_COVERAGE`.
   - Miscellaneous areas (water, pits) yield null horizons and are counted as null weight.

### 5.4 Handling different spatial resolutions [REC]

We do **not** resample coarse products to 30 m. Resampling would fabricate spatial detail that does not exist. Instead:

| Support class | Products | Extraction | Display rule |
|---|---|---|---|
| **F, field-resolved** (≤ 100 m; field spans many pixels) | HLS, CDL, SRTM, SSURGO, OpenET, CSB | Zonal statistics over the polygon | Show as "field value" |
| **S, sub-regional** (≤ 5 km) | PRISM 800 m / 4 km | Area-weighted mean of intersecting cells (800 m); containing cell (4 km) | Show as "local estimate (4 km grid)" |
| **R, regional context** (> 5 km; field ≪ pixel) | POWER, SMAP L3/L4, IMERG, NLDAS, GAEZ | Gridded products: value of the containing cell; store `cell_id` and `field_area / cell_area`. POWER: `extraction_method = "api_point_query"` at the field centroid. We make no claim about POWER's internal interpolation, which is not verified. | Always shown with the badge "Regional context: ~9 km grid. Not a field measurement." |

Every observation row stores `spatial_support_m` (native pixel size) and `support_class` (F/S/R). The resilience profile records, per component, which support class it came from.

### 5.5 Temporal aggregation [REC]

| From | To | Rule | Completeness rule |
|---|---|---|---|
| SMAP L4 3-hourly | Daily | Mean of 8 steps (UTC day; document the UTC/local offset) | ≥ 6 of 8 steps, else `null` |
| HLS scenes | Monthly / seasonal | Median of valid scene-level field medians; also store maximum NDVI and its date | Scene valid if ≥ 70% clear field pixels. Month valid if ≥ 1 valid scene. Season curve fitted only if ≥ 6 valid scenes. |
| Daily climate | Monthly / season | Sum (precipitation, GDD, ET₀) or mean (T, RH, solar radiation) | ≥ 90% of days present, else `null` + `completeness` value |
| Season | Climatology | 1991–2020 normal for POWER/PRISM; 2015→ for SMAP (state the short record) | Record `n_years` |

**Growing season windows** are crop-specific [REC; to be confirmed with Kansas State Research and Extension calendars, see PHASE_0_DECISIONS D5.6]:
- Winter wheat: Oct → Jun.
- Corn, sorghum and soybean: Apr/May → Sep/Oct.

### 5.6 Unit normalization

| Quantity | Canonical unit | Source conversions |
|---|---|---|
| Precipitation | mm (per period) | POWER mm/day; PRISM mm; IMERG mm/day (V07 daily is mean rate × 24 **[DOC]**) |
| Temperature | °C | POWER °C; PRISM °C |
| Relative humidity | % | POWER % |
| Solar radiation | MJ m⁻² day⁻¹ | POWER MJ/m²/day **[LIVE]** (kWh/m²/day × 3.6 if requested in that unit) |
| Soil moisture | m³ m⁻³ | SMAP m³/m³; POWER GWETROOT is unitless 0–1 wetness, **not** volumetric, and is stored separately |
| ET | mm (per period) | OpenET mm |
| Texture, OM | % (mass) | SSURGO % |
| AWC | cm cm⁻¹ (horizon); cm (profile storage) | SSURGO |
| Elevation | m (EGM96 for SRTM) | — |
| Slope | degrees and percent | Derived |
| Reflectance / VI | Unitless | HLS SR and HLS-VI: int16, scale factor 0.0001, fill −9999 **[DOC: Earthdata catalog variable tables for HLSS30 and HLSL30_VI v2.0]**. Still read `scale_factor` from file metadata at ingest. |

### 5.7 Missing observations

- Missing is **`null` with a reason code**, never 0 and never interpolated silently.
- Reason codes: `NO_DATA_SOURCE`, `FILL_VALUE`, `QA_MASKED_CLOUD`, `QA_MASKED_SHADOW`, `QA_MASKED_SNOW`, `QA_LOW_QUALITY_RETRIEVAL`, `INSUFFICIENT_COVERAGE`, `OUT_OF_TEMPORAL_RANGE`, `UPSTREAM_ERROR`, `NOT_YET_PUBLISHED` (e.g., IMERG Final latency), and three added 2026-11-14 for the API contract: `NOT_COMPUTED`, `OUTSIDE_AOI`, `PENDING_PROCESSING`. SOILSTICE_API_CONTRACTS §2 holds the authoritative list.
- Gap-filling, such as NDVI curve smoothing, happens **only in the derived-indicator layer**. It is flagged `gap_filled: true` with its method, and the raw observations stay untouched.

### 5.8 Quality flags preserved

| Product | Flag | How preserved |
|---|---|---|
| HLS | `Fmask` (uint8, fill 255 **[DOC]**). The asset is present in both SR and **VI** granules **[LIVE: STAC assets of HLSS30_VI_2.0 / HLSL30_VI_2.0 items, 2026-11-14]**. Bits 1 = cloud, 2 = adjacent to cloud/shadow, 3 = cloud shadow **[DOC, secondary: NASA-IMPACT `hls-vi` code citing User Guide v2 Table 9]**. Bit 4 = snow/ice, 5 = water, 6–7 = aerosol level, 0 = cirrus (reserved) **[UNVERIFIED]**. | Mask bits 1–3 always. Mask bits 4–5 only after their positions are confirmed against the User Guide or the Fmask COG's embedded description (Phase 3 Test H-5). Per-scene counts per reason go in `mask_counts`. |
| SMAP L3 | `retrieval_qual_flag`, `surface_flag` | Keep the raw integer + decoded `recommended_quality: bool` |
| SMAP L4 | L4 is gap-free; analysis-uncertainty fields exist in the companion `SPL4SMAU` product **[UNVERIFIED for v008]** | Store `uncertainty: null` unless SPL4SMAU is integrated |
| CDL | Per-class producer/user accuracy (state metadata) | `quality.class_accuracy` populated from NASS metadata where available **[DOC: state-level accuracy on CDL FAQ page]** |
| SSURGO | `majcompflag`, `comppct_r`, low/high (`_l`, `_h`) ranges, survey area `saverest` date | Store `_l`/`_r`/`_h` as uncertainty bounds; store survey version date |
| POWER | Fill `-999`; header `sources` | Fill → `null`; keep `sources` array in provenance |
| PRISM | Bundled `.stn.csv` (station count) and `.info.txt` **[LIVE]** | Keep the info text in provenance; station density as optional QA |

### 5.9 Source provenance

Every stored value can be traced to a `dataset_metadata` row (product, version, DOI, URL) and an `acquisition_log` row (exact request, time, checksum). Derived indicators store `inputs[]`: a list of `{observation_id | indicator_id, role}`. Library versions and the git commit of the processing code are stored once the repository exists. **No git operations happen in Phase 0.**

### 5.10 Field resilience methodology (framework frozen; breakpoint values set in Phase 4)

| Component (`key`) | Inputs (indicator keys) | Support | Scoring direction |
|---|---|---|---|
| `soil_water_buffer` | `aws_0_150` | F | Higher AWS → higher score |
| `terrain_erosion_risk` | `slope_p90_pct`, hydrologic group | F | Steeper slope / group D → lower score |
| `vegetation_stability` | `ndvi_peak_cv` over available years (HLS 2016→ where S30 + L30 overlap) | F | Lower interannual CV → higher score |
| `climate_exposure` | `precip_anomaly_pct` (multi-year variability), `heat_stress_days`, `sm_rootzone_dry_days` | **R** | More exposure → lower score |
| `rotation_diversity` | `distinct_crops`, `max_monoculture_run`, `rotation_shannon` (CDL 2006–2025) | F | More diversity, shorter runs → higher score |

**Rules [REC, frozen]:**
1. **Absolute, documented breakpoints**, not percentiles within the AOI.
   - Each component maps its inputs to 0–100 with a piecewise-linear table (`rule_ref` = table id + version).
   - Each breakpoint is either cited or explicitly labelled "SOILSTICE heuristic".
   - Fields are never ranked against each other.
2. **Band:** < 40 `low`; 40–70 `moderate`; > 70 `high`. A missing component gets band `unknown`.
3. **Composite:**
   - Equal-weighted mean of the available components.
   - Computed only if ≥ 4 of 5 components are available; otherwise `status = "insufficient_data"`.
   - Weights live in the versioned model config, not in code.
4. **Confidence** per component:
   - `high`: support F and completeness ≥ 0.9.
   - `medium`: support S, or completeness 0.6–0.9.
   - `low`: support R or completeness < 0.6.
   - Composite confidence = the lowest component confidence among those used.
5. **Explanations** are generated from the rule table, e.g. "AWS 0–150 cm is in the upper breakpoint range". There are no free-form claims.
6. The model is versioned `soilstice-resilience-<semver>` and stored on every profile.

### 5.11 Crop knowledge base and rotation recommendation methodology (framework frozen; KB content in Phase 5)

- **Candidate set:** crops present in AOI CDL history, namely winter wheat (24), corn (1), sorghum (4), soybeans (5), alfalfa (36), double-crop winter wheat/soybeans (26) and fallow/idle (61). Codes 24, 26, 36 and 61 must be confirmed against the CDL attribute table at ingest. Code 236 (double-crop winter wheat/sorghum) was observed live at the Reno test point, and its inclusion is a Phase 5 KB decision.
- **KB entry per crop:**
  - Season window (planting → harvest).
  - GDD base/cap.
  - pH optimal and acceptable ranges.
  - Drainage tolerance.
  - Minimum AWS / drought tolerance.
  - Maximum slope.
  - Rotation rules: self-rotation penalty, beneficial and adverse predecessors, family.
  - **A citation for every threshold** (K-State Research and Extension, NRCS or peer-reviewed). Entries without citations are blocked from the live KB. The KB is versioned (`kb_version`).
- **Suitability = limiting-factor method:** FAO land-evaluation style.
  - Each factor is classed `suitable` / `marginal` / `unsuitable` against the KB thresholds.
  - The overall class is the *worst* factor.
  - Factors with regional support (R) can at most downgrade to `marginal`, never to `unsuitable`.
- **Ranking within a class:**
  1. Rotation-history fit (break of monoculture, beneficial predecessor).
  2. Number of `marginal` factors.
- **Scenario evaluation:** applies the same rules year by year, plus sequence rules: maximum consecutive same crop, distinct crops, legume inclusion, fallow frequency. Outputs four dimension bands: agronomic fit, rotation benefit, water risk, diversity.
- **Not in scope:** yield, price or profit forecasts. AMS Market News stays excluded.

---

## 6. Normalized data contracts

> **All JSON below is a schema illustration. Every numeric value is a placeholder, not a real observation.** Each example carries `"_example": true`, and adapters must reject any payload containing that key.
>
> **Scope note (2026-11-14):** this section describes **storage-level** records. The **wire contract** between the frontend and FastAPI is [SOILSTICE_API_CONTRACTS.md](SOILSTICE_API_CONTRACTS.md), which is authoritative for field names, enums and units on the API. Storage rows map to it one-to-one through `SourceRef`, `SpatialSupport`, `TemporalSupport` and `QualityInfo`.

### 6.1 Common conventions

- IDs: UUID v4 strings.
- Timestamps: ISO 8601 UTC (`Z`). Dates: `YYYY-MM-DD`. Intervals: `start` inclusive, `end` inclusive for dates.
- Geometry: GeoJSON in EPSG:4326 in the API. PostGIS columns `geometry(MultiPolygon, 4326)`.
- `support_class`: `"F" | "S" | "R"` (see §5.4).
- `nature`: `"observation" | "model" | "derived" | "proxy_statistic"`.

### 6.2 Dataset metadata

```json
{
  "_example": true,
  "dataset_id": "nasa_smap_spl4smgp",
  "title": "SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data",
  "publisher": "NASA NSIDC DAAC",
  "product_short_name": "SPL4SMGP",
  "product_version": "008",
  "doi": "10.5067/<to-be-read-from-CMR>",
  "documentation_url": "https://nsidc.org/data/spl4smgp",
  "access_method": "earthaccess (CMR search + HTTPS), Earthdata Login",
  "native_crs": "EPSG:6933",
  "native_resolution_m": 9000,
  "temporal_resolution": "PT3H",
  "temporal_coverage": { "start": "2015-03-31", "end": null },
  "spatial_coverage": "global",
  "support_class": "R",
  "nature": "model",
  "variables": [
    { "name": "sm_surface", "unit": "m3 m-3", "depth_cm": [0, 5] },
    { "name": "sm_rootzone", "unit": "m3 m-3", "depth_cm": [0, 100] }
  ],
  "license": "NASA EOSDIS open data",
  "verification_status": "CMR",
  "last_verified": "2026-11-13"
}
```

### 6.3 Environmental observation (time series row)

```json
{
  "_example": true,
  "observation_id": "00000000-0000-4000-8000-000000000001",
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "dataset_id": "nasa_power_daily_ag",
  "product_version": "POWER Daily API v2.10.3",
  "variable": "precipitation",
  "source_variable": "PRECTOTCORR",
  "value": 0.0,
  "unit": "mm",
  "source_unit": "mm/day",
  "time": { "start": "2025-07-01", "end": "2025-07-01", "aggregation": "daily_sum", "time_standard": "LST" },
  "spatial": {
    "support_class": "R",
    "native_resolution_m": 55000,
    "extraction": "point_at_centroid",
    "cell_id": null,
    "field_fraction_of_cell": 0.0
  },
  "quality": { "status": "valid", "missing_reason": null, "flags": [], "completeness": 1.0 },
  "uncertainty": { "type": "none_provided", "value": null },
  "provenance": { "acquisition_id": "00000000-0000-4000-8000-0000000000a1", "sources": ["MERRA2"] }
}
```

### 6.4 Soil characteristics

```json
{
  "_example": true,
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "dataset_id": "usda_nrcs_ssurgo_sda",
  "survey_version": { "areasymbol": "KS000", "saverest": "YYYY-MM-DD" },
  "depth_interval_cm": [0, 30],
  "aggregation": "area_and_comppct_weighted_major_components",
  "properties": {
    "sand_pct":   { "value": 0.0, "low": 0.0, "high": 0.0, "unit": "%" },
    "silt_pct":   { "value": 0.0, "low": 0.0, "high": 0.0, "unit": "%" },
    "clay_pct":   { "value": 0.0, "low": 0.0, "high": 0.0, "unit": "%" },
    "texture_class": "placeholder",
    "ph_h2o":     { "value": 0.0, "low": 0.0, "high": 0.0, "unit": "pH" },
    "om_pct":     { "value": 0.0, "low": 0.0, "high": 0.0, "unit": "%" },
    "awc_cm_per_cm": { "value": 0.0, "unit": "cm cm-1" },
    "aws_0_100_cm":  { "value": 0.0, "unit": "cm" },
    "aws_0_150_cm":  { "value": 0.0, "unit": "cm" },
    "drainage_class": "placeholder",
    "hydrologic_group": "placeholder",
    "slope_pct_ssurgo": { "value": 0.0, "unit": "%" }
  },
  "map_units": [
    { "mukey": "0000000", "muname": "placeholder", "area_fraction": 1.0, "major_components": [ { "cokey": "0", "compname": "placeholder", "comppct_r": 0 } ] }
  ],
  "spatial": { "support_class": "F", "source_scale": "1:12000-1:24000" },
  "quality": { "null_weight_fraction": 0.0, "missing_reason": null },
  "provenance": { "acquisition_id": "00000000-0000-4000-8000-0000000000a2" }
}
```

### 6.5 Crop-history observation

```json
{
  "_example": true,
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "dataset_id": "usda_nass_cdl",
  "year": 2025,
  "majority_class": { "code": 0, "name": "placeholder" },
  "purity": 0.0,
  "class_histogram": [ { "code": 0, "name": "placeholder", "area_fraction": 0.0 } ],
  "pixels": { "valid": 0, "total": 0, "inward_buffer_m": 15 },
  "native_resolution_m": 30,
  "quality": {
    "class_accuracy": { "producer_accuracy": null, "user_accuracy": null, "source": "NASS CDL state metadata" },
    "low_purity": false,
    "missing_reason": null
  },
  "cross_check": { "csb_crop_code": null, "agrees": null },
  "provenance": { "acquisition_id": "00000000-0000-4000-8000-0000000000a3" }
}
```

### 6.6 Vegetation observation

```json
{
  "_example": true,
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "dataset_id": "nasa_hls_vi",
  "product": "HLSS30_VI",
  "product_version": "2.0",
  "granule_id": "placeholder",
  "acquired_at": "2025-06-15T17:30:00Z",
  "index": "NDVI",
  "stats": { "median": 0.0, "mean": 0.0, "std": 0.0, "p10": 0.0, "p90": 0.0 },
  "pixels": { "valid": 0, "total": 0, "clear_fraction": 0.0, "inward_buffer_m": 15 },
  "quality": {
    "scene_accepted": false,
    "mask_counts": { "cloud": 0, "cloud_adjacent": 0, "cloud_shadow": 0, "snow_ice": 0, "water": 0 },
    "missing_reason": null
  },
  "spatial": { "support_class": "F", "native_resolution_m": 30, "crs": "EPSG:326xx" },
  "provenance": { "acquisition_id": "00000000-0000-4000-8000-0000000000a4" }
}
```

### 6.7 Terrain characteristics

```json
{
  "_example": true,
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "dataset_id": "nasa_srtm_gl1",
  "product_version": "003",
  "elevation_m": { "mean": 0.0, "min": 0.0, "max": 0.0, "vertical_datum": "EGM96" },
  "slope_deg": { "mean": 0.0, "p90": 0.0 },
  "slope_pct": { "mean": 0.0, "p90": 0.0 },
  "aspect_dominant": "placeholder",
  "method": { "slope_algorithm": "Horn 1981", "computed_in_crs": "EPSG:5070", "resampling": "bilinear" },
  "spatial": { "support_class": "F", "native_resolution_m": 30 },
  "quality": { "void_filled_pixels": 0, "missing_reason": null },
  "provenance": { "acquisition_id": "00000000-0000-4000-8000-0000000000a5" }
}
```

### 6.8 Field resilience profile

```json
{
  "_example": true,
  "profile_id": "00000000-0000-4000-8000-0000000000b1",
  "field_id": "00000000-0000-4000-8000-0000000000f1",
  "as_of": "2026-11-13",
  "model_version": "soilstice-resilience-0.0.0",
  "components": [
    {
      "name": "soil_water_buffer",
      "score": 0.0,
      "inputs": ["aws_0_150_cm"],
      "support_class": "F",
      "confidence": "placeholder",
      "explanation": "placeholder"
    },
    {
      "name": "seasonal_moisture_stress",
      "score": 0.0,
      "inputs": ["smap_rootzone_percentile", "precip_anomaly_pct"],
      "support_class": "R",
      "confidence": "placeholder",
      "explanation": "Regional context (9 km SMAP, ~50 km POWER): not field-measured."
    },
    { "name": "vegetation_vigor_stability", "score": 0.0, "inputs": ["ndvi_peak_series"], "support_class": "F", "confidence": "placeholder", "explanation": "placeholder" },
    { "name": "rotation_diversity", "score": 0.0, "inputs": ["cdl_sequence_2006_2025"], "support_class": "F", "confidence": "placeholder", "explanation": "placeholder" },
    { "name": "terrain_erosion_risk", "score": 0.0, "inputs": ["slope_pct_p90", "hydrologic_group"], "support_class": "F", "confidence": "placeholder", "explanation": "placeholder" }
  ],
  "crop_suitability": [
    { "crop": "placeholder", "score": 0.0, "limiting_factors": [], "regional_prior": { "source": "FAO GAEZ v5", "value": null } }
  ],
  "rotation": {
    "sequence": [ { "year": 2025, "crop": "placeholder", "source": "CDL" } ],
    "monoculture_max_run_years": 0,
    "distinct_crops": 0
  },
  "data_completeness": 0.0,
  "disclaimers": [
    "Scores are decision-support indicators, not agronomic prescriptions.",
    "Components marked support_class R are regional context and do not measure this field."
  ]
}
```

### 6.9 Proposed PostGIS tables (design only; no migrations in Phase 0)

| Table | Key columns |
|---|---|
| `dataset_metadata` | `dataset_id` PK, product fields per §6.2, `verification_status`, `last_verified` |
| `acquisition_log` | `acquisition_id` PK, `dataset_id` FK, `request_url`, `request_params_redacted` jsonb, `http_status`, `sha256`, `bytes`, `retrieved_at`, `object_uri` |
| `farms` | `farm_id` PK, `name`, `aoi_id` (`ks_reno`/`ks_finney`), timestamps |
| `fields` | `field_id` PK, `farm_id` FK, `name`, `geom geometry(MultiPolygon,4326)`, `area_ha`, `source` (`csb`/`user`), `csb_id`, `state_fips`, `county_fips`, `processing_status`, `created_at` |
| `processing_jobs` | `job_id` PK, `field_id` FK, `status`, `steps` jsonb, timestamps |
| `env_observations` | `observation_id` PK, `field_id` FK, `dataset_id` FK, `variable`, `t_start`, `t_end`, `value` (nullable), `unit`, `support_class`, `quality` jsonb, `acquisition_id` FK. Unique on (`field_id`, `dataset_id`, `variable`, `t_start`, `t_end`). |
| `soil_profiles` | `field_id` FK, `depth_top_cm`, `depth_bottom_cm`, `properties` jsonb, `map_units` jsonb, `acquisition_id` |
| `crop_history` | `field_id` FK, `year`, `majority_code`, `purity`, `histogram` jsonb, `acquisition_id`. PK (`field_id`, `year`, `dataset_id`). |
| `vegetation_observations` | `field_id`, `granule_id`, `acquired_at`, `index`, stats columns, `quality` jsonb |
| `terrain_profiles` | `field_id` PK, stats columns, `method` jsonb |
| `resilience_profiles` | `profile_id` PK, `field_id`, `as_of`, `model_version`, `payload` jsonb |
| `indicators` | `indicator_id` PK (`field_id:key:period_start`), `field_id` FK, `key`, `value` (nullable), `unit`, `support_class`, `quality` jsonb, `method_id`, `method_version`, `input_ids` text[] |
| `crop_kb` | `crop_code` PK, `name`, `family`, `is_double_crop`, `kb_version`, `thresholds` jsonb (each threshold with `citation_evidence_id`) |
| `rotation_scenarios` | `scenario_id` PK, `field_id` FK, `name`, `start_year`, `sequence` jsonb, `evaluation` jsonb, timestamps |
| `rotation_recommendations` | `recommendation_id` PK, `field_id` FK, `season_year`, `engine_version`, `kb_version`, `payload` jsonb |
| `evidence_items` | `evidence_id` PK, `kind`, `field_id` (nullable), `dataset_id`, `citation`, `url`, `doi`, `verification_status`, `related_ids` text[] |

Indexes: GIST on `fields.geom`; B-tree on (`field_id`, `variable`, `t_start`).

---

## 7. Technical integration stack (recommendation)

| Need | Recommended | Why | Alternatives considered |
|---|---|---|---|
| NASA Earthdata search, auth and download | **`earthaccess`** | Official NASA-supported library. Handles Earthdata Login, CMR search and authenticated HTTPS/S3 for NSIDC (SMAP), LP DAAC (HLS, SRTM) and GES DISC (IMERG, NLDAS). | `pystac-client` against CMR-STAC (good for HLS, which lists items as STAC); raw `requests` + `.netrc` |
| HLS scene discovery | **`pystac-client`** on `https://cmr.earthdata.nasa.gov/stac/LPCLOUD` **[LIVE]** | Bbox + datetime + cloud filters return COG asset URLs | `earthaccess.search_data(short_name="HLSS30")` |
| Raster I/O | **`rasterio`** (GDAL), **`rioxarray`** | Windowed COG reads; CRS handling | — |
| N-D arrays (SMAP HDF5, NLDAS/IMERG NetCDF) | **`xarray`** + `h5netcdf`/`netCDF4` | Labelled time series | `h5py` directly for SMAP groups |
| Vector | **`geopandas`**, **`shapely` 2.x**, **`pyproj`** | Standard | — |
| Zonal statistics | **`exactextract`** (Python bindings) | Fractional-coverage-correct statistics on small fields | `rasterstats` |
| POWER, PRISM, SDA, CropScape, Quick Stats, OpenET | **`httpx`** (or `requests`) + thin adapters | Plain REST; no SDK needed | `pynasapower` (community); `soilDB` is R-only |
| Terrain derivatives | `numpy` Horn kernel, or `xarray-spatial` / `richdem` | Small dependency | GDAL `gdaldem slope` |
| Backend | **FastAPI** + background worker (RQ/Arq or FastAPI `BackgroundTasks` for the MVP) | Matches the team stack | Celery (heavier) |
| Database | **Supabase Postgres + PostGIS** | Stores vectors, statistics and indicators. Rasters go to Supabase Storage as COGs/cache, not into Postgres. | PostGIS raster (avoid: heavy, slow) |
| Frontend | Next.js + MapLibre GL | Field polygons + attribute display | — |
| Google Earth Engine | **Not recommended for the MVP** | Needs a registered Cloud project and noncommercial-use eligibility, and adds a second processing paradigm. Every P0 product is reachable directly. Keep it as an optional exploration tool. **[DOC/UNVERIFIED: verify current GEE noncommercial terms if reconsidered]** | — |

**Simplest reliable path [REC]:** pre-compute everything for a fixed set of demo fields (CSB polygons in Reno and Finney counties) in a batch job. Store the statistics in PostGIS and serve them read-only through FastAPI. User-drawn fields are restricted to the two AOI counties. For them, POWER and SDA are called on demand, and CDL is clipped from the cached AOI county GeoTIFFs. SRTM statistics come from the cached AOI mosaic. HLS and SMAP for a new field are queued as a background job, and coverage reports `pending` until the job finishes. Avoid live SMAP/HLS processing during the judged demo.

---

## 8. Limitations and caveats

1. **Coarse-grid products are not field measurements.**
   - SMAP (9 km), POWER (~50 km meteorology, ~110 km solar), IMERG (~11 km) and GAEZ (~1 km) describe the surrounding region.
   - Kansas fields are typically ~65 ha (a quarter section), against ~8,100 ha in one SMAP cell.
2. **SMAP L4 is model-assimilated.** It is a land-surface-model estimate informed by SMAP brightness temperatures, not a direct measurement. SMAP L3 is a direct retrieval but has gaps and must be quality-filtered.
3. **CDL is a classification, not ground truth.**
   - Accuracy varies by crop and state, and is lower for minor crops such as sorghum and for double-crop classes.
   - From 2024 NASS publishes state-level accuracy on the CDL FAQ page rather than per-state metadata **[DOC]**.
   - Kansas CDL begins in 2006. Native pixel size for 2006–2009 must be checked at ingest **[UNVERIFIED; some early years may be 56 m]**.
4. **CSB polygons are not ownership or legal field boundaries [DOC].** They are crop-based segments.
5. **SSURGO values are representative values (`_r`)** for map-unit components, often estimated, not sampled at this field. The survey date varies by county. Use `_l`/`_h` as uncertainty bounds.
6. **SRTM dates from February 2000** and is a surface model (C-band), not bare earth. On cropland the bias is small, but tree lines and buildings inflate it.
7. **HLS VI historical back-processing** was expected to finish by mid-2026 **[DOC]**. Archive completeness for 2013–2019 must be confirmed in Phase 1 (Test H-3). If incomplete, compute indices from `HLSL30`/`HLSS30` surface reflectance.
8. **IMERG Final** lags about 3.5 months. CMR showed its end at 2025-09-30 on 2026-11-13.
9. **MODIS Terra and Aqua science collection is planned to end** in February and September 2027 respectively **[DOC]**. Do not build P0 features on MODIS.
10. **PRISM changed formats and web services on 2025-10-01 [DOC].**
    - The current file naming uses `25m` (2.5 arc-minute, about 4 km) and `30s` (30 arc-second, about 800 m) **[LIVE]**.
    - The older `.../prism/data/public/4km/...` path no longer returns a data file **[LIVE]**.
11. **OpenET eastern expansion** (December 2025) arrived without eastern field boundaries at announcement. This does not affect Kansas **[DOC]**.
12. **Rate limits:**
    - POWER does not publish a fixed numeric limit; it throttles rapid repeated requests **[DOC, via client documentation]**.
    - Quick Stats caps a request at 50,000 records.
    - OpenET publishes its quotas **[DOC, OpenET docs, read 2026-11-14]**:
      - Tier 1: 100 queries/month, ≤ 50,000 acres per request.
      - Tier 2 (Earth Engine-linked): 400 queries/month, ≤ 200,000 acres per request.
      - Global rate limit: 20 requests/minute, 500/hour.
      - The multipolygon endpoints were temporarily disabled at changelog v3.2.2 (dated 08-11-2026).
      - **Consequence:** one request per demo field, run once and cached.
    - SDA responses are capped in rows and time **[UNVERIFIED: exact limits; documented on SDA help pages]**.
