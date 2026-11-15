"""Entity contracts — API_CONTRACTS §5. Field names, enums and optionality mirror src/types/contracts.ts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field as PField

from .common import (
    GeoJSONMultiPolygon,
    MethodRef,
    QualityFlag,
    QualityInfo,
    Quantity,
    SourceRef,
    SpatialSupport,
    TemporalSupport,
    TimeSeries,
    Uncertainty,
)
from .envelope import ProcessingJob
from .vocab import (
    CONTRACT_VERSION,
    Confidence,
    Contract,
    CropCode,
    DataNature,
    DatasetId,
    IndicatorCategory,
    IndicatorKey,
    MissingReason,
    ScenarioInterpretation,
    ScoreBand,
    SupportClass,
    TemporalResolution,
)

# ── 5.3 EnvironmentalIndicator ──────────────────────────────────────────────


class EnvironmentalIndicator(Contract):
    indicator_id: str
    key: IndicatorKey
    label: str
    category: IndicatorCategory
    value: Quantity
    nature: DataNature
    spatial: SpatialSupport
    temporal: TemporalSupport
    quality: QualityInfo
    sources: list[SourceRef]
    method: MethodRef
    input_ids: list[str] = []
    reference_value: Quantity | None = None


# ── 5.2 Field ───────────────────────────────────────────────────────────────

FieldSource = Literal["csb", "user", "synthetic"]
FieldProcessingStatus = Literal["ready", "processing", "partial", "failed"]


class Field(Contract):
    field_id: UUID
    farm_id: UUID
    name: str
    geometry: GeoJSONMultiPolygon
    centroid: tuple[float, float]
    area: Quantity
    state_fips: str
    county_fips: str
    source: FieldSource
    source_ref: SourceRef | None = None
    csb_id: str | None = None
    editable: bool
    processing_status: FieldProcessingStatus
    latest_job_id: UUID | None = None
    created_at: datetime


class LatestCrop(Contract):
    year: int
    crop_code: CropCode | None = None
    crop_name: str | None = None


class FieldSummary(Contract):
    field_id: UUID
    name: str
    centroid: tuple[float, float]
    geometry: GeoJSONMultiPolygon
    area: Quantity
    source: FieldSource
    processing_status: FieldProcessingStatus
    latest_crop: LatestCrop | None = None
    resilience_band: ScoreBand
    coverage_completeness: float | None = PField(default=None, ge=0, le=1)


class CreateFieldRequest(Contract):
    name: str = PField(min_length=1, max_length=80)
    geometry: GeoJSONMultiPolygon


class CreateFieldResponse(Contract):
    field: Field
    job: ProcessingJob


# ── 5.1 Farm ────────────────────────────────────────────────────────────────

AoiId = Literal["ks_reno", "ks_finney"]


class AOI(Contract):
    aoi_id: AoiId
    label: str
    county_fips: list[str]
    state: Literal["KS"]


class Farm(Contract):
    farm_id: UUID
    name: str
    aoi: AOI
    field_count: int
    total_area: Quantity
    created_at: datetime
    updated_at: datetime


class CoverageCount(Contract):
    dataset_id: DatasetId
    fields_available: int
    fields_total: int


class FarmOverview(Contract):
    farm: Farm
    fields: list[FieldSummary]
    coverage_summary: list[CoverageCount]
    alerts: list[QualityFlag]
    regional_context: list[EnvironmentalIndicator]


class UpdateFarmRequest(Contract):
    """Body of E5 `PATCH /farms/{farm_id}` (`{name}` in API_CONTRACTS §6)."""

    name: str = PField(min_length=1, max_length=80)


# ── 5.4 ClimateProfile ──────────────────────────────────────────────────────


class Season(Contract):
    label: str
    start: date
    end: date
    crop_code: CropCode | None = None


class AuthoritativeClimateSource(Contract):
    precipitation: DatasetId
    temperature: DatasetId


class ClimateProfile(Contract):
    field_id: UUID
    season: Season
    authoritative_source: AuthoritativeClimateSource
    indicators: list[EnvironmentalIndicator]
    series: list[TimeSeries]
    quality: QualityInfo


# ── 5.5 SoilProfile ─────────────────────────────────────────────────────────


class SoilLayer(Contract):
    top_cm: float
    bottom_cm: float
    sand_pct: Quantity
    silt_pct: Quantity
    clay_pct: Quantity
    texture_class: str | None = None
    ph_h2o: Quantity
    om_pct: Quantity
    awc: Quantity


class SoilComponentRef(Contract):
    cokey: str
    compname: str
    comppct_r: float | None = None


class SoilMapUnitShare(Contract):
    mukey: str
    muname: str
    area_fraction: float = PField(ge=0, le=1)
    major_components: list[SoilComponentRef]


class ClassValue(Contract):
    value: str | None = None
    weight_share: float | None = PField(default=None, ge=0, le=1)
    missing_reason: MissingReason | None = None


class SurveyRef(Contract):
    areasymbol: str
    saverest: date | None = None


class SoilProfile(Contract):
    field_id: UUID
    layers: list[SoilLayer]
    aws_0_100: Quantity
    aws_0_150: Quantity
    drainage_class: ClassValue
    hydrologic_group: ClassValue
    slope_pct_ssurgo: Quantity
    map_units: list[SoilMapUnitShare]
    survey: list[SurveyRef]
    method: MethodRef
    null_weight_fraction: float | None = None
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo


# ── 5.6 TerrainProfile ──────────────────────────────────────────────────────


class TerrainProfile(Contract):
    field_id: UUID
    elevation_mean: Quantity
    elevation_min: Quantity
    elevation_max: Quantity
    slope_mean_pct: Quantity
    slope_p90_pct: Quantity
    method: MethodRef
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo


# ── 5.7 VegetationProfile ───────────────────────────────────────────────────

VegetationIndex = Literal["NDVI", "EVI", "NDMI", "SAVI", "MSAVI", "NDWI", "NBR", "NBR2", "TVI"]


class MaskCounts(Contract):
    cloud: int
    cloud_adjacent: int
    cloud_shadow: int
    snow_ice: int
    water: int


class VegetationScene(Contract):
    granule_id: str
    product: Literal["HLSL30_VI", "HLSS30_VI", "HLSL30", "HLSS30", "synthetic"]
    acquired_at: datetime
    median: float | None = None
    p10: float | None = None
    p90: float | None = None
    valid_pixels: int
    total_pixels: int
    clear_fraction: float = PField(ge=0, le=1)
    accepted: bool
    mask_counts: MaskCounts
    missing_reason: MissingReason | None = None


class Phenology(Contract):
    peak_value: Quantity
    peak_date: date | None = None
    greenup_date: date | None = None
    senescence_date: date | None = None
    method: MethodRef
    gap_filled: bool
    missing_reason: MissingReason | None = None


class VegetationProfile(Contract):
    field_id: UUID
    year: int
    index: VegetationIndex
    scenes: list[VegetationScene]
    series: TimeSeries
    phenology: Phenology
    spatial: SpatialSupport
    sources: list[SourceRef]
    quality: QualityInfo


# ── 5.8 CropHistory ─────────────────────────────────────────────────────────


class CropRef(Contract):
    crop_code: CropCode | None = None
    crop_name: str | None = None


class CropShare(Contract):
    crop_code: CropCode
    crop_name: str
    area_fraction: float = PField(ge=0, le=1)


class CropYear(Contract):
    year: int
    majority: CropRef
    purity: float | None = PField(default=None, ge=0, le=1)
    histogram: list[CropShare]
    low_purity: bool
    class_accuracy: Uncertainty | None = None
    csb_crop_code: CropCode | None = None
    agrees_with_csb: bool | None = None
    native_resolution_m: float | None = None
    missing_reason: MissingReason | None = None
    source: SourceRef


class YearPeriod(Contract):
    start_year: int
    end_year: int


class CropHistory(Contract):
    field_id: UUID
    period: YearPeriod
    years: list[CropYear]
    metrics: list[EnvironmentalIndicator]
    spatial: SpatialSupport
    quality: QualityInfo


# ── 5.9 DataCoverage ────────────────────────────────────────────────────────

CoverageStatus = Literal["available", "partial", "missing", "pending", "not_applicable", "not_integrated"]
Priority = Literal["P0", "P1", "P2"]


class TemporalRange(Contract):
    start: date | None = None
    end: date | None = None


class DatasetCoverage(Contract):
    dataset_id: DatasetId
    label: str
    priority: Priority
    status: CoverageStatus
    support_class: SupportClass
    native_resolution_m: float | None = None
    temporal_coverage: TemporalRange
    product_version: str | None = None
    last_updated: datetime | None = None
    missing_reason: MissingReason | None = None
    note: str | None = None


class DataCoverage(Contract):
    field_id: UUID
    datasets: list[DatasetCoverage]
    completeness: float = PField(ge=0, le=1)


# ── 5.10 ResilienceProfile ──────────────────────────────────────────────────

ResilienceComponentKey = Literal[
    "soil_water_buffer", "terrain_erosion_risk", "vegetation_stability", "climate_exposure", "rotation_diversity"
]


class ResilienceComponent(Contract):
    key: ResilienceComponentKey
    label: str
    score: Quantity
    band: ScoreBand
    support_class: SupportClass
    confidence: Confidence
    input_indicator_ids: list[str]
    explanation: str
    rule_ref: MethodRef


class ResilienceComposite(Contract):
    score: Quantity
    band: ScoreBand
    confidence: Confidence
    components_used: int = PField(ge=0, le=5)
    components_total: Literal[5] = 5


class ResilienceProfile(Contract):
    profile_id: UUID
    field_id: UUID
    as_of: date
    model_version: str
    status: Literal["computed", "insufficient_data", "pending"]
    composite: ResilienceComposite
    components: list[ResilienceComponent]
    limitations: list[QualityFlag]
    disclaimers: list[str]


# ── 5.11 CropOption ─────────────────────────────────────────────────────────


class CropOption(Contract):
    crop_code: CropCode
    name: str
    family: str
    is_double_crop: bool
    kb_version: str


# ── 5.12 RotationScenario ───────────────────────────────────────────────────

FitBand = Literal["suitable", "marginal", "unsuitable", "unknown"]


class ScenarioYear(Contract):
    year: int
    crop_code: CropCode
    crop_name: str


class EvaluationDimension(Contract):
    key: Literal["agronomic_fit", "rotation_benefit", "water_risk", "diversity"]
    band: FitBand
    explanation: str


class YearFinding(Contract):
    year: int
    band: FitBand
    messages: list[QualityFlag]
    evidence_ids: list[UUID]


class ScenarioEvaluation(Contract):
    engine_version: str
    kb_version: str
    overall: FitBand
    interpretation: ScenarioInterpretation = "supported"
    dimensions: list[EvaluationDimension]
    year_findings: list[YearFinding]
    warnings: list[QualityFlag]
    evaluated_at: datetime


class RotationScenario(Contract):
    scenario_id: UUID
    field_id: UUID
    name: str
    start_year: int
    sequence: list[ScenarioYear] = PField(min_length=2, max_length=8)
    evaluation: ScenarioEvaluation | None = None
    created_at: datetime
    updated_at: datetime


class ScenarioYearInput(Contract):
    year: int
    crop_code: CropCode


class UpsertScenarioRequest(Contract):
    name: str = PField(min_length=1, max_length=80)
    start_year: int
    sequence: list[ScenarioYearInput] = PField(min_length=2, max_length=8)


class GenerateRotationsRequest(Contract):
    horizon: int = PField(default=3, ge=2, le=5)
    start_year: int = PField(default=2026, ge=2026, le=2035)
    include_cover_crops: bool = True
    max_candidates: int = PField(default=10, ge=1, le=20)


class GenerateCandidate(Contract):
    rank: int
    name: str
    sequence: list[ScenarioYear]
    evaluation: ScenarioEvaluation
    is_pareto_optimal: bool = True
    pareto_rank: int = 1
    pareto_explanation: str | None = None


class GenerateRotationsResponse(Contract):
    field_id: UUID
    horizon: int
    start_year: int
    antecedent_crop: ScenarioYear | None = None
    candidates: list[GenerateCandidate]
    pareto_optimal_count: int = 0
    generated_at: datetime


class CompareScenariosRequest(Contract):
    scenario_ids: list[UUID] = PField(min_length=2, max_length=3)


class TradeoffFinding(Contract):
    category: str
    summary: str


class CompareScenariosResponse(Contract):
    field_id: UUID
    scenarios: list[RotationScenario]
    tradeoffs: list[TradeoffFinding]


# ── 5.13 RotationRecommendation ─────────────────────────────────────────────


class FactorAssessment(Contract):
    factor: Literal["ph", "drainage", "water_holding", "gdd", "slope", "rotation_history", "regional_climate"]
    band: FitBand
    observed: Quantity | None = None
    requirement: str
    support_class: SupportClass
    evidence_ids: list[UUID] = []


class RecommendationCandidate(Contract):
    rank: int = PField(ge=1)
    crop_code: CropCode
    crop_name: str
    overall: FitBand
    confidence: Confidence
    factors: list[FactorAssessment]
    rotation_effects: list[QualityFlag]
    reasons: list[str]


class TargetSeason(Contract):
    label: str
    start: date
    end: date


class ExcludedCrop(Contract):
    crop_code: CropCode
    crop_name: str
    reason: str


class RotationRecommendation(Contract):
    recommendation_id: UUID
    field_id: UUID
    target_season: TargetSeason
    engine_version: str
    kb_version: str
    status: Literal["computed", "insufficient_data", "pending"]
    candidates: list[RecommendationCandidate]
    excluded: list[ExcludedCrop]
    disclaimers: list[str]
    generated_at: datetime


# ── 5.14 EvidenceItem ───────────────────────────────────────────────────────

EvidenceKind = Literal["dataset", "indicator", "method", "kb_rule", "literature"]
VerificationStatus = Literal["LIVE", "CMR", "DOC", "UNVERIFIED", "SYNTHETIC"]


class EvidenceItem(Contract):
    evidence_id: UUID
    kind: EvidenceKind
    title: str
    summary: str
    field_id: UUID | None = None
    dataset_id: DatasetId | None = None
    product_version: str | None = None
    citation: str | None = None
    url: str | None = None
    doi: str | None = None
    accessed_at: date | None = None
    verification_status: VerificationStatus
    spatial: SpatialSupport | None = None
    temporal: TemporalSupport | None = None
    related_ids: list[str] = []


# ── 5.15 FieldProfile ───────────────────────────────────────────────────────


class FieldProfile(Contract):
    field: Field
    coverage: DataCoverage
    soil: SoilProfile | None = None
    terrain: TerrainProfile | None = None
    crop_history: CropHistory | None = None
    climate_summary: list[EnvironmentalIndicator] = []
    vegetation_summary: list[EnvironmentalIndicator] = []
    resilience: ResilienceProfile | None = None


# ── 5.16 DatasetDescriptor ──────────────────────────────────────────────────


class DatasetDescriptor(Contract):
    dataset_id: DatasetId
    title: str
    publisher: str
    product: str
    product_version: str
    priority: Priority
    support_class: SupportClass
    native_resolution_m: float | None = None
    temporal_resolution: TemporalResolution
    temporal_coverage: TemporalRange
    documentation_url: str
    doi: str | None = None
    verification_status: VerificationStatus
    last_verified: date
    integration_status: Literal["integrated", "planned"]


# ── Small response bodies (API_CONTRACTS §6) ────────────────────────────────


class Health(Contract):
    status: Literal["ok"] = "ok"
    contract_version: str = CONTRACT_VERSION


class Deleted(Contract):
    deleted: Literal[True] = True


# ── 5.17 Crop Knowledge Base Entities (Phase 5) ──────────────────────────────


class KnowledgeBaseMetadata(Contract):
    dataset_name: str
    schema_version: str
    stage: str
    effective_date: str
    geographic_scope: str
    canonical_crop_count: int
    evidence_records_count: int
    directed_rotation_transitions_count: int = 196
    description: str
    last_updated: str | None = None
    notes: str | None = None


class CropEvidenceRecord(Contract):
    evidence_id: str
    crop_ids: list[str]
    related_domain: str
    attribute_or_claim: str
    recorded_value_or_summary: str | None = None
    source_organization: str
    source_title: str
    author_or_institution: str
    publication_year: int | None = None
    publication_date: str | None = None
    access_date: str | None = None
    source_url_or_doi: str | None = None
    citation_location: str | None = None
    exact_supporting_context: str | None = None
    geographic_scope: str | None = None
    variety_scope: str | None = None
    source_quality: str
    data_availability: str | None = None
    conditions_and_assumptions: str | None = None
    limitations: str | None = None


class DirectedRotationTransition(Contract):
    preceding_crop_id: str
    preceding_crop_name: str
    following_crop_id: str
    following_crop_name: str
    compatibility_rating: str
    is_monoculture: bool
    monoculture_risk: str | None = None
    synergy_mechanisms: str | None = None
    disease_break_potential: str | None = None
    shared_pest_disease_risks: str | None = None
    herbicide_carryover_risks: str | None = None
    rotational_niche: str | None = None
    evidence_ids: list[str] = PField(default_factory=list)
    limitations: str | None = None


class CropProfileSummary(Contract):
    crop_id: str
    cdl_code: int | None = None
    common_name: str
    scientific_name: str
    botanical_family: str
    crop_group: str
    portfolio_role: str
    lifecycle_class: str
    is_cover_crop: bool
    can_serve_as_cover_crop: bool
    commercial_harvest_feasible: bool
    usda_plants_symbol: str | None = None


class CropProfile(Contract):
    crop_id: str
    cdl_code: int | None = None
    common_name: str
    scientific_name: str
    taxonomic_authority: str | None = None
    botanical_family: str
    crop_group: str
    portfolio_role: str
    lifecycle_class: str
    is_cover_crop: bool
    can_serve_as_cover_crop: bool
    commercial_harvest_feasible: bool
    usda_plants_symbol: str | None = None
    crop_identity: dict[str, Any]
    growing_duration: dict[str, Any]
    temperature_requirements: dict[str, Any]
    rainfall_requirements: dict[str, Any]
    water_demand_and_tolerance: dict[str, Any]
    soil_preferences: dict[str, Any]
    root_and_nutrients: dict[str, Any]
    nitrogen_and_biomass: dict[str, Any]
    rotation_compatibility: dict[str, Any]
    regional_suitability: list[dict[str, Any]]
    evidence_ids: list[str] = PField(default_factory=list)


# ── 5.18 Crop Suitability Entities (Phase 6) ─────────────────────────────────

SuitabilityClass = Literal[
    "suitable",
    "conditionally_suitable",
    "limited_suitability",
    "unsuitable",
    "insufficient_data",
]

FactorCompatibility = Literal[
    "optimal",
    "compatible",
    "moderate_limitation",
    "critical_limitation",
    "unknown",
]

FactorSeverity = Literal[
    "none",
    "favorable",
    "moderate",
    "critical",
    "unknown",
]

FactorCategory = Literal[
    "thermal",
    "water_climate",
    "soil",
    "rooting",
    "terrain",
    "historical",
    "regional",
]


class SuitabilityFactorAssessment(Contract):
    factor_key: str
    factor_name: str
    category: FactorCategory
    observed_value: Quantity
    crop_requirement: str | None = None
    compatibility: FactorCompatibility
    is_limiting: bool
    is_favorable: bool
    severity: FactorSeverity
    score: float | None = None
    interpretation: str
    evidence_ids: list[str] = PField(default_factory=list)
    data_status: Literal["available", "missing", "provisional", "not_integrated"] = "available"
    support_class: SupportClass = "F"


class CropSuitabilityAssessment(Contract):
    crop_id: str
    crop_name: str
    cdl_code: int | None = None
    botanical_family: str
    portfolio_role: str
    is_cover_crop: bool
    assessment_status: Literal["evaluated", "provisional", "insufficient_data"]
    suitability_class: SuitabilityClass
    suitability_score: float | None = None
    score_methodology: str | None = None
    factor_assessments: list[SuitabilityFactorAssessment]
    limiting_factors: list[str]
    favorable_factors: list[str]
    unknown_factors: list[str]
    data_quality: QualityInfo
    spatial_support: SpatialSupport
    temporal_support: TemporalSupport
    evidence_ids: list[str] = PField(default_factory=list)
    explanation: str
    limitations: list[str]


class SuitabilitySummaryCounts(Contract):
    total_evaluated: int
    suitable: int
    conditionally_suitable: int
    limited_suitability: int
    unsuitable: int
    insufficient_data: int


class FieldSuitabilityResponse(Contract):
    field_id: UUID
    season_year: int
    as_of: date
    engine_version: str
    kb_version: str
    status: Literal["evaluated", "provisional", "insufficient_data"]
    summary: SuitabilitySummaryCounts
    crops: list[CropSuitabilityAssessment]
    disclaimers: list[str]


