/**
 * Mock catalog. Dataset descriptors are REAL metadata copied from docs/DATASET_SOURCE_REGISTER.md
 * (they describe datasets, not observations — permitted by UI_ARCHITECTURE §4.7).
 * Every observation-like value elsewhere is synthetic and carries dataset_id "synthetic".
 */
import type {
  CropCode, CropOption, DatasetDescriptor, DatasetId, EvidenceItem, MethodRef, Quantity, QualityInfo,
  SourceRef, SpatialSupport, TemporalSupport, Unit, MissingReason,
} from "@/types/contracts";

export const DEMO_AS_OF = "2026-11-01";
export const LATEST_CROP_YEAR = 2025;
export const KB_VERSION = "synthetic-kb-0";
export const ENGINE_VERSION = "synthetic-engine-0";
export const RESILIENCE_MODEL = "soilstice-resilience-0.0.0-synthetic";

export const DATASETS: DatasetDescriptor[] = [
  d("nasa_power_daily_ag", "NASA POWER Daily (AG community)", "NASA LaRC", "POWER Daily API", "v2.10.3", "P0", "R", 55000, "P1D", "1981-01-01", null, "https://power.larc.nasa.gov/docs/services/api/temporal/daily/", null, "LIVE"),
  d("usda_nrcs_ssurgo_sda", "SSURGO via Soil Data Access", "USDA NRCS", "SSURGO (SDA)", "live database", "P0", "F", null, "static", null, null, "https://sdmdataaccess.sc.egov.usda.gov/", null, "LIVE"),
  d("usda_nass_cdl", "Cropland Data Layer (CropScape)", "USDA NASS", "CDL", "2006–2025 (KS)", "P0", "F", 30, "P1Y", "2006-01-01", "2025-12-31", "https://nassgeodata.gmu.edu/CropScape/devhelp/getexamples.html", null, "LIVE"),
  d("usda_nass_csb", "Crop Sequence Boundaries", "USDA NASS", "CSB 2018–2025 rev23", "rev23", "P0", "F", null, "P1Y", "2018-01-01", "2025-12-31", "https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries", null, "DOC"),
  d("nasa_hls_vi", "HLS Vegetation Indices (L30/S30)", "NASA LP DAAC", "HLSL30_VI / HLSS30_VI", "2.0", "P0", "F", 30, "irregular", "2013-04-11", null, "https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-vi-2.0", "10.5067/HLS/HLSL30_VI.002", "LIVE"),
  d("nasa_hls", "HLS Surface Reflectance (L30/S30)", "NASA LP DAAC", "HLSL30 / HLSS30", "2.0", "P0", "F", 30, "irregular", "2013-04-11", null, "https://www.earthdata.nasa.gov/data/projects/hls", null, "CMR"),
  d("nasa_smap_spl4smgp", "SMAP L4 Surface & Root-Zone Soil Moisture", "NASA NSIDC DAAC", "SPL4SMGP", "008", "P0", "R", 9000, "PT3H", "2015-03-31", null, "https://nsidc.org/data/spl4smgp", null, "CMR"),
  d("nasa_srtm_gl1", "SRTM Global 1 arc-second", "NASA LP DAAC", "SRTMGL1", "003", "P0", "F", 30, "static", "2000-02-11", "2000-02-21", "https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003", "10.5067/MEaSUREs/SRTM/SRTMGL1.003", "CMR"),
  d("prism_daily", "PRISM daily climate", "PRISM Group, Oregon State University", "PRISM daily (4 km / 800 m)", "post-2025-10 COG", "P1", "S", 4000, "P1D", "1981-01-01", null, "https://prism.oregonstate.edu/", null, "LIVE"),
  d("openet", "OpenET Ensemble ET", "OpenET consortium", "OpenET Collection", "2.1", "P1", "F", 30, "P1M", "2000-01-01", null, "https://openet.gitbook.io/docs", null, "DOC"),
  d("usda_nass_quickstats", "NASS Quick Stats", "USDA NASS", "Quick Stats API", "api_GET", "P1", "R", null, "P1Y", null, null, "https://quickstats.nass.usda.gov/api", null, "LIVE"),
  d("nasa_smap_spl3smp_e", "SMAP L3 Enhanced Soil Moisture", "NASA NSIDC DAAC", "SPL3SMP_E", "006", "P1", "R", 9000, "P1D", "2015-03-31", null, "https://nsidc.org/data/SPL3SMP_E", null, "CMR"),
  d("nasa_gpm_imerg", "GPM IMERG Final daily", "NASA GES DISC", "GPM_3IMERGDF", "07", "P2", "R", 11000, "P1D", "1998-01-01", "2025-09-30", "https://catalog.data.gov/dataset/gpm-imerg-final-precipitation-l3-1-day-0-1-degree-x-0-1-degree-v07-gpm-3imergdf-at-ges-dis-f1669", null, "CMR"),
  d("fao_gaez_v5", "FAO GAEZ v5 crop suitability", "FAO + IIASA", "GAEZ v5", "v5", "P2", "R", 1000, "static", null, null, "https://www.fao.org/gaez/en/", null, "DOC"),
];

