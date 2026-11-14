# SOILSTICE: Dataset Integration Guide (P0)

**Status:** Phase 0 specification. Code blocks are **reference snippets for Phase 1**. Nothing has been installed or implemented.
**Research date:** 2026-11-13
**Labels:** **[LIVE]** tested against the real endpoint on 2026-11-13 · **[CMR]** confirmed in NASA CMR · **[DOC]** official documentation · **[UNVERIFIED]** check before relying on it. Full definitions are in [SOILSTICE_DATA_ARCHITECTURE.md §0](SOILSTICE_DATA_ARCHITECTURE.md).

---

## 0. Shared conventions

### 0.1 Test locations

These are fixed test coordinates for smoke tests. They are **not** demo fields. Demo fields come from CSB polygons (§4).

| ID | Purpose | Lon, Lat (WGS84) | CONUS Albers (EPSG:5070) x, y | Notes |
|---|---|---|---|---|
| `KS-RENO-PT` | Primary AOI test point | −98.05, 37.95 | −178419, 1659145 (computed with the EPSG:5070 Albers formulas; cross-check with `pyproj` in Phase 3) | SDA returned mukey 1443836, "Nalim loam, 0 to 1 percent slopes" **[LIVE]**. CDL `GetCDLValue`: 2024 = 236 "Dbl Crop WinWht/Sorghum", 2025 = 1 "Corn" **[LIVE 2026-11-14]** |
| `IA-STORY-PT` | Fallback-region test point | −93.62, 42.03 | 195689, 2116719 (computed) | Inside Ames urban area. CDL 2024 value = 123 "Developed/Medium Intensity" **[LIVE]**. Use only for the service smoke test. |
| AOI county FIPS | County-file tests | Reno KS `20155`; Finney KS `20055` | — | — |

### 0.2 Credentials needed in Phase 1

The team must create these accounts. Store secrets in `.env`, never in code or docs.

| Credential | For | How |
|---|---|---|
| NASA Earthdata Login | SMAP (NSIDC), HLS + SRTM (LP DAAC), IMERG/NLDAS (GES DISC) | Register at `urs.earthdata.nasa.gov`. GES DISC additionally requires authorizing the "NASA GESDISC DATA ARCHIVE" application in the profile **[UNVERIFIED: current step name]**. |
| NASS Quick Stats API key (P1) | County statistics | `quickstats.nass.usda.gov/api` |
| OpenET API key (P1) | ET | Create the key in the Account Dashboard (`account.etdata.org`, API Keys tab). Send it as the raw value in the `Authorization` header, with no "Bearer" prefix. Quota: 100 queries/month (Tier 1), 20/min, 500/h **[DOC: openet.gitbook.io/docs, read 2026-11-14]** |

No credentials are needed for **POWER, SDA, CropScape, CSB or PRISM [LIVE]**.

### 0.3 Common adapter contract (design)

```python
# Design sketch for Phase 1. Not implemented.
class DatasetAdapter(Protocol):
    dataset_id: str
    def acquire(self, aoi: BaseGeometry, start: date | None, end: date | None) -> list[RawAsset]: ...
    def validate(self, asset: RawAsset) -> ValidationReport: ...
    def extract(self, asset: RawAsset, fields: GeoDataFrame) -> list[dict]: ...  # rows per data contract
```

Retry policy for all HTTP sources:
- Up to 3 retries with exponential backoff (2 s, 4 s, 8 s) and jitter, on 429, 5xx and timeouts.
- **No retry** on 4xx other than 429.
- Timeout: 60 s connect+read for REST; 300 s for large file downloads.
- Every failure writes an `acquisition_log` row with `http_status` and an error class.

---

## 1. NASA POWER (meteorology, solar radiation)

| Item | Detail |
|---|---|
| Product | POWER Daily API, `community=AG`. Header reported `"api": {"version": "v2.10.3"}` **[LIVE]** |
| Docs | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ · parameter dictionary: https://power.larc.nasa.gov/docs/tutorials/parameters/ |
| Endpoint | `GET https://power.larc.nasa.gov/api/temporal/daily/point` **[LIVE]** |
| Auth | None **[LIVE]** |
| Limits | Up to 20 parameters per point request for daily data. The API throttles rapid, repetitive requests; no fixed numeric limit is published **[DOC via `nasapower` client docs; confirm on POWER site]** |
| Python | `httpx` / `requests` (no SDK required) |

### 1.1 Retrieval example

