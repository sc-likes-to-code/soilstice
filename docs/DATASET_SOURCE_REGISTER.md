# SOILSTICE: Dataset Source Register

**Research date:** 2026-11-13 · **Labels:** **[LIVE]** live endpoint test · **[CMR]** NASA CMR record · **[DOC]** official documentation · **[UNVERIFIED]** must be confirmed.

**Verification status column values:**
- `Verified-Live`: we called the endpoint ourselves.
- `Verified-CMR`: confirmed in NASA's catalog.
- `Verified-Doc`: confirmed in official documentation.
- `Partial`: some fields verified, others not.
- `Unverified`.

---

## 1. Summary register

| # | Dataset | Organization | Official source URL | Product identifier | Key variables | Native resolution | Temporal coverage | Access method | Priority | Verification status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NASA POWER | NASA LaRC | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ | POWER Daily API v2.10.3 (`community=AG`) | T2M, T2M_MAX/MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN, WS2M, GWETROOT | Meteorology ~0.5°×0.625° (MERRA-2); solar 1°×1° (CERES SYN1deg) | Daily, 1981→ (solar from 1984 **[UNVERIFIED]**) | REST GET, no auth | P0 | Verified-Live |
| 2 | SSURGO (Soil Data Access) | USDA NRCS | https://sdmdataaccess.sc.egov.usda.gov/ | SSURGO via SDA `Tabular/post.rest` | sand/silt/clay, om, pH, awc, drainagecl, hydgrp, aws0100/0150, slopegradwta | Survey polygons, 1:12k–1:24k | Static; survey vintage varies | REST POST (T-SQL), no auth | P0 | Verified-Live |
| 3 | Cropland Data Layer (CropScape) | USDA NASS (hosted by GMU CSISS) | https://nassgeodata.gmu.edu/CropScape/devhelp/getexamples.html | CDL 2000/2006–2025 | Crop/land-cover class (uint8) | 30 m (early years possibly 56 m **[UNVERIFIED]**) | Annual; national 2008→; KS 2006→; IA 2000→ | REST GET (`GetCDLValue`, `GetCDLFile`, `GetCDLStat`), no auth | P0 | Verified-Live |
| 4 | Crop Sequence Boundaries | USDA NASS | https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries | CSB 2018–2025 rev23 (`NationalCSB_2018-2025_rev23.zip` → `CSB1825.gdb/national1825`; released 2026-03-27) | Polygons + `CDL2018…CDL2025`, `CSBID`, `CSBACRES`, `STATEFIPS`, `CNTYFIPS` | Vector (segmented from CDL resampled to 10 m; ≥ ~1 ha; 60 m simplification); NAD83 Albers | 2018–2025 (windows back to 2008–2015) | National file-geodatabase zip; public domain | P0 (validated schema & reprojection) | Verified-Code + Doc |
| 5 | HLS Landsat | NASA LP DAAC | https://www.earthdata.nasa.gov/data/projects/hls | `HLSL30` v2.0 | SR bands B01–B07, B09–B11, Fmask | 30 m | 2013-04-11→ | CMR-STAC / earthaccess; Earthdata Login | P0 | Verified-CMR + STAC-Live |
| 6 | HLS Sentinel-2 | NASA LP DAAC | same | `HLSS30` v2.0 | SR bands B01–B12, B8A, Fmask | 30 m | 2015-11-28→ | same | P0 | Verified-CMR + STAC-Live |
| 7 | HLS Vegetation Indices | NASA LP DAAC | https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-vi-2.0 | `HLSL30_VI` v2.0, `HLSS30_VI` v2.0 (STAC `HLSL30_VI_2.0`, `HLSS30_VI_2.0`) | NDVI, EVI, SAVI, MSAVI, NDMI, NDWI, NBR, NBR2, TVI **+ Fmask asset** (int16, scale 0.0001, fill −9999) | 30 m | L30 2013→, S30 2015→ (back-processing due mid-2026) | CMR-STAC / earthaccess; Earthdata Login | P0 | Verified-CMR + STAC-Live |
| 8 | SMAP L4 Soil Moisture | NASA NSIDC DAAC | https://nsidc.org/data/spl4smgp | `SPL4SMGP` v008 | sm_surface, sm_rootzone, sm_profile | 9 km EASE-Grid 2.0 | 3-hourly, 2015-03-31→ | earthaccess; Earthdata Login | P0 | Verified-CMR-Live |
| 9 | SRTM | NASA LP DAAC | https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003 | `SRTMGL1` v003 | Elevation (m, EGM96) | 1″ (~30 m) | Static (2000-02-11..21) | earthaccess; Earthdata Login | P0 | Verified-CMR |
| 10 | PRISM | PRISM Group, Oregon State Univ. | https://prism.oregonstate.edu/ · web service guide: https://www.prism.oregonstate.edu/documents/PRISM_downloads_web_service.pdf | PRISM daily `ppt`, `tmin`, `tmax`, `tmean`, `tdmean`, `vpdmin`, `vpdmax` | as listed | 4 km (`25m`) and 800 m (`30s`) | Daily 1981→; monthly 1895→ **[DOC]** | REST GET `services.nacse.org/prism/data/get/us/{4km\|800m}/{var}/{YYYYMMDD}` → zip (COG + metadata), no auth | P1 | Verified-Live |
| 11 | OpenET | OpenET consortium (NASA, USGS, DRI, EDF, Google, et al.) | Docs: https://openet.gitbook.io/docs · API: https://openet-api.org | Collection 2.1 (API default `version: 2.1`; 2.1 assets cover all 48 contiguous states) | `et`, `eto`, `etr`, `etof`, `ndvi`, `pr`, `count`, … ; models `ensemble`, `disalexi`, `eemetric`, `geesebal`, `ptjpl`, `sims`, `ssebop` | 30 m | Daily from 2016; monthly from 2000 (data-availability table), but the changelog v3.2.0 says v2.1 starts 2015 (**conflict, unresolved**) | `POST /raster/timeseries/polygon` with `Authorization: <key>`; Tier 1: 100 queries/month, 50,000 acres/request, 20 req/min, 500/h | P1 | Verified-Doc (host Live) |
| 12 | NASS Quick Stats | USDA NASS | https://quickstats.nass.usda.gov/api | Quick Stats API (`api_GET`, `get_counts`, `get_param_values`) | Yield, planted/harvested acres, production | County / state | Annual (varies) | REST GET with key; 50,000 records per request | P1 | Verified-Live (auth required) + Doc |
| 13 | SMAP L3 Enhanced | NASA NSIDC DAAC | https://nsidc.org/data/SPL3SMP_E | `SPL3SMP_E` v006 | soil_moisture (AM/PM), retrieval_qual_flag | 9 km EASE-Grid 2.0 | Daily, 2015-03-31→ | earthaccess | P1 | Verified-CMR |
| 14 | GPM IMERG | NASA GES DISC | https://catalog.data.gov/dataset/gpm-imerg-final-precipitation-l3-1-day-0-1-degree-x-0-1-degree-v07-gpm-3imergdf-at-ges-dis-f1669 | `GPM_3IMERGDF` V07 (Final); `GPM_3IMERGDL` V07 (Late) | precipitation (mm/day) | 0.1° | Final: 1998-01-01..2025-09-30 (per CMR on 2026-11-13); Late: 1998→ | earthaccess / OPeNDAP; Earthdata Login | P2 | Verified-CMR |
| 15 | MODIS Vegetation Indices | NASA LP DAAC | https://www.earthdata.nasa.gov/data/catalog (MOD13Q1) | `MOD13Q1` v061 | NDVI, EVI, VI Quality | 250 m | 16-day, 2000-02-18→ (Terra science ends ~Feb 2027) | earthaccess | P2 | Verified-CMR + Doc |
| 16 | VIIRS Vegetation Indices | NASA LP DAAC | — | `VNP13A1` v002 | NDVI, EVI | 500 m | 16-day, 2012-01-17→ | earthaccess | P2 | Verified-CMR |
| 17 | MODIS ET | NASA LP DAAC | — | `MOD16A2GF` v061 | ET, PET, LE | 500 m | 8-day, 2000→ | earthaccess | Excluded (OpenET preferred) | Verified-CMR |
| 18 | ECOSTRESS ET | NASA LP DAAC | https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l3t-jet-003 | `ECO_L3T_JET` v002 / v003 | ET (PT-JPL-SM, STIC, BESS, PM-JPL ensemble) | 70 m | Irregular (ISS), 2018-07→ | earthaccess | P2 | Verified-CMR + Doc |
| 19 | NAIP | USDA FPAC-BC (APFO) | https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip · STAC: https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip | NAIP (4-band RGBN) | R, G, B, NIR | 0.5 / 0.6 / 1.0 m (varies by year/state) | ~2–3-yr cycle; PC holds 2010→ | Planetary Computer STAC (COG); USGS EarthExplorer | P2 | Verified-Doc |
| 20 | FAO GAEZ v5 | FAO + IIASA | https://www.fao.org/gaez/en/ | GAEZ v5 (launched 2025-04-14) | Crop suitability, attainable yield, agro-climatic indicators | 30″ (~1 km) for key outputs | Historical (AgERA5) + CMIP6 scenarios | GAEZ v5 Data Portal / Geospatial Platform; programmatic API **[UNVERIFIED]** | P2 | Verified-Doc (partial) |
| 21 | NLDAS-2 | NASA GES DISC | https://catalog.data.gov/dataset/nldas-primary-forcing-data-l4-hourly-0-125-x-0-125-degree-v2-0-nldas_fora0125_h-at-ges-dis | `NLDAS_FORA0125_H` v2.0; `NLDAS_NOAH0125_H` v2.0 | Forcing (T, q, P, SW, LW, wind); Noah soil moisture | 0.125° | Hourly, 1979→ | earthaccess; NetCDF (GRIB v002 retired) | P2 | Verified-CMR + Doc |
| 22 | CoCoRaHS | CoCoRaHS (Colorado Climate Center) | https://www.cocorahs.org/ | Daily precipitation reports | Precip, snow | Point (volunteer gauges) | Daily, 1998→ **[UNVERIFIED]** | Web export **[UNVERIFIED API]** | P2 | Unverified |
| 23 | USGS 3DEP | USGS | https://catalog.data.gov/dataset/1-3rd-arc-second-digital-elevation-models-dems-usgs-national-map-3dep-downloadable-data-collection | 3DEP 1/3 arc-second seamless DEM | Elevation | ~10 m | Continually updated | TNM downloads; `py3dep` (static 10/30/60 m service) | P2 (not on supplied list) | Verified-Doc |
| 24 | GLDAS | NASA GES DISC | — | `GLDAS_NOAH025_3H` v2.1 (2000→); v2.0 (1948–2014) | Land-surface states/fluxes | 0.25° | 3-hourly | earthaccess | Excluded | Verified-CMR |
| 25 | ERA5-Land | ECMWF / Copernicus C3S | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land | `reanalysis-era5-land` | 50+ land variables | 0.1° (~9 km) | Hourly, 1950→ | CDS API (`cdsapi`), account + licence acceptance | Excluded | Verified-Doc |
| 26 | ERA5 | ECMWF / Copernicus C3S | https://cds.climate.copernicus.eu/ | `reanalysis-era5-single-levels` **[UNVERIFIED id]** | Atmospheric reanalysis | 0.25° | Hourly, 1940→ **[UNVERIFIED]** | CDS API, account | Excluded | Partial |
| 27 | Annual NLCD | USGS EROS + MRLC | https://www.usgs.gov/centers/eros/science/annual-nlcd-science-user-product-guide | Annual NLCD Collection 1.1 | Land cover, change, confidence, impervious | 30 m | Annual 1985–2024 (released 2025-06) | EarthExplorer, MRLC, AWS S3 | Excluded | Verified-Doc |
| 28 | Landsat Collection 2 | USGS | https://www.usgs.gov/landsat-missions | Landsat C2 L2 SR/ST | SR bands, ST | 30 m | 1982→ (TM onward) | EarthExplorer, M2M API, AWS | Excluded (via HLS) | Not re-verified (covered by HLS) |
| 29 | Sentinel-2 | ESA / Copernicus | https://dataspace.copernicus.eu/ | S2 MSI L2A | 13 bands | 10/20/60 m | 2015→ | Copernicus Data Space | Excluded (via HLS) | Not re-verified (covered by HLS) |
| 30 | GEDI | NASA LP DAAC / ORNL DAAC | — | `GEDI02_A` v003 (v002 ended 2025-07-10 per CMR) | Footprint canopy height/elevation | ~25 m footprints, sparse | 2019-04→ | earthaccess | Excluded | Verified-CMR |
| 31 | LANDFIRE | USGS / USFS | https://landfire.gov/ | LANDFIRE (EVT, fuels, etc.) | Vegetation type/fuel | 30 m | Periodic | LANDFIRE Product Service | Excluded | Not re-verified (excluded on scope) |
| 32 | USGS NWIS / Water Data APIs | USGS | https://www.usgs.gov/tools/usgs-water-data-apis | Water Data OGC API (`api.waterdata.usgs.gov/ogcapi/`); legacy `waterservices.usgs.gov` decommissioning Q1 2027 (2027-02-22 per USGS bulletin) | Streamflow, gage height, groundwater | Point (gauges) | Varies | OGC API Features | Excluded | Verified-Doc |
| 33 | USDA AMS Market News | USDA AMS | https://mymarketnews.ams.usda.gov/mars-api | MyMarketNews (MARS) API v1.2 | Commodity price reports | Market/region | Daily/weekly | REST with personal API key (basic auth) | Excluded | Verified-Doc |
| 34 | Web Soil Survey | USDA NRCS | https://websoilsurvey.nrcs.usda.gov/ | Web Soil Survey (interactive) | Same as SSURGO | — | — | Browser UI | Excluded as integration (use SDA) | Not re-verified (UI) |
| 35 | Ag Data Commons | USDA NAL | https://agdatacommons.nal.usda.gov/ | Repository | n/a | n/a | n/a | Catalog | Excluded as integration | Not re-verified (catalog) |
| 36 | STATSGO2 | USDA NRCS | via SDA | STATSGO2 (`areasymbol='US'`) | Generalized soil properties | 1:250,000 | Static | SDA | Fallback only | Unverified query form |
| 37 | NASS Crop Frequency Layers | USDA NASS | https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_Crop-Frequency-Layers-2025_FGDC-STD-001-1998.htm | Crop Frequency Layers 2025 | Planting frequency of corn, cotton, soybeans, wheat (2008–2025) | 30 m | Cumulative 2008→ | NASS download | Optional (derivable from CDL) | Verified-Doc |

