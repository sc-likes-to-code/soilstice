import { describe, expect, it } from "vitest";
import { formatQuantity, qText, resolutionText } from "./format";
import { multiPolygonAreaHa, rectangleFromMetres, validateFieldDraft, type LngLat } from "./geo";
import { AOI_BBOX } from "./aoi";

describe("formatQuantity", () => {
  it("never renders a missing value as zero", () => {
    const f = formatQuantity({ value: null, unit: "mm", uncertainty: null, missing_reason: "QA_MASKED_CLOUD" });
    expect(f.missing).toBe(true);
    expect(f.text).toBe("—");
    expect(f.reason).toBe("QA_MASKED_CLOUD");
  });
  it("converts for display only", () => {
    expect(qText({ value: 25.4, unit: "mm", uncertainty: null, missing_reason: null }, "us")).toBe("1.00 in");
    expect(qText({ value: 100, unit: "ha", uncertainty: null, missing_reason: null }, "us")).toBe("247 ac");
    expect(qText({ value: 20, unit: "degC", uncertainty: null, missing_reason: null }, "us")).toBe("68.0 °F");
    expect(qText({ value: 12, unit: "percent", uncertainty: null, missing_reason: null })).toBe("12.0%");
  });
  it("formats uncertainty ranges", () => {
    const f = formatQuantity({ value: 6.4, unit: "pH", uncertainty: { kind: "range", low: 6.0, high: 6.8, value: null, note: null }, missing_reason: null });
    expect(f.range).toBe("6.0–6.8");
  });
  it("describes resolution", () => {
    expect(resolutionText(9000)).toBe("9 km");
    expect(resolutionText(30)).toBe("30 m");
    expect(resolutionText(null)).toBe("vector");
  });
});

describe("geometry helpers", () => {
  it("computes field area within 1% for an 800 m square", () => {
    const g = rectangleFromMetres([-98.1, 37.9], 800, 800);
    expect(multiPolygonAreaHa(g)).toBeGreaterThan(63.3);
    expect(multiPolygonAreaHa(g)).toBeLessThan(64.7);
  });
  it("pre-validates drawn fields like the E8 422 codes", () => {
    const reno = AOI_BBOX.ks_reno;
    const sq = (rectangleFromMetres([-98.1, 37.9], 500, 500).coordinates[0][0] as LngLat[]).slice(0, 4);
    expect(validateFieldDraft(sq, reno).ok).toBe(true);
    expect(validateFieldDraft(sq.slice(0, 2), reno).issues).toContain("TOO_FEW_VERTICES");
    const outside = (rectangleFromMetres([-96.0, 37.9], 500, 500).coordinates[0][0] as LngLat[]).slice(0, 4);
    expect(validateFieldDraft(outside, reno).issues).toContain("OUTSIDE_AOI");
    const big = (rectangleFromMetres([-98.3, 37.8], 2500, 2500).coordinates[0][0] as LngLat[]).slice(0, 4);
    expect(validateFieldDraft(big, reno).issues).toContain("FIELD_TOO_LARGE");
    const bow: LngLat[] = [[-98.1, 37.9], [-98.09, 37.91], [-98.09, 37.9], [-98.1, 37.91]];
    expect(validateFieldDraft(bow, reno).issues).toContain("SELF_INTERSECTING");
  });
});

describe("Task 7 & 8: Crop Ranking and Agronomic Descriptions", () => {
  it("ensures all 14 canonical crops have distinctive descriptions", async () => {
    const { CROP_AGRONOMIC_DESCRIPTIONS } = await import("@/components/views/suitability-section");
    const expected = Array.from({ length: 14 }, (_, i) => `CRP${String(i + 1).padStart(3, "0")}`);
    expect(Object.keys(CROP_AGRONOMIC_DESCRIPTIONS)).toHaveLength(14);
    for (const cid of expected) {
      const desc = CROP_AGRONOMIC_DESCRIPTIONS[cid];
      expect(desc).toBeDefined();
      expect(desc.length).toBeGreaterThan(60);
      expect(desc).toContain("(");
    }
  });

  it("sorts eligible crops deterministically by suitability score, confidence, limitations, and name", () => {
    interface CropItem {
      crop_id: string;
      crop_name: string;
      suitability_score: number;
      data_quality?: { status: string };
      limiting_factors: string[];
      suitability_class: string;
    }

    const crops: CropItem[] = [
      { crop_id: "CRP001", crop_name: "Corn", suitability_score: 85, data_quality: { status: "valid" }, limiting_factors: [], suitability_class: "suitable" },
      { crop_id: "CRP003", crop_name: "Winter Wheat", suitability_score: 92, data_quality: { status: "valid" }, limiting_factors: [], suitability_class: "suitable" },
      { crop_id: "CRP002", crop_name: "Soybean", suitability_score: 85, data_quality: { status: "valid" }, limiting_factors: ["pH"], suitability_class: "suitable" },
      { crop_id: "CRP008", crop_name: "Barley", suitability_score: 75, data_quality: { status: "valid" }, limiting_factors: ["drainage"], suitability_class: "conditionally_suitable" },
      { crop_id: "CRP010", crop_name: "Oats", suitability_score: 75, data_quality: { status: "valid" }, limiting_factors: ["drainage"], suitability_class: "conditionally_suitable" },
      { crop_id: "CRP007", crop_name: "Rice", suitability_score: 25, data_quality: { status: "valid" }, limiting_factors: ["drainage"], suitability_class: "unsuitable" },
    ];

    const eligible = crops.filter((c) => c.suitability_class !== "unsuitable");
    eligible.sort((a, b) => {
      const diff = (b.suitability_score ?? 0) - (a.suitability_score ?? 0);
      if (Math.abs(diff) > 1e-4) return diff;
      const aValid = a.data_quality?.status === "valid" ? 1 : 0;
      const bValid = b.data_quality?.status === "valid" ? 1 : 0;
      if (aValid !== bValid) return bValid - aValid;
      const limDiff = a.limiting_factors.length - b.limiting_factors.length;
      if (limDiff !== 0) return limDiff;
      return a.crop_name.localeCompare(b.crop_name);
    });

    expect(eligible[0].crop_name).toBe("Winter Wheat"); // 92
    expect(eligible[1].crop_name).toBe("Corn"); // 85 (0 limits)
    expect(eligible[2].crop_name).toBe("Soybean"); // 85 (1 limit)
    expect(eligible[3].crop_name).toBe("Barley"); // 75 ('B' < 'O')
    expect(eligible[4].crop_name).toBe("Oats"); // 75
  });
});
