/**
 * Contract drift check (API_CONTRACTS §1 source-of-truth flow; PHASE_0 T13).
 * Every hand-written type in src/types/contracts.ts must be structurally IDENTICAL (same keys, mutually assignable)
 * to the type generated from the FastAPI OpenAPI schema (contract/openapi.gen.ts).
 * Run: npm run contract:check   (fails to compile on any drift)
 */
import type * as C from "../src/types/contracts";
import type { components, paths } from "./openapi.gen";

type S = components["schemas"];
type Equals<A, B> = [A] extends [B] ? ([B] extends [A] ? true : false) : false;
type SameKeys<A, B> = Equals<keyof A, keyof B>;
type Same<A, B> = Equals<A, B> extends true ? (SameKeys<A, B> extends true ? true : false) : false;
type Assert<T extends true> = T;

export type Checks = [
  Assert<Same<C.Uncertainty, S["Uncertainty"]>>,
  Assert<Same<C.Quantity, S["Quantity"]>>,
  Assert<Same<C.SourceRef, S["SourceRef"]>>,
  Assert<Same<C.SpatialSupport, S["SpatialSupport"]>>,
  Assert<Same<C.TemporalSupport, S["TemporalSupport"]>>,
  Assert<Same<C.QualityFlag, S["QualityFlag"]>>,
  Assert<Same<C.QualityInfo, S["QualityInfo"]>>,
  Assert<Same<C.MethodRef, S["MethodRef"]>>,
  Assert<Same<C.TimeSeriesPoint, S["TimeSeriesPoint"]>>,
  Assert<Same<C.TimeSeries, S["TimeSeries"]>>,
  Assert<Same<C.GeoJSONMultiPolygon, S["GeoJSONMultiPolygon"]>>,
  Assert<Same<C.ResponseMeta, S["ResponseMeta"]>>,
  Assert<Same<C.ApiErrorResponse, S["ApiErrorResponse"]>>,
  Assert<Same<C.JobStep, S["JobStep"]>>,
  Assert<Same<C.ProcessingJob, S["ProcessingJob"]>>,
  Assert<Same<C.AOI, S["AOI"]>>,
  Assert<Same<C.Farm, S["Farm"]>>,
  Assert<Same<C.FarmOverview, S["FarmOverview"]>>,
  Assert<Same<C.Field, S["Field"]>>,
  Assert<Same<C.FieldSummary, S["FieldSummary"]>>,
  Assert<Same<C.CreateFieldRequest, S["CreateFieldRequest"]>>,
  Assert<Same<C.CreateFieldResponse, S["CreateFieldResponse"]>>,
  Assert<Same<C.EnvironmentalIndicator, S["EnvironmentalIndicator"]>>,
  Assert<Same<C.Season, S["Season"]>>,
  Assert<Same<C.ClimateProfile, S["ClimateProfile"]>>,
  Assert<Same<C.SoilLayer, S["SoilLayer"]>>,
  Assert<Same<C.SoilMapUnitShare, S["SoilMapUnitShare"]>>,
  Assert<Same<C.ClassValue, S["ClassValue"]>>,
  Assert<Same<C.SoilProfile, S["SoilProfile"]>>,
  Assert<Same<C.TerrainProfile, S["TerrainProfile"]>>,
  Assert<Same<C.MaskCounts, S["MaskCounts"]>>,
  Assert<Same<C.VegetationScene, S["VegetationScene"]>>,
  Assert<Same<C.Phenology, S["Phenology"]>>,
  Assert<Same<C.VegetationProfile, S["VegetationProfile"]>>,
  Assert<Same<C.CropYear, S["CropYear"]>>,
  Assert<Same<C.CropHistory, S["CropHistory"]>>,
  Assert<Same<C.DatasetCoverage, S["DatasetCoverage"]>>,
  Assert<Same<C.DataCoverage, S["DataCoverage"]>>,
  Assert<Same<C.ResilienceComponent, S["ResilienceComponent"]>>,
  Assert<Same<C.ResilienceProfile, S["ResilienceProfile"]>>,
  Assert<Same<C.CropOption, S["CropOption"]>>,
  Assert<Same<C.ScenarioYear, S["ScenarioYear"]>>,
  Assert<Same<C.ScenarioEvaluation, S["ScenarioEvaluation"]>>,
  Assert<Same<C.RotationScenario, S["RotationScenario"]>>,
  Assert<Same<C.UpsertScenarioRequest, S["UpsertScenarioRequest"]>>,
  Assert<Same<C.FactorAssessment, S["FactorAssessment"]>>,
  Assert<Same<C.RecommendationCandidate, S["RecommendationCandidate"]>>,
  Assert<Same<C.RotationRecommendation, S["RotationRecommendation"]>>,
  Assert<Same<C.EvidenceItem, S["EvidenceItem"]>>,
  Assert<Same<C.FieldProfile, S["FieldProfile"]>>,
  Assert<Same<C.DatasetDescriptor, S["DatasetDescriptor"]>>,
  Assert<Same<C.KnowledgeBaseMetadata, S["KnowledgeBaseMetadata"]>>,
  Assert<Same<C.CropEvidenceRecord, S["CropEvidenceRecord"]>>,
  Assert<Same<C.DirectedRotationTransition, S["DirectedRotationTransition"]>>,
  Assert<Same<C.CropProfileSummary, S["CropProfileSummary"]>>,
  Assert<Same<C.CropProfile, S["CropProfile"]>>,
  Assert<Same<C.SuitabilityFactorAssessment, S["SuitabilityFactorAssessment"]>>,
  Assert<Same<C.CropSuitabilityAssessment, S["CropSuitabilityAssessment"]>>,
  Assert<Same<C.SuitabilitySummaryCounts, S["SuitabilitySummaryCounts"]>>,
  Assert<Same<C.FieldSuitabilityResponse, S["FieldSuitabilityResponse"]>>,
  // Envelopes used by the frontend services
  Assert<Same<C.ApiResponse<C.Farm[]>, S["ApiResponse_list_Farm__"]>>,
  Assert<Same<C.ApiResponse<C.FieldProfile>, S["ApiResponse_FieldProfile_"]>>,
  Assert<Same<C.ApiResponse<{ deleted: true }>, S["ApiResponse_Deleted_"]>>,
  // Body of E5 PATCH /farms/{farm_id} matches FarmService.updateFarm's patch argument
  Assert<Same<{ name: string }, S["UpdateFarmRequest"]>>,
];