```python
import httpx

PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M,GWETROOT"
r = httpx.get(
    "https://power.larc.nasa.gov/api/temporal/daily/point",
    params={
        "parameters": PARAMS, "community": "AG",
        "longitude": -98.05, "latitude": 37.95,
        "start": "20240101", "end": "20241231", "format": "JSON",
    },
    timeout=60,
)
r.raise_for_status()
doc = r.json()
series = doc["properties"]["parameter"]          # {"T2M": {"20240101": 1.23, ...}, ...}
fill = doc["header"]["fill_value"]               # -999.0  [LIVE]
units = {k: v["units"] for k, v in doc["parameters"].items()}
```

### 1.2 Tests

| Test | Procedure | Expected output | Validation checks |
|---|---|---|---|
| W-1 Minimal retrieval | 3-day request for `IA-STORY-PT` (already run on 2026-11-13: 2024-07-01..03) | HTTP 200 GeoJSON Feature; `header.sources` ⊇ `["MERRA2","SYN1DEG"]`; units T2M=`C`, PRECTOTCORR=`mm/day`, ALLSKY_SFC_SW_DWN=`MJ/m^2/day`, RH2M=`%`, GWETROOT=`1` **[LIVE]** | Keys present for every requested parameter and every date; `fill_value == -999` |
| W-2 AOI test | Full year 2024 at `KS-RENO-PT` | 366 daily values per parameter | Count = days in range; T2M_MIN ≤ T2M ≤ T2M_MAX on every non-fill day; 0 ≤ RH2M ≤ 100; PRECTOTCORR ≥ 0; ALLSKY ≥ 0 |
| W-3 Climatology | 1991-01-01..2020-12-31 in yearly chunks | 30 chunks succeed | No year with > 5% fill |

**Failure handling:**
- On 422/400, the parameter or date is invalid: log it and fail fast.
- On 429/5xx, back off and retry.
- On a partial range (recent days not yet available), store `null` with `NOT_YET_PUBLISHED`.

**Fallback:** PRISM (P1) for precipitation and temperature. If POWER is down during the demo, serve the cached precomputed values.

---

## 2. USDA NRCS SSURGO via Soil Data Access (soil properties)

| Item | Detail |
|---|---|
| Product | SSURGO, live database via Soil Data Access (SDA) |
| Docs | https://sdmdataaccess.sc.egov.usda.gov/ · Advanced/spatial macros: https://sdmdataaccess.sc.egov.usda.gov/documents/AdvancedQueries.html · test page: https://sdmdataaccess.sc.egov.usda.gov/test/testpost.html |
| Endpoint | `POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest`, body `{"format": "JSON+COLUMNNAME", "query": "<T-SQL>"}` **[LIVE]** |
| Spatial macro | `SDA_Get_Mukey_from_intersection_with_WktWgs84('<WKT>')` returns mukeys intersecting a WGS84 WKT geometry **[LIVE, DOC]** |
| Auth | None **[LIVE]** |
| Limits | Row and time limits on responses **[UNVERIFIED: exact values]**. Keep queries to one field or one batch of ≤ 50 fields. |
| Python | `httpx`; `shapely` for WKT; `geopandas` for the polygon form |

### 2.1 Retrieval example

```python
import httpx
from shapely.geometry import Polygon

wkt = field_polygon_wgs84.wkt   # lon lat order; simplify to keep the request small
SQL = f"""
SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.majcompflag,
       c.drainagecl, c.hydgrp,
       h.hzdept_r, h.hzdepb_r, h.sandtotal_r, h.silttotal_r, h.claytotal_r,
       h.om_r, h.ph1to1h2o_r, h.awc_r,
       h.sandtotal_l, h.sandtotal_h, h.claytotal_l, h.claytotal_h,
       h.om_l, h.om_h, h.ph1to1h2o_l, h.ph1to1h2o_h
FROM mapunit mu
JOIN component c ON c.mukey = mu.mukey
JOIN chorizon h  ON h.cokey  = c.cokey
WHERE mu.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}'))
  AND c.majcompflag = 'Yes'
ORDER BY mu.mukey, c.comppct_r DESC, h.hzdept_r
"""
r = httpx.post("https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest",
               json={"format": "JSON+COLUMNNAME", "query": SQL}, timeout=120)
r.raise_for_status()
table = r.json().get("Table", [])   # first row = column names; absent key => no rows
```

