/**
 * Contract-level tests for the Phase 1 mock services (API_CONTRACTS §8 rule 7).
 * These guard the honesty rules: synthetic provenance, null-with-reason, no silent zeros, typed errors.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { createMockServices } from "./services";
import { ApiError } from "@/services/errors";
import type { Services } from "@/services/types";
import { rectangleFromMetres, ringToMultiPolygon } from "@/lib/geo";

function setSearch(search: string) {
  (globalThis as unknown as { window: { location: { search: string } } }).window = { location: { search } };
}

/** Walk any payload and collect contract violations. */
function audit(node: unknown, path = "$", out: string[] = []): string[] {
  if (Array.isArray(node)) node.forEach((n, i) => audit(n, `${path}[${i}]`, out));
  else if (node && typeof node === "object") {
    const o = node as Record<string, unknown>;
    if ("unit" in o && "missing_reason" in o && "value" in o) {
      if ((o.value === null) !== (o.missing_reason !== null)) out.push(`${path}: value/missing_reason mismatch`);
    }
    if ("dataset_id" in o && "product_version" in o && "acquisition_id" in o) {
      if (o.dataset_id !== "synthetic") out.push(`${path}: non-synthetic SourceRef in mock data`);
    }
    for (const [k, v] of Object.entries(o)) audit(v, `${path}.${k}`, out);
  }
  return out;
}

let svc: Services;
beforeEach(() => {
  setSearch("?mock_latency=0");
  svc = createMockServices();
});

describe("mock services — contract invariants", () => {
  it("every response is synthetic and every field payload satisfies Quantity / SourceRef rules", async () => {
    const farms = await svc.farms.listFarms();
    expect(farms.meta.data_mode).toBe("synthetic");
    expect(farms.data.length).toBe(2);
    const violations: string[] = [];
    for (const farm of farms.data) {
      const ov = await svc.farms.getOverview(farm.farm_id, 2025);
      violations.push(...audit(ov.data, `overview(${farm.name})`));
      for (const f of ov.data.fields) {
        const id = f.field_id;
        const payloads = await Promise.all([
          svc.fields.getProfile(id, 2025), svc.environment.getClimate(id, 2025), svc.environment.getClimate(id, 2012),
          svc.environment.getSoil(id), svc.environment.getVegetation(id, 2025, "NDVI"), svc.environment.getVegetation(id, 2011, "EVI"),
          svc.environment.getIndicators(id), svc.rotation.getCropHistory(id), svc.rotation.getRecommendation(id, 2026),
          svc.resilience.getResilience(id), svc.fields.getCoverage(id),
        ]);
        payloads.forEach((p, i) => violations.push(...audit(p.data, `${f.name}#${i}`)));
      }
    }
    expect(violations).toEqual([]);
  });

  it("represents gaps as null with a reason — never as zero", async () => {
    const farm = (await svc.farms.listFarms()).data[0];
    const fields = (await svc.fields.listFields(farm.farm_id)).data;
    const anyField = fields[0].field_id;
    const clim2012 = (await svc.environment.getClimate(anyField, 2012)).data;
    const sm = clim2012.series.find((s) => s.variable === "sm_rootzone")!;
    expect(sm.points.every((p) => p.value === null && p.missing_reason === "OUT_OF_TEMPORAL_RANGE")).toBe(true);
    const veg2011 = (await svc.environment.getVegetation(anyField, 2011, "NDVI")).data;
    expect(veg2011.scenes).toHaveLength(0);
    expect(veg2011.phenology.peak_value.value).toBeNull();
    expect(veg2011.phenology.missing_reason).toBe("OUT_OF_TEMPORAL_RANGE");
    const et = clim2012.indicators.find((i) => i.key === "et_actual_season");
    expect(et).toBeUndefined();
    const et0 = clim2012.indicators.find((i) => i.key === "et0_total_season")!;
    expect(et0.value.value).not.toBeNull();
  });

  it("covers the required fixture states (full, partial, processing, failed, insufficient)", async () => {
    const farm = (await svc.farms.listFarms()).data[0];
    const fields = (await svc.fields.listFields(farm.farm_id)).data;
    const statuses = new Set(fields.map((f) => f.processing_status));
    expect(statuses).toEqual(new Set(["ready", "partial", "processing", "failed"]));
    const res = await Promise.all(fields.map((f) => svc.resilience.getResilience(f.field_id)));
    const st = new Set(res.map((r) => r.data.status));
    expect(st.has("computed") && st.has("insufficient_data") && st.has("pending")).toBe(true);
    const insufficient = res.find((r) => r.data.status === "insufficient_data")!.data;
    expect(insufficient.composite.score.value).toBeNull();
    expect(insufficient.composite.components_used).toBeLessThan(3);
  });

  it("is deterministic for a given seed", async () => {
    const a = (await svc.farms.listFarms()).data.map((f) => f.farm_id);
    const b = (await createMockServices().farms.listFarms()).data.map((f) => f.farm_id);
    expect(a).toEqual(b);
  });
});

