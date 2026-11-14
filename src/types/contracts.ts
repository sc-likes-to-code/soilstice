/**
 * SOILSTICE wire contracts — transcribed from docs/SOILSTICE_API_CONTRACTS.md
 * Contract version 1.0.0-phase0. Do not edit without bumping the contract version (rule R9).
 * snake_case mirrors the JSON wire format exactly (rule R1).
 */

export const CONTRACT_VERSION = "1.0.0-phase0" as const;

// ───────────────────────── §2 Controlled vocabularies ─────────────────────────
export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;

export type DataMode = "synthetic" | "live";
export type SupportClass = "F" | "S" | "R";
export type DataNature = "observation" | "model" | "derived" | "classification" | "proxy_statistic";
export type QualityStatus = "valid" | "partial" | "flagged" | "missing";
export type ScoreBand = "low" | "moderate" | "high" | "unknown";
export type Confidence = "low" | "medium" | "high";
export type Severity = "info" | "warning" | "critical";

export type MissingReason =
  | "NO_DATA_SOURCE" | "FILL_VALUE" | "QA_MASKED_CLOUD" | "QA_MASKED_SHADOW" | "QA_MASKED_SNOW"
  | "QA_LOW_QUALITY_RETRIEVAL" | "INSUFFICIENT_COVERAGE" | "OUT_OF_TEMPORAL_RANGE"
  | "UPSTREAM_ERROR" | "NOT_YET_PUBLISHED" | "NOT_COMPUTED" | "OUTSIDE_AOI" | "PENDING_PROCESSING";

export type DatasetId =
  | "nasa_power_daily_ag" | "usda_nrcs_ssurgo_sda" | "usda_nass_cdl" | "usda_nass_csb"
  | "nasa_hls" | "nasa_hls_vi" | "nasa_smap_spl4smgp" | "nasa_srtm_gl1"
  | "prism_daily" | "openet" | "usda_nass_quickstats" | "nasa_smap_spl3smp_e"
  | "nasa_gpm_imerg" | "fao_gaez_v5"
  | "soilstice_derived" | "user_input" | "synthetic";

export type ExtractionMethod =
  | "zonal_polygon" | "zonal_polygon_inward_buffer" | "containing_cell" | "api_point_query"
  | "vector_intersection" | "attribute_join" | "not_applicable";

export type TemporalResolution = "PT3H" | "P1D" | "P1M" | "season" | "P1Y" | "static" | "irregular";
export type Aggregation =
  | "none" | "mean" | "sum" | "median" | "min" | "max" | "majority" | "weighted_mean" | "percentile" | "count";
export type TimeStandard = "UTC" | "LST" | "not_applicable";

export type Unit =
  | "mm" | "degC" | "degC_day" | "percent" | "MJ_m-2_day-1" | "MJ_m-2" | "m3_m-3" | "wetness_0_1"
  | "cm" | "cm_cm-1" | "m" | "degree" | "pH" | "ha" | "day" | "year" | "count"
  | "percentile" | "unitless" | "score_0_100";

export type IndicatorCategory = "climate" | "soil_moisture" | "vegetation" | "water" | "soil" | "terrain" | "rotation";

export type IndicatorKey =
  | "precip_total_season" | "precip_anomaly_pct" | "gdd_season" | "heat_stress_days"
  | "frost_free_days" | "solar_total_season" | "rh_mean_season"
  | "et0_total_season" | "water_balance_season" | "et_actual_season"
  | "sm_rootzone_mean_season" | "sm_rootzone_percentile" | "sm_rootzone_dry_days"
  | "ndvi_peak" | "ndvi_peak_doy" | "ndvi_peak_cv" | "ndmi_peak_season"
  | "aws_0_150" | "ph_0_30" | "om_0_30" | "clay_0_30"
  | "slope_mean_pct" | "slope_p90_pct" | "elevation_mean"
  | "distinct_crops" | "max_monoculture_run" | "rotation_shannon";

export type CropCode = number;

// ───────────────────────── §3 Shared building blocks ─────────────────────────
export interface Uncertainty {
  kind: "range" | "std" | "ci95" | "classification_accuracy" | "none_provided";
  low: number | null;
  high: number | null;
  value: number | null;
  note: string | null;
}

export interface Quantity {
  value: number | null;
  unit: Unit;
  uncertainty: Uncertainty | null;
  missing_reason: MissingReason | null;
}

