"""Provider parsing and HTTP failure handling. All payloads are SYNTHETIC, shaped like the live formats."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date

import httpx
import numpy as np
import pytest

from app.providers.cdl import CdlClient, parse_return_url, parse_stat_legend
from app.providers.http import EarthdataAuth, HttpAcquirer, ProviderError, ProviderNotConfigured, redact
from app.providers.power import PowerClient, parse_power_daily
from app.providers.srtm import SIZE, SrtmClient, parse_hgt, tile_origin
from app.providers.ssurgo import SsurgoClient, mapunit_areas_from_clip, parse_saverest, parse_table, to_float

from .conftest import acq


def acquirer(tmp_path, handler, **kw):
    return HttpAcquirer(tmp_path, retries=kw.pop("retries", 2), backoff_base_s=0, transport=httpx.MockTransport(handler),
                        sleep=lambda s: None, **kw)


# ── HTTP layer ──────────────────────────────────────────────────────────────

def test_retry_on_503_then_success_and_cache(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(503) if len(calls) < 2 else httpx.Response(200, content=b'{"ok": true}')

    records = []
    h = acquirer(tmp_path, handler, record_sink=records.append)
    first = h.fetch("nasa_power_daily_ag", "GET", "https://x.test/a", params={"q": 1})
    assert first.json() == {"ok": True} and not first.from_cache and len(calls) == 2
    assert [r.error_class for r in records] == ["HTTP503", None]
    again = h.fetch("nasa_power_daily_ag", "GET", "https://x.test/a", params={"q": 1})
    assert again.from_cache and again.acquisition.acquisition_id == first.acquisition.acquisition_id
    assert len(calls) == 2  # served from the raw cache


def test_no_retry_on_400_and_no_5xx_retry_when_disabled(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(400 if "bad" in str(req.url) else 500)

    h = acquirer(tmp_path, handler)
    with pytest.raises(ProviderError):
        h.fetch("nasa_power_daily_ag", "GET", "https://x.test/bad")
    assert len(calls) == 1
    with pytest.raises(ProviderError):
        h.fetch("usda_nrcs_ssurgo_sda", "POST", "https://x.test/sql", json_body={}, retry_on_5xx=False)
    assert len(calls) == 2


def test_timeouts_exhaust_retries(tmp_path):
    def handler(req):
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(ProviderError) as e:
        acquirer(tmp_path, handler, retries=1).fetch("usda_nass_cdl", "GET", "https://x.test/slow")
    assert e.value.missing_reason == "UPSTREAM_ERROR"


def test_secrets_redacted():
    assert redact({"token": "abc", "year": 2025, "api_key": "k"}) == {"token": "<redacted>", "year": 2025,
                                                                      "api_key": "<redacted>"}


def test_earthdata_auth_requires_credentials_and_scopes_basic_to_urs():
    with pytest.raises(ProviderNotConfigured):
        EarthdataAuth()
    a = EarthdataAuth(username="u", password="p")
    assert a.initial_headers() == {}
    assert a.headers_for("urs.earthdata.nasa.gov")["Authorization"].startswith("Basic ")
    assert a.headers_for("data.lpdaac.earthdatacloud.nasa.gov") == {}
    assert EarthdataAuth(token="t").initial_headers() == {"Authorization": "Bearer t"}


def test_redirect_sends_basic_auth_only_to_urs(tmp_path):
    seen = []

    def handler(req):
        seen.append((req.url.host, req.headers.get("authorization")))
        if req.url.host == "data.test" and "code" not in str(req.url):
            return httpx.Response(302, headers={"location": "https://urs.earthdata.nasa.gov/oauth"})
        if req.url.host == "urs.earthdata.nasa.gov":
            return httpx.Response(302, headers={"location": "https://data.test/file?code=1"})
        return httpx.Response(200, content=b"zipbytes")

    h = acquirer(tmp_path, handler)
    out = h.fetch("nasa_srtm_gl1", "GET", "https://data.test/file", auth=EarthdataAuth(username="u", password="p"))
    assert out.content == b"zipbytes"
    assert seen[0][1] is None and seen[1][1].startswith("Basic ") and seen[2][1] is None


# ── POWER ───────────────────────────────────────────────────────────────────

POWER_DOC = {
    "header": {"api": {"version": "v2.10.3"}, "sources": ["MERRA2"], "fill_value": -999.0, "time_standard": "LST"},
    "parameters": {"PRECTOTCORR": {"units": "mm/day"}, "T2M": {"units": "C"}},
    "properties": {"parameter": {"PRECTOTCORR": {"20250101": 1.5, "20250102": -999.0, "20250103": 0.0},
                                 "T2M": {"20250101": 2.0, "20250102": -999, "20250103": 3.1}}},
    "geometry": {"type": "Point", "coordinates": [-98.05, 37.95, 497.36]},
}


def test_power_parse_fill_is_null_and_zero_is_kept():
    d = parse_power_daily(POWER_DOC, acq("nasa_power_daily_ag"), -98.05, 37.95, date(2025, 1, 1), date(2025, 1, 3))
    assert d.values["PRECTOTCORR"][date(2025, 1, 2)] is None
    assert d.values["PRECTOTCORR"][date(2025, 1, 3)] == 0.0  # real zero precipitation, not missing
    assert date(2025, 1, 2) in d.fill_dates["T2M"]
    assert d.api_version == "v2.10.3" and d.header_elevation_m == 497.36


def test_power_client_builds_request(tmp_path):
    seen = {}

    def handler(req):
        seen.update(dict(req.url.params))
        return httpx.Response(200, content=json.dumps(POWER_DOC).encode())

    d = PowerClient(acquirer(tmp_path, handler)).daily(-98.05, 37.95, date(2025, 1, 1), date(2025, 1, 3))
    assert seen["community"] == "AG" and seen["start"] == "20250101" and "ALLSKY_SFC_SW_DWN" in seen["parameters"]
    assert d.sources == ["MERRA2"]


def test_power_malformed_response():
    with pytest.raises(ProviderError):
        parse_power_daily({"nope": 1}, acq("nasa_power_daily_ag"), 0, 0, date(2025, 1, 1), date(2025, 1, 1))


# ── SSURGO ──────────────────────────────────────────────────────────────────

def test_sda_parsing_helpers():
    assert parse_table({"Table": [["a", "b"], ["1", None]]}) == [{"a": "1", "b": None}]
    assert parse_table({}) == []
    assert to_float("16.14") == 16.14 and to_float("") is None and to_float(None) is None and to_float("0") == 0.0
    assert parse_saverest("8/27/2026 2:30:06 PM") == date(2026, 8, 27)
    assert parse_saverest(None) is None


def test_clip_areas_summed_per_mukey():
    rows = [{"mukey": "1", "wkt": "POLYGON((-98.05 37.95,-98.049 37.95,-98.049 37.951,-98.05 37.951,-98.05 37.95))"},
            {"mukey": "1", "wkt": "POLYGON((-98.049 37.95,-98.048 37.95,-98.048 37.951,-98.049 37.951,-98.049 37.95))"},
            {"mukey": "2", "wkt": "POLYGON((-98.05 37.951,-98.049 37.951,-98.049 37.952,-98.05 37.952,-98.05 37.951))"}]
    a = mapunit_areas_from_clip(rows)
    assert set(a) == {"1", "2"} and a["1"] == pytest.approx(2 * a["2"], rel=0.01)
    assert 8000 < a["2"] < 10000  # ~88 m x 111 m in EPSG:5070


def test_ssurgo_no_mapunits_is_no_data_source(tmp_path):
    def handler(req):
        return httpx.Response(200, content=b"{}")

    from shapely.geometry import box

    with pytest.raises(ProviderError) as e:
        SsurgoClient(acquirer(tmp_path, handler)).fetch_for_polygon(box(-98.05, 37.95, -98.04, 37.96))
    assert e.value.missing_reason == "NO_DATA_SOURCE"


def test_ssurgo_rejects_non_numeric_mukeys():
    from app.providers.ssurgo import component_query

    with pytest.raises(ProviderError):
        component_query(["1; DROP TABLE x"])


# ── CDL ─────────────────────────────────────────────────────────────────────

def test_cdl_return_url_and_fault():
    ok = '<ns1:GetCDLFileResponse><returnURL>https://h/CDL_2025_20155.tif</returnURL></ns1:GetCDLFileResponse>'
    assert parse_return_url(ok) == "https://h/CDL_2025_20155.tif"
    fault = "<faultstring>Error: The CDL data is not available within the area of 20155 for the year of 2005.</faultstring>"
    with pytest.raises(ProviderError) as e:
        parse_return_url(fault)
    assert e.value.missing_reason == "OUT_OF_TEMPORAL_RANGE"


def test_cdl_stat_legend_unquoted_keys():
    text = ('{success:true, totalCount:2, rows:[{value:1, count:283340, category:"Corn", color:"#FFD400", '
            'acreage:63013.3},{value:236, count:5, category:"Dbl Crop WinWht/Sorghum", color:"#000", acreage:1.1}]}')
    assert parse_stat_legend(text) == {1: "Corn", 236: "Dbl Crop WinWht/Sorghum"}


def test_cdl_client_rejects_non_tiff_and_bad_fips(tmp_path):
    def handler(req):
        if "GetCDLFile" in str(req.url):
            return httpx.Response(200, text="<returnURL>https://h.test/x.tif</returnURL>")
        return httpx.Response(200, content=b"<html>error</html>")

    c = CdlClient(acquirer(tmp_path, handler))
    with pytest.raises(ProviderError):
        c.county_raster(2025, "20155")
    with pytest.raises(ProviderError) as e:
        c.county_raster(2025, "155")
    assert e.value.missing_reason == "OUTSIDE_AOI"


# ── SRTM ────────────────────────────────────────────────────────────────────

def test_srtm_tile_names_and_hgt_parsing():
    assert tile_origin("N37W099.SRTMGL1.hgt") == (37, -99)
    assert tile_origin("S01E010") == (-1, 10)
    arr = parse_hgt(np.full((SIZE, SIZE), 5, dtype=">i2").tobytes())
    assert arr.shape == (SIZE, SIZE) and arr[0, 0] == 5
    with pytest.raises(ProviderError):
        parse_hgt(b"\x00" * 10)


def test_srtm_requires_credentials_before_download(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(200, content=b"{}")

    def no_auth():
        raise ProviderNotConfigured("no creds")

    with pytest.raises(ProviderNotConfigured):
        SrtmClient(acquirer(tmp_path, handler), tmp_path, no_auth).tiles_for_bounds((-98.06, 37.94, -98.04, 37.96))
    assert calls == []


def test_srtm_download_end_to_end_with_synthetic_tile(tmp_path):
    hgt = (np.arange(SIZE, dtype="int32")[:, None] + np.zeros((1, SIZE), dtype="int32")).astype(">i2").tobytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("N37W099.hgt", hgt)
    link = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL1.003/N37W099.SRTMGL1.hgt/N37W099.SRTMGL1.hgt.zip"

    def handler(req):
        if "cmr.earthdata" in str(req.url):
            return httpx.Response(200, json={"feed": {"entry": [{"title": "N37W099.SRTMGL1.hgt",
                                                                 "links": [{"href": link}]}]}})
        assert req.headers["authorization"] == "Bearer tkn"
        return httpx.Response(200, content=buf.getvalue())

    tiles = SrtmClient(acquirer(tmp_path, handler), tmp_path, lambda: EarthdataAuth(token="tkn")).tiles_for_bounds(
        (-98.06, 37.94, -98.04, 37.96))
    assert [t.name for t in tiles] == ["N37W099"] and tiles[0].path.exists()