Map-unit aggregates (AWS and drainage) come from the `muaggatt` table: `aws0100wta`, `aws0150wta`, `drclassdcd`, `slopegradwta`, `hydgrpdcd` **[LIVE]**.

**Area fractions (verified 2026-11-14):** the tabular call above returns no geometry. Use the SDA clip macro:

```sql
~DeclareGeometry(@aoi)~
SELECT @aoi = geometry::STPolyFromText('<field WKT, lon lat>', 4326);
~DeclareIdGeomTable(@int)~
~GetClippedMapunits(@aoi,polygon,geo,@int)~
SELECT id AS mukey, geom.STAsText() AS wkt FROM @int
```

- **[LIVE]** For an ~0.9 × 1.1 km test square at `KS-RENO-PT`, this returned 4 rows over 3 mukeys (1443836, 1443853 twice, 1443851).
- Sum rows per mukey, reproject the WKT to EPSG:5070 and compute `area_fraction` locally. `geom.STArea()` is in degree², so don't use it.
- A direct `mupolygongeo.STIntersection(geography::…)` query **fails** with "geography is incompatible with geometry" **[LIVE]**, so use the macro.
- Fallback: gSSURGO 10 m raster mukeys via zonal statistics.
- The full aggregation rule is in DATA_ARCHITECTURE §5.3.1.

### 2.2 Tests

| Test | Procedure | Expected output | Validation checks |
|---|---|---|---|
| S-1 Minimal | Point WKT `point(-98.05 37.95)` (run on 2026-11-13) | mukey `1443836`, Nalim loam, major component Nalim 80%, "Well drained", hydgrp C, 6 horizons 0–200 cm; muaggatt aws0100wta 16.14, aws0150wta 21.68 **[LIVE]** | Header row present; horizons contiguous (`hzdepb_r[i] == hzdept_r[i+1]`) |
| S-2 Field polygon | Polygon from a CSB field in Reno County | ≥ 1 mukey; Σ area fractions ≈ 1 (± 0.02) | sand + silt + clay ≈ 100 (± 2) per horizon; 3 ≤ pH ≤ 10; 0 ≤ OM ≤ 100; 0 ≤ AWC ≤ 0.6 |
| S-3 County completeness | `SELECT COUNT(*)` of major-component horizons in Reno/Finney with null `ph1to1h2o_r`, `om_r`, `awc_r` (survey areas KS155, KS055 **[UNVERIFIED symbols]**) | Null fraction reported | Flag if > 10% |

**Failure handling:**
- An empty `Table` means no SSURGO coverage. Fall back to STATSGO2 (`SDA_Get_Mukey_from_intersection_with_WktWgs84` returns SSURGO implicitly **[DOC]**; STATSGO needs `legend.areasymbol = 'US'` queries **[UNVERIFIED]**).
- An HTTP 500 with an SQL error message is a bug in our query: do not retry.
- On timeout, simplify the polygon (`shapely.simplify(10 m)`) and retry once.

**Fallback:** gSSURGO / gNATSGO rasters (bulk download) for offline processing.

---

## 3. USDA NASS Cropland Data Layer via CropScape (crop history)