export interface SourceRef {
  dataset_id: DatasetId;
  product: string;
  product_version: string;
  acquisition_id: UUID | null;
  doi: string | null;
  documentation_url: string | null;
  retrieved_at: ISODateTime | null;
}

export interface SpatialSupport {
  support_class: SupportClass;
  native_resolution_m: number | null;
  extraction_method: ExtractionMethod;
  field_fraction_of_cell: number | null;
  cell_id: string | null;
  crs: string | null;
}

export interface TemporalSupport {
  resolution: TemporalResolution;
  period_start: ISODate | null;
  period_end: ISODate | null;
  aggregation: Aggregation;
  time_standard: TimeStandard;
}

export interface QualityFlag { code: string; severity: Severity; message: string; }

export interface QualityInfo {
  status: QualityStatus;
  flags: QualityFlag[];
  completeness: number | null;
  missing_reason: MissingReason | null;
}

export interface MethodRef {
  method_id: string;
  name: string;
  version: string;
  description: string;
  reference_url: string | null;
}

export interface TimeSeriesPoint {
  t: ISODate | ISODateTime;
  value: number | null;
  quality_status: QualityStatus;
  missing_reason: MissingReason | null;
}

export interface TimeSeries {
  series_id: string;
  variable: string;
  label: string;
  unit: Unit;
  nature: DataNature;
  spatial: SpatialSupport;
  temporal: TemporalSupport;
  sources: SourceRef[];
  points: TimeSeriesPoint[];
  reference: { label: string; period_start: ISODate; period_end: ISODate; points: TimeSeriesPoint[] } | null;
}

export interface GeoJSONMultiPolygon { type: "MultiPolygon"; coordinates: number[][][][]; }

// ───────────────────────── §4 Envelope, errors, jobs ─────────────────────────
export interface ResponseMeta {
  request_id: string;
  generated_at: ISODateTime;
  api_version: string;
  contract_version: string;
  data_mode: DataMode;
  warnings: QualityFlag[];
}
export interface ApiResponse<T> { data: T; meta: ResponseMeta; }

export type ApiErrorCode =
  | "NOT_FOUND" | "VALIDATION_ERROR" | "OUTSIDE_AOI" | "GEOMETRY_INVALID" | "FIELD_TOO_LARGE"
  | "NOT_EDITABLE" | "UPSTREAM_UNAVAILABLE" | "RATE_LIMITED" | "NOT_IMPLEMENTED" | "INTERNAL";
export interface ApiErrorResponse {
  error: { code: ApiErrorCode; message: string; details: Record<string, unknown> | null; request_id: string; retryable: boolean };
}

