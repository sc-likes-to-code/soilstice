/**
 * Contract fixture export (API_CONTRACTS §8 rule 7): every mock-service response is collected so the backend can
 * validate it against the Pydantic models (backend/tests/test_frontend_fixtures.py).
 * Writes files only when EXPORT_FIXTURES_DIR is set (npm run contract:fixtures); otherwise it just asserts that the
 * collection succeeds. All payloads are SYNTHETIC (meta.data_mode "synthetic").
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createMockServices } from "./services";
import { rectangleFromMetres } from "@/lib/geo";

type Fixture = { name: string; model: string; list: boolean; payload: unknown };

describe("mock fixture export", () => {
  it("collects every endpoint response for every synthetic field", async () => {
    (globalThis as unknown as { window: { location: { search: string } } }).window = { location: { search: "?mock_latency=0" } };
    const svc = createMockServices();
    const out: Fixture[] = [];
    const add = (name: string, model: string, list: boolean, payload: unknown) => out.push({ name, model, list, payload });

    add("datasets", "DatasetDescriptor", true, await svc.evidence.listDatasets());
    add("crops", "CropOption", true, await svc.rotation.listCrops());
    const farms = await svc.farms.listFarms();
    add("farms", "Farm", true, farms);
    for (const farm of farms.data) {
      add(`farm_${farm.aoi.aoi_id}`, "Farm", false, await svc.farms.getFarm(farm.farm_id));
      add(`overview_${farm.aoi.aoi_id}`, "FarmOverview", false, await svc.farms.getOverview(farm.farm_id));
      const fields = await svc.fields.listFields(farm.farm_id);
      add(`fields_${farm.aoi.aoi_id}`, "FieldSummary", true, fields);
      for (const f of fields.data) {
        const id = f.field_id;
        add(`field_${id}`, "Field", false, await svc.fields.getField(id));
        add(`profile_${id}`, "FieldProfile", false, await svc.fields.getProfile(id));
        add(`coverage_${id}`, "DataCoverage", false, await svc.fields.getCoverage(id));
        add(`climate_${id}`, "ClimateProfile", false, await svc.environment.getClimate(id, 2025));
        add(`soil_${id}`, "SoilProfile", false, await svc.environment.getSoil(id));
        add(`terrain_${id}`, "TerrainProfile", false, await svc.environment.getTerrain(id));
        add(`vegetation_${id}`, "VegetationProfile", false, await svc.environment.getVegetation(id, 2025));
        add(`indicators_${id}`, "EnvironmentalIndicator", true, await svc.environment.getIndicators(id));
        add(`history_${id}`, "CropHistory", false, await svc.rotation.getCropHistory(id));
        add(`resilience_${id}`, "ResilienceProfile", false, await svc.resilience.getResilience(id));
        add(`recommendation_${id}`, "RotationRecommendation", false, await svc.rotation.getRecommendation(id, 2026));
        add(`scenarios_${id}`, "RotationScenario", true, await svc.rotation.listScenarios(id));
        add(`evidence_${id}`, "EvidenceItem", true, await svc.evidence.listEvidence(id));
      }
    }
    const reno = farms.data.find((f) => f.aoi.aoi_id === "ks_reno")!;
    const created = await svc.fields.createField(reno.farm_id, {
      name: "Fixture field",
      geometry: rectangleFromMetres([-98.1, 37.9], 400, 400),
    });
    add("create_field", "CreateFieldResponse", false, created);
    add("job", "ProcessingJob", false, await svc.fields.getJob(created.data.job.job_id));
    const fieldId = created.data.field.field_id;
    const scenario = await svc.rotation.createScenario(fieldId, {
      name: "Fixture scenario", start_year: 2026, sequence: [{ year: 2026, crop_code: 24 }, { year: 2027, crop_code: 4 }],
    });
    add("scenario", "RotationScenario", false, scenario);

    expect(out.length).toBeGreaterThan(20);
    const dir = process.env.EXPORT_FIXTURES_DIR;
    if (dir) {
      mkdirSync(dir, { recursive: true });
      for (const fx of out) writeFileSync(join(dir, `${fx.name}.json`), JSON.stringify(fx, null, 1));
    }
  });
});
