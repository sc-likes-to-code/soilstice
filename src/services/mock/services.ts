/**
 * Mock implementations of the service interfaces (Phase 1). In-memory state; resets on reload.
 * Supports ?mock_error=<ApiErrorCode>[&mock_error_on=<method substring>] and ?mock_latency=<ms> (API_CONTRACTS §7).
 */
import type {
  ApiErrorCode, ApiResponse, CreateFieldResponse, EnvironmentalIndicator, FarmOverview, FieldSummary,
  ProcessingJob, QualityFlag, RotationScenario, UpsertScenarioRequest, UUID,
} from "@/types/contracts";
import { CONTRACT_VERSION } from "@/types/contracts";
import type { Services } from "@/services/types";
import { ApiError, API_ERROR_CODES } from "@/services/errors";
import { multiPolygonAreaHa, validateFieldDraft, centroidOfRing, type LngLat } from "@/lib/geo";
import { CROPS, DATASETS, DEMO_AS_OF, LATEST_CROP_YEAR, cropName, globalEvidence, q } from "./catalog";
import { AOI_BBOX, buildWorld, traitsForNewUserField, type MockFieldRecord, type World } from "./world";
import {
  climateProfile, coverage, cropHistory, evaluateScenario, fieldEvidence, recommendation, resilienceProfile,
  soilProfile, soilTerrainIndicators, terrainProfile, vegetationIndicators, vegetationProfile, bandFor,
} from "./generators";
import { createRng, round } from "./rng";

const DEFAULT_SEASON = LATEST_CROP_YEAR;

interface JobRecord { job: ProcessingJob; startedAt: number; }

interface Store {
  world: World;
  jobs: Map<UUID, JobRecord>;
  scenarios: Map<UUID, RotationScenario>;
  globalEvidence: ReturnType<typeof globalEvidence>;
  kbEvidence: Record<string, string>;
}

function createStore(): Store {
  const world = buildWorld();
  const ge = globalEvidence(world.uuid);
  const kbEvidence: Record<string, string> = {};
  ge.filter((e) => e.kind === "kb_rule").forEach((e) => (kbEvidence[e.related_ids[0]] = e.evidence_id));
  const store: Store = { world, jobs: new Map(), scenarios: new Map(), globalEvidence: ge, kbEvidence };
  // Seed: the pre-existing user field has a running job; first ready field has one example scenario.
  world.fields.filter((f) => f.traits.variant === "processing_user").forEach((rec) => startJob(store, rec, Date.now() - 2000));
  const first = world.fields.find((f) => f.traits.variant === "full");
  if (first) {
    const seq = [24, 4, 5, 24].map((c, i) => ({ year: LATEST_CROP_YEAR + 1 + i, crop_code: c, crop_name: cropName(c) }));
    const id = world.uuid();
    store.scenarios.set(id, {
      scenario_id: id, field_id: first.field.field_id, name: "Example: wheat → sorghum → soybeans", start_year: LATEST_CROP_YEAR + 1,
      sequence: seq, evaluation: evaluateScenario(first, seq), created_at: `${DEMO_AS_OF}T09:00:00Z`, updated_at: `${DEMO_AS_OF}T09:00:00Z`,
    });
  }
  return store;
}