// Every path the frontend HTTP services call must exist in the OpenAPI schema.
export type PathChecks = [
  paths["/api/v1/health"], paths["/api/v1/datasets"], paths["/api/v1/farms"], paths["/api/v1/farms/{farm_id}"],
  paths["/api/v1/farms/{farm_id}/overview"], paths["/api/v1/farms/{farm_id}/fields"], paths["/api/v1/fields/{field_id}"],
  paths["/api/v1/fields/{field_id}/profile"], paths["/api/v1/fields/{field_id}/coverage"],
  paths["/api/v1/fields/{field_id}/climate"], paths["/api/v1/fields/{field_id}/soil"],
  paths["/api/v1/fields/{field_id}/terrain"], paths["/api/v1/fields/{field_id}/vegetation"],
  paths["/api/v1/fields/{field_id}/crop-history"], paths["/api/v1/fields/{field_id}/indicators"],
  paths["/api/v1/fields/{field_id}/resilience"], paths["/api/v1/crops"],
  paths["/api/v1/fields/{field_id}/recommendations"], paths["/api/v1/fields/{field_id}/scenarios"],
  paths["/api/v1/scenarios/{scenario_id}"], paths["/api/v1/fields/{field_id}/evidence"], paths["/api/v1/jobs/{job_id}"],
  paths["/api/v1/canonical-crops"], paths["/api/v1/crops/{crop_id}"], paths["/api/v1/crops/{crop_id}/attributes"],
  paths["/api/v1/rotations"], paths["/api/v1/rotations/matrix"], paths["/api/v1/evidence/{evidence_id}"], paths["/api/v1/kb/metadata"],
  paths["/api/v1/fields/{field_id}/suitability"], paths["/api/v1/fields/{field_id}/suitability/{crop_id}"],
];
