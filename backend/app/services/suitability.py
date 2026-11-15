"""Crop suitability service: orchestrates field data retrieval and Phase 6 engine evaluation."""

from __future__ import annotations

from uuid import UUID

from app.contracts import (
    CropSuitabilityAssessment,
    FieldSuitabilityResponse,
)
from app.errors import NotFound
from app.suitability.engine import CropSuitabilityEngine

from .container import Container
from .environment import EnvironmentService
from .fields import FieldService


class SuitabilityService:
    def __init__(self, ctx: Container):
        self.ctx = ctx
        self.fields = FieldService(ctx)
        self.env = EnvironmentService(ctx)
        self.engine = ctx.suitability or CropSuitabilityEngine(ctx.kb)

    def evaluate_field(self, field_id: UUID, season_year: int | None = None) -> FieldSuitabilityResponse:
        f = self.fields.get_field(field_id)
        default_year = self.ctx.settings.default_season_year()
        target_year = season_year or default_year

        soil = self.env.soil(field_id)
        climate = self.env.climate(field_id, target_year)
        terrain = self.env.terrain(field_id)
        crop_history = self.ctx.repos.crop_history.get(str(field_id))

        state_code = "KS" if f.state_fips == "20" else "US"

        return self.engine.evaluate_field(
            field_id=field_id,
            season_year=target_year,
            soil=soil,
            climate=climate,
            terrain=terrain,
            history=crop_history,
            state_code=state_code,
        )

    def evaluate_crop(
        self, field_id: UUID, crop_id: str, season_year: int | None = None
    ) -> CropSuitabilityAssessment:
        f = self.fields.get_field(field_id)
        default_year = self.ctx.settings.default_season_year()
        target_year = season_year or default_year

        crop = self.ctx.kb.get_crop(crop_id)
        if crop is None:
            raise NotFound(
                f"Crop '{crop_id}' not found in knowledge base.",
                details={"crop_id": crop_id, "valid_range": "CRP001 to CRP014, or supported CDL codes"},
            )

        soil = self.env.soil(field_id)
        climate = self.env.climate(field_id, target_year, crop.cdl_code)
        terrain = self.env.terrain(field_id)
        crop_history = self.ctx.repos.crop_history.get(str(field_id))

        state_code = "KS" if f.state_fips == "20" else "US"

        return self.engine.evaluate_crop(
            crop=crop,
            soil=soil,
            climate=climate,
            terrain=terrain,
            history=crop_history,
            state_code=state_code,
        )
