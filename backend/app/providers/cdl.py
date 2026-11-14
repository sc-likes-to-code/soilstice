"""USDA NASS Cropland Data Layer via CropScape (INTEGRATION_GUIDE §3; decision T16). Acquisition + parsing.

County GeoTIFFs are acquired BY FIPS ONLY (never by bbox, never per-field value calls) and cached.
Verified 2026-11-14 [LIVE]: GetCDLFile -> XML with <returnURL> to .../byfips/CDL_<year>_<fips>.tif (EPSG:5070,
30 m, uint8, nodata=None, value 0 = background outside the county). Out-of-range years answer HTTP 200 with a
<faultstring> ("...not available ... for the year of 2005."). GetCDLStat -> <returnURL> to a JS-style object
literal with unquoted keys; its rows carry the class names used as the per-year legend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.repositories.records import AcquisitionRecord

from .http import HttpAcquirer, ProviderError

BASE = "https://nassgeodata.gmu.edu/axis2/services/CDLService/"
DATASET_ID = "usda_nass_cdl"
FILE_TIMEOUT_S = 120.0

_RETURN_URL = re.compile(r"<returnURL>(.*?)</returnURL>", re.S)
_FAULT = re.compile(r"<faultstring>(.*?)</faultstring>", re.S)
_STAT_ROW = re.compile(r"\{\s*value\s*:\s*(\d+)\s*,[^{}]*?category\s*:\s*\"([^\"]*)\"")


@dataclass
class CdlCountyRaster:
    year: int
    fips: str
    path: Path
    url: str
    acquisition: AcquisitionRecord
    legend: dict[int, str]


def parse_return_url(xml: str) -> str:
    fault = _FAULT.search(xml)
    if fault:
        msg = fault.group(1).strip()
        reason = "OUT_OF_TEMPORAL_RANGE" if "not available" in msg.lower() else "UPSTREAM_ERROR"
        raise ProviderError(f"CropScape: {msg}", reason)
    m = _RETURN_URL.search(xml)
    if not m:
        raise ProviderError(f"CropScape response had no <returnURL>: {xml[:200]}")
    return m.group(1).strip()


def parse_stat_legend(text: str) -> dict[int, str]:
    return {int(code): name for code, name in _STAT_ROW.findall(text)}


class CdlClient:
    dataset_id = DATASET_ID

    def __init__(self, http: HttpAcquirer, download_timeout_s: float = 300.0):
        self.http = http
        self.download_timeout_s = download_timeout_s

    def county_raster(self, year: int, fips: str) -> CdlCountyRaster:
        if not re.fullmatch(r"\d{5}", fips):
            raise ProviderError(f"Invalid county FIPS {fips!r}.", "OUTSIDE_AOI")
        xml = self.http.fetch(DATASET_ID, "GET", BASE + "GetCDLFile", params={"year": year, "fips": fips},
                              timeout=FILE_TIMEOUT_S).text
        tif_url = parse_return_url(xml)
        tif = self.http.fetch(DATASET_ID, "GET", tif_url, timeout=self.download_timeout_s)
        if tif.content[:4] not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            raise ProviderError(f"CropScape file for {year}/{fips} is not a GeoTIFF.")
        if not tif.acquisition.object_uri:
            raise ProviderError("CDL raster was not cached to disk.")
        legend: dict[int, str] = {}
        try:
            stat_xml = self.http.fetch(DATASET_ID, "GET", BASE + "GetCDLStat",
                                       params={"year": year, "fips": fips, "format": "json"},
                                       timeout=FILE_TIMEOUT_S).text
            legend = parse_stat_legend(self.http.fetch(DATASET_ID, "GET", parse_return_url(stat_xml),
                                                       timeout=FILE_TIMEOUT_S).text)
        except ProviderError:
            legend = {}  # names fall back to "CDL class <code>"; the classification itself is unaffected
        return CdlCountyRaster(year=year, fips=fips, path=Path(tif.acquisition.object_uri), url=tif_url,
                               acquisition=tif.acquisition, legend=legend)
