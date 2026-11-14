"""NASA POWER Daily API provider (INTEGRATION_GUIDE §1). Acquisition + parsing only; no aggregation here.

Endpoint: GET https://power.larc.nasa.gov/api/temporal/daily/point (no auth) [LIVE 2026-11-14]
Response: GeoJSON Feature; header {api.version, sources, fill_value (-999.0), time_standard ("LST")};
`parameters` {NAME: {units, longname}}; `properties.parameter` {NAME: {"YYYYMMDD": value}}.
Fill values become None with FILL_VALUE (never 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.repositories.records import AcquisitionRecord

from .http import HttpAcquirer, ProviderError

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DATASET_ID = "nasa_power_daily_ag"

# POWER parameter -> (canonical variable, label, expected POWER unit string, canonical contract unit)
PARAMETERS: dict[str, tuple[str, str, str, str]] = {
    "PRECTOTCORR": ("precipitation", "Precipitation (corrected)", "mm/day", "mm"),
    "T2M": ("t2m", "Mean air temperature at 2 m", "C", "degC"),
    "T2M_MAX": ("tmax", "Maximum air temperature at 2 m", "C", "degC"),
    "T2M_MIN": ("tmin", "Minimum air temperature at 2 m", "C", "degC"),
    "RH2M": ("rh2m", "Relative humidity at 2 m", "%", "percent"),
    "ALLSKY_SFC_SW_DWN": ("solar", "All-sky surface shortwave downward irradiance", "MJ/m^2/day", "MJ_m-2_day-1"),
}
SOLAR_PARAMETERS = {"ALLSKY_SFC_SW_DWN"}  # CERES SYN1deg (~1°) rather than MERRA-2 (~0.5° x 0.625°)


@dataclass
class PowerDaily:
    longitude: float
    latitude: float
    start: date
    end: date
    api_version: str
    sources: list[str]
    time_standard: str
    units: dict[str, str]
    values: dict[str, dict[date, float | None]]  # None = fill value
    fill_dates: dict[str, set[date]]
    acquisition: AcquisitionRecord
    header_elevation_m: float | None = None
    messages: list[str] = field(default_factory=list)


def parse_power_daily(doc: dict, acquisition: AcquisitionRecord, lon: float, lat: float, start: date, end: date
                      ) -> PowerDaily:
    try:
        header = doc["header"]
        params = doc["properties"]["parameter"]
        meta = doc.get("parameters", {})
    except (KeyError, TypeError) as exc:
        raise ProviderError(f"POWER response is missing expected keys: {exc}") from exc
    fill = header.get("fill_value", -999.0)
    values: dict[str, dict[date, float | None]] = {}
    fills: dict[str, set[date]] = {}
    for name, series in params.items():
        vals: dict[date, float | None] = {}
        fset: set[date] = set()
        for key, v in series.items():
            d = datetime.strptime(key, "%Y%m%d").date()
            if v is None or float(v) == float(fill):
                vals[d] = None
                fset.add(d)
            else:
                vals[d] = float(v)
        values[name] = vals
        fills[name] = fset
    coords = (doc.get("geometry") or {}).get("coordinates") or []
    return PowerDaily(
        longitude=lon,
        latitude=lat,
        start=start,
        end=end,
        api_version=str((header.get("api") or {}).get("version") or "unknown"),
        sources=[str(s) for s in header.get("sources", [])],
        time_standard=str(header.get("time_standard", "LST")),
        units={k: str(v.get("units")) for k, v in meta.items()},
        values=values,
        fill_dates=fills,
        acquisition=acquisition,
        header_elevation_m=float(coords[2]) if len(coords) > 2 and coords[2] is not None else None,
        messages=[str(m) for m in doc.get("messages", [])],
    )


class PowerClient:
    dataset_id = DATASET_ID

    def __init__(self, http: HttpAcquirer):
        self.http = http

    def daily(self, lon: float, lat: float, start: date, end: date, *, cache: bool = True) -> PowerDaily:
        params = {
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "longitude": round(lon, 5),
            "latitude": round(lat, 5),
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        fetched = self.http.fetch(DATASET_ID, "GET", BASE_URL, params=params, cache=cache)
        try:
            doc = fetched.json()
        except ValueError as exc:
            raise ProviderError("POWER returned a non-JSON response.") from exc
        return parse_power_daily(doc, fetched.acquisition, lon, lat, start, end)