| Item | Detail |
|---|---|
| Product | Cropland Data Layer (CDL), annual, 30 m, 2025 is the latest year **[LIVE]** |
| Docs | Developer guide: https://nassgeodata.gmu.edu/CropScape/devhelp/getexamples.html · Metadata: https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/meta.php · FAQ (accuracy): https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php |
| Endpoints **[LIVE]** | `GET https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLValue?year=YYYY&x=<EPSG:5070 x>&y=<EPSG:5070 y>` · `GetCDLFile?year=YYYY&fips=<state or county FIPS>` (also `bbox=xmin,ymin,xmax,ymax` in EPSG:5070 **[DOC]**) → XML containing `<returnURL>` to a GeoTIFF · `GetCDLStat?year=YYYY&fips=<FIPS>&format=json` → URL to a JSON-like stats file |
| Coordinate gotcha | `GetCDLValue` with lon/lat returns `Error: Failed to get value.` The service expects **EPSG:5070** coordinates **[LIVE]**. |
| Stats format gotcha | The `GetCDLStat` "json" output has **unquoted keys** (`{success:true, rows:[{value:1, ...}]}`) and is not valid JSON **[LIVE]**. Parse it with a regex or a JSON5 parser. |
| Year availability | Reno KS: 2006–2025 (2005 rejected); Story IA: 2000–2025 **[LIVE]**. Nationwide from 2008 **[DOC]**. |
| Auth / limits | None **[LIVE]**. Limits not published **[UNVERIFIED]**. Cache county files. |
| Reliability (2026-11-14) | `GetCDLFile` by **bbox** (EPSG:5070) timed out at 60 s on two attempts, and one `GetCDLValue` call hung for more than 100 s. The same calls by **fips** and an immediate retry of the value call answered in about 1.5 s **[LIVE]**. **Decision:** acquire **county GeoTIFFs by fips only**, clip locally, and never call CropScape per field at request time. Timeouts: 30 s for value, 120 s for file; up to 3 retries. |
| Response parsing | `GetCDLFile` / `GetCDLStat`: XML; extract `<returnURL>` with a regex or XML parser. `GetCDLValue`: XML wrapping a non-JSON object literal `{x: …, y: …, value: 236, category: "…", color: "…"}`; parse with a regex (`value:\s*(\d+)`, `category:\s*"([^"]*)"`). `GetCDLStat` file: JS-style object literal with unquoted keys; parse rows with a regex or a JSON5 parser. Errors come back as `<faultstring>` text, not HTTP status codes, so always check for `faultstring`. **[LIVE]** |
| Coordinate transform | Use `pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)`. The CDL GeoTIFF and the CSB use NAD83 Albers with standard parallels 29.5/45.5, origin 23°N/96°W **[DOC: CSB metadata]**, which match EPSG:5070. Confirm the GeoTIFF CRS at ingest. |
| Python | `httpx`, `rasterio`, `exactextract`, `pyproj` |

### 3.1 Retrieval example

```python
import re, httpx, rasterio

def cdl_county_tif(year: int, fips: str) -> str:
    xml = httpx.get("https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile",
                    params={"year": year, "fips": fips}, timeout=120).text
    m = re.search(r"<returnURL>(.*?)</returnURL>", xml)
    if not m:
        raise CDLUnavailable(xml)        # e.g., "The CDL data is not available ... for the year of 2005."
    return m.group(1)                    # https://nassgeodata.gmu.edu/webservice/nass_data_cache/byfips/CDL_2025_20155.tif

url = cdl_county_tif(2025, "20155")
# download once to the raw cache, then:
with rasterio.open(local_path) as src:
    assert src.crs.to_epsg() == 5070 or src.crs is not None   # confirm CRS at ingest (expected Albers)
    # exactextract categorical: frac / majority over the 15 m inward-buffered field polygon
```

