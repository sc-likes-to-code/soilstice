"""Meteomatics environmental data provider.

Integrates:
- Soil moisture at four depths:
  - volumetric_soil_water_-5cm:m3m3
  - volumetric_soil_water_-15cm:m3m3
  - volumetric_soil_water_-50cm:m3m3
  - volumetric_soil_water_-150cm:m3m3
- Historical soil moisture time series
- Digital elevation: elevation:m
- Regional vegetation: sat_ndvi:idx

Features:
- HTTP Basic Authentication over HTTPS (credentials never placed in URLs or logged)
- Redaction of credentials in provenance and logs
- Error discrimination: missing credentials, 401 auth, 402/403 subscription/permission, 404 parameter/date,
  429 rate limit, 5xx server, network errors
- Model selection support (defaults to 'mix' for data requests)
- Point, time-series, and spatial grid queries
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Callable

import httpx
from shapely.geometry.base import BaseGeometry

from app.logging import get_logger
from app.providers.http import HttpAcquirer, ProviderError, ProviderNotConfigured

log = get_logger("providers.meteomatics")

DATASET_ID = "meteomatics"
BASE_URL = "https://api.meteomatics.com"

# Required parameter identifiers
SOIL_MOISTURE_PARAMETERS = [
    "volumetric_soil_water_-5cm:m3m3",
    "volumetric_soil_water_-15cm:m3m3",
    "volumetric_soil_water_-50cm:m3m3",
    "volumetric_soil_water_-150cm:m3m3",
]
ELEVATION_PARAMETER = "elevation:m"
NDVI_PARAMETER = "sat_ndvi:idx"

NODATA_VALUES = {-666, -666.0, -999, -999.0, -9999, -9999.0, -32768, -32768.0}


@dataclass(frozen=True)
class TimeSeriesObservation:
    timestamp: datetime
    value: float | None
    valid: bool


@dataclass(frozen=True)
class GridPoint:
    lat: float
    lon: float
    value: float | None
    valid: bool


class MeteomaticsError(ProviderError):
    """Categorized Meteomatics provider error."""

    def __init__(
        self,
        message: str,
        category: str,
        missing_reason: str = "UPSTREAM_ERROR",
        http_status: int | None = None,
    ):
        super().__init__(message, missing_reason=missing_reason, http_status=http_status)
        self.category = category


def format_iso(dt: datetime | date | str) -> str:
    """Format datetime as UTC ISO-8601 string expected by Meteomatics."""
    if isinstance(dt, str):
        return dt if dt.endswith("Z") else f"{dt}T00:00:00Z"
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return f"{dt.isoformat()}T00:00:00Z"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_value(v: Any) -> float | None:
    """Normalize missing/nodata values to None."""
    if v is None:
        return None
    try:
        val = float(v)
        if val in NODATA_VALUES or (isinstance(val, float) and (val < -900 or val != val)):
            return None
        return val
    except (ValueError, TypeError):
        return None


class MeteomaticsClient:
    dataset_id = DATASET_ID

    def __init__(
        self,
        http: HttpAcquirer,
        auth_factory: Callable[[], tuple[str | None, str | None]],
        base_url: str = BASE_URL,
        timeout_s: float = 60.0,
    ):
        self.http = http
        self._auth_factory = auth_factory
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _get_auth_header(self) -> dict[str, str]:
        username, password = self._auth_factory()
        if not username or not password:
            raise MeteomaticsError(
                "Meteomatics credentials not configured (METEOMATICS_USERNAME / METEOMATICS_PASSWORD missing).",
                category="MISSING_CREDENTIALS",
                missing_reason="NO_DATA_SOURCE",
            )
        pwd_val = password.get_secret_value() if hasattr(password, "get_secret_value") else str(password)
        if not pwd_val:
            raise MeteomaticsError(
                "Meteomatics credentials not configured (METEOMATICS_PASSWORD empty).",
                category="MISSING_CREDENTIALS",
                missing_reason="NO_DATA_SOURCE",
            )
        creds = f"{username}:{pwd_val}".encode()
        return {"Authorization": f"Basic {base64.b64encode(creds).decode('ascii')}"}

    def _execute_request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = self._get_auth_header()
        url = f"{self.base_url}/{path}"
        try:
            resp = self.http.fetch(
                self.dataset_id,
                "GET",
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_s,
            )
        except (httpx.HTTPStatusError, ProviderError) as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else exc.http_status
            text = exc.response.text[:200] if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            if status == 401:
                raise MeteomaticsError(
                    f"Meteomatics authentication failed (401 Unauthorized): {text}",
                    category="AUTHENTICATION_FAILURE",
                    missing_reason="UPSTREAM_ERROR",
                    http_status=401,
                ) from exc
            if status in (402, 403):
                raise MeteomaticsError(
                    f"Meteomatics permission or subscription limitation ({status}): {text}",
                    category="SUBSCRIPTION_LIMITATION",
                    missing_reason="UPSTREAM_ERROR",
                    http_status=status,
                ) from exc
            if status == 404:
                raise MeteomaticsError(
                    f"Meteomatics parameter or date range not available ({status}): {text}",
                    category="PARAMETER_UNAVAILABLE",
                    missing_reason="OUT_OF_TEMPORAL_RANGE",
                    http_status=404,
                ) from exc
            if status == 429:
                raise MeteomaticsError(
                    f"Meteomatics rate limit exceeded ({status}): {text}",
                    category="RATE_LIMITED",
                    missing_reason="UPSTREAM_ERROR",
                    http_status=429,
                ) from exc
            if status == 400:
                raise MeteomaticsError(
                    f"Meteomatics invalid request ({status}): {text}",
                    category="INVALID_REQUEST",
                    missing_reason="UPSTREAM_ERROR",
                    http_status=400,
                ) from exc
            raise MeteomaticsError(
                f"Meteomatics upstream HTTP error ({status}): {text}",
                category="UPSTREAM_ERROR",
                missing_reason=getattr(exc, "missing_reason", "UPSTREAM_ERROR"),
                http_status=status,
            ) from exc
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise MeteomaticsError(
                f"Meteomatics network failure: {exc}",
                category="NETWORK_FAILURE",
                missing_reason="UPSTREAM_ERROR",
            ) from exc
        except ProviderError as exc:
            # Re-wrap if necessary
            status = exc.http_status
            if status == 401:
                category = "AUTHENTICATION_FAILURE"
            elif status in (402, 403):
                category = "SUBSCRIPTION_LIMITATION"
            elif status == 404:
                category = "PARAMETER_UNAVAILABLE"
            elif status == 400:
                category = "INVALID_REQUEST"
            else:
                category = "UPSTREAM_ERROR"
            raise MeteomaticsError(
                str(exc),
                category=category,
                missing_reason=exc.missing_reason,
                http_status=status,
            ) from exc

        return resp.json()

    def test_connection(self, lat: float = 37.95, lon: float = -98.05) -> dict[str, Any]:
        """Diagnostic probe performing one minimal valid request without leaking secrets."""
        username, password = self._auth_factory()
        if not username or not password:
            return {
                "ok": False,
                "configured": False,
                "status": "MISSING_CREDENTIALS",
                "category": "missing_credentials",
                "message": "METEOMATICS_USERNAME or METEOMATICS_PASSWORD is not set in backend/.env.",
                "error": "Credentials not configured",
            }

        now_str = format_iso(datetime.now(UTC).replace(minute=0, second=0, microsecond=0))
        path = f"{now_str}/{ELEVATION_PARAMETER}/{lat:.5f},{lon:.5f}/json"
        try:
            t0 = time.perf_counter()
            data = self._execute_request(path)
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            # Verify data presence
            entries = data.get("data", [])
            if entries and len(entries[0].get("coordinates", [])) > 0:
                val = entries[0]["coordinates"][0]["dates"][0].get("value")
                return {
                    "ok": True,
                    "configured": True,
                    "status": "PASS",
                    "status_code": 200,
                    "category": "success",
                    "latency_ms": latency_ms,
                    "message": "Authentication successful and minimal request validated.",
                    "sample_elevation": val,
                    "sample": {"parameter": ELEVATION_PARAMETER, "value": val, "unit": "m"},
                }
            return {
                "ok": False,
                "configured": True,
                "status": "WARN",
                "status_code": 200,
                "latency_ms": latency_ms,
                "category": "empty_data",
                "error": "Provider responded OK but returned empty coordinate data.",
                "message": "Provider responded OK but returned empty coordinate data.",
            }
        except MeteomaticsError as exc:
            return {
                "ok": False,
                "configured": True,
                "status": "FAIL",
                "category": exc.category,
                "error": str(exc),
                "message": str(exc),
                "status_code": exc.http_status,
                "http_status": exc.http_status,
            }
        except Exception as exc:
            return {
                "ok": False,
                "configured": True,
                "status": "FAIL",
                "category": "UNEXPECTED_ERROR",
                "error": str(exc),
                "message": str(exc),
            }

    def query_time_series(
        self,
        lat: float,
        lon: float,
        start: datetime | date | str,
        end: datetime | date | str,
        step: str,
        parameters: list[str],
        model: str = "mix",
    ) -> dict[str, list[TimeSeriesObservation]]:
        """Query time series for one or more parameters at a single point coordinate."""
        start_str = format_iso(start)
        end_str = format_iso(end)
        param_str = ",".join(parameters)
        range_str = f"{start_str}--{end_str}:{step}"
        loc_str = f"{lat:.5f},{lon:.5f}"
        path = f"{range_str}/{param_str}/{loc_str}/json"

        params = {"model": model} if model else None
        res_json = self._execute_request(path, params=params)

        results: dict[str, list[TimeSeriesObservation]] = {}
        for entry in res_json.get("data", []):
            param = entry.get("parameter")
            coords_list = entry.get("coordinates", [])
            obs_list: list[TimeSeriesObservation] = []
            if coords_list:
                for pt in coords_list[0].get("dates", []):
                    dt_str = pt.get("date")
                    try:
                        ts = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                    val = sanitize_value(pt.get("value"))
                    obs_list.append(TimeSeriesObservation(timestamp=ts, value=val, valid=val is not None))
            results[param] = obs_list
        return results

    def query_point(
        self,
        lat: float,
        lon: float,
        timestamp: datetime | date | str,
        parameters: list[str],
        model: str = "mix",
    ) -> dict[str, float | None]:
        """Query point values at a single timestamp."""
        ts_str = format_iso(timestamp)
        param_str = ",".join(parameters)
        loc_str = f"{lat:.5f},{lon:.5f}"
        path = f"{ts_str}/{param_str}/{loc_str}/json"

        params = {"model": model} if model else None
        res_json = self._execute_request(path, params=params)

        results: dict[str, float | None] = {}
        for entry in res_json.get("data", []):
            param = entry.get("parameter")
            coords = entry.get("coordinates", [])
            if coords and coords[0].get("dates"):
                val = sanitize_value(coords[0]["dates"][0].get("value"))
                results[param] = val
            else:
                results[param] = None
        return results

    def query_grid(
        self,
        bounds: tuple[float, float, float, float],
        res_lat: float,
        res_lon: float,
        timestamp: datetime | date | str,
        parameters: list[str],
        model: str = "mix",
    ) -> dict[str, list[GridPoint]]:
        """Query spatial grid over bounding box (w, s, e, n) using upper-left to lower-right coordinates.

        Meteomatics rectangle syntax: <lat_max>,<lon_min>_<lat_min>,<lon_max>:<res_lat>,<res_lon>
        """
        w, s, e, n = bounds
        ts_str = format_iso(timestamp)
        param_str = ",".join(parameters)
        loc_str = f"{n:.5f},{w:.5f}_{s:.5f},{e:.5f}:{res_lat:.5f},{res_lon:.5f}"
        path = f"{ts_str}/{param_str}/{loc_str}/json"

        params = {"model": model} if model else None
        res_json = self._execute_request(path, params=params)

        results: dict[str, list[GridPoint]] = {}
        for entry in res_json.get("data", []):
            param = entry.get("parameter")
            points: list[GridPoint] = []
            for coord in entry.get("coordinates", []):
                lat = float(coord.get("lat", 0.0))
                lon = float(coord.get("lon", 0.0))
                dates_list = coord.get("dates", [])
                val = sanitize_value(dates_list[0].get("value")) if dates_list else None
                points.append(GridPoint(lat=lat, lon=lon, value=val, valid=val is not None))
            results[param] = points
        return results
