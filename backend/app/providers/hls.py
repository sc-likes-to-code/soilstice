"""NASA Harmonized Landsat Sentinel-2 (HLS) v2.0 & HLS-VI provider (INTEGRATION_GUIDE §5).

Discovery: Open CMR-STAC endpoint at https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search
Collections: HLSS30_VI_2.0 (Sentinel-2 VI), HLSL30_VI_2.0 (Landsat 8/9 VI),
             HLSS30_2.0 (Sentinel-2 SR), HLSL30_2.0 (Landsat 8/9 SR).
Native spatial resolution: 30 m UTM grid (MGRS tiles).
Native temporal cadence: 2–3 days combined constellation revisit.

Data access: Raw COG download requires NASA Earthdata Login credentials.
When credentials are not configured, discovery returns real STAC observation metadata
(granule IDs, acquisition times, cloud cover) with an explicit EARTHDATA_NOT_CONFIGURED
missing_reason, preserving scientific honesty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .http import EarthdataAuth, HttpAcquirer, ProviderError, ProviderNotConfigured

CMR_STAC_URL = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search"
DATASET_ID = "nasa_hls_vi"
SR_DATASET_ID = "nasa_hls"


@dataclass
class HlsStacScene:
    granule_id: str
    collection: str
    product: str  # "HLSS30_VI" | "HLSL30_VI" | "HLSS30" | "HLSL30"
    acquired_at: datetime
    cloud_cover: float
    bbox: list[float]
    assets: dict[str, str] = field(default_factory=dict)


class HlsClient:
    dataset_id = DATASET_ID

    def __init__(
        self,
        http: HttpAcquirer,
        derived_dir: Path,
        auth_factory: Any = None,
        timeout_s: float = 60.0,
    ):
        self.http = http
        self.derived_dir = Path(derived_dir)
        self._auth_factory = auth_factory
        self.timeout_s = timeout_s

    def search_scenes(
        self,
        bounds: tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        *,
        collections: list[str] | None = None,
        limit: int = 100,
    ) -> list[HlsStacScene]:
        """Search LP DAAC CMR-STAC for HLS scenes intersecting the bounding box.
        
        This search is open and requires no authentication.
        """
        w, s, e, n = bounds
        colls = collections or ["HLSS30_VI_2.0", "HLSL30_VI_2.0"]
        body = {
            "collections": colls,
            "bbox": [w, s, e, n],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": limit,
        }

        try:
            resp = self.http.fetch(
                self.dataset_id,
                "POST",
                CMR_STAC_URL,
                json_body=body,
                timeout=self.timeout_s,
            )
            doc = resp.json()
        except ProviderError as exc:
            # If VI is not yet available, fallback to surface reflectance collections
            if colls != ["HLSS30_2.0", "HLSL30_2.0"]:
                return self.search_scenes(
                    bounds,
                    start_date,
                    end_date,
                    collections=["HLSS30_2.0", "HLSL30_2.0"],
                    limit=limit,
                )
            raise exc

        features = doc.get("features", [])
        scenes: list[HlsStacScene] = []
        for feat in features:
            props = feat.get("properties", {})
            coll = feat.get("collection", "")
            dt_str = props.get("datetime") or props.get("start_datetime")
            if not dt_str:
                continue

            # Product discriminator
            if "HLSS30_VI" in coll:
                prod = "HLSS30_VI"
            elif "HLSL30_VI" in coll:
                prod = "HLSL30_VI"
            elif "HLSS30" in coll:
                prod = "HLSS30"
            elif "HLSL30" in coll:
                prod = "HLSL30"
            else:
                prod = "synthetic"

            # Parse ISO datetime
            try:
                acq_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            cloud_cov = float(props.get("eo:cloud_cover", 0.0))
            asset_dict: dict[str, str] = {}
            for asset_key, asset_val in feat.get("assets", {}).items():
                if isinstance(asset_val, dict) and "href" in asset_val:
                    asset_dict[asset_key] = asset_val["href"]

            scenes.append(
                HlsStacScene(
                    granule_id=feat.get("id", ""),
                    collection=coll,
                    product=prod,
                    acquired_at=acq_dt,
                    cloud_cover=cloud_cov,
                    bbox=feat.get("bbox", [w, s, e, n]),
                    assets=asset_dict,
                )
            )

        # Sort chronologically
        scenes.sort(key=lambda x: x.acquired_at)
        return scenes

    def get_auth(self) -> EarthdataAuth | None:
        """Attempt to construct EarthdataAuth; returns None if not configured."""
        if not self._auth_factory:
            return None
        try:
            return self._auth_factory()
        except ProviderNotConfigured:
            return None
