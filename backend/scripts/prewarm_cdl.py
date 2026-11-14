"""Pre-warm and cache USDA NASS Cropland Data Layer (CDL) county rasters.

Usage:
    .venv/Scripts/python scripts/prewarm_cdl.py [--counties 20155,20055] [--years 2006-2025]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.providers.cdl import CdlClient  # noqa: E402
from app.providers.http import HttpAcquirer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-warm CDL county rasters into raw cache")
    parser.add_argument("--counties", default="20155,20055", help="Comma-separated FIPS list (default: 20155,20055)")
    parser.add_argument("--start-year", type=int, default=2006, help="Start year (default: 2006)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")
    args = parser.parse_args()

    counties = [c.strip() for c in args.counties.split(",") if c.strip()]
    years = list(range(args.start_year, args.end_year + 1))

    settings = get_settings()
    raw_dir = settings.cache_dir / "raw"
    http = HttpAcquirer(raw_dir)
    client = CdlClient(http)

    print(f"Pre-warming CDL rasters for counties {counties} across years {years[0]}–{years[-1]}")
    print(f"Target raw cache: {raw_dir}")

    total = len(counties) * len(years)
    cached_count = 0
    downloaded_count = 0
    failed_count = 0

    for fips in counties:
        for year in years:
            try:
                raster = client.county_raster(year, fips)
                if raster.path.exists():
                    cached_count += 1
                    kb = raster.path.stat().st_size // 1024
                    print(f"[{cached_count + downloaded_count}/{total}] OK: {fips} year {year} ({kb} KB)")
            except Exception as e:
                failed_count += 1
                print(f"[{cached_count + downloaded_count + failed_count}/{total}] FAIL: {fips} year {year} - {e}")

    print(f"Done. {cached_count} rasters ready, {failed_count} failures.")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