---

## 2. Live verification log (2026-11-13)

| Check | Request (abbreviated) | Result |
|---|---|---|
| POWER daily point | `/api/temporal/daily/point?parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,GWETROOT&community=AG&longitude=-93.62&latitude=42.03&start=20240701&end=20240703` | 200; API v2.10.3; sources MERRA2, SYN1DEG, POWER; fill −999; time standard LST |
| SDA point → mapunit | `SDA_Get_Mukey_from_intersection_with_WktWgs84('point(-93.62 42.03)')` | mukey 2765537 "Clarion loam, Bemis moraine, 2 to 6 percent slopes" |
| SDA horizons (Reno KS) | `point(-98.05 37.95)` joined to component/chorizon | mukey 1443836 Nalim loam; 6 horizons with sand/silt/clay/om/pH/awc |
| SDA muaggatt | same point | aws0100wta 16.14, aws0150wta 21.68, drclassdcd "Well drained", hydgrpdcd C |
| CropScape value (lon/lat) | `GetCDLValue?year=2024&x=-93.62&y=42.03` | Fault "Failed to get value" (coordinates must be EPSG:5070) |
| CropScape value (Albers) | `GetCDLValue?year=2024|2025&x=195689&y=2116719` | value 123 "Developed/Medium Intensity" |
| CropScape file | `GetCDLFile?year=2025&fips=19169` | returnURL `.../CDL_2025_19169.tif` |
| CropScape year range | `GetCDLFile` Reno 2005/2006/2007/2008; Story 2000/2001 | KS 2005 not available; 2006+ OK; IA 2000+ OK |
| CropScape stats | `GetCDLStat?year=2024&fips=…&format=json` (7 counties) | OK; non-standard JSON (unquoted keys) |
| PRISM 4 km daily | `services.nacse.org/prism/data/get/us/4km/ppt/20240701` | 200; zip with `prism_ppt_us_25m_20240701.tif` (+ .stn.csv, .info.txt, .xml, .prj) |
| PRISM 800 m daily | `…/get/us/800m/ppt/20240701` | 200; `prism_ppt_us_30s_20240701.zip` (headers only) |
| PRISM legacy path | `…/prism/data/public/4km/ppt/20240701` | 200 with 430-byte HTML (no data); legacy path not usable |
| CMR-STAC HLS | `cmr.earthdata.nasa.gov/stac/LPCLOUD/collections/HLSL30_2.0` | Collection JSON returned |
| OpenET host | `HEAD https://openet-api.org/` | 405 (allow: GET), so the host is live |
| Quick Stats | `get_counts/?key=INVALID…` | `{"error":["unauthorized"]}`, so a key is required |
| CMR collections | 20 short names queried | Versions/time ranges as listed in §1 (VNP16A2: no CMR record found under that short name) |
| *2026-11-14 additions* | | |
| HLS STAC collection list | `GET /stac/LPCLOUD/collections` | `HLSL30_2.0`, `HLSS30_2.0`, `HLSL30_VI_2.0`, `HLSS30_VI_2.0` |
| HLS-VI items | STAC search, Reno bbox, June 2025 | 26 S30-VI / 15 L30-VI matched; assets include `Fmask` and the nine indices |
| SDA clipped map units | `~GetClippedMapunits(@aoi,polygon,geo,@int)~` on a ~1 km square | 4 rows / 3 mukeys; areas returned in degree² (compute locally) |
| SDA geography intersection | `mupolygongeo.STIntersection(geography::…)` | Error: geography incompatible with geometry (approach rejected) |
| CropScape Reno point | `GetCDLValue` at (−178419, 1659145) | 2024 = 236 Dbl Crop WinWht/Sorghum; 2025 = 1 Corn |
| CropScape bbox | `GetCDLFile?year=2024|2025&bbox=…` | Timed out (60 s) twice, so use fips only |
| CropScape intermittency | `GetCDLValue` 2025 | First attempt hung > 100 s; retry answered in 1.5 s |