function d(
  dataset_id: DatasetId, title: string, publisher: string, product: string, product_version: string,
  priority: "P0" | "P1" | "P2", support_class: "F" | "S" | "R", native_resolution_m: number | null,
  temporal_resolution: DatasetDescriptor["temporal_resolution"], start: string | null, end: string | null,
  documentation_url: string, doi: string | null, verification_status: DatasetDescriptor["verification_status"],
): DatasetDescriptor {
  return {
    dataset_id, title, publisher, product, product_version, priority, support_class, native_resolution_m,
    temporal_resolution, temporal_coverage: { start, end }, documentation_url, doi, verification_status,
    last_verified: "2026-11-14", integration_status: "planned",
  };
}

export function descriptor(id: DatasetId): DatasetDescriptor {
  const found = DATASETS.find((x) => x.dataset_id === id);
  if (!found) throw new Error(`Unknown dataset ${id}`);
  return found;
}

/** Crop catalog — codes are the CDL legend; names per CDL. Families are presentation groupings. */
export const CROPS: CropOption[] = [
  { crop_code: 24, name: "Winter Wheat", family: "Cereal (cool season)", is_double_crop: false, kb_version: KB_VERSION },
  { crop_code: 1, name: "Corn", family: "Cereal (warm season)", is_double_crop: false, kb_version: KB_VERSION },
  { crop_code: 4, name: "Sorghum", family: "Cereal (warm season)", is_double_crop: false, kb_version: KB_VERSION },
  { crop_code: 5, name: "Soybeans", family: "Legume", is_double_crop: false, kb_version: KB_VERSION },
  { crop_code: 36, name: "Alfalfa", family: "Legume (perennial forage)", is_double_crop: false, kb_version: KB_VERSION },
  { crop_code: 26, name: "Dbl Crop WinWht/Soybeans", family: "Double crop", is_double_crop: true, kb_version: KB_VERSION },
  { crop_code: 236, name: "Dbl Crop WinWht/Sorghum", family: "Double crop", is_double_crop: true, kb_version: KB_VERSION },
  { crop_code: 61, name: "Fallow/Idle Cropland", family: "Fallow", is_double_crop: false, kb_version: KB_VERSION },
];

export function cropName(code: CropCode): string {
  return CROPS.find((c) => c.crop_code === code)?.name ?? `CDL class ${code}`;
}

/** Synthetic SourceRef that names the real product it stands in for (rule R6). */
export function synthSource(standsFor: DatasetId): SourceRef {
  const desc = DATASETS.find((x) => x.dataset_id === standsFor);
  return {
    dataset_id: "synthetic",
    product: `Synthetic stand-in for ${desc ? desc.product : standsFor}`,
    product_version: "synthetic-0",
    acquisition_id: null,
    doi: null,
    documentation_url: desc?.documentation_url ?? null,
    retrieved_at: null,
  };
}

