"""Environment + resilience services (E13–E19)."""

from __future__ import annotations

from datetime import date

from app.analytics.indicators import all_indicators
from app.contracts import (
    ClimateProfile,
    EnvironmentalIndicator,
    ResilienceProfile,
    SoilMoistureProfile,
    SoilProfile,
    TerrainProfile,
    VegetationProfile,
)
from app.errors import ValidationFailed
from app.logging import get_logger
from app.processing.geometry import to_shapely
from app.processing.placeholders import missing_soil, missing_soil_moisture, missing_terrain, missing_vegetation
from app.processing.soil_moisture import build_soil_moisture_profile
from app.processing.terrain import build_terrain_profile_from_meteomatics
from app.processing.vegetation import build_regional_ndvi_profile_from_meteomatics, build_vegetation_profile_from_stac

from .container import Container
from .fields import FieldService
from .pipeline import fetch_climate


def _clean_indicators(inds: list[EnvironmentalIndicator]) -> list[EnvironmentalIndicator]:
    return [
        i for i in inds
        if i.key not in {"et_actual_season", "sm_rootzone_percentile"}
        and "actual et" not in i.label.lower()
        and "openet" not in i.label.lower()
    ]


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
                # If cached profile lacks multi-depth soil moisture series, enrich it seamlessly
                has_sm = any(s.variable == "sm_rootzone" for s in cached.series)
                if not has_sm and self.ctx.providers.meteomatics is not None:
                    try:
                        sm_prof = self.soil_moisture(field_id, season_year)
                        if sm_prof is not None and sm_prof.quality.status != "missing":
                            from app.processing.soil_moisture import build_soil_moisture_indicators
                            existing_vars = {s.variable for s in cached.series}
                            extra_series = [s for s in sm_prof.series if s.variable not in existing_vars]
                            extra_indicators = build_soil_moisture_indicators(f.field_id, season_year, sm_prof)
                            extra_keys = {i.key for i in extra_indicators}
                            retained_indicators = [i for i in cached.indicators if i.key not in extra_keys]
                            cached = cached.model_copy(update={
                                "series": extra_series + cached.series,
                                "indicators": _clean_indicators(retained_indicators + extra_indicators),
                            })
                            self.repos.climate.put(f"{f.field_id}:{season_year}", cached, parent=f.field_id)
                    except Exception:
                        pass
                return cached.model_copy(update={"indicators": _clean_indicators(cached.indicators)})
        profile, _ = fetch_climate(self.ctx, f, season_year, crop_code)
        return profile.model_copy(update={"indicators": _clean_indicators(profile.indicators)})

    def soil(self, field_id) -> SoilProfile:
        f = self.fields.get_field(field_id)
        p = self.repos.soil.get(str(f.field_id))
        return p or missing_soil(f.field_id, *self._reason(f.field_id, "usda_nrcs_ssurgo_sda"))

    def terrain(self, field_id) -> TerrainProfile:
        f = self.fields.get_field(field_id)
        p = self.repos.terrain.get(str(f.field_id))
        if p is None and self.ctx.providers.meteomatics is not None:
            try:
                p = build_terrain_profile_from_meteomatics(f.field_id, to_shapely(f.geometry), self.ctx.providers.meteomatics)
                self.repos.terrain.put(str(f.field_id), p, parent=f.field_id)
            except Exception as exc:
                pass
        return p or missing_terrain(f.field_id, *self._reason(f.field_id, "meteomatics"))

    def soil_moisture(self, field_id, season_year: int | None = None) -> SoilMoistureProfile:
        f = self.fields.get_field(field_id)
        year = season_year or self.ctx.settings.default_season_year()
        key = f"{f.field_id}:{year}"
        cached = self.repos.soil_moisture.get(key)
        if cached is not None:
            return cached
        if self.ctx.providers.meteomatics is not None:
            try:
                prof = build_soil_moisture_profile(
                    f.field_id, to_shapely(f.geometry), year, self.ctx.providers.meteomatics
                )
                self.repos.soil_moisture.put(key, prof, parent=f.field_id)
                return prof
            except Exception as exc:
                pass
        return missing_soil_moisture(f.field_id, year, *self._reason(f.field_id, "meteomatics"))

    def vegetation(self, field_id, year: int, index: str = "NDVI") -> VegetationProfile:
        f = self.fields.get_field(field_id)
        if year < 1980 or year > date.today().year + 1:
            raise ValidationFailed("year is out of range.", details={"year": year})
        key = f"{f.field_id}:{year}:{index}"
        cached = self.repos.vegetation.get(key)
        # Stale HLS discovery records (with AUTHENTICATION_REQUIRED for GeoTIFFs) are superseded by Meteomatics regional NDVI
        is_stale_hls = (
            cached is not None
            and any(fl.code == "AUTHENTICATION_REQUIRED" for fl in cached.quality.flags)
        )
        if cached is not None and not is_stale_hls:
            return cached

        # Prioritize Meteomatics regional NDVI (P1 migration requirement)
        if index.upper() == "NDVI" and self.ctx.providers.meteomatics is not None:
            try:
                profile = build_regional_ndvi_profile_from_meteomatics(
                    f.field_id, to_shapely(f.geometry), year, self.ctx.providers.meteomatics
                )
                self.repos.vegetation.put(key, profile, parent=f.field_id)
                return profile
            except Exception as exc:
                pass

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
            f.field_id,
            soil=self.repos.soil.get(str(f.field_id)),
            terrain=self.repos.terrain.get(str(f.field_id)),
            climate=self.repos.climate.get(f"{f.field_id}:{year}"),
            crop_history=self.repos.crop_history.get(str(f.field_id)),
            year=year,
            soil_moisture=self.repos.soil_moisture.get(f"{f.field_id}:{year}"),
            vegetation=self.repos.vegetation.get(f"{f.field_id}:{year}:NDVI"),
            soil_reason=self._reason(f.field_id, "usda_nrcs_ssurgo_sda")[0],
            terrain_reason=self._reason(f.field_id, "meteomatics")[0],
        )
        return [i for i in _clean_indicators(inds) if category is None or i.category == category]

    def resilience(self, field_id) -> ResilienceProfile:
        f = self.fields.get_field(field_id)
        return self.ctx.resilience.profile(f.field_id, self.indicators(f.field_id), date.today())