describe("mock services — typed errors and mutations", () => {
  it("simulates any ApiErrorCode via ?mock_error, optionally scoped with mock_error_on", async () => {
    setSearch("?mock_latency=0&mock_error=UPSTREAM_UNAVAILABLE&mock_error_on=getClimate");
    const s = createMockServices();
    const farm = (await s.farms.listFarms()).data[0];
    const field = (await s.fields.listFields(farm.farm_id)).data[0];
    await expect(s.environment.getClimate(field.field_id, 2025)).rejects.toMatchObject({ code: "UPSTREAM_UNAVAILABLE", retryable: true });
    await expect(s.environment.getSoil(field.field_id)).resolves.toBeTruthy();
  });

  it("returns NOT_FOUND for unknown ids and NOT_EDITABLE for non-user fields", async () => {
    await expect(svc.fields.getField("nope")).rejects.toBeInstanceOf(ApiError);
    await expect(svc.fields.getField("nope")).rejects.toMatchObject({ code: "NOT_FOUND" });
    const farm = (await svc.farms.listFarms()).data[0];
    const synthetic = (await svc.fields.listFields(farm.farm_id)).data.find((f) => f.source === "synthetic")!;
    await expect(svc.fields.deleteField(synthetic.field_id)).rejects.toMatchObject({ code: "NOT_EDITABLE" });
  });

  it("validates drawn fields against the AOI and size limit, then creates a processing job", async () => {
    const farm = (await svc.farms.listFarms()).data.find((f) => f.aoi.aoi_id === "ks_reno")!;
    const outside = rectangleFromMetres([-95.0, 38.0], 400, 400);
    await expect(svc.fields.createField(farm.farm_id, { name: "Outside", geometry: outside })).rejects.toMatchObject({ code: "OUTSIDE_AOI" });
    const huge = rectangleFromMetres([-98.3, 37.8], 3000, 3000);
    await expect(svc.fields.createField(farm.farm_id, { name: "Huge", geometry: huge })).rejects.toMatchObject({ code: "FIELD_TOO_LARGE" });
    const bow = ringToMultiPolygon([[-98.1, 37.9], [-98.09, 37.91], [-98.09, 37.9], [-98.1, 37.91]]);
    await expect(svc.fields.createField(farm.farm_id, { name: "Bowtie", geometry: bow })).rejects.toMatchObject({ code: "GEOMETRY_INVALID" });
    const ok = rectangleFromMetres([-98.2, 37.85], 500, 500);
    const created = await svc.fields.createField(farm.farm_id, { name: "My field", geometry: ok });
    expect(created.data.field.editable).toBe(true);
    expect(created.data.field.processing_status).toBe("processing");
    expect(created.data.job.steps.map((s) => s.dataset_id)).toContain("nasa_hls_vi");
    const job = await svc.fields.getJob(created.data.job.job_id);
    expect(["queued", "running"]).toContain(job.data.status);
    await expect(svc.fields.deleteField(created.data.field.field_id)).resolves.toMatchObject({ data: { deleted: true } });
  });

  it("creates, evaluates, updates and deletes rotation scenarios; rejects invalid ones", async () => {
    const farm = (await svc.farms.listFarms()).data[0];
    const field = (await svc.fields.listFields(farm.farm_id)).data.find((f) => f.processing_status === "ready")!;
    await expect(svc.rotation.createScenario(field.field_id, { name: "", start_year: 2026, sequence: [{ year: 2026, crop_code: 24 }, { year: 2027, crop_code: 4 }] })).rejects.toMatchObject({ code: "VALIDATION_ERROR" });
    await expect(svc.rotation.createScenario(field.field_id, { name: "Bad", start_year: 2026, sequence: [{ year: 2026, crop_code: 999 }, { year: 2027, crop_code: 4 }] })).rejects.toMatchObject({ code: "VALIDATION_ERROR" });
    const sc = (await svc.rotation.createScenario(field.field_id, { name: "Test", start_year: 2026, sequence: [{ year: 2026, crop_code: 24 }, { year: 2027, crop_code: 24 }, { year: 2028, crop_code: 5 }] })).data;
    expect(sc.evaluation?.warnings.some((w) => w.code === "SYNTHETIC_EVALUATION")).toBe(true);
    expect(sc.evaluation?.year_findings[1].messages.some((m) => m.code === "REPEAT")).toBe(true);
    const upd = (await svc.rotation.updateScenario(sc.scenario_id, { name: "Renamed", start_year: 2026, sequence: [{ year: 2026, crop_code: 1 }, { year: 2027, crop_code: 5 }] })).data;
    expect(upd.name).toBe("Renamed");
    await svc.rotation.deleteScenario(sc.scenario_id);
    await expect(svc.rotation.deleteScenario(sc.scenario_id)).rejects.toMatchObject({ code: "NOT_FOUND" });
  });
});
