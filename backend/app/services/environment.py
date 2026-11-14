"""Environment + resilience services (E13–E19)."""

from __future__ import annotations

from datetime import date

from app.analytics.indicators import all_indicators
from app.contracts import (
    ClimateProfile,
    EnvironmentalIndicator,
    ResilienceProfile,
    SoilProfile,
    TerrainProfile,
    VegetationProfile,
)
from app.errors import ValidationFailed
from app.processing.geometry import to_shapely
from app.processing.placeholders import missing_soil, missing_terrain, missing_vegetation
from app.processing.vegetation import build_vegetation_profile_from_stac

from .container import Container
from .fields import FieldService
from .pipeline import fetch_climate


class EnvironmentService:
    def __init__(self, ctx: Container):
        self.ctx = ctx
        self.repos = ctx.repos
        self.fields = FieldService(ctx)

    def _reason(self, field_id, dataset_id) -> tuple[str, str | None]:
        st = self.repos.dataset_states.get(f"{field_id}:{dataset_id}")
        if st is None:
            return "PENDING_PROCESSING", "Not yet processed."
        if st.state == "pending":
            return "PENDING_PROCESSING", "Processing in progress."
        return st.missing_reason or "UPSTREAM_ERROR", st.message

    def climate(self, field_id, season_year: int, crop_code: int | None = None) -> ClimateProfile:
        f = self.fields.get_field(field_id)
        if season_year < 1900 or season_year > date.today().year + 1:
            raise ValidationFailed("season_year is out of range.", details={"season_year": season_year})
        if crop_code is None:
            cached = self.repos.climate.get(f"{f.field_id}:{season_year}")
            if cached is not None:
                return cached
        profile, _ = fetch_climate(self.ctx, f, season_year, crop_code)
        return profile

    def soil(self, field_id) -> SoilProfile:
        f = self.fields.get_field(field_id)
        p = self.repos.soil.get(str(f.field_id))
        return p or missing_soil(f.field_id, *self._reason(f.field_id, "usda_nrcs_ssurgo_sda"))

    def terrain(self, field_id) -> TerrainProfile:
        f = self.fields.get_field(field_id)
        p = self.repos.terrain.get(str(f.field_id))
        return p or missing_terrain(f.field_id, *self._reason(f.field_id, "nasa_srtm_gl1"))

    def vegetation(self, field_id, year: int, index: str = "NDVI") -> VegetationProfile:
        f = self.fields.get_field(field_id)
        if year < 1980 or year > date.today().year + 1:
            raise ValidationFailed("year is out of range.", details={"year": year})
        key = f"{f.field_id}:{year}:{index}"
        cached = self.repos.vegetation.get(key)
        if cached is not None:
            return cached

        if self.ctx.providers.hls is not None:
            geom = to_shapely(f.geometry)
            bounds = geom.bounds
            try:
                scenes = self.ctx.providers.hls.search_scenes(
                    bounds, f"{year}-01-01", f"{year}-12-31", limit=100
                )
                profile = build_vegetation_profile_from_stac(f.field_id, year, index, scenes)
            except Exception:
                profile = missing_vegetation(f.field_id, year, index)
        else:
            profile = missing_vegetation(f.field_id, year, index)

        self.repos.vegetation.put(key, profile, parent=f.field_id)
        return profile

    def indicators(self, field_id, category: str | None = None, season_year: int | None = None
                   ) -> list[EnvironmentalIndicator]:
        f = self.fields.get_field(field_id)
        year = season_year or self.ctx.settings.default_season_year()
        inds = all_indicators(
            f.field_id, soil=self.repos.soil.get(str(f.field_id)), terrain=self.repos.terrain.get(str(f.field_id)),
            climate=self.repos.climate.get(f"{f.field_id}:{year}"),
            crop_history=self.repos.crop_history.get(str(f.field_id)), year=year,
            soil_reason=self._reason(f.field_id, "usda_nrcs_ssurgo_sda")[0],
            terrain_reason=self._reason(f.field_id, "nasa_srtm_gl1")[0],
        )
        return [i for i in inds if category is None or i.category == category]

    def resilience(self, field_id) -> ResilienceProfile:
        f = self.fields.get_field(field_id)
        return self.ctx.resilience.profile(f.field_id, self.indicators(f.field_id), date.today())