export function spatialFor(id: DatasetId, overrides?: Partial<SpatialSupport>): SpatialSupport {
  const base: Record<string, SpatialSupport> = {
    nasa_power_daily_ag: { support_class: "R", native_resolution_m: 55000, extraction_method: "api_point_query", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:4326" },
    nasa_smap_spl4smgp: { support_class: "R", native_resolution_m: 9000, extraction_method: "containing_cell", field_fraction_of_cell: 0.008, cell_id: "synthetic-cell", crs: "EPSG:6933" },
    usda_nrcs_ssurgo_sda: { support_class: "F", native_resolution_m: null, extraction_method: "vector_intersection", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:4326" },
    usda_nass_cdl: { support_class: "F", native_resolution_m: 30, extraction_method: "zonal_polygon_inward_buffer", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:5070" },
    nasa_hls_vi: { support_class: "F", native_resolution_m: 30, extraction_method: "zonal_polygon_inward_buffer", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:32614" },
    nasa_srtm_gl1: { support_class: "F", native_resolution_m: 30, extraction_method: "zonal_polygon", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:4326" },
    openet: { support_class: "F", native_resolution_m: 30, extraction_method: "zonal_polygon", field_fraction_of_cell: null, cell_id: null, crs: null },
    soilstice_derived: { support_class: "F", native_resolution_m: null, extraction_method: "not_applicable", field_fraction_of_cell: null, cell_id: null, crs: null },
  };
  return { ...(base[id] ?? base.soilstice_derived), ...overrides };
}

export function q(value: number | null, unit: Unit, opts?: { low?: number; high?: number; reason?: MissingReason; note?: string }): Quantity {
  if (value === null) return { value: null, unit, uncertainty: null, missing_reason: opts?.reason ?? "NOT_COMPUTED" };
  const hasRange = opts?.low !== undefined && opts?.high !== undefined;
  return {
    value,
    unit,
    uncertainty: hasRange ? { kind: "range", low: opts!.low!, high: opts!.high!, value: null, note: opts?.note ?? null } : null,
    missing_reason: null,
  };
}

export function missing(unit: Unit, reason: MissingReason): Quantity {
  return { value: null, unit, uncertainty: null, missing_reason: reason };
}

export const validQuality = (completeness = 1): QualityInfo => ({ status: "valid", flags: [], completeness, missing_reason: null });

export function temporal(resolution: TemporalSupport["resolution"], start: string | null, end: string | null, aggregation: TemporalSupport["aggregation"], ts: TemporalSupport["time_standard"] = "not_applicable"): TemporalSupport {
  return { resolution, period_start: start, period_end: end, aggregation, time_standard: ts };
}

export function method(method_id: string, name: string, description: string, reference_url: string | null = null): MethodRef {
  return { method_id, name, version: "synthetic-0", description, reference_url };
}

export const PENDING_KB_REQUIREMENT = "Threshold pending a cited crop knowledge-base entry (Phase 5).";

/** Global evidence items (field_id null). Dataset items carry real metadata; methods point to Phase 0 docs. */
export function globalEvidence(uuid: () => string): EvidenceItem[] {
  const datasetItems: EvidenceItem[] = DATASETS.map((ds) => ({
    evidence_id: uuid(),
    kind: "dataset",
    title: ds.title,
    summary: `${ds.publisher} · ${ds.product} v${ds.product_version} · ${ds.priority} · support ${ds.support_class}. Not yet integrated (Phase 3).`,
    field_id: null,
    dataset_id: ds.dataset_id,
    product_version: ds.product_version,
    citation: `${ds.publisher}. ${ds.title} (${ds.product}, version ${ds.product_version}).`,
    url: ds.documentation_url,
    doi: ds.doi,
    accessed_at: ds.last_verified,
    verification_status: ds.verification_status,
    spatial: null,
    temporal: null,
    related_ids: [ds.dataset_id],
  }));
  const methods: [string, string, string][] = [
    ["ssurgo_area_comppct_weighting", "SSURGO area × component-percent weighting", "Normative soil aggregation: major components, fixed depth intervals 0–30/30–100/100–150 cm, AWS from muaggatt. See SOILSTICE_DATA_ARCHITECTURE §5.3.1."],
    ["resilience_framework", "Field resilience framework", "Five components, absolute breakpoints (set in Phase 4), equal-weight composite when ≥4 of 5 components exist, confidence from support class. See SOILSTICE_DATA_ARCHITECTURE §5.10."],
    ["rotation_limiting_factor", "Rotation recommendation: limiting-factor method", "Each factor classed suitable/marginal/unsuitable against cited KB thresholds; worst factor wins; regional factors cannot exceed 'marginal'. See SOILSTICE_DATA_ARCHITECTURE §5.11."],
    ["hls_fmask_policy", "HLS Fmask cloud-masking policy", "Bits 1–3 (cloud, adjacent, shadow) masked; bits 4–5 pending confirmation (Test H-5); scenes accepted at ≥70% clear field pixels."],
    ["support_classes", "Field vs regional support classes", "F = field-resolved (≤100 m), S = sub-regional (≤5 km), R = regional context (>5 km). Coarse grids are never resampled to field pixels."],
  ];
  const methodItems: EvidenceItem[] = methods.map(([id, title, summary]) => ({
    evidence_id: uuid(), kind: "method", title, summary, field_id: null, dataset_id: "soilstice_derived",
    product_version: "phase0", citation: "SOILSTICE Phase 0 architecture documents (2026-11-14).", url: null, doi: null,
    accessed_at: "2026-11-14", verification_status: "DOC", spatial: null, temporal: null, related_ids: [id],
  }));
  const kbItems: EvidenceItem[] = ["ph", "drainage", "water_holding", "gdd", "slope", "rotation_history", "regional_climate"].map((factor) => ({
    evidence_id: uuid(), kind: "kb_rule", title: `Crop KB rule: ${factor.replace("_", " ")}`,
    summary: "Placeholder rule. The cited threshold will be added to the crop knowledge base in Phase 5; until then no agronomic claim is made.",
    field_id: null, dataset_id: null, product_version: KB_VERSION, citation: null, url: null, doi: null, accessed_at: null,
    verification_status: "UNVERIFIED", spatial: null, temporal: null, related_ids: [factor],
  }));
  return [...datasetItems, ...methodItems, ...kbItems];
}
