/**
 * HTTP implementations of the service interfaces against FastAPI /api/v1 (API_CONTRACTS §6).
 * Phase 1: compiled and selectable, but no backend exists yet — calls fail with a clear UPSTREAM_UNAVAILABLE.
 */
import type { Services } from "@/services/types";
import { request } from "./client";

export function createHttpServices(): Services {
  return {
    mode: "api",
    farms: {
      listFarms: () => request("GET", "/farms"),
      getFarm: (id) => request("GET", `/farms/${id}`),
      updateFarm: (id, patch) => request("PATCH", `/farms/${id}`, { body: patch }),
      getOverview: (id, seasonYear) => request("GET", `/farms/${id}/overview`, { query: { season_year: seasonYear } }),
    },
    fields: {
      listFields: (farmId, filter) => request("GET", `/farms/${farmId}/fields`, { query: { source: filter?.source, status: filter?.status } }),
      getField: (id) => request("GET", `/fields/${id}`),
      createField: (farmId, req) => request("POST", `/farms/${farmId}/fields`, { body: req }),
      deleteField: (id) => request("DELETE", `/fields/${id}`),
      getProfile: (id, seasonYear) => request("GET", `/fields/${id}/profile`, { query: { season_year: seasonYear } }),
      getCoverage: (id) => request("GET", `/fields/${id}/coverage`),
      getJob: (jobId) => request("GET", `/jobs/${jobId}`),
    },
    environment: {
      getClimate: (id, seasonYear, cropCode) => request("GET", `/fields/${id}/climate`, { query: { season_year: seasonYear, crop_code: cropCode } }),
      getSoil: (id) => request("GET", `/fields/${id}/soil`),
      getTerrain: (id) => request("GET", `/fields/${id}/terrain`),
      getVegetation: (id, year, index) => request("GET", `/fields/${id}/vegetation`, { query: { year, index } }),
      getIndicators: (id, opts) => request("GET", `/fields/${id}/indicators`, { query: { category: opts?.category, season_year: opts?.seasonYear } }),
    },
    rotation: {
      listCrops: () => request("GET", "/crops"),
      listCanonicalCrops: (params) => request("GET", "/canonical-crops", { query: params }),
      getCropProfile: (cropId) => request("GET", `/crops/${cropId}`),
      getCropAttributes: (cropId, params) => request("GET", `/crops/${cropId}/attributes`, { query: params }),
      getRotationCompatibility: (previousCrop, nextCrop) => request("GET", "/rotations", { query: { previous_crop: previousCrop, next_crop: nextCrop } }),
      listRotationMatrix: (cropId) => request("GET", "/rotations/matrix", { query: cropId !== undefined ? { crop_id: cropId } : undefined }),
      getCropEvidence: (evidenceId) => request("GET", `/evidence/${evidenceId}`),
      getKbMetadata: () => request("GET", "/kb/metadata"),
      getCropHistory: (id) => request("GET", `/fields/${id}/crop-history`),
      getRecommendation: (id, seasonYear) => request("GET", `/fields/${id}/recommendations`, { query: { season_year: seasonYear } }),
      listScenarios: (id) => request("GET", `/fields/${id}/scenarios`),
      createScenario: (id, req) => request("POST", `/fields/${id}/scenarios`, { body: req }),
      updateScenario: (scenarioId, req) => request("PUT", `/scenarios/${scenarioId}`, { body: req }),
      deleteScenario: (scenarioId) => request("DELETE", `/scenarios/${scenarioId}`),
      generateRotations: (fieldId, req) => request("POST", `/fields/${fieldId}/rotations/generate`, { body: req }),
      compareScenarios: (fieldId, req) => request("POST", `/fields/${fieldId}/rotations/compare`, { body: req }),
    },
    resilience: {
      getResilience: (id) => request("GET", `/fields/${id}/resilience`),
    },
    evidence: {
      listDatasets: () => request("GET", "/datasets"),
      listEvidence: (id, opts) => request("GET", `/fields/${id}/evidence`, { query: { kind: opts?.kind, related_id: opts?.relatedId } }),
    },
    suitability: {
      getFieldSuitability: (id, seasonYear) => request("GET", `/fields/${id}/suitability`, { query: { season_year: seasonYear } }),
      getCropSuitability: (id, cropId, seasonYear) => request("GET", `/fields/${id}/suitability/${cropId}`, { query: { season_year: seasonYear } }),
    },
  };
}
