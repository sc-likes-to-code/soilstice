"use client";
/**
 * Data hooks over the service interfaces (UI_ARCHITECTURE §5). Pages call these; components receive contract types as props.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDataMode, getServices } from "@/services";
import type { CompareScenariosRequest, CreateFieldRequest, CropCode, EvidenceKind, GenerateRotationsRequest, IndicatorCategory, UpsertScenarioRequest, UUID, VegetationIndex } from "@/types/contracts";

const svc = () => getServices();

export const qk = {
  farms: () => [getDataMode(), "farms"] as const,
  overview: (farmId: UUID, season?: number) => [getDataMode(), "farm", farmId, "overview", season] as const,
  fields: (farmId: UUID) => [getDataMode(), "farm", farmId, "fields"] as const,
  field: (id: UUID) => [getDataMode(), "field", id] as const,
  profile: (id: UUID, season?: number) => [getDataMode(), "field", id, "profile", season] as const,
  coverage: (id: UUID) => [getDataMode(), "field", id, "coverage"] as const,
  climate: (id: UUID, season: number) => [getDataMode(), "field", id, "climate", season] as const,
  soil: (id: UUID) => [getDataMode(), "field", id, "soil"] as const,
  terrain: (id: UUID) => [getDataMode(), "field", id, "terrain"] as const,
  vegetation: (id: UUID, year: number, index: VegetationIndex) => [getDataMode(), "field", id, "vegetation", year, index] as const,
  indicators: (id: UUID, category?: IndicatorCategory, season?: number) => [getDataMode(), "field", id, "indicators", category, season] as const,
  cropHistory: (id: UUID) => [getDataMode(), "field", id, "crop-history"] as const,
  recommendation: (id: UUID, season: number) => [getDataMode(), "field", id, "recommendation", season] as const,
  scenarios: (id: UUID) => [getDataMode(), "field", id, "scenarios"] as const,
  resilience: (id: UUID) => [getDataMode(), "field", id, "resilience"] as const,
  suitability: (id: UUID, season?: number) => [getDataMode(), "field", id, "suitability", season] as const,
  cropSuitability: (id: UUID, cropId: string, season?: number) => [getDataMode(), "field", id, "cropSuitability", cropId, season] as const,
  evidence: (id: UUID, kind?: EvidenceKind, related?: string) => [getDataMode(), "field", id, "evidence", kind, related] as const,
  datasets: () => [getDataMode(), "datasets"] as const,
  crops: () => [getDataMode(), "crops"] as const,
  job: (id: UUID) => [getDataMode(), "job", id] as const,
};

export const useFarms = () => useQuery({ queryKey: qk.farms(), queryFn: () => svc().farms.listFarms() });
export const useFarmOverview = (farmId: UUID | null, season?: number) =>
  useQuery({ queryKey: qk.overview(farmId ?? "", season), queryFn: () => svc().farms.getOverview(farmId!, season), enabled: !!farmId, placeholderData: keepPreviousData });
export const useFields = (farmId: UUID | null) =>
  useQuery({ queryKey: qk.fields(farmId ?? ""), queryFn: () => svc().fields.listFields(farmId!), enabled: !!farmId });
export const useField = (id: UUID) => useQuery({ queryKey: qk.field(id), queryFn: () => svc().fields.getField(id) });
export const useFieldProfile = (id: UUID, season?: number) =>
  useQuery({ queryKey: qk.profile(id, season), queryFn: () => svc().fields.getProfile(id, season), placeholderData: keepPreviousData });
export const useCoverage = (id: UUID) => useQuery({ queryKey: qk.coverage(id), queryFn: () => svc().fields.getCoverage(id) });
export const useClimate = (id: UUID, season: number, cropCode?: CropCode) =>
  useQuery({ queryKey: qk.climate(id, season), queryFn: () => svc().environment.getClimate(id, season, cropCode), placeholderData: keepPreviousData });
export const useSoil = (id: UUID) => useQuery({ queryKey: qk.soil(id), queryFn: () => svc().environment.getSoil(id) });
export const useTerrain = (id: UUID) => useQuery({ queryKey: qk.terrain(id), queryFn: () => svc().environment.getTerrain(id), retry: false });
export const useVegetation = (id: UUID, year: number, index: VegetationIndex) =>
  useQuery({ queryKey: qk.vegetation(id, year, index), queryFn: () => svc().environment.getVegetation(id, year, index), placeholderData: keepPreviousData });
export const useIndicators = (id: UUID, category?: IndicatorCategory, season?: number) =>
  useQuery({ queryKey: qk.indicators(id, category, season), queryFn: () => svc().environment.getIndicators(id, { category, seasonYear: season }) });
export const useCropHistory = (id: UUID) => useQuery({ queryKey: qk.cropHistory(id), queryFn: () => svc().rotation.getCropHistory(id) });
export const useRecommendation = (id: UUID, season: number) =>
  useQuery({ queryKey: qk.recommendation(id, season), queryFn: () => svc().rotation.getRecommendation(id, season) });
export const useScenarios = (id: UUID) => useQuery({ queryKey: qk.scenarios(id), queryFn: () => svc().rotation.listScenarios(id) });
export const useCrops = () => useQuery({ queryKey: qk.crops(), queryFn: () => svc().rotation.listCrops(), staleTime: Infinity });
export const useResilience = (id: UUID) => useQuery({ queryKey: qk.resilience(id), queryFn: () => svc().resilience.getResilience(id) });
export const useFieldSuitability = (id: UUID, season?: number) =>
  useQuery({ queryKey: qk.suitability(id, season), queryFn: () => svc().suitability.getFieldSuitability(id, season), placeholderData: keepPreviousData });
export const useCropSuitability = (id: UUID, cropId: string, season?: number) =>
  useQuery({ queryKey: qk.cropSuitability(id, cropId, season), queryFn: () => svc().suitability.getCropSuitability(id, cropId, season), placeholderData: keepPreviousData });
export const useEvidence = (id: UUID | null, kind?: EvidenceKind, related?: string) =>
  useQuery({ queryKey: qk.evidence(id ?? "", kind, related), queryFn: () => svc().evidence.listEvidence(id!, { kind, relatedId: related }), enabled: !!id });
export const useDatasets = () => useQuery({ queryKey: qk.datasets(), queryFn: () => svc().evidence.listDatasets(), staleTime: Infinity });

export const useJob = (jobId: UUID | null) =>
  useQuery({
    queryKey: qk.job(jobId ?? ""),
    queryFn: () => svc().fields.getJob(jobId!),
    enabled: !!jobId,
    // Poll every 3 s while running; stop on a terminal status (UI_ARCHITECTURE §3.4).
    refetchInterval: (query) => {
      const s = query.state.data?.data.status;
      return s === "queued" || s === "running" ? 3000 : false;
    },
  });

export function useCreateScenario(fieldId: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: UpsertScenarioRequest) => svc().rotation.createScenario(fieldId, req),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.scenarios(fieldId) }),
  });
}
export function useUpdateScenario(fieldId: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, req }: { id: UUID; req: UpsertScenarioRequest }) => svc().rotation.updateScenario(id, req),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.scenarios(fieldId) }),
  });
}
export function useDeleteScenario(fieldId: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => svc().rotation.deleteScenario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.scenarios(fieldId) }),
  });
}
export function useGenerateRotations(fieldId: UUID) {
  return useMutation({
    mutationFn: (req: GenerateRotationsRequest) => svc().rotation.generateRotations(fieldId, req),
  });
}
export function useCompareScenarios(fieldId: UUID) {
  return useMutation({
    mutationFn: (req: CompareScenariosRequest) => svc().rotation.compareScenarios(fieldId, req),
  });
}
export function useUpdateFarm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: UUID; name: string }) => svc().farms.updateFarm(id, { name }),
    onSuccess: () => qc.invalidateQueries(),
  });
}
export function useCreateField(farmId: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: CreateFieldRequest) => svc().fields.createField(farmId, req),
    onSuccess: () => qc.invalidateQueries(),
  });
}
export function useDeleteField() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => svc().fields.deleteField(id),
    onSuccess: () => qc.invalidateQueries(),
  });
}