export type JobStatus = "queued" | "running" | "succeeded" | "partial" | "failed";
export interface JobStep { dataset_id: DatasetId; status: JobStatus; missing_reason: MissingReason | null; message: string | null; }
export interface ProcessingJob {
  job_id: UUID;
  field_id: UUID;
  status: JobStatus;
  steps: JobStep[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ───────────────────────── §5 Entities ─────────────────────────
// 5.1 Farm
export type AoiId = "ks_reno" | "ks_finney";
export interface AOI { aoi_id: AoiId; label: string; county_fips: string[]; state: "KS"; }
export interface Farm {
  farm_id: UUID;
  name: string;
  aoi: AOI;
  field_count: number;
  total_area: Quantity;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export interface FarmOverview {
  farm: Farm;
  fields: FieldSummary[];
  coverage_summary: { dataset_id: DatasetId; fields_available: number; fields_total: number }[];
  alerts: QualityFlag[];
  regional_context: EnvironmentalIndicator[];
}

// 5.2 Field
export type FieldSource = "csb" | "user" | "synthetic";
export type FieldProcessingStatus = "ready" | "processing" | "partial" | "failed";

export interface Field {
  field_id: UUID;
  farm_id: UUID;
  name: string;
  geometry: GeoJSONMultiPolygon;
  centroid: [number, number];
  area: Quantity;
  state_fips: string;
  county_fips: string;
  source: FieldSource;
  source_ref: SourceRef | null;
  csb_id: string | null;
  editable: boolean;
  processing_status: FieldProcessingStatus;
  latest_job_id: UUID | null;
  created_at: ISODateTime;
}

export interface FieldSummary {
  field_id: UUID;
  name: string;
  centroid: [number, number];
  geometry: GeoJSONMultiPolygon;
  area: Quantity;
  source: FieldSource;
  processing_status: FieldProcessingStatus;
  latest_crop: { year: number; crop_code: CropCode | null; crop_name: string | null } | null;
  resilience_band: ScoreBand;
  coverage_completeness: number | null;
}

export interface CreateFieldRequest { name: string; geometry: GeoJSONMultiPolygon; }
export interface CreateFieldResponse { field: Field; job: ProcessingJob; }

// 5.3 EnvironmentalIndicator
export interface EnvironmentalIndicator {
  indicator_id: string;
  key: IndicatorKey;
  label: string;
  category: IndicatorCategory;
  value: Quantity;
  nature: DataNature;
  spatial: SpatialSupport;
  temporal: TemporalSupport;
  quality: QualityInfo;
  sources: SourceRef[];
  method: MethodRef;
  input_ids: string[];
  reference_value: Quantity | null;
}

// 5.4 ClimateProfile
export interface Season { label: string; start: ISODate; end: ISODate; crop_code: CropCode | null; }
export interface ClimateProfile {
  field_id: UUID;
  season: Season;
  authoritative_source: { precipitation: DatasetId; temperature: DatasetId };
  indicators: EnvironmentalIndicator[];
  series: TimeSeries[];
  quality: QualityInfo;
}

// 5.5 SoilProfile
export interface SoilLayer {
  top_cm: number;
  bottom_cm: number;
  sand_pct: Quantity; silt_pct: Quantity; clay_pct: Quantity;
  texture_class: string | null;
  ph_h2o: Quantity;
  om_pct: Quantity;
  awc: Quantity;
}
export interface SoilMapUnitShare {
  mukey: string;
  muname: string;
  area_fraction: number;
  major_components: { cokey: string; compname: string; comppct_r: number | null }[];
}
export interface ClassValue { value: string | null; weight_share: number | null; missing_reason: MissingReason | null; }
export interface SoilProfile {
  field_id: UUID;
  layers: SoilLayer[];
  aws_0_100: Quantity;
  aws_0_150: Quantity;
  drainage_class: ClassValue;
  hydrologic_group: ClassValue;
  slope_pct_ssurgo: Quantity;
  map_units: SoilMapUnitShare[];
  survey: { areasymbol: string; saverest: ISODate | null }[];
  method: MethodRef;
  null_weight_fraction: number | null;
  spatial: SpatialSupport;
  sources: SourceRef[];
  quality: QualityInfo;
}

// 5.6 TerrainProfile
export interface TerrainProfile {
  field_id: UUID;
  elevation_mean: Quantity; elevation_min: Quantity; elevation_max: Quantity;
  slope_mean_pct: Quantity; slope_p90_pct: Quantity;
  method: MethodRef;
  spatial: SpatialSupport;
  sources: SourceRef[];
  quality: QualityInfo;
}

// 5.7 VegetationProfile
export type VegetationIndex = "NDVI" | "EVI" | "NDMI" | "SAVI" | "MSAVI" | "NDWI" | "NBR" | "NBR2" | "TVI";
export interface MaskCounts { cloud: number; cloud_adjacent: number; cloud_shadow: number; snow_ice: number; water: number; }
export interface VegetationScene {
  granule_id: string;
  product: "HLSL30_VI" | "HLSS30_VI" | "HLSL30" | "HLSS30" | "synthetic";
  acquired_at: ISODateTime;
  median: number | null; p10: number | null; p90: number | null;
  valid_pixels: number; total_pixels: number;
  clear_fraction: number;
  accepted: boolean;
  mask_counts: MaskCounts;
  missing_reason: MissingReason | null;
}
export interface Phenology {
  peak_value: Quantity; peak_date: ISODate | null;
  greenup_date: ISODate | null; senescence_date: ISODate | null;
  method: MethodRef; gap_filled: boolean;
  missing_reason: MissingReason | null;
}
export interface VegetationProfile {
  field_id: UUID;
  year: number;
  index: VegetationIndex;
  scenes: VegetationScene[];
  series: TimeSeries;
  phenology: Phenology;
  spatial: SpatialSupport;
  sources: SourceRef[];
  quality: QualityInfo;
}

// 5.8 CropHistory
export interface CropYear {
  year: number;
  majority: { crop_code: CropCode | null; crop_name: string | null };
  purity: number | null;
  histogram: { crop_code: CropCode; crop_name: string; area_fraction: number }[];
  low_purity: boolean;
  class_accuracy: Uncertainty | null;
  csb_crop_code: CropCode | null;
  agrees_with_csb: boolean | null;
  native_resolution_m: number | null;
  missing_reason: MissingReason | null;
  source: SourceRef;
}
export interface CropHistory {
  field_id: UUID;
  period: { start_year: number; end_year: number };
  years: CropYear[];
  metrics: EnvironmentalIndicator[];
  spatial: SpatialSupport;
  quality: QualityInfo;
}

// 5.9 DataCoverage
export type CoverageStatus = "available" | "partial" | "missing" | "pending" | "not_applicable" | "not_integrated";
export interface DatasetCoverage {
  dataset_id: DatasetId;
  label: string;
  priority: "P0" | "P1" | "P2";
  status: CoverageStatus;
  support_class: SupportClass;
  native_resolution_m: number | null;
  temporal_coverage: { start: ISODate | null; end: ISODate | null };
  product_version: string | null;
  last_updated: ISODateTime | null;
  missing_reason: MissingReason | null;
  note: string | null;
}
export interface DataCoverage { field_id: UUID; datasets: DatasetCoverage[]; completeness: number; }

// 5.10 ResilienceProfile
export type ResilienceComponentKey =
  | "soil_water_buffer" | "terrain_erosion_risk" | "vegetation_stability"
  | "climate_exposure" | "rotation_diversity";
export interface ResilienceComponent {
  key: ResilienceComponentKey;
  label: string;
  score: Quantity;
  band: ScoreBand;
  support_class: SupportClass;
  confidence: Confidence;
  input_indicator_ids: string[];
  explanation: string;
  rule_ref: MethodRef;
}
export interface ResilienceProfile {
  profile_id: UUID;
  field_id: UUID;
  as_of: ISODate;
  model_version: string;
  status: "computed" | "insufficient_data" | "pending";
  composite: { score: Quantity; band: ScoreBand; confidence: Confidence; components_used: number; components_total: 5 };
  components: ResilienceComponent[];
  limitations: QualityFlag[];
  disclaimers: string[];
}

// 5.11 Crop catalog
export interface CropOption { crop_code: CropCode; name: string; family: string; is_double_crop: boolean; kb_version: string; }

// 5.12 RotationScenario
export type FitBand = "suitable" | "marginal" | "unsuitable" | "unknown";
export interface ScenarioYear { year: number; crop_code: CropCode; crop_name: string; }
export type EvaluationDimensionKey = "agronomic_fit" | "rotation_benefit" | "water_risk" | "diversity";
export interface ScenarioEvaluation {
  engine_version: string;
  kb_version: string;
  overall: FitBand;
  dimensions: { key: EvaluationDimensionKey; band: FitBand; explanation: string }[];
  year_findings: { year: number; band: FitBand; messages: QualityFlag[]; evidence_ids: UUID[] }[];
  warnings: QualityFlag[];
  evaluated_at: ISODateTime;
}
export interface RotationScenario {
  scenario_id: UUID;
  field_id: UUID;
  name: string;
  start_year: number;
  sequence: ScenarioYear[];
  evaluation: ScenarioEvaluation | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export interface UpsertScenarioRequest { name: string; start_year: number; sequence: { year: number; crop_code: CropCode }[]; }

// 5.13 RotationRecommendation
export type RecommendationFactor = "ph" | "drainage" | "water_holding" | "gdd" | "slope" | "rotation_history" | "regional_climate";
export interface FactorAssessment {
  factor: RecommendationFactor;
  band: FitBand;
  observed: Quantity | null;
  requirement: string;
  support_class: SupportClass;
  evidence_ids: UUID[];
}
export interface RecommendationCandidate {
  rank: number;
  crop_code: CropCode;
  crop_name: string;
  overall: FitBand;
  confidence: Confidence;
  factors: FactorAssessment[];
  rotation_effects: QualityFlag[];
  reasons: string[];
}
export interface RotationRecommendation {
  recommendation_id: UUID;
  field_id: UUID;
  target_season: { label: string; start: ISODate; end: ISODate };
  engine_version: string;
  kb_version: string;
  status: "computed" | "insufficient_data" | "pending";
  candidates: RecommendationCandidate[];
  excluded: { crop_code: CropCode; crop_name: string; reason: string }[];
  disclaimers: string[];
  generated_at: ISODateTime;
}

// 5.14 EvidenceItem
export type EvidenceKind = "dataset" | "indicator" | "method" | "kb_rule" | "literature";
export type VerificationStatus = "LIVE" | "CMR" | "DOC" | "UNVERIFIED" | "SYNTHETIC";
export interface EvidenceItem {
  evidence_id: UUID;
  kind: EvidenceKind;
  title: string;
  summary: string;
  field_id: UUID | null;
  dataset_id: DatasetId | null;
  product_version: string | null;
  citation: string | null;
  url: string | null;
  doi: string | null;
  accessed_at: ISODate | null;
  verification_status: VerificationStatus;
  spatial: SpatialSupport | null;
  temporal: TemporalSupport | null;
  related_ids: string[];
}

// 5.15 FieldProfile
export interface FieldProfile {
  field: Field;
  coverage: DataCoverage;
  soil: SoilProfile | null;
  terrain: TerrainProfile | null;
  crop_history: CropHistory | null;
  climate_summary: EnvironmentalIndicator[];
  vegetation_summary: EnvironmentalIndicator[];
  resilience: ResilienceProfile | null;
}

// 5.16 DatasetDescriptor
export interface DatasetDescriptor {
  dataset_id: DatasetId; title: string; publisher: string; product: string; product_version: string;
  priority: "P0" | "P1" | "P2"; support_class: SupportClass; native_resolution_m: number | null;
  temporal_resolution: TemporalResolution; temporal_coverage: { start: ISODate | null; end: ISODate | null };
  documentation_url: string; doi: string | null; verification_status: VerificationStatus; last_verified: ISODate;
  integration_status: "integrated" | "planned";
}

// 5.17 Crop Knowledge Base Entities (Phase 5)
export interface KnowledgeBaseMetadata {
  dataset_name: string;
  schema_version: string;
  stage: string;
  effective_date: string;
  geographic_scope: string;
  canonical_crop_count: number;
  evidence_records_count: number;
  directed_rotation_transitions_count: number;
  description: string;
  last_updated: string | null;
  notes: string | null;
}

export interface CropEvidenceRecord {
  evidence_id: string;
  crop_ids: string[];
  related_domain: string;
  attribute_or_claim: string;
  recorded_value_or_summary: string | null;
  source_organization: string;
  source_title: string;
  author_or_institution: string;
  publication_year: number | null;
  publication_date: string | null;
  access_date: string | null;
  source_url_or_doi: string | null;
  citation_location: string | null;
  exact_supporting_context: string | null;
  geographic_scope: string | null;
  variety_scope: string | null;
  source_quality: string;
  data_availability: string | null;
  conditions_and_assumptions: string | null;
  limitations: string | null;
}

export interface DirectedRotationTransition {
  preceding_crop_id: string;
  preceding_crop_name: string;
  following_crop_id: string;
  following_crop_name: string;
  compatibility_rating: string;
  is_monoculture: boolean;
  monoculture_risk: string | null;
  synergy_mechanisms: string | null;
  disease_break_potential: string | null;
  shared_pest_disease_risks: string | null;
  herbicide_carryover_risks: string | null;
  rotational_niche: string | null;
  evidence_ids: string[];
  limitations: string | null;
}

export interface CropProfileSummary {
  crop_id: string;
  cdl_code: number | null;
  common_name: string;
  scientific_name: string;
  botanical_family: string;
  crop_group: string;
  portfolio_role: string;
  lifecycle_class: string;
  is_cover_crop: boolean;
  can_serve_as_cover_crop: boolean;
  commercial_harvest_feasible: boolean;
  usda_plants_symbol: string | null;
}

export interface CropProfile {
  crop_id: string;
  cdl_code: number | null;
  common_name: string;
  scientific_name: string;
  taxonomic_authority: string | null;
  botanical_family: string;
  crop_group: string;
  portfolio_role: string;
  lifecycle_class: string;
  is_cover_crop: boolean;
  can_serve_as_cover_crop: boolean;
  commercial_harvest_feasible: boolean;
  usda_plants_symbol: string | null;
  crop_identity: { [key: string]: unknown };
  growing_duration: { [key: string]: unknown };
  temperature_requirements: { [key: string]: unknown };
  rainfall_requirements: { [key: string]: unknown };
  water_demand_and_tolerance: { [key: string]: unknown };
  soil_preferences: { [key: string]: unknown };
  root_and_nutrients: { [key: string]: unknown };
  nitrogen_and_biomass: { [key: string]: unknown };
  rotation_compatibility: { [key: string]: unknown };
  regional_suitability: { [key: string]: unknown }[];
  evidence_ids: string[];
}

