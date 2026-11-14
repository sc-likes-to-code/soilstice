/**
 * Frontend service interfaces — docs/SOILSTICE_API_CONTRACTS.md §7.
 * UI code depends ONLY on these interfaces (obtained via `@/services`), never on an implementation.
 */
import type {
  ApiResponse, ClimateProfile, CreateFieldRequest, CreateFieldResponse, CropCode, CropHistory, CropOption,
  DataCoverage, DatasetDescriptor, EnvironmentalIndicator, EvidenceItem, EvidenceKind, Farm, FarmOverview, Field,
  FieldProcessingStatus, FieldProfile, FieldSource, FieldSummary, IndicatorCategory, ProcessingJob,
  ResilienceProfile, RotationRecommendation, RotationScenario, SoilProfile, TerrainProfile, UpsertScenarioRequest,
  UUID, VegetationIndex, VegetationProfile,
} from "@/types/contracts";

export interface FarmService {
  listFarms(): Promise<ApiResponse<Farm[]>>;
  getFarm(farmId: UUID): Promise<ApiResponse<Farm>>;
  updateFarm(farmId: UUID, patch: { name: string }): Promise<ApiResponse<Farm>>;
  getOverview(farmId: UUID, seasonYear?: number): Promise<ApiResponse<FarmOverview>>;
}

export interface FieldService {
  listFields(farmId: UUID, filter?: { source?: FieldSource; status?: FieldProcessingStatus }): Promise<ApiResponse<FieldSummary[]>>;
  getField(fieldId: UUID): Promise<ApiResponse<Field>>;
  createField(farmId: UUID, req: CreateFieldRequest): Promise<ApiResponse<CreateFieldResponse>>;
  deleteField(fieldId: UUID): Promise<ApiResponse<{ deleted: true }>>;
  getProfile(fieldId: UUID, seasonYear?: number): Promise<ApiResponse<FieldProfile>>;
  getCoverage(fieldId: UUID): Promise<ApiResponse<DataCoverage>>;
  getJob(jobId: UUID): Promise<ApiResponse<ProcessingJob>>;
}

export interface EnvironmentService {
  getClimate(fieldId: UUID, seasonYear: number, cropCode?: CropCode): Promise<ApiResponse<ClimateProfile>>;
  getSoil(fieldId: UUID): Promise<ApiResponse<SoilProfile>>;
  getTerrain(fieldId: UUID): Promise<ApiResponse<TerrainProfile>>;
  getVegetation(fieldId: UUID, year: number, index?: VegetationIndex): Promise<ApiResponse<VegetationProfile>>;
  getIndicators(fieldId: UUID, opts?: { category?: IndicatorCategory; seasonYear?: number }): Promise<ApiResponse<EnvironmentalIndicator[]>>;
}

export interface RotationService {
  listCrops(): Promise<ApiResponse<CropOption[]>>;
  getCropHistory(fieldId: UUID): Promise<ApiResponse<CropHistory>>;
  getRecommendation(fieldId: UUID, seasonYear: number): Promise<ApiResponse<RotationRecommendation>>;
  listScenarios(fieldId: UUID): Promise<ApiResponse<RotationScenario[]>>;
  createScenario(fieldId: UUID, req: UpsertScenarioRequest): Promise<ApiResponse<RotationScenario>>;
  updateScenario(scenarioId: UUID, req: UpsertScenarioRequest): Promise<ApiResponse<RotationScenario>>;
  deleteScenario(scenarioId: UUID): Promise<ApiResponse<{ deleted: true }>>;
}

export interface ResilienceService {
  getResilience(fieldId: UUID): Promise<ApiResponse<ResilienceProfile>>;
}

export interface EvidenceService {
  listDatasets(): Promise<ApiResponse<DatasetDescriptor[]>>;
  listEvidence(fieldId: UUID, opts?: { kind?: EvidenceKind; relatedId?: string }): Promise<ApiResponse<EvidenceItem[]>>;
}

export interface Services {
  mode: "mock" | "api";
  farms: FarmService;
  fields: FieldService;
  environment: EnvironmentService;
  rotation: RotationService;
  resilience: ResilienceService;
  evidence: EvidenceService;
}