---

## 3. Items that could not be verified

*Status updated 2026-11-14. Resolved items are struck through with the outcome noted.*

| Item | Why it matters | How to resolve |
|---|---|---|
| ~~OpenET quota numbers~~ | API planning | **Resolved [DOC]:** Tier 1: 100 queries/month, 20/min, 500/h |
| OpenET start year for v2.1 (2000 vs 2015 conflict in its own docs) | P1 history depth | Test with one monthly request in Phase 3 |
| ~~HLS-VI STAC collection IDs; Fmask in VI granules~~ | Discovery + masking | **Resolved [LIVE]:** `HLS*30_VI_2.0`; Fmask present |
| HLS-VI historical back-processing completeness | Pre-2020 vegetation history | Test H-3 |
| HLS Fmask bits 0 and 4–7 | Correct masking | **Partly resolved:** bits 1–3 confirmed via a secondary source. The rest needs Test H-5. |
| SMAP L4 v008 HDF5 dataset paths, fill value, file size; Harmony/OPeNDAP subsetting | Download volume | Inspect one granule (Test M-1/M-2) |
| CDL pixel size for 2006–2009 Kansas rasters | Zonal-statistics consistency | Read the GeoTIFF transform at ingest |
| ~~CSB file format~~ / CSB file size | Download plan | **Format resolved [DOC]:** national FileGDB zip. Size still unknown. |
| CSB `CNTYFIPS` code width (3 vs 5 digits) | AOI filter | Inspect at ingest |
| SDA row/time limits and STATSGO query form | Batch sizing, fallback | SDA help pages |
| CoCoRaHS programmatic export | Validation dataset | CoCoRaHS site / contact |
| GAEZ v5 programmatic access | P2 suitability prior | GAEZ v5 portal docs |
| POWER solar record start (1984 vs 1981) and published rate limits | Climatology window | POWER docs |
| Google Earth Engine current noncommercial terms | Only if GEE is reconsidered | GEE terms page |
| Official challenge resource document | Brief references it, but none was found in the project folder | Team to supply |
