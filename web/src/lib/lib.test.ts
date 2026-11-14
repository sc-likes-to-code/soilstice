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
