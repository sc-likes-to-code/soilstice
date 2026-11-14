"""HTTP routes E1–E27 (API_CONTRACTS §6), mounted under /api/v1. Thin: parse, call a service, wrap envelope."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.contracts import (
    ApiErrorResponse,
    ApiResponse,
    ClimateProfile,
    CreateFieldRequest,
    CreateFieldResponse,
    CropHistory,
    CropOption,
    DataCoverage,
    DatasetDescriptor,
    Deleted,
    EnvironmentalIndicator,
    EvidenceItem,
    EvidenceKind,
    Farm,
    FarmOverview,
    Field,
    FieldProcessingStatus,
    FieldProfile,
    FieldSource,
    FieldSummary,
    Health,
    IndicatorCategory,
    ProcessingJob,
    ResilienceProfile,
    RotationRecommendation,
    RotationScenario,
    SoilProfile,
    TerrainProfile,
    UpdateFarmRequest,
    UpsertScenarioRequest,
    VegetationIndex,
    VegetationProfile,
)
from app.services.container import Container
from app.services.environment import EnvironmentService
from app.services.evidence import EvidenceService
from app.services.fields import FieldService
from app.services.rotation import RotationService

from .envelope import ok

ERRORS = {code: {"model": ApiErrorResponse} for code in (404, 409, 422, 429, 500, 503)}
router = APIRouter(responses=ERRORS)


def ctx(request: Request) -> Container:
    return request.app.state.container


def fields_svc(c: Container = Depends(ctx)) -> FieldService:
    return FieldService(c)


def env_svc(c: Container = Depends(ctx)) -> EnvironmentService:
    return EnvironmentService(c)


def rot_svc(c: Container = Depends(ctx)) -> RotationService:
    return RotationService(c)


def ev_svc(c: Container = Depends(ctx)) -> EvidenceService:
    return EvidenceService(c)


# E1
@router.get("/health", response_model=ApiResponse[Health], tags=["system"], operation_id="health")
def health(request: Request):
    return ok(request, Health())


# E2
@router.get("/datasets", response_model=ApiResponse[list[DatasetDescriptor]], tags=["evidence"],
            operation_id="listDatasets")
def list_datasets(request: Request, svc: EvidenceService = Depends(ev_svc)):
    return ok(request, svc.datasets())


# E3–E6 farms
@router.get("/farms", response_model=ApiResponse[list[Farm]], tags=["farms"], operation_id="listFarms")
def list_farms(request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.list_farms())


@router.get("/farms/{farm_id}", response_model=ApiResponse[Farm], tags=["farms"], operation_id="getFarm")
def get_farm(farm_id: UUID, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.get_farm(farm_id))


@router.patch("/farms/{farm_id}", response_model=ApiResponse[Farm], tags=["farms"], operation_id="updateFarm")
def update_farm(farm_id: UUID, body: UpdateFarmRequest, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.rename_farm(farm_id, body.name))


@router.get("/farms/{farm_id}/overview", response_model=ApiResponse[FarmOverview], tags=["farms"],
            operation_id="getFarmOverview")
def farm_overview(farm_id: UUID, request: Request, season_year: int | None = None,
                  svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.overview(farm_id, season_year))


# E7–E8 farm fields
@router.get("/farms/{farm_id}/fields", response_model=ApiResponse[list[FieldSummary]], tags=["fields"],
            operation_id="listFields")
def list_fields(farm_id: UUID, request: Request, source: FieldSource | None = None,
                status: FieldProcessingStatus | None = None, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.list_fields(farm_id, source, status))


@router.post("/farms/{farm_id}/fields", response_model=ApiResponse[CreateFieldResponse], status_code=202,
             tags=["fields"], operation_id="createField")
def create_field(farm_id: UUID, body: CreateFieldRequest, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.create_field(farm_id, body))


# E9–E12 field
@router.get("/fields/{field_id}", response_model=ApiResponse[Field], tags=["fields"], operation_id="getField")
def get_field(field_id: UUID, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.get_field(field_id))


@router.delete("/fields/{field_id}", response_model=ApiResponse[Deleted], tags=["fields"], operation_id="deleteField")
def delete_field(field_id: UUID, request: Request, svc: FieldService = Depends(fields_svc)):
    svc.delete_field(field_id)
    return ok(request, Deleted())


@router.get("/fields/{field_id}/profile", response_model=ApiResponse[FieldProfile], tags=["fields"],
            operation_id="getFieldProfile")
def field_profile(field_id: UUID, request: Request, season_year: int | None = None,
                  svc: FieldService = Depends(fields_svc), env: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.profile(field_id, season_year, env))


@router.get("/fields/{field_id}/coverage", response_model=ApiResponse[DataCoverage], tags=["fields"],
            operation_id="getFieldCoverage")
def field_coverage(field_id: UUID, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.get_coverage(field_id))


# E13–E19 environment
@router.get("/fields/{field_id}/climate", response_model=ApiResponse[ClimateProfile], tags=["environment"],
            operation_id="getClimate")
def climate(field_id: UUID, request: Request, season_year: int = Query(...), crop_code: int | None = None,
            svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.climate(field_id, season_year, crop_code))


@router.get("/fields/{field_id}/soil", response_model=ApiResponse[SoilProfile], tags=["environment"],
            operation_id="getSoil")
def soil(field_id: UUID, request: Request, svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.soil(field_id))


@router.get("/fields/{field_id}/terrain", response_model=ApiResponse[TerrainProfile], tags=["environment"],
            operation_id="getTerrain")
def terrain(field_id: UUID, request: Request, svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.terrain(field_id))


@router.get("/fields/{field_id}/vegetation", response_model=ApiResponse[VegetationProfile], tags=["environment"],
            operation_id="getVegetation")
def vegetation(field_id: UUID, request: Request, year: int = Query(...), index: VegetationIndex = "NDVI",
               svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.vegetation(field_id, year, index))


@router.get("/fields/{field_id}/crop-history", response_model=ApiResponse[CropHistory], tags=["rotation"],
            operation_id="getCropHistory")
def crop_history(field_id: UUID, request: Request, svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.crop_history(field_id))


@router.get("/fields/{field_id}/indicators", response_model=ApiResponse[list[EnvironmentalIndicator]],
            tags=["environment"], operation_id="getIndicators")
def indicators(field_id: UUID, request: Request, category: IndicatorCategory | None = None,
               season_year: int | None = None, svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.indicators(field_id, category, season_year))


@router.get("/fields/{field_id}/resilience", response_model=ApiResponse[ResilienceProfile], tags=["resilience"],
            operation_id="getResilience")
def resilience(field_id: UUID, request: Request, svc: EnvironmentService = Depends(env_svc)):
    return ok(request, svc.resilience(field_id))


# E20–E25 rotation
@router.get("/crops", response_model=ApiResponse[list[CropOption]], tags=["rotation"], operation_id="listCrops")
def crops(request: Request, svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.crops())


@router.get("/fields/{field_id}/recommendations", response_model=ApiResponse[RotationRecommendation],
            tags=["rotation"], operation_id="getRecommendation")
def recommendations(field_id: UUID, request: Request, season_year: int = Query(...),
                    svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.recommendation(field_id, season_year))


@router.get("/fields/{field_id}/scenarios", response_model=ApiResponse[list[RotationScenario]], tags=["rotation"],
            operation_id="listScenarios")
def list_scenarios(field_id: UUID, request: Request, svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.list_scenarios(field_id))


@router.post("/fields/{field_id}/scenarios", response_model=ApiResponse[RotationScenario], status_code=201,
             tags=["rotation"], operation_id="createScenario")
def create_scenario(field_id: UUID, body: UpsertScenarioRequest, request: Request,
                    svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.create_scenario(field_id, body))


@router.put("/scenarios/{scenario_id}", response_model=ApiResponse[RotationScenario], tags=["rotation"],
            operation_id="updateScenario")
def update_scenario(scenario_id: UUID, body: UpsertScenarioRequest, request: Request,
                    svc: RotationService = Depends(rot_svc)):
    return ok(request, svc.update_scenario(scenario_id, body))


@router.delete("/scenarios/{scenario_id}", response_model=ApiResponse[Deleted], tags=["rotation"],
               operation_id="deleteScenario")
def delete_scenario(scenario_id: UUID, request: Request, svc: RotationService = Depends(rot_svc)):
    svc.delete_scenario(scenario_id)
    return ok(request, Deleted())


# E26 evidence, E27 jobs
@router.get("/fields/{field_id}/evidence", response_model=ApiResponse[list[EvidenceItem]], tags=["evidence"],
            operation_id="listEvidence")
def evidence(field_id: UUID, request: Request, kind: EvidenceKind | None = None, related_id: str | None = None,
             svc: EvidenceService = Depends(ev_svc)):
    return ok(request, svc.evidence(field_id, kind, related_id))


@router.get("/jobs/{job_id}", response_model=ApiResponse[ProcessingJob], tags=["fields"], operation_id="getJob")
def get_job(job_id: UUID, request: Request, svc: FieldService = Depends(fields_svc)):
    return ok(request, svc.get_job(job_id))