**Crop codes in the AOI** (names confirmed in 2024 stats **[LIVE]**): 1 Corn, 4 Sorghum, 5 Soybeans. Expected but not yet seen in our live data: 24 Winter Wheat, 26 Dbl Crop WinWht/Soybeans, 36 Alfalfa, 61 Fallow/Idle Cropland **[DOC: standard CDL legend; confirm against each year's attribute table]**.

### 3.2 Tests

| Test | Procedure | Expected | Validation |
|---|---|---|---|
| C-1 Minimal | `GetCDLValue` at Albers (195689, 2116719), years 2024 & 2025 | `value: 123, category: "Developed/Medium Intensity"` **[LIVE]** | Parsed integer code; category string non-empty |
| C-2 County file | `GetCDLFile` 2025 / 20155 | URL `.../CDL_2025_20155.tif` **[LIVE: 2025/19169 URL returned]** | GeoTIFF opens; single band uint8; CRS present; pixel size recorded (30 m expected; **check 2006–2009**) |
| C-3 Field history | For one CSB field: 2006–2025 histograms | 20 rows | Each histogram sums to ~1; `purity` computed; flag years with purity < 0.6 |
| C-4 County sanity | `GetCDLStat` 2024 / 20155 | Winter wheat ≈ 43% of crop acres, Shannon ≈ 1.72 **[LIVE]** | Within ±1% when recomputed from the GeoTIFF |

**Failure handling:**
- A `faultstring` "not available" means the year is out of range: store `OUT_OF_TEMPORAL_RANGE`.
- If the GMU host fails, retry it. Then use the NASS bulk national/state downloads (`https://www.nass.usda.gov/Research_and_Science/Cropland/Release/index.php` **[UNVERIFIED path]**).

**Fallback:**
- CDL is also mirrored on Google Earth Engine (`USDA/NASS/CDL`, listed through the 2024 season **[DOC]**) and Source Cooperative **[DOC]**.
- Use these mirrors only if both NASS paths fail.

---

## 4. USDA NASS Crop Sequence Boundaries (field polygons)

| Item | Detail |
|---|---|
| Product | Crop Sequence Boundaries (CSB) 2018–2025. Released 2026-03-27 **[DOC]**. Public domain, no access constraints **[DOC]**. |
| Docs | https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries · metadata: https://data.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/metadata_Crop-Sequence-Boundaries-2025.htm |
| Access | National zip containing a **file geodatabase**: `https://www.nass.usda.gov/sites/default/files/Research_and_Science/Crop-Sequence-Boundaries/datasets/NationalCSB_2018-2025_rev23.zip`, layer `CSB1825.gdb/national1825` **[DOC]**. No state-level files are listed. Size not stated **[UNVERIFIED]**; expect a large national file. A community GeoParquet conversion exists on Source Cooperative (`fiboa/us-usda-cropland`) **[DOC]**, but the NASS file is the source of record. |
| Attributes **[DOC]** | `CSBID` (state FIPS + start/end year + sequence), `CSBACRES`, `CDL2018`…`CDL2025` (majority CDL code per year), `STATEFIPS`, `STATEASD`, `ASD`, `CNTY`, `CNTYFIPS`, `INSIDE_X`, `INSIDE_Y`, `Shape_Length`, `Shape_Area` |
| Construction **[DOC]** | Fully automated from a CDL stack, with no manual drawing: CDL resampled to 10 m; road and rail lines (TIGER) imposed; polygons < 1 ha with ≥ 2 crop years merged into neighbours; simplified at a 60 m tolerance. Boundaries are *crop* segments, not ownership or legal fields. Crop accuracy inherits the CDL's (~85–95% for major crops). |
| CRS **[DOC]** | NAD83 Albers Conical Equal Area (29.5/45.5, 23°N, 96°W), metres, so EPSG:5070-equivalent |
| Auth | None. Public domain, free to redistribute **[DOC]** |
| Python | `geopandas` (+ `pyogrio`, which reads FileGDB through GDAL's OpenFileGDB driver), `pyarrow` for GeoParquet |

### 4.1 Procedure

1. Download once (manual or scripted). Record the file name, size and sha256 in `acquisition_log`.
2. Read only the Kansas AOI with an attribute filter: `pyogrio.read_dataframe(path, layer="national1825", where="CNTYFIPS IN ('155','055') AND STATEFIPS = '20'")`. **Confirm at ingest** whether `CNTYFIPS` holds 3-digit or 5-digit codes.
   - Alternatively use `bbox=` given **in the layer's Albers CRS**, not WGS84.
3. **Reliability filter:** keep polygons where at least 6 of the 8 `CDL20xx` values are crop codes (not 62/63/111/121–124/141–143/176/190/195, i.e. pasture, forest, water, developed, wetlands), and `CSBACRES` ≥ 10. Record the filter in provenance.
4. Select 20–50 demo fields per AOI with a stratified pick:
   - wheat-dominant
   - corn/soy
   - sorghum
   - dryland vs irrigated (Finney)
5. Store them in `fields` with `source='csb'` and the original `CSBID`.

**Manual polygon fallback (decided):**
- Used if CSB is ruled ineligible, or if a demo field's CSB polygon is visibly wrong against NAIP.
- Users or the team draw polygons in the UI (Settings → Add field) inside the AOI counties, at most 260 ha. These are stored with `source='user'`.
- They run through exactly the same pipeline, and coverage shows any dataset not yet processed as `pending`.

### 4.2 Tests

| Test | Expected | Validation |
|---|---|---|
| B-1 Load | Reno County subset loads | Valid geometries (`make_valid`); CRS defined; areas 5–260 ha typical |
| B-2 Cross-check | For each demo field, CSB crop sequence vs our CDL majority per year (2018–2025) | Agreement ≥ 90% expected (CSB is derived from CDL); disagreements logged |

**Fallback:** user-drawn polygons in the UI, or polygons digitized over NAIP. Mark these `source='user'`.

---

## 5. HLS v2.0 + HLS-VI (vegetation, 30 m)

| Item | Detail |
|---|---|
| Products | `HLSL30` v2.0 (2013-04-11→), `HLSS30` v2.0 (2015-11-28→), `HLSL30_VI` v2.0, `HLSS30_VI` v2.0 (LPCLOUD) **[CMR]**. VI DOIs: `10.5067/HLS/HLSL30_VI.002`, `10.5067/HLS/HLSS30_VI.002` **[DOC]** |
| Docs | https://www.earthdata.nasa.gov/data/projects/hls · VI release: https://www.earthdata.nasa.gov/news/harmonized-landsat-sentinel-2-project-releases-vegetation-indices · HLS v2.0 User Guide (LP DAAC) for band and Fmask definitions |
| Endpoint | CMR-STAC `https://cmr.earthdata.nasa.gov/stac/LPCLOUD`, collection IDs `HLSL30_2.0`, `HLSS30_2.0`, `HLSL30_VI_2.0`, `HLSS30_VI_2.0` **[LIVE 2026-11-14]**. June 2025 search over a Reno bbox matched 26 S30-VI and 15 L30-VI items. MGRS tiles seen: T14SNH, T14SNG. |
| Assets **[LIVE]** | VI items: `EVI, Fmask, MSAVI, NBR, NBR2, NDMI, NDVI, NDWI, SAVI, TVI` (+ `s3_*` duplicates, browse, metadata). **The VI granules include Fmask**, so no second download is needed. S30 SR items: `B01–B12, B8A, Fmask, SAA, SZA, VAA, VZA`. |
| Scale / fill | SR and VI: int16, scale 0.0001, fill −9999. Fmask: uint8, fill 255 **[DOC: Earthdata catalog variable tables]** |
| Format | One COG per band or index, tiled on the MGRS grid in UTM (109.8 km tiles) **[DOC]** |
| Auth | Earthdata Login for asset download (HTTPS); STAC search is open |
| Bands | L30: B02 blue, B03 green, B04 red, **B05 NIR**, B06 SWIR1, B07 SWIR2, Fmask. S30: B02, B03, B04, B08 NIR broad, **B8A NIR narrow**, B11, B12, Fmask. Use B05 (L30) and B8A (S30) for harmonized NDVI **[DOC: HLS User Guide; confirm at implementation]**. SR scale factor 0.0001 **[UNVERIFIED for VI files]** |
| VI content | NDVI, EVI, SAVI, MSAVI, NDMI, NDWI, NBR, NBR2, TVI **[DOC]** |
| Archive status | VI historical processing was expected to finish by mid-2026 **[DOC]**. Confirm with Test H-3. |
| Python | `pystac-client`, `earthaccess` (auth), `rasterio`/`rioxarray`, `exactextract` |

### 5.1 Retrieval example

```python
import earthaccess, rasterio
from pystac_client import Client

earthaccess.login(strategy="netrc")          # ~/.netrc or env vars; never hard-code
earthaccess.get_requests_https_session()    # sets cookies for GDAL/rasterio via env below

cat = Client.open("https://cmr.earthdata.nasa.gov/stac/LPCLOUD")
items = cat.search(collections=["HLSS30_2.0", "HLSL30_2.0"],
                   bbox=field_bbox_wgs84, datetime="2025-04-01/2025-10-31",
                   limit=100).item_collection()

gdal_env = dict(GDAL_HTTP_COOKIEFILE="~/cookies.txt", GDAL_HTTP_COOKIEJAR="~/cookies.txt",
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS="TIF")
with rasterio.Env(**gdal_env):
    for it in items:
        nir_key = "B05" if it.collection_id.startswith("HLSL30") else "B8A"
        # windowed read of red, nir, Fmask for the field bbox (reproject polygon to item CRS)
        ...
```

### 5.2 Fmask filtering (to confirm against User Guide v2.0)

Bit status as of 2026-11-14:

- **Mask always:** bit 1 cloud, bit 2 adjacent to cloud/shadow, bit 3 cloud shadow. **[DOC, secondary]** NASA-IMPACT's `hls-vi` code cites the HLS User Guide v2, Table 9, for these.
- **Mask after confirmation:** bit 4 snow/ice, bit 5 water. **[UNVERIFIED]**
- **Soft flag only:** bits 6–7 aerosol level (00 climatology, 01 low, 10 medium, 11 high). **[UNVERIFIED]**
- **Ignore:** bit 0 cirrus (reserved). **[UNVERIFIED]**

We could not read the User Guide PDF (April 2026 edition) text in Phase 0.

**Test H-5 (Phase 3, first HLS task):** confirm all bit positions from one of these:
- the User Guide Table 9, opened in a PDF reader, or
- the `Fmask` COG's embedded band description, read with `gdalinfo` after Earthdata login.

Commit the confirmed table to the adapter's constants with a citation.

### 5.3 Tests

| Test | Procedure | Expected | Validation |
|---|---|---|---|
| H-1 STAC search | Search 2025-06 over a Reno County field bbox | ≥ 6 items across L30 + S30 (assumes ~2–3 day revisit before clouds) | Items have B04, B05/B8A and Fmask assets |
| H-2 Field NDVI | Compute the field median NDVI for every item in Apr–Oct 2025 | Seasonal curve; wheat fields peak Apr–May, summer crops Jul–Aug | −1 ≤ NDVI ≤ 1; clear fraction recorded; scenes with < 70% clear rejected |
| H-3 VI archive completeness | Count `HLSS30_VI`/`HLSL30_VI` granules per year 2013–2025 for the AOI MGRS tile(s), against counts of `HLSS30`/`HLSL30` | Equal counts if back-processing is complete | If VI < SR for any year, compute indices from SR for that year |
| H-4 VI vs SR consistency | For 5 scenes, compare NDVI from the VI product with NDVI computed from SR | Difference ≈ 0 (< 0.01) | Confirms scale factors and band choice |
| H-5 Fmask bit confirmation | Read the Fmask band description of one granule, or User Guide v2 Table 9 | Bit table matches §5.2 | Blocks enabling the bit 4/5 masks |

**Failure handling:**
- 401/403 means Earthdata auth or EULA is missing: surface a configuration error.
- On a COG read timeout, retry with backoff, then skip the scene with `UPSTREAM_ERROR`.
- If a month has zero clear scenes, store `null` with `QA_MASKED_CLOUD`.

**Fallback:** compute indices from `HLSL30`/`HLSS30` SR. For pre-2013 history, MODIS `MOD13Q1` (P2) at 250 m, labelled regional context.

---

## 6. SMAP L4 `SPL4SMGP` v008 (soil moisture)

| Item | Detail |
|---|---|
| Product | SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, `SPL4SMGP` **v008**, NSIDC_CPRD, 2015-03-31→ **[CMR]** |
| Docs | https://nsidc.org/data/spl4smgp |
| Access | `earthaccess.search_data(short_name="SPL4SMGP", version="008", temporal=..., bounding_box=...)` then download (HDF5, ~global files) |
| Auth | Earthdata Login |
| Variables | `Geophysical_Data/sm_surface` (0–5 cm), `Geophysical_Data/sm_rootzone` (0–100 cm), m³/m³; lat/lon in `cell_lat`/`cell_lon` **[UNVERIFIED: dataset paths; confirm with `h5py` listing]** |
| Grid | EASE-Grid 2.0 Global 9 km (EPSG:6933) |
| File size | Each 3-hourly granule is a global file, roughly tens of MB **[UNVERIFIED]**. 8 files per day × 365 days is large. **Use subsetting or a precomputed cell time series.** |
| Python | `earthaccess`, `h5py` / `xarray[h5netcdf]`, `numpy` |

### 6.1 Retrieval strategy [REC]

- Do **not** download the full archive.
- For each AOI, identify the handful of 9 km cells covering the demo fields (Reno ≈ 1,300 km² ≈ ~16 cells).
- Pull granules for the needed dates. Extract only those cells and persist a compact `(cell_id, time, sm_surface, sm_rootzone)` table.
- Option: NASA Harmony subsetting or OPeNDAP for SPL4SMGP, to fetch only the AOI **[UNVERIFIED: service availability for v008]**. Check `earthaccess` / Harmony capabilities in Test M-1.

```python
import earthaccess, h5py, numpy as np
earthaccess.login(strategy="netrc")
res = earthaccess.search_data(short_name="SPL4SMGP", version="008",
                              temporal=("2025-07-01", "2025-07-01"),
                              bounding_box=(-98.5, 37.7, -97.6, 38.2))
files = earthaccess.download(res, local_path=RAW_DIR / "smap")
with h5py.File(files[0]) as f:
    lat = f["cell_lat"][:]; lon = f["cell_lon"][:]
    sm = f["Geophysical_Data/sm_rootzone"][:]
    # nearest cell to field centroid; store row/col as cell_id
```

### 6.2 Tests

| Test | Procedure | Expected | Validation |
|---|---|---|---|
| M-1 Search | `earthaccess.search_data` for one day | 8 granules (3-hourly) | Version string "008"; granule names include the date |
| M-2 Extract | Root-zone soil moisture at the cell containing `KS-RENO-PT` | One float per granule | 0 ≤ value ≤ 0.6 m³/m³; fill (−9999 **[UNVERIFIED]**) mapped to null |
| M-3 Season | Apr–Oct 2025 daily means for AOI cells | ~214 values per cell | Completeness ≥ 95%; plausible response after PRISM/POWER rain events (lagged positive correlation) |

**Failure handling:**
- Missing granule: store `null` with `UPSTREAM_ERROR` and retry later.
- A daily mean with < 6 of 8 steps is `null`.

**Fallback:**
- SMAP L3 `SPL3SMP_E` v006 (daily, gappy).
- POWER `GWETROOT`, a unitless MERRA-2 wetness, labelled as such and never mixed with m³/m³.

---

## 7. SRTM `SRTMGL1` v003 (elevation, slope)

| Item | Detail |
|---|---|
| Product | NASA SRTM Global 1 arc-second v003, LP DAAC (LPCLOUD) **[CMR]**. DOI `10.5067/MEaSUREs/SRTM/SRTMGL1.003` **[DOC]** |
| Docs | https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003 (catalog page) |
| Access | `earthaccess.search_data(short_name="SRTMGL1", version="003", bounding_box=...)` → 1°×1° zipped `.hgt` tiles (e.g., `N37W099.SRTMGL1.hgt.zip`) **[DOC: tile naming by lower-left corner]** |
| Auth | Earthdata Login |
| Units / datum | metres, EGM96 geoid **[DOC]**; void-filled in v3 **[DOC]** |
| Python | `earthaccess`, `rasterio` (reads `.hgt`), `numpy` |

### 7.1 Procedure

1. Download the tiles covering the AOI. Reno County needs N37W098, N37W099, N38W098 and N38W099 **[REC: compute from bbox]**.
2. Mosaic the tiles, then reproject to EPSG:5070 at 30 m (bilinear).
3. Compute slope with a Horn kernel, in degrees and percent.
4. Run zonal statistics per field.

### 7.2 Tests

| Test | Expected | Validation |
|---|---|---|
| T-1 Search | ≥ 1 granule per 1° tile | Tile names match the bbox |
| T-2 Point elevation | Elevation at `KS-RENO-PT` | Within ±15 m of POWER's header elevation for the same point (POWER is a coarse-grid reference only; 3DEP spot check is better) |
| T-3 Field slope | Slope statistics for demo fields | Central KS cropland mostly 0–5%; compare with SSURGO `slopegradwta` (Nalim 0–1% map unit → expect mean < 2%) |

**Fallback:**
- NASADEM (`NASADEM_HGT` v001 **[CMR]**), an improved reprocessing of SRTM.
- USGS 3DEP 10 m (P2 upgrade, via `py3dep` **[DOC]**).

---

## 8. Dependencies and parallel development

```
                 ┌──────────────────────────┐
                 │ 4. CSB field polygons    │  (defines fields table)
                 └────────────┬─────────────┘
         ┌──────────┬─────────┼──────────┬───────────┬───────────┐
         ▼          ▼         ▼          ▼           ▼           ▼
   2. SSURGO   3. CDL    5. HLS     7. SRTM    1. POWER    6. SMAP L4
   (polygon)  (polygon) (polygon)  (polygon)  (centroid)  (centroid→cell)
         │          │         │          │           │           │
         └──────────┴─────────┴────┬─────┴───────────┴───────────┘
                                   ▼
                     Derived indicators → Resilience profile
```

| Integration | Depends on | Can start independently? |
|---|---|---|
| POWER | Only a lon/lat | **Yes**: day 1 |
| SSURGO/SDA | Polygon or point | **Yes**: use test points, then CSB polygons |
| CDL | County FIPS + polygons for zonal stats | **Yes** for download; zonal stats need CSB |
| CSB | None | **Yes**: the first data task, because it unblocks polygon stats |
| HLS | Earthdata Login; polygons | Auth setup is independent; stats need CSB |
| SMAP L4 | Earthdata Login | **Yes** (cell time series per AOI) |
| SRTM | Earthdata Login | **Yes** (AOI mosaic) |
| Derived indicators | All of the above | No |

**Shared prerequisite:** one Earthdata Login account plus a `.netrc` file covers HLS, SMAP and SRTM, so set it up first.

**Suggested parallel tracks for a 3–4 person team:**
- A: POWER + PRISM (P1).
- B: SDA + CSB + CDL.
- C: Earthdata auth + HLS.
- D: SMAP + SRTM.
