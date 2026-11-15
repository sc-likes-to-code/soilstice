"""NASA SRTM SRTMGL1 v003 provider (INTEGRATION_GUIDE §7). Acquisition + parsing.

Discovery: CMR granule search (open, no auth) [LIVE 2026-11-14]:
  https://cmr.earthdata.nasa.gov/search/granules.json?short_name=SRTMGL1&version=003&bounding_box=W,S,E,N
  -> data link https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL1.003/<T>.SRTMGL1.hgt/<T>.SRTMGL1.hgt.zip
Download: requires NASA Earthdata Login (token or username/password from env vars) — NOT verified live in Phase 2
(no credentials available in the build environment).
Format: 1°×1° tile, 3601×3601 big-endian int16, metres (EGM96), void = -32768; pixel centres on whole arc-seconds
from the tile's lower-left corner named in the file (e.g. N37W099).
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None  # type: ignore
    from_origin = None  # type: ignore

from app.repositories.records import AcquisitionRecord

from .http import EarthdataAuth, HttpAcquirer, ProviderError

CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
DATASET_ID = "nasa_srtm_gl1"
VOID = -32768
SIZE = 3601
_TILE = re.compile(r"([NS])(\d{2})([EW])(\d{3})")


@dataclass
class SrtmTile:
    name: str
    path: Path  # GeoTIFF (EPSG:4326) converted from the .hgt
    acquisition: AcquisitionRecord


def tile_origin(name: str) -> tuple[int, int]:
    m = _TILE.search(name)
    if not m:
        raise ProviderError(f"Unrecognised SRTM tile name {name!r}.")
    lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
    lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
    return lat, lon


def parse_hgt(data: bytes) -> np.ndarray:
    if len(data) != SIZE * SIZE * 2:
        raise ProviderError(f"Unexpected .hgt size {len(data)} bytes (expected 1 arc-second, {SIZE}x{SIZE}).")
    return np.frombuffer(data, dtype=">i2").reshape(SIZE, SIZE).astype(np.int16)


def hgt_to_geotiff(arr: np.ndarray, name: str, out: Path) -> Path:
    lat, lon = tile_origin(name)
    res = 1.0 / 3600.0
    transform = from_origin(lon - res / 2, lat + 1 + res / 2, res, res)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", driver="GTiff", height=SIZE, width=SIZE, count=1, dtype="int16", crs="EPSG:4326",
                       transform=transform, nodata=VOID, compress="deflate") as dst:
        dst.write(arr, 1)
    return out


class SrtmClient:
    dataset_id = DATASET_ID

    def __init__(self, http: HttpAcquirer, derived_dir: Path, auth_factory, download_timeout_s: float = 300.0):
        self.http = http
        self.derived_dir = Path(derived_dir)
        self._auth_factory = auth_factory  # () -> EarthdataAuth ; raises ProviderNotConfigured
        self.download_timeout_s = download_timeout_s

    def granule_links(self, bounds: tuple[float, float, float, float]) -> dict[str, str]:
        w, s, e, n = bounds
        doc = self.http.fetch(DATASET_ID, "GET", CMR_URL, params={
            "short_name": "SRTMGL1", "version": "003", "bounding_box": f"{w},{s},{e},{n}", "page_size": 20,
        }).json()
        links: dict[str, str] = {}
        for entry in (doc.get("feed") or {}).get("entry", []):
            for link in entry.get("links", []):
                href = link.get("href", "")
                if href.startswith("https://") and href.endswith(".hgt.zip"):
                    links[entry.get("title") or href.rsplit("/", 1)[-1]] = href
        if not links:
            raise ProviderError("CMR returned no SRTMGL1 granules for the field.", "NO_DATA_SOURCE")
        return links

    def tiles_for_bounds(self, bounds: tuple[float, float, float, float]) -> list[SrtmTile]:
        auth: EarthdataAuth = self._auth_factory()  # fail fast before any download if credentials are missing
        tiles: list[SrtmTile] = []
        for title, href in sorted(self.granule_links(bounds).items()):
            fetched = self.http.fetch(DATASET_ID, "GET", href, auth=auth, timeout=self.download_timeout_s)
            name = _TILE.search(title or href).group(0)
            tif = self.derived_dir / "srtm" / f"{name}.tif"
            if not tif.exists():
                try:
                    with zipfile.ZipFile(io.BytesIO(fetched.content)) as zf:
                        member = next(m for m in zf.namelist() if m.lower().endswith(".hgt"))
                        arr = parse_hgt(zf.read(member))
                except (zipfile.BadZipFile, StopIteration) as exc:
                    raise ProviderError(f"SRTM download for {name} was not a valid .hgt zip "
                                        "(check Earthdata credentials / EULA).") from exc
                hgt_to_geotiff(arr, name, tif)
            tiles.append(SrtmTile(name=name, path=tif, acquisition=fetched.acquisition))
        return tiles
