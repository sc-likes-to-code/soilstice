"""Backend configuration. Every value comes from environment variables (prefix SOILSTICE_) or backend/.env.

Credentials (Earthdata) are read here and nowhere else; they are never logged or written to provenance.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOILSTICE_",
        env_file=(
            BACKEND_ROOT / ".env",
            PROJECT_ROOT / ".env.local",
            PROJECT_ROOT / ".env",
            BACKEND_ROOT / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Storage
    db_path: str = str(BACKEND_ROOT / ".data" / "soilstice.sqlite3")
    cache_dir: Path = BACKEND_ROOT / ".cache"

    # HTTP / CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100", "http://localhost:3101"]
    rate_limit_writes_per_minute: int = 60

    # Processing
    job_execution: Literal["thread", "inline"] = "thread"
    job_workers: int = 2
    http_retries: int = 3
    http_backoff_base_s: float = 2.0
    http_timeout_s: float = 60.0
    http_download_timeout_s: float = 300.0

    # Dataset windows
    cdl_first_year: int = 2006  # Kansas CDL starts 2006 (DATA_ARCHITECTURE §3.1, LIVE)
    cdl_last_year: int = 2025
    # CropScape answered sequential calls in ~2 s but timed out on 4 parallel GetCDLFile calls (2026-11-14), so
    # requests are sequential by default.
    cdl_parallel_requests: int = 1
    climate_default_season_year: int | None = None  # None -> previous calendar year

    # Credentials (NASA Earthdata Login) — needed for SRTM (and later HLS/SMAP)
    earthdata_token: SecretStr | None = Field(default=None)
    earthdata_username: str | None = None
    earthdata_password: SecretStr | None = None

    # Credentials (Meteomatics) — Primary provider for soil moisture, elevation, conditional terrain, and regional NDVI.
    meteomatics_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("METEOMATICS_USERNAME", "SOILSTICE_METEOMATICS_USERNAME"),
    )
    meteomatics_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("METEOMATICS_PASSWORD", "SOILSTICE_METEOMATICS_PASSWORD"),
    )

    # Crop knowledge base directory (Phase 5 canonical handoff)
    crop_kb_dir: Path | None = PROJECT_ROOT / "data" / "backend_handoff"

    def default_season_year(self) -> int:
        return self.climate_default_season_year or (date.today().year - 1)

    @property
    def earthdata_configured(self) -> bool:
        return self.earthdata_token is not None or (
            self.earthdata_username is not None and self.earthdata_password is not None
        )

    @property
    def meteomatics_configured(self) -> bool:
        return bool(
            self.meteomatics_username and self.meteomatics_password and self.meteomatics_password.get_secret_value()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
