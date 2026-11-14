"""NASA SMAP L4 Global 3-hourly 9 km EASE-Grid Soil Moisture (SPL4SMGP v008) provider.

Acquisition + parsing (INTEGRATION_GUIDE §6).
CMR Granule search (open):
  https://cmr.earthdata.nasa.gov/search/granules.json?short_name=SPL4SMGP&version=008&bounding_box=W,S,E,N

Spatial Support: Regional context (R), 9 km EASE-Grid 2.0 (~8,100 ha grid cell).
Variables:
  - sm_rootzone: Root-zone soil moisture (0–100 cm), m³/m³
  - sm_surface: Surface soil moisture (0–5 cm), m³/m³

Failure isolation: Missing credentials or network issues emit honest missing_reasons.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .http import EarthdataAuth, HttpAcquirer, ProviderNotConfigured

CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
DATASET_ID = "nasa_smap_spl4smgp"
CELL_AREA_HA = 8100.0  # 9 km x 9 km = 81 km^2 = 8,100 ha


@dataclass
class SmapGranule:
    granule_id: str
    title: str
    h5_url: str
    start_time: datetime
    end_time: datetime


@dataclass
class SmapDailyValue:
    date: date
    sm_rootzone: float | None = None
    sm_surface: float | None = None
    missing_reason: str | None = None


class SmapClient:
    dataset_id = DATASET_ID

    def __init__(
        self,
        http: HttpAcquirer,
        auth_factory: Any = None,
        timeout_s: float = 60.0,
    ):
        self.http = http
        self._auth_factory = auth_factory
        self.timeout_s = timeout_s

    def search_granules(
        self,
        bounds: tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        limit: int = 100,
    ) -> list[SmapGranule]:
        """Search CMR for SPL4SMGP v008 granules. Open, no credentials required."""
        w, s, e, n = bounds
        params = {
            "short_name": "SPL4SMGP",
            "version": "008",
            "bounding_box": f"{w},{s},{e},{n}",
            "temporal": f"{start_date}T00:00:00Z,{end_date}T23:59:59Z",
            "page_size": min(100, limit),
        }

        resp = self.http.fetch(self.dataset_id, "GET", CMR_URL, params=params, timeout=self.timeout_s)
        doc = resp.json()
        entries = (doc.get("feed") or {}).get("entry", [])

        granules: list[SmapGranule] = []
        for ent in entries:
            title = ent.get("title", "")
            time_start_str = ent.get("time_start", "")
            time_end_str = ent.get("time_end", "")
            if not time_start_str:
                continue

            h5_href = ""
            for link in ent.get("links", []):
                href = link.get("href", "")
                if href.endswith(".h5") and "protected" in href:
                    h5_href = href
                    break
            if not h5_href:
                for link in ent.get("links", []):
                    href = link.get("href", "")
                    if href.endswith(".h5"):
                        h5_href = href
                        break

            try:
                dt_start = datetime.fromisoformat(time_start_str.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(time_end_str.replace("Z", "+00:00")) if time_end_str else dt_start
            except ValueError:
                continue

            granules.append(
                SmapGranule(
                    granule_id=ent.get("id", title),
                    title=title,
                    h5_url=h5_href,
                    start_time=dt_start,
                    end_time=dt_end,
                )
            )

        granules.sort(key=lambda g: g.start_time)
        return granules

    def get_auth(self) -> EarthdataAuth | None:
        if not self._auth_factory:
            return None
        try:
            return self._auth_factory()
        except ProviderNotConfigured:
            return None