const JOB_STEPS = ["nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "nasa_srtm_gl1", "nasa_hls_vi", "nasa_smap_spl4smgp"] as const;

function startJob(store: Store, rec: MockFieldRecord, startedAt = Date.now()): ProcessingJob {
  const job: ProcessingJob = {
    job_id: store.world.uuid(), field_id: rec.field.field_id, status: "queued",
    steps: JOB_STEPS.map((d) => ({ dataset_id: d, status: "queued", missing_reason: null, message: null })),
    created_at: new Date(startedAt).toISOString(), updated_at: new Date(startedAt).toISOString(),
  };
  store.jobs.set(job.job_id, { job, startedAt });
  rec.field.latest_job_id = job.job_id;
  return job;
}

/** Simulated progression: fast datasets finish in ~1.5 s each; satellite steps stay queued for the batch. */
function progressJob(store: Store, rec: JobRecord): ProcessingJob {
  const elapsed = Date.now() - rec.startedAt;
  const done = Math.floor(elapsed / 1500);
  const steps = rec.job.steps.map((s, i) => {
    if (i < 4) {
      if (i < done) return { ...s, status: "succeeded" as const, message: "Synthetic step completed." };
      if (i === done) return { ...s, status: "running" as const, message: "Synthetic step running…" };
      return s;
    }
    return done >= 4
      ? { ...s, status: "partial" as const, missing_reason: "PENDING_PROCESSING" as const, message: "Deferred to the satellite background batch (Phase 3)." }
      : s;
  });
  const status = done >= 4 ? "partial" : done > 0 || elapsed > 300 ? "running" : "queued";
  const job: ProcessingJob = { ...rec.job, steps, status, updated_at: new Date().toISOString() };
  rec.job = job;
  const field = store.world.fields.find((f) => f.field.field_id === job.field_id);
  if (field && field.field.processing_status === "processing" && status === "partial") field.field.processing_status = "partial";
  return job;
}

// ───────────── envelope, latency, simulated errors ─────────────
function mockParams(): { error: ApiErrorCode | null; errorOn: string | null; latency: number | null } {
  if (typeof window === "undefined") return { error: null, errorOn: null, latency: null };
  const p = new URLSearchParams(window.location.search);
  const e = p.get("mock_error");
  const l = p.get("mock_latency");
  return {
    error: e && (API_ERROR_CODES as readonly string[]).includes(e) ? (e as ApiErrorCode) : null,
    errorOn: p.get("mock_error_on"),
    latency: l && !Number.isNaN(Number(l)) ? Number(l) : null,
  };
}

let reqCounter = 0;
async function respond<T>(op: string, produce: () => T, warnings: QualityFlag[] = []): Promise<ApiResponse<T>> {
  const { error, errorOn, latency } = mockParams();
  const wait = latency ?? 180 + Math.random() * 420;
  await new Promise((r) => setTimeout(r, wait));
  const request_id = `mock-${(++reqCounter).toString(36)}-${Date.now().toString(36)}`;
  if (error && (!errorOn || op.toLowerCase().includes(errorOn.toLowerCase()))) {
    throw new ApiError(error, `Simulated ${error} for “${op}” (mock_error).`, { requestId: request_id });
  }
  const data = produce();
  return {
    data,
    meta: { request_id, generated_at: new Date().toISOString(), api_version: "v1", contract_version: CONTRACT_VERSION, data_mode: "synthetic", warnings },
  };
}

function notFound(what: string, id: string): never {
  throw new ApiError("NOT_FOUND", `${what} ${id} was not found.`, { retryable: false });
}

// ───────────── factory ─────────────
let store: Store | null = null;
function s(): Store {
  if (!store) store = createStore();
  return store;
}

function fieldRec(id: UUID): MockFieldRecord {
  return s().world.fields.find((f) => f.field.field_id === id) ?? notFound("Field", id);
}

function summary(rec: MockFieldRecord): FieldSummary {
  const last = rec.traits.history[rec.traits.history.length - 1];
  const res = resilienceProfile(rec, () => "summary");
  const jobDone = rec.field.processing_status !== "processing";
  return {
    field_id: rec.field.field_id, name: rec.field.name, centroid: rec.field.centroid, geometry: rec.field.geometry, area: rec.field.area,
    source: rec.field.source, processing_status: rec.field.processing_status,
    latest_crop: rec.field.source === "user" && !jobDone ? null : { year: LATEST_CROP_YEAR, crop_code: last, crop_name: cropName(last) },
    resilience_band: res.composite.band,
    coverage_completeness: coverage(rec, jobDone).completeness,
  };
}

function allIndicators(rec: MockFieldRecord, year: number): EnvironmentalIndicator[] {
  return [...climateProfile(rec, year).indicators, ...vegetationIndicators(rec, year), ...soilTerrainIndicators(rec), ...cropHistory(rec).metrics];
}

function validateScenario(req: UpsertScenarioRequest) {
  if (!req.name.trim()) throw new ApiError("VALIDATION_ERROR", "Scenario name is required.", { retryable: false, details: { field: "name" } });
  if (req.sequence.length < 2 || req.sequence.length > 8) throw new ApiError("VALIDATION_ERROR", "A scenario needs 2–8 years.", { retryable: false, details: { field: "sequence" } });
  const unknown = req.sequence.find((y) => !CROPS.some((c) => c.crop_code === y.crop_code));
  if (unknown) throw new ApiError("VALIDATION_ERROR", `Unknown crop code ${unknown.crop_code}.`, { retryable: false, details: { field: "crop_code" } });
}

export function createMockServices(): Services {
  return {
    mode: "mock",
    farms: {
      listFarms: () => respond("farms.listFarms", () => s().world.farms),
      getFarm: (id) => respond("farms.getFarm", () => s().world.farms.find((f) => f.farm_id === id) ?? notFound("Farm", id)),
      updateFarm: (id, patch) => respond("farms.updateFarm", () => {
        const farm = s().world.farms.find((f) => f.farm_id === id) ?? notFound("Farm", id);
        const name = patch.name.trim();
        if (!name || name.length > 80) throw new ApiError("VALIDATION_ERROR", "Farm name must be 1–80 characters.", { retryable: false });
        farm.name = name;
        farm.updated_at = new Date().toISOString();
        return farm;
      }),
      getOverview: (id, seasonYear = DEFAULT_SEASON) => respond("farms.getOverview", (): FarmOverview => {
        const farm = s().world.farms.find((f) => f.farm_id === id) ?? notFound("Farm", id);
        const recs = s().world.fields.filter((f) => f.field.farm_id === id);
        const fields = recs.map(summary);
        const covs = recs.map((r) => coverage(r, r.field.processing_status !== "processing"));
        const ids = covs[0]?.datasets.map((d) => d.dataset_id) ?? [];
        const coverage_summary = ids.filter((d) => covs[0].datasets.find((x) => x.dataset_id === d)?.priority === "P0").map((dataset_id) => ({
          dataset_id,
          fields_available: covs.filter((c) => ["available", "partial"].includes(c.datasets.find((x) => x.dataset_id === dataset_id)!.status)).length,
          fields_total: covs.filter((c) => c.datasets.find((x) => x.dataset_id === dataset_id)!.status !== "not_applicable").length,
        })).filter((c) => c.fields_total > 0);
        const alerts: QualityFlag[] = [];
        recs.forEach((r) => {
          const n = r.field.name;
          if (r.traits.variant === "cloudy") alerts.push({ code: "CLOUD_LIMITED", severity: "warning", message: `${n}: fewer than 6 clear HLS scenes in ${seasonYear}; vegetation phenology is limited.` });
          if (r.traits.variant === "insufficient") alerts.push({ code: "INSUFFICIENT_COMPONENTS", severity: "warning", message: `${n}: resilience composite withheld — only 3 of 5 components available.` });
          if (r.traits.variant === "failed") alerts.push({ code: "PROCESSING_FAILED", severity: "critical", message: `${n}: synthetic processing failure for terrain, climate and vegetation.` });
          if (r.field.processing_status === "processing") alerts.push({ code: "PROCESSING", severity: "info", message: `${n}: processing job in progress.` });
        });
        const ref = recs.find((r) => r.traits.variant === "full") ?? recs[0];
        const regional = ref ? climateProfile(ref, seasonYear).indicators.filter((i) => ["precip_anomaly_pct", "gdd_season", "sm_rootzone_percentile", "heat_stress_days"].includes(i.key)).map((i) => ({ ...i, indicator_id: `${farm.aoi.aoi_id}:${i.key}:${seasonYear}`, label: `${i.label} (AOI)` })) : [];
        return { farm, fields, coverage_summary, alerts, regional_context: regional };
      }),
    },
    fields: {
      listFields: (farmId, filter) => respond("fields.listFields", () =>
        s().world.fields.filter((f) => f.field.farm_id === farmId && (!filter?.source || f.field.source === filter.source) && (!filter?.status || f.field.processing_status === filter.status)).map(summary)),
      getField: (id) => respond("fields.getField", () => fieldRec(id).field),
      createField: (farmId, req) => respond("fields.createField", (): CreateFieldResponse => {
        const farm = s().world.farms.find((f) => f.farm_id === farmId) ?? notFound("Farm", farmId);
        const ring = req.geometry?.coordinates?.[0]?.[0] as LngLat[] | undefined;
        if (!req.name?.trim()) throw new ApiError("VALIDATION_ERROR", "Field name is required.", { retryable: false });
        if (!ring || ring.length < 4) throw new ApiError("GEOMETRY_INVALID", "Polygon needs at least three vertices.", { retryable: false });
        const check = validateFieldDraft(ring, AOI_BBOX[farm.aoi.aoi_id]);
        if (check.issues.includes("SELF_INTERSECTING") || check.issues.includes("TOO_FEW_VERTICES") || check.issues.includes("FIELD_TOO_SMALL")) throw new ApiError("GEOMETRY_INVALID", "Polygon is invalid (self-intersecting or too small).", { retryable: false });
        if (check.issues.includes("OUTSIDE_AOI")) throw new ApiError("OUTSIDE_AOI", `Field must lie inside ${farm.aoi.label}.`, { retryable: false });
        if (check.issues.includes("FIELD_TOO_LARGE")) throw new ApiError("FIELD_TOO_LARGE", `Field is ${round(check.areaHa, 1)} ha; the limit is 260 ha.`, { retryable: false });
        const id = s().world.uuid();
        const c = centroidOfRing(ring);
        const rec: MockFieldRecord = {
          field: {
            field_id: id, farm_id: farmId, name: req.name.trim(), geometry: req.geometry, centroid: [round(c[0], 5), round(c[1], 5)],
            area: q(round(multiPolygonAreaHa(req.geometry), 1), "ha"), state_fips: "20", county_fips: farm.aoi.county_fips[0].slice(2),
            source: "user", source_ref: null, csb_id: null, editable: true, processing_status: "processing", latest_job_id: null, created_at: new Date().toISOString(),
          },
          traits: traitsForNewUserField(farm.aoi.aoi_id, `${id}`),
        };
        s().world.fields.push(rec);
        farm.field_count += 1;
        farm.total_area = q(round((farm.total_area.value ?? 0) + (rec.field.area.value ?? 0), 1), "ha");
        const job = startJob(s(), rec);
        return { field: rec.field, job };
      }),
      deleteField: (id) => respond("fields.deleteField", () => {
        const rec = fieldRec(id);
        if (!rec.field.editable) throw new ApiError("NOT_EDITABLE", "Only user-drawn fields can be deleted.", { retryable: false });
        const w = s().world;
        w.fields = w.fields.filter((f) => f.field.field_id !== id);
        const farm = w.farms.find((f) => f.farm_id === rec.field.farm_id);
        if (farm) {
          farm.field_count -= 1;
          farm.total_area = q(round((farm.total_area.value ?? 0) - (rec.field.area.value ?? 0), 1), "ha");
        }
        return { deleted: true as const };
      }),
      getProfile: (id, seasonYear = DEFAULT_SEASON) => respond("fields.getProfile", () => {
        const rec = fieldRec(id);
        const v = rec.traits.variant;
        const jobDone = rec.field.processing_status !== "processing";
        const userPending = v === "processing_user" && !jobDone;
        const clim = climateProfile(rec, seasonYear);
        return {
          field: rec.field,
          coverage: coverage(rec, jobDone),
          soil: userPending ? null : soilProfile(rec),
          terrain: userPending ? null : terrainProfile(rec),
          crop_history: userPending ? null : cropHistory(rec),
          climate_summary: v === "failed" ? [] : clim.indicators.filter((i) => ["precip_total_season", "precip_anomaly_pct", "gdd_season", "sm_rootzone_percentile"].includes(i.key)),
          vegetation_summary: vegetationIndicators(rec, seasonYear).filter((i) => i.key === "ndvi_peak" || i.key === "ndvi_peak_doy"),
          resilience: resilienceProfile(rec, s().world.uuid),
        };
      }),
      getCoverage: (id) => respond("fields.getCoverage", () => { const r = fieldRec(id); return coverage(r, r.field.processing_status !== "processing"); }),
      getJob: (jobId) => respond("fields.getJob", () => {
        const rec = s().jobs.get(jobId) ?? notFound("Job", jobId);
        return progressJob(s(), rec);
      }),
    },
    environment: {
      getClimate: (id, seasonYear) => respond("environment.getClimate", () => climateProfile(fieldRec(id), seasonYear)),
      getSoil: (id) => respond("environment.getSoil", () => soilProfile(fieldRec(id))),
      getTerrain: (id) => respond("environment.getTerrain", () => terrainProfile(fieldRec(id)) ?? notFound("Terrain for field", id)),
      getVegetation: (id, year, index = "NDVI") => respond("environment.getVegetation", () => vegetationProfile(fieldRec(id), year, index)),
      getIndicators: (id, opts) => respond("environment.getIndicators", () => {
        const all = allIndicators(fieldRec(id), opts?.seasonYear ?? DEFAULT_SEASON);
        return opts?.category ? all.filter((i) => i.category === opts.category) : all;
      }),
    },
    rotation: {
      listCrops: () => respond("rotation.listCrops", () => CROPS),
      listCanonicalCrops: () => respond("rotation.listCanonicalCrops", () => [
        { crop_id: "CRP001", cdl_code: 1, common_name: "Corn (Maize)", scientific_name: "Zea mays L.", botanical_family: "Poaceae", crop_group: "Cereal", portfolio_role: "primary_commercial", lifecycle_class: "Annual", is_cover_crop: false, can_serve_as_cover_crop: false, commercial_harvest_feasible: true, usda_plants_symbol: "ZEMA" },
        { crop_id: "CRP002", cdl_code: 5, common_name: "Soybean", scientific_name: "Glycine max (L.) Merr.", botanical_family: "Fabaceae", crop_group: "Legume", portfolio_role: "primary_commercial", lifecycle_class: "Annual", is_cover_crop: false, can_serve_as_cover_crop: false, commercial_harvest_feasible: true, usda_plants_symbol: "GLMA4" },
        { crop_id: "CRP003", cdl_code: 24, common_name: "Winter Wheat", scientific_name: "Triticum aestivum L.", botanical_family: "Poaceae", crop_group: "Cereal", portfolio_role: "primary_commercial", lifecycle_class: "Annual", is_cover_crop: false, can_serve_as_cover_crop: false, commercial_harvest_feasible: true, usda_plants_symbol: "TRAE" },
      ]),
      getCropProfile: (cropId) => respond("rotation.getCropProfile", () => ({
        crop_id: String(cropId), cdl_code: 1, common_name: "Corn (Maize)", scientific_name: "Zea mays L.", taxonomic_authority: "L.", botanical_family: "Poaceae", crop_group: "Cereal", portfolio_role: "primary_commercial", lifecycle_class: "Annual", is_cover_crop: false, can_serve_as_cover_crop: false, commercial_harvest_feasible: true, usda_plants_symbol: "ZEMA",
        crop_identity: {}, growing_duration: {}, temperature_requirements: {}, rainfall_requirements: {}, water_demand_and_tolerance: {}, soil_preferences: {}, root_and_nutrients: {}, nitrogen_and_biomass: {}, rotation_compatibility: {}, regional_suitability: [], evidence_ids: ["EV0001", "EV0003"],
      })),
      getCropAttributes: () => respond("rotation.getCropAttributes", () => ({})),
      getRotationCompatibility: (previousCrop, nextCrop) => respond("rotation.getRotationCompatibility", () => ({
        preceding_crop_id: String(previousCrop), preceding_crop_name: "Preceding", following_crop_id: String(nextCrop), following_crop_name: "Following", compatibility_rating: "compatible", is_monoculture: false, monoculture_risk: null, synergy_mechanisms: "Standard rotation synergy", disease_break_potential: null, shared_pest_disease_risks: null, herbicide_carryover_risks: null, rotational_niche: null, evidence_ids: [], limitations: null,
      })),
      listRotationMatrix: () => respond("rotation.listRotationMatrix", () => []),
      getCropEvidence: (evidenceId) => respond("rotation.getCropEvidence", () => ({
        evidence_id: evidenceId, crop_ids: ["CRP001"], related_domain: "crop_identity", attribute_or_claim: "Mock Evidence", recorded_value_or_summary: "Mock summary", source_organization: "USDA", source_title: "Mock Title", author_or_institution: "USDA", publication_year: 2026, publication_date: null, access_date: "2026-11-14", source_url_or_doi: null, citation_location: null, exact_supporting_context: null, geographic_scope: "CONUS", variety_scope: null, source_quality: "high", data_availability: "Available", conditions_and_assumptions: null, limitations: null,
      })),
      getKbMetadata: () => respond("rotation.getKbMetadata", () => ({
        dataset_name: "SOILSTICE Backend Crop Knowledge Base", schema_version: "1.4.1-REMEDIATED", stage: "Production", effective_date: "2026-11-14", geographic_scope: "CONUS", canonical_crop_count: 14, evidence_records_count: 212, directed_rotation_transitions_count: 196, description: "Canonical Crop KB", last_updated: null, notes: null,
      })),
      getCropHistory: (id) => respond("rotation.getCropHistory", () => cropHistory(fieldRec(id))),
      getRecommendation: (id, seasonYear) => respond("rotation.getRecommendation", () => recommendation(fieldRec(id), seasonYear, s().world.uuid, s().kbEvidence)),
      listScenarios: (id) => respond("rotation.listScenarios", () => { fieldRec(id); return [...s().scenarios.values()].filter((x) => x.field_id === id).sort((a, b) => a.created_at.localeCompare(b.created_at)); }),
      createScenario: (id, req) => respond("rotation.createScenario", () => {
        const rec = fieldRec(id);
        validateScenario(req);
        const seq = req.sequence.map((y) => ({ ...y, crop_name: cropName(y.crop_code) }));
        const now = new Date().toISOString();
        const sc: RotationScenario = { scenario_id: s().world.uuid(), field_id: id, name: req.name.trim(), start_year: req.start_year, sequence: seq, evaluation: evaluateScenario(rec, seq), created_at: now, updated_at: now };
        s().scenarios.set(sc.scenario_id, sc);
        return sc;
      }),
      updateScenario: (scenarioId, req) => respond("rotation.updateScenario", () => {
        const existing = s().scenarios.get(scenarioId) ?? notFound("Scenario", scenarioId);
        validateScenario(req);
        const seq = req.sequence.map((y) => ({ ...y, crop_name: cropName(y.crop_code) }));
        const sc: RotationScenario = { ...existing, name: req.name.trim(), start_year: req.start_year, sequence: seq, evaluation: evaluateScenario(fieldRec(existing.field_id), seq), updated_at: new Date().toISOString() };
        s().scenarios.set(scenarioId, sc);
        return sc;
      }),
      deleteScenario: (scenarioId) => respond("rotation.deleteScenario", () => {
        if (!s().scenarios.delete(scenarioId)) notFound("Scenario", scenarioId);
        return { deleted: true as const };
      }),
    },
    resilience: {
      getResilience: (id) => respond("resilience.getResilience", () => resilienceProfile(fieldRec(id), s().world.uuid)),
    },
    evidence: {
      listDatasets: () => respond("evidence.listDatasets", () => DATASETS),
      listEvidence: (id, opts) => respond("evidence.listEvidence", () => {
        const rec = fieldRec(id);
        const items = [...s().globalEvidence, ...fieldEvidence(rec, allIndicators(rec, DEFAULT_SEASON), createRng(`${id}:ev`).uuid)];
        return items.filter((e) => (!opts?.kind || e.kind === opts.kind) && (!opts?.relatedId || e.related_ids.includes(opts.relatedId)));
      }),
    },
  };
}

/** Exposed for tests only. */
export const __test = { createStore, bandFor };
