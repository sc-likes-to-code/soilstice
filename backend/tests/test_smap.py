"""Unit and contract tests for NASA SMAP L4 provider."""

from __future__ import annotations

from datetime import UTC, datetime

from app.catalog import SPATIAL
from app.providers.http import HttpAcquirer
from app.providers.smap import CELL_AREA_HA, SmapClient


def test_smap_spatial_support_and_cell_size():
    # Verify SMAP spatial support contract metadata
    smap_spec = SPATIAL["nasa_smap_spl4smgp"]
    assert smap_spec.support_class == "R"  # Regional context
    assert smap_spec.native_resolution_m == 9000  # 9 km EASE-Grid 2.0
    assert smap_spec.crs == "EPSG:6933"
    assert CELL_AREA_HA == 8100.0  # 9km x 9km = 8,100 ha


def test_smap_client_cmr_search_parsing(respx_mock, tmp_path):
    http = HttpAcquirer(tmp_path)
    client = SmapClient(http)

    mock_cmr_payload = {
        "feed": {
            "entry": [
                {
                    "id": "G12345-NSIDC",
                    "title": "SMAP_L4_SM_gph_20250601T013000_Vv8012_001.h5",
                    "time_start": "2025-06-01T00:00:00.000Z",
                    "time_end": "2025-06-01T03:00:00.000Z",
                    "links": [
                        {
                            "href": "https://data.nsidc.earthdatacloud.nasa.gov/protected/SMAP_L4_SM_gph_20250601T013000_Vv8012_001.h5",
                            "rel": "http://esipfed.org/ns/fed/1.0/data#",
                        }
                    ],
                }
            ]
        }
    }

    respx_mock.get("https://cmr.earthdata.nasa.gov/search/granules.json").respond(200, json=mock_cmr_payload)

    granules = client.search_granules((-98.1, 37.9, -98.0, 38.0), "2025-06-01", "2025-06-02")
    assert len(granules) == 1
    g = granules[0]
    assert g.title == "SMAP_L4_SM_gph_20250601T013000_Vv8012_001.h5"
    assert g.start_time == datetime(2025, 6, 1, 0, 0, tzinfo=UTC)
    assert g.h5_url.endswith(".h5")
