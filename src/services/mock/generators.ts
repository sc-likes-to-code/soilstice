/**
 * Synthetic profile generators. They produce contract-valid, visibly synthetic payloads.
 * They are NOT the Phase 4 analytical engine or the Phase 5 rotation engine: any arithmetic here
 * exists only so that synthetic charts are internally consistent. All outputs carry dataset_id "synthetic".
 */
import type {
  ClimateProfile, CompareScenariosResponse, CropCode, CropHistory, CropSuitabilityAssessment, CropYear, DataCoverage, DatasetCoverage, DatasetId, EnvironmentalIndicator,
  EvidenceItem, FactorAssessment, FieldSuitabilityResponse, FitBand, GenerateCandidate, GenerateRotationsRequest, GenerateRotationsResponse, IndicatorCategory, IndicatorKey, MissingReason, QualityFlag, QualityInfo,
  Quantity, RecommendationCandidate, ResilienceComponent, ResilienceComponentKey, ResilienceProfile,
  RotationRecommendation, RotationScenario, ScenarioEvaluation, ScenarioInterpretation, ScenarioYear, ScoreBand, SoilLayer, SoilProfile, SpatialSupport,
  SuitabilityFactorAssessment, SuitabilityClass,
  TemporalSupport, TerrainProfile, TimeSeries, TimeSeriesPoint, TradeoffFinding, Unit, VegetationIndex, VegetationProfile,
  VegetationScene, Confidence,
} from "@/types/contracts";
import { clamp, createRng, hashString, round } from "./rng";
import {
  CROPS, DEMO_AS_OF, ENGINE_VERSION, KB_VERSION, LATEST_CROP_YEAR, PENDING_KB_REQUIREMENT, RESILIENCE_MODEL,
  cropName, descriptor, method, missing, q, spatialFor, synthSource, temporal,
} from "./catalog";
import type { MockFieldRecord } from "./world";

const SYNTH_FLAG: QualityFlag = { code: "SYNTHETIC", severity: "info", message: "Synthetic demo value — not an observation." };

function quality(status: QualityInfo["status"], completeness: number | null, reason: MissingReason | null = null, extra: QualityFlag[] = []): QualityInfo {
  return { status, flags: [SYNTH_FLAG, ...extra], completeness, missing_reason: reason };
}

function indicator(
  fieldId: string, key: IndicatorKey, label: string, category: IndicatorCategory, value: Quantity,
  standsFor: DatasetId, spatial: SpatialSupport, temp: TemporalSupport, opts?: { reference?: Quantity | null; nature?: EnvironmentalIndicator["nature"]; methodName?: string; flags?: QualityFlag[] },
): EnvironmentalIndicator {
  const isMissing = value.value === null;
  return {
    indicator_id: `${fieldId}:${key}:${temp.period_start ?? "static"}`,
    key, label, category, value,
    nature: opts?.nature ?? "derived",
    spatial, temporal: temp,
    quality: isMissing ? quality("missing", 0, value.missing_reason, opts?.flags) : quality("valid", 1, null, opts?.flags),
    sources: [synthSource(standsFor)],
    method: method(`synthetic_${key}`, opts?.methodName ?? `Synthetic ${label.toLowerCase()}`, "Synthetic placeholder generated for the Phase 1 UI. The real calculation is specified in SOILSTICE_DATA_ARCHITECTURE and implemented in Phase 4."),
    input_ids: [],
    reference_value: opts?.reference ?? null,
  };
}

// ───────────────────────── Climate ─────────────────────────
const PRECIP_NORMAL: Record<string, number[]> = {
  ks_reno: [20, 25, 55, 70, 110, 115, 90, 85, 70, 55, 35, 25],
  ks_finney: [10, 12, 30, 40, 70, 80, 65, 60, 40, 30, 15, 12],
};
const TMAX = [6, 9, 15, 20, 25, 31, 34, 33, 28, 21, 13, 7];
const TMIN = [-7, -5, 0, 5, 11, 17, 20, 19, 14, 7, 0, -5];
const DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function monthStart(year: number, m: number) {
  return `${year}-${String(m + 1).padStart(2, "0")}-01`;
}
function pt(t: string, v: number | null, reason: MissingReason | null = null): TimeSeriesPoint {
  return { t, value: v, quality_status: v === null ? "missing" : "valid", missing_reason: v === null ? reason ?? "UPSTREAM_ERROR" : null };
}

export function climateProfile(rec: MockFieldRecord, year: number): ClimateProfile {
  const { field, traits } = rec;
  const fid = field.field_id;
  const rng = createRng(`${traits.aoi}:climate:${year}`);
  const frng = createRng(`${fid}:climate:${year}`);
  const start = `${year}-01-01`;
  const end = `${year}-12-31`;
  const power = spatialFor("nasa_power_daily_ag");
  const smap = spatialFor("nasa_smap_spl4smgp", { field_fraction_of_cell: round((field.area.value ?? 65) / 8100, 4) });
  const normals = PRECIP_NORMAL[traits.aoi];
  const yearFactor = rng.range(0.7, 1.3);
  const finney = traits.aoi === "ks_finney";
  const failed = traits.variant === "failed";

  const precip: number[] = normals.map((n) => round(Math.max(0, n * yearFactor * rng.range(0.4, 1.6) * (1 + traits.climateBias)), 1));
  const tmax = TMAX.map((t) => round(t + rng.normal(0.6, 1.4) + (finney ? 0.5 : 0), 1));
  const tmin = TMIN.map((t) => round(t + rng.normal(0.3, 1.2) - (finney ? 2 : 0), 1));
  // Placeholder GDD (base 10 °C, cap 30 °C) for chart consistency only — real per-crop GDD is Phase 4 (D5.6).
  const gddMonthly = tmax.map((hi, i) => Math.max(0, (Math.min(hi, 30) + Math.max(tmin[i], 10)) / 2 - 10) * DAYS[i]);
  const et0 = TMAX.map((t, i) => round(Math.max(15, (t + 5) * DAYS[i] * (finney ? 0.17 : 0.15) * rng.range(0.9, 1.1)), 1));

  const monthly = (label: string, variable: string, unit: Unit, values: (number | null)[], standsFor: DatasetId, agg: TemporalSupport["aggregation"], ref?: number[]): TimeSeries => ({
    series_id: `${fid}:${variable}:${year}`,
    variable, label, unit, nature: "model",
    spatial: power,
    temporal: temporal("P1M", start, end, agg, "LST"),
    sources: [synthSource(standsFor)],
    points: values.map((v, i) => pt(monthStart(year, i), failed ? null : v, failed ? "UPSTREAM_ERROR" : null)),
    reference: ref ? { label: "Synthetic 1991–2020 normal", period_start: "1991-01-01", period_end: "2020-12-31", points: ref.map((v, i) => pt(monthStart(year, i), v)) } : null,
  });

  let cum = 0;
  const gddCum = gddMonthly.map((g) => round((cum += g), 0));

  // SMAP L4 root-zone daily (regional context). Before 2015-03-31: out of temporal range.
  const smPoints: TimeSeriesPoint[] = [];
  let sm = finney ? 0.17 : 0.24;
  const d0 = Date.UTC(year, 0, 1);
  for (let i = 0; i < 365; i++) {
    const t = new Date(d0 + i * 86400000).toISOString().slice(0, 10);
    if (year < 2015 || (year === 2015 && i < 89)) { smPoints.push(pt(t, null, "OUT_OF_TEMPORAL_RANGE")); continue; }
    const m = new Date(d0 + i * 86400000).getUTCMonth();
    const rainChance = (precip[m] / DAYS[m]) / 9;
    sm = sm * 0.985 + (frng.chance(rainChance) ? frng.range(0.01, 0.035) : 0) + (finney ? 0.0022 : 0.0033);
    sm = clamp(sm, finney ? 0.08 : 0.12, finney ? 0.3 : 0.38);
    smPoints.push(failed || frng.chance(0.03) ? pt(t, null, "UPSTREAM_ERROR") : pt(t, round(sm, 3)));
  }
  const smValid = smPoints.filter((p) => p.value !== null).map((p) => p.value as number);
  const smSeries: TimeSeries = {
    series_id: `${fid}:sm_rootzone:${year}`, variable: "sm_rootzone", label: "Root-zone soil moisture (0–100 cm)", unit: "m3_m-3",
    nature: "model", spatial: smap, temporal: temporal("P1D", start, end, "mean", "UTC"), sources: [synthSource("nasa_smap_spl4smgp")],
    points: smPoints, reference: null,
  };

  const total = precip.reduce((a, b) => a + b, 0);
  const normalTotal = normals.reduce((a, b) => a + b, 0);
  const etTotal = et0.reduce((a, b) => a + b, 0);
  const season = temporal("season", start, end, "sum", "LST");
  const seasonMean = temporal("season", start, end, "mean", "LST");
  const smReason: MissingReason = year < 2015 ? "OUT_OF_TEMPORAL_RANGE" : "UPSTREAM_ERROR";
  const val = (v: number, unit: Unit): Quantity => (failed ? missing(unit, "UPSTREAM_ERROR") : q(v, unit));

  const indicators: EnvironmentalIndicator[] = [
    indicator(fid, "precip_total_season", "Precipitation total", "climate", val(round(total, 0), "mm"), "nasa_power_daily_ag", power, season, { reference: q(normalTotal, "mm"), nature: "model" }),
    indicator(fid, "precip_anomaly_pct", "Precipitation anomaly", "climate", val(round(((total - normalTotal) / normalTotal) * 100, 0), "percent"), "nasa_power_daily_ag", power, season),
    indicator(fid, "gdd_season", "Growing degree days", "climate", val(round(gddCum[11], 0), "degC_day"), "nasa_power_daily_ag", power, season, { methodName: "Placeholder GDD (base 10 °C, cap 30 °C)", flags: [{ code: "GDD_PARAMS_PENDING", severity: "warning", message: "Per-crop GDD base/cap pending a cited KB entry (D5.6)." }] }),
    indicator(fid, "heat_stress_days", "Heat-stress days (Tmax > 35 °C)", "climate", val(rng.int(finney ? 6 : 2, finney ? 34 : 22), "day"), "nasa_power_daily_ag", power, season, { flags: [{ code: "HEURISTIC_THRESHOLD", severity: "info", message: "35 °C threshold is a labelled heuristic pending citation." }] }),
    indicator(fid, "frost_free_days", "Frost-free days", "climate", val(rng.int(finney ? 158 : 172, finney ? 178 : 198), "day"), "nasa_power_daily_ag", power, season),
    indicator(fid, "solar_total_season", "Solar radiation total", "climate", val(round(rng.range(5900, 6500), 0), "MJ_m-2"), "nasa_power_daily_ag", { ...power, native_resolution_m: 110000 }, season),
    indicator(fid, "rh_mean_season", "Mean relative humidity", "climate", val(round(rng.range(finney ? 52 : 60, finney ? 60 : 70), 0), "percent"), "nasa_power_daily_ag", power, seasonMean),
    indicator(fid, "et0_total_season", "Reference ET₀ total", "water", val(round(etTotal, 0), "mm"), "nasa_power_daily_ag", power, season),
    indicator(fid, "water_balance_season", "Water balance (P − ET₀)", "water", val(round(total - etTotal, 0), "mm"), "nasa_power_daily_ag", power, season),
    indicator(fid, "sm_rootzone_mean_season", "Root-zone soil moisture (mean)", "soil_moisture", smValid.length ? q(round(smValid.reduce((a, b) => a + b, 0) / smValid.length, 3), "m3_m-3") : missing("m3_m-3", smReason), "nasa_smap_spl4smgp", smap, temporal("season", start, end, "mean", "UTC"), { nature: "model" }),
    indicator(fid, "sm_rootzone_dry_days", "Root-zone dry days", "soil_moisture", smValid.length ? q(rng.int(5, 70), "day") : missing("day", smReason), "nasa_smap_spl4smgp", smap, temporal("season", start, end, "count", "UTC")),
  ];

  return {
    field_id: fid,
    season: { label: `${year} calendar year (crop calendars pending KB)`, start, end, crop_code: null },
    authoritative_source: { precipitation: "nasa_power_daily_ag", temperature: "nasa_power_daily_ag" },
    indicators,
    series: [
      monthly("Precipitation (monthly)", "precipitation", "mm", precip, "nasa_power_daily_ag", "sum", normals),
      monthly("Maximum temperature (monthly mean)", "tmax", "degC", tmax, "nasa_power_daily_ag", "mean", TMAX),
      monthly("Minimum temperature (monthly mean)", "tmin", "degC", tmin, "nasa_power_daily_ag", "mean", TMIN),
      monthly("Cumulative GDD (placeholder base 10 °C)", "gdd_cumulative", "degC_day", gddCum, "nasa_power_daily_ag", "sum"),
      monthly("Reference ET₀ (monthly)", "et0", "mm", et0, "nasa_power_daily_ag", "sum"),
      smSeries,
    ],
    quality: failed ? quality("missing", 0, "UPSTREAM_ERROR") : quality(year < 2015 ? "partial" : "valid", year < 2015 ? 0.85 : 0.97),
  };
}

// ───────────────────────── Soil ─────────────────────────
const TEXTURE_FRACTIONS: Record<string, [number, number, number]> = {
  "Silt loam": [20, 64, 16], Loam: [40, 39, 21], "Silty clay loam": [10, 58, 32], "Fine sandy loam": [62, 25, 13], "Loamy fine sand": [80, 12, 8],
};
const AWC_BY_TEXTURE: Record<string, number> = { "Silt loam": 0.21, Loam: 0.17, "Silty clay loam": 0.19, "Fine sandy loam": 0.13, "Loamy fine sand": 0.08 };

export function soilProfile(rec: MockFieldRecord): SoilProfile {
  const { field, traits } = rec;
  const rng = createRng(`${field.field_id}:soil`);
  const [s0, , c0] = TEXTURE_FRACTIONS[traits.textureClass];
  const intervals: [number, number][] = [[0, 30], [30, 100], [100, 150]];
  const layers: SoilLayer[] = intervals.map(([top, bottom], i) => {
    const clay = clamp(c0 + i * rng.range(3, 8) + rng.normal(0, 1.5), 3, 55);
    const sand = clamp(s0 - i * rng.range(1, 4) + rng.normal(0, 2), 3, 92);
    const silt = clamp(100 - clay - sand, 2, 85);
    const ph = traits.ph + i * rng.range(0.2, 0.5);
    const om = Math.max(0.1, traits.om * [1, 0.45, 0.2][i]);
    const awc = clamp(AWC_BY_TEXTURE[traits.textureClass] - i * 0.015 + rng.normal(0, 0.01), 0.03, 0.25);
    const r = (v: number, d: number, dp = 0) => q(round(v, dp), "percent", { low: round(v - d, dp), high: round(v + d, dp) });
    return {
      top_cm: top, bottom_cm: bottom,
      sand_pct: r(sand, 5), silt_pct: r(silt, 5), clay_pct: r(clay, 4),
      texture_class: i === 0 ? traits.textureClass : i === 1 && clay > 27 ? "Silty clay loam" : traits.textureClass,
      ph_h2o: { ...q(round(ph, 1), "pH", { low: round(ph - 0.4, 1), high: round(ph + 0.4, 1) }) },
      om_pct: q(round(om, 1), "percent", { low: round(om * 0.6, 1), high: round(om * 1.4, 1) }),
      awc: q(round(awc, 2), "cm_cm-1"),
    };
  });
  const aws100 = layers[0].awc.value! * 30 + layers[1].awc.value! * 70;
  const aws150 = aws100 + layers[2].awc.value! * 50;
  const sandy = traits.textureClass.includes("sand");
  const nMu = rng.int(1, 3);
  const shares = nMu === 1 ? [1] : nMu === 2 ? [0.72, 0.28] : [0.61, 0.27, 0.12];
  return {
    field_id: field.field_id,
    layers,
    aws_0_100: q(round(aws100, 1), "cm"),
    aws_0_150: q(round(aws150, 1), "cm"),
    drainage_class: { value: sandy ? "Somewhat excessively drained" : rng.chance(0.75) ? "Well drained" : "Moderately well drained", weight_share: round(shares[0] * 0.85, 2), missing_reason: null },
    hydrologic_group: { value: sandy ? "A" : rng.pick(["B", "C", "B"]), weight_share: round(shares[0] * 0.85, 2), missing_reason: null },
    slope_pct_ssurgo: q(round(traits.slopeMean * 0.9, 1), "percent", { low: 0, high: round(traits.slopeMean * 1.8, 1) }),
    map_units: shares.map((share, i) => ({
      mukey: `SYN-${1000 + (hashString(field.field_id + i) % 9000)}`,
      muname: `Synthetic map unit ${i + 1} — ${i === 0 ? traits.textureClass.toLowerCase() : rng.pick(["loam", "silt loam", "clay loam"])}, ${i === 0 ? "0 to 1" : "1 to 3"} percent slopes`,
      area_fraction: share,
      major_components: [{ cokey: `SYN-C${i}`, compname: `Synthetic component ${String.fromCharCode(65 + i)}`, comppct_r: rng.int(70, 90) }],
    })),
    survey: [{ areasymbol: "SYN000", saverest: null }],
    method: method("ssurgo_area_comppct_weighting", "SSURGO area × component-percent weighting", "Normative method in SOILSTICE_DATA_ARCHITECTURE §5.3.1 (values here are synthetic)."),
    null_weight_fraction: round(rng.range(0, 0.08), 2),
    spatial: spatialFor("usda_nrcs_ssurgo_sda"),
    sources: [synthSource("usda_nrcs_ssurgo_sda")],
    quality: quality("valid", 0.95),
  };
}

// ───────────────────────── Terrain ─────────────────────────
export function terrainProfile(rec: MockFieldRecord): TerrainProfile | null {
  const { field, traits } = rec;
  const rng = createRng(`${field.field_id}:terrain`);
  const unavailable = traits.variant === "insufficient" || traits.variant === "failed";
  const m = (v: number, unit: Unit) => (unavailable ? missing(unit, "UPSTREAM_ERROR") : q(v, unit));
  return {
    field_id: field.field_id,
    elevation_mean: m(traits.elevation, "m"),
    elevation_min: m(traits.elevation - rng.int(1, 6), "m"),
    elevation_max: m(traits.elevation + rng.int(2, 9), "m"),
    slope_mean_pct: m(traits.slopeMean, "percent"),
    slope_p90_pct: m(round(traits.slopeMean * rng.range(1.6, 2.3), 1), "percent"),
    method: method("srtm_horn_slope", "Horn slope in EPSG:5070", "Slope from SRTMGL1 reprojected to CONUS Albers, Horn 1981 kernel (values here are synthetic)."),
    spatial: spatialFor("nasa_srtm_gl1"),
    sources: [synthSource("nasa_srtm_gl1")],
    quality: unavailable ? quality("missing", 0, "UPSTREAM_ERROR") : quality("valid", 1),
  };
}

// ───────────────────────── Crop history ─────────────────────────
export function cropHistory(rec: MockFieldRecord): CropHistory {
  const { field, traits } = rec;
  const rng = createRng(`${field.field_id}:cdl`);
  const years: CropYear[] = traits.history.map((code, i) => {
    const year = 2006 + i;
    const purity = traits.purity[i];
    const others = CROPS.filter((c) => c.crop_code !== code).slice(0, 2);
    const rest = 1 - purity;
    const edge = round(rest * rng.range(0.3, 0.6), 2);
    const histogram = [
      { crop_code: code, crop_name: cropName(code), area_fraction: purity },
      { crop_code: others[0].crop_code, crop_name: others[0].name, area_fraction: round(rest - edge, 2) },
      { crop_code: 176, crop_name: "Grassland/Pasture", area_fraction: edge },
    ];
    const inCsb = year >= 2018;
    const disagree = traits.csbDisagree.includes(year);
    return {
      year,
      majority: { crop_code: code, crop_name: cropName(code) },
      purity,
      histogram,
      low_purity: purity < 0.6,
      class_accuracy: null,
      csb_crop_code: inCsb && field.source !== "user" ? (disagree ? others[0].crop_code : code) : null,
      agrees_with_csb: inCsb && field.source !== "user" ? !disagree : null,
      native_resolution_m: year <= 2009 ? null : 30,
      missing_reason: null,
      source: synthSource("usda_nass_cdl"),
    };
  });
  const seq = traits.history;
  let maxRun = 1, run = 1;
  for (let i = 1; i < seq.length; i++) { run = seq[i] === seq[i - 1] ? run + 1 : 1; maxRun = Math.max(maxRun, run); }
  const counts = new Map<number, number>();
  seq.forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
  const shannon = -[...counts.values()].reduce((a, n) => a + (n / seq.length) * Math.log(n / seq.length), 0);
  const fid = field.field_id;
  const sp = spatialFor("usda_nass_cdl");
  const tp = temporal("P1Y", "2006-01-01", "2025-12-31", "count");
  return {
    field_id: fid,
    period: { start_year: 2006, end_year: LATEST_CROP_YEAR },
    years,
    metrics: [
      indicator(fid, "distinct_crops", "Distinct crops (2006–2025)", "rotation", q(counts.size, "count"), "usda_nass_cdl", sp, tp, { nature: "derived" }),
      indicator(fid, "max_monoculture_run", "Longest same-crop run", "rotation", q(maxRun, "year"), "usda_nass_cdl", sp, tp),
      indicator(fid, "rotation_shannon", "Rotation diversity (Shannon)", "rotation", q(round(shannon, 2), "unitless"), "usda_nass_cdl", sp, tp),
    ],
    spatial: sp,
    quality: quality("valid", 1, null, years.some((y) => y.low_purity) ? [{ code: "LOW_PURITY_YEARS", severity: "warning", message: "Some years have majority-class purity below 0.6." }] : []),
  };
}

// ───────────────────────── Vegetation ─────────────────────────
type Curve = (doy: number) => number;
function curveFor(code: CropCode): Curve {
  const g = (doy: number, mu: number, sd: number) => Math.exp(-((doy - mu) ** 2) / (2 * sd * sd));
  switch (code) {
    case 24: return (d) => (d < 175 ? 0.24 + 0.56 * g(d, 118, 32) : 0.17);
    case 26: case 236: return (d) => (d < 175 ? 0.24 + 0.54 * g(d, 118, 32) : 0.17 + 0.46 * g(d, 245, 24));
    case 1: return (d) => 0.17 + 0.66 * g(d, 205, 28);
    case 4: return (d) => 0.17 + 0.56 * g(d, 228, 25);
    case 5: return (d) => 0.17 + 0.62 * g(d, 220, 24);
    case 36: return (d) => (d < 80 || d > 300 ? 0.3 : 0.52 + 0.2 * Math.sin(((d - 80) / 38) * Math.PI * 2));
    default: return () => 0.19;
  }
}
const INDEX_TRANSFORM: Record<VegetationIndex, (ndvi: number) => number> = {
  NDVI: (v) => v, EVI: (v) => v * 0.62, NDMI: (v) => v * 0.72 - 0.17, SAVI: (v) => v * 0.68, MSAVI: (v) => v * 0.66,
  NDWI: (v) => -v * 0.7 + 0.05, NBR: (v) => v * 0.8 - 0.05, NBR2: (v) => v * 0.25, TVI: (v) => Math.sqrt(Math.max(0, v + 0.5)),
};

export function vegetationProfile(rec: MockFieldRecord, year: number, index: VegetationIndex): VegetationProfile {
  const { field, traits } = rec;
  const fid = field.field_id;
  const rng = createRng(`${fid}:veg:${year}:${index}`);
  const code = traits.history[year - 2006] ?? traits.history[traits.history.length - 1];
  const curve = curveFor(code);
  const sp = spatialFor("nasa_hls_vi");
  const tf = INDEX_TRANSFORM[index];
  const outOfRange = year < 2013;
  const blocked = traits.variant === "failed" || traits.variant === "processing_user";
  const cloudy = traits.variant === "cloudy" || traits.variant === "insufficient";
  const total = Math.round(((field.area.value ?? 65) * 10000) / 900 * 0.86);
  const scenes: VegetationScene[] = [];
  if (!outOfRange && !blocked) {
    for (let doy = 60 + rng.int(0, 3); doy <= 320; doy += rng.int(2, 5)) {
      const s30 = rng.chance(0.6) && year >= 2016;
      const r = rng.next();
      const clear = cloudy ? (r < 0.15 ? rng.range(0.7, 0.95) : rng.range(0, 0.6)) : r < 0.55 ? rng.range(0.9, 1) : r < 0.8 ? rng.range(0.4, 0.9) : rng.range(0, 0.3);
      const valid = Math.round(total * clear);
      const accepted = clear >= 0.7;
      const ndvi = clamp(curve(doy) + rng.normal(0, 0.025), -0.1, 0.95);
      const v = round(tf(ndvi), 3);
      const masked = total - valid;
      const date = new Date(Date.UTC(year, 0, doy, 17, 20));
      const tile = traits.aoi === "ks_reno" ? "T14SNH" : "T14SKH";
      scenes.push({
        granule_id: `SYNTHETIC.HLS-VI.${s30 ? "S30" : "L30"}.${tile}.${year}${String(doy).padStart(3, "0")}`,
        product: "synthetic",
        acquired_at: date.toISOString(),
        median: valid > 0 ? v : null,
        p10: valid > 0 ? round(v - rng.range(0.03, 0.08), 3) : null,
        p90: valid > 0 ? round(v + rng.range(0.02, 0.06), 3) : null,
        valid_pixels: valid,
        total_pixels: total,
        clear_fraction: round(clear, 2),
        accepted,
        mask_counts: { cloud: Math.round(masked * 0.6), cloud_adjacent: Math.round(masked * 0.25), cloud_shadow: Math.round(masked * 0.15), snow_ice: 0, water: 0 },
        missing_reason: valid === 0 ? "QA_MASKED_CLOUD" : accepted ? null : "INSUFFICIENT_COVERAGE",
      });
    }
  }
  const acc = scenes.filter((s) => s.accepted && s.median !== null);
  const enough = acc.length >= 6;
  const reason: MissingReason = outOfRange ? "OUT_OF_TEMPORAL_RANGE" : blocked ? (traits.variant === "failed" ? "UPSTREAM_ERROR" : "PENDING_PROCESSING") : "INSUFFICIENT_COVERAGE";
  const peak = enough ? acc.reduce((a, s) => ((s.median ?? -1) > (a.median ?? -1) ? s : a)) : null;
  const thr = peak ? (peak.median! + Math.min(...acc.map((s) => s.median!))) / 2 : 0;
  const above = acc.filter((s) => s.median! >= thr);
  return {
    field_id: fid,
    year,
    index,
    scenes,
    series: {
      series_id: `${fid}:${index}:${year}`, variable: index.toLowerCase(), label: `${index} (accepted scene medians)`, unit: "unitless", nature: "derived",
      spatial: sp, temporal: temporal("irregular", `${year}-01-01`, `${year}-12-31`, "median", "UTC"), sources: [synthSource("nasa_hls_vi")],
      points: acc.map((s) => ({ t: s.acquired_at.slice(0, 10), value: s.median, quality_status: "valid", missing_reason: null })), reference: null,
    },
    phenology: {
      peak_value: peak ? q(peak.median!, "unitless") : missing("unitless", reason),
      peak_date: peak ? peak.acquired_at.slice(0, 10) : null,
      greenup_date: enough && above.length ? above[0].acquired_at.slice(0, 10) : null,
      senescence_date: enough && above.length ? above[above.length - 1].acquired_at.slice(0, 10) : null,
      method: method("synthetic_phenology", "Placeholder phenology markers", "Highest accepted scene and half-amplitude crossings of synthetic medians. Real phenology fitting is Phase 4."),
      gap_filled: false,
      missing_reason: enough ? null : reason,
    },
    spatial: sp,
    sources: [synthSource("nasa_hls_vi")],
    quality: scenes.length === 0 ? quality("missing", 0, reason) : enough ? quality(cloudy ? "partial" : "valid", round(acc.length / Math.max(scenes.length, 1), 2)) : quality("partial", round(acc.length / Math.max(scenes.length, 1), 2), "INSUFFICIENT_COVERAGE", [{ code: "FEW_CLEAR_SCENES", severity: "warning", message: `Only ${acc.length} scenes passed the 70% clear-pixel rule; phenology needs ≥ 6.` }]),
  };
}

export function vegetationIndicators(rec: MockFieldRecord, year: number): EnvironmentalIndicator[] {
  const v = vegetationProfile(rec, year, "NDVI");
  const n = vegetationProfile(rec, year, "NDMI");
  const fid = rec.field.field_id;
  const sp = spatialFor("nasa_hls_vi");
  const tp = temporal("season", `${year}-01-01`, `${year}-12-31`, "max", "UTC");
  const peakDoy = v.phenology.peak_date ? Math.round((Date.parse(v.phenology.peak_date) - Date.UTC(year, 0, 1)) / 86400000) + 1 : null;
  const reason = v.phenology.missing_reason ?? "INSUFFICIENT_COVERAGE";
  const cvRng = createRng(`${fid}:ndvicv`);
  const insufficient = rec.traits.variant === "insufficient" || rec.traits.variant === "failed" || rec.traits.variant === "processing_user";
  return [
    indicator(fid, "ndvi_peak", "Peak NDVI", "vegetation", v.phenology.peak_value, "nasa_hls_vi", sp, tp),
    indicator(fid, "ndvi_peak_doy", "Peak NDVI day of year", "vegetation", peakDoy !== null ? q(peakDoy, "day") : missing("day", reason), "nasa_hls_vi", sp, tp),
    indicator(fid, "ndmi_peak_season", "Peak NDMI", "vegetation", n.phenology.peak_value, "nasa_hls_vi", sp, tp),
    indicator(fid, "ndvi_peak_cv", "Peak NDVI variability (2016–2025)", "vegetation", insufficient ? missing("unitless", "INSUFFICIENT_COVERAGE") : q(round(cvRng.range(0.05, 0.24), 2), "unitless"), "nasa_hls_vi", sp, temporal("P1Y", "2016-01-01", "2025-12-31", "none", "UTC")),
  ];
}

export function soilTerrainIndicators(rec: MockFieldRecord): EnvironmentalIndicator[] {
  const s = soilProfile(rec);
  const t = terrainProfile(rec);
  const fid = rec.field.field_id;
  const st = temporal("static", null, null, "weighted_mean");
  const ss = spatialFor("usda_nrcs_ssurgo_sda");
  const ts = spatialFor("nasa_srtm_gl1");
  const tt = temporal("static", "2000-02-11", "2000-02-21", "mean");
  const out = [
    indicator(fid, "aws_0_150", "Available water storage 0–150 cm", "soil", s.aws_0_150, "usda_nrcs_ssurgo_sda", ss, st, { nature: "observation" }),
    indicator(fid, "ph_0_30", "Soil pH 0–30 cm", "soil", s.layers[0].ph_h2o, "usda_nrcs_ssurgo_sda", ss, st, { nature: "observation" }),
    indicator(fid, "om_0_30", "Organic matter 0–30 cm", "soil", s.layers[0].om_pct, "usda_nrcs_ssurgo_sda", ss, st, { nature: "observation" }),
    indicator(fid, "clay_0_30", "Clay 0–30 cm", "soil", s.layers[0].clay_pct, "usda_nrcs_ssurgo_sda", ss, st, { nature: "observation" }),
  ];
  if (t) {
    out.push(
      indicator(fid, "slope_mean_pct", "Mean slope", "terrain", t.slope_mean_pct, "nasa_srtm_gl1", ts, tt),
      indicator(fid, "slope_p90_pct", "Slope (90th percentile)", "terrain", t.slope_p90_pct, "nasa_srtm_gl1", ts, tt),
      indicator(fid, "elevation_mean", "Mean elevation", "terrain", t.elevation_mean, "nasa_srtm_gl1", ts, tt, { nature: "observation" }),
    );
  }
  return out;
}

// ───────────────────────── Coverage ─────────────────────────
export function coverage(rec: MockFieldRecord, jobDone: boolean = true): DataCoverage {
  const { field, traits } = rec;
  const v = traits.variant;
  const P0: DatasetId[] = ["meteomatics", "nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "nasa_srtm_gl1"];
  const entry = (id: DatasetId): DatasetCoverage => {
    const d = descriptor(id);
    let status: DatasetCoverage["status"] = "available";
    let reason: MissingReason | null = null;
    let note: string | null = "Operational dataset integrated.";
    if (!jobDone) {
      status = "missing";
      reason = "UPSTREAM_ERROR";
      note = "Processing job in progress.";
    } else if (v === "insufficient" && id === "nasa_srtm_gl1") {
      status = "missing";
      reason = "UPSTREAM_ERROR";
    } else if (v === "failed" && id !== "usda_nrcs_ssurgo_sda" && id !== "usda_nass_cdl") {
      status = "missing";
      reason = "UPSTREAM_ERROR";
      note = "Synthetic processing failure.";
    }
    const isAvail = status === "available" || (status as string) === "partial";
    return {
      dataset_id: id, label: d.title, priority: d.priority, status, support_class: d.support_class, native_resolution_m: d.native_resolution_m,
      temporal_coverage: d.temporal_coverage, product_version: "synthetic-0",
      last_updated: isAvail ? `${DEMO_AS_OF}T09:00:00Z` : null, missing_reason: reason, note,
    };
  };
  const datasets = P0.map(entry).filter(
    (x) =>
      x.status !== "not_applicable" &&
      x.status !== "not_integrated" &&
      x.dataset_id !== "nasa_hls_vi" &&
      x.dataset_id !== "nasa_hls" &&
      !x.label.toLowerCase().includes("ndvi") &&
      !x.label.toLowerCase().includes("ndmi")
  );
  const p0 = datasets.filter((x) => x.priority === "P0");
  const ok = p0.filter((x) => x.status === "available" || x.status === "partial").length;
  return { field_id: field.field_id, datasets, completeness: p0.length ? round(ok / p0.length, 2) : 0 };
}

// ───────────────────────── Resilience ─────────────────────────
const COMPONENT_META: [ResilienceComponentKey, string, "F" | "S" | "R", string[]][] = [
  ["soil_water_buffer", "Soil water buffer", "F", ["aws_0_150"]],
  ["terrain_erosion_risk", "Terrain & erosion risk", "F", ["slope_p90_pct"]],
  ["climate_exposure", "Climate exposure", "R", ["precip_anomaly_pct", "heat_stress_days", "sm_rootzone_dry_days"]],
  ["rotation_diversity", "Rotation diversity", "F", ["distinct_crops", "max_monoculture_run", "rotation_shannon"]],
];

export function bandFor(score: number | null): ScoreBand {
  if (score === null) return "unknown";
  return score < 40 ? "low" : score <= 70 ? "moderate" : "high";
}

export function resilienceProfile(rec: MockFieldRecord, uuid: () => string): ResilienceProfile {
  const { field, traits } = rec;
  const rng = createRng(`${field.field_id}:resilience`);
  const v = traits.variant;
  const disclaimers = [
    "Synthetic demo scores — the breakpoint tables are defined in Phase 4 (SOILSTICE_DATA_ARCHITECTURE §5.10).",
    "Scores are decision-support indicators, not agronomic prescriptions.",
    "Components marked “Regional context” do not measure this field.",
  ];
  if (v === "failed" || v === "processing_user") {
    return {
      profile_id: uuid(), field_id: field.field_id, as_of: DEMO_AS_OF, model_version: RESILIENCE_MODEL, status: "pending",
      composite: { score: missing("score_0_100", "PENDING_PROCESSING"), band: "unknown", confidence: "low", components_used: 0, components_total: 4 },
      components: [], limitations: [{ code: v === "failed" ? "PROCESSING_FAILED" : "PROCESSING", severity: "warning", message: v === "failed" ? "Upstream processing failed for this synthetic field; resilience was not computed." : "Waiting for satellite datasets to finish processing." }],
      disclaimers,
    };
  }
  const unavailable: ResilienceComponentKey[] = v === "insufficient" ? ["terrain_erosion_risk", "rotation_diversity"] : [];
  // Per-field synthetic level so the demo shows a spread of bands (not a method; Phase 4 defines scoring).
  const level = rng.pick([30, 48, 58, 74, 84]);
  const components: ResilienceComponent[] = COMPONENT_META.map(([key, label, support, inputs]) => {
    const missingComp = unavailable.includes(key);
    const score = missingComp ? null : Math.round(clamp(level + rng.normal(0, 11), 8, 97));
    const conf: Confidence = support === "R" ? "low" : "high";
    return {
      key, label,
      score: score === null ? missing("score_0_100", "UPSTREAM_ERROR") : q(score, "score_0_100"),
      band: bandFor(score),
      support_class: support,
      confidence: missingComp ? "low" : conf,
      input_indicator_ids: inputs.map((k) => `${field.field_id}:${k}`),
      explanation: missingComp
        ? "Not scored: required inputs are unavailable for this field."
        : `Synthetic placeholder score. In Phase 4 this component maps ${inputs.join(", ")} through a cited breakpoint table.`,
      rule_ref: method(`resilience_${key}_breakpoints`, `${label} breakpoint table`, "Breakpoints pending (Phase 4)."),
    };
  });
  const used = components.filter((c) => c.score.value !== null);
  const enough = used.length >= 3;
  const mean = enough ? Math.round(used.reduce((a, c) => a + (c.score.value as number), 0) / used.length) : null;
  const order: Confidence[] = ["low", "medium", "high"];
  const conf = used.reduce<Confidence>((lo, c) => (order.indexOf(c.confidence) < order.indexOf(lo) ? c.confidence : lo), "high");
  const limitations: QualityFlag[] = [{ code: "REGIONAL_COMPONENT", severity: "info", message: "Climate exposure uses regional-context inputs (POWER ~55 km, SMAP 9 km)." }];
  if (!enough) limitations.push({ code: "INSUFFICIENT_COMPONENTS", severity: "warning", message: `Only ${used.length} of 4 components are available; a composite needs at least 3.` });
  return {
    profile_id: uuid(), field_id: field.field_id, as_of: DEMO_AS_OF, model_version: RESILIENCE_MODEL,
    status: enough ? "computed" : "insufficient_data",
    composite: { score: mean === null ? missing("score_0_100", "INSUFFICIENT_COVERAGE") : q(mean, "score_0_100"), band: bandFor(mean), confidence: enough ? conf : "low", components_used: used.length, components_total: 4 },
    components, limitations, disclaimers,
  };
}

// ───────────────────────── Recommendations & scenarios ─────────────────────────
const FIT_ORDER: FitBand[] = ["suitable", "marginal", "unsuitable", "unknown"];
function worst(bands: FitBand[]): FitBand {
  const known = bands.filter((b) => b !== "unknown");
  if (!known.length) return "unknown";
  return known.reduce((a, b) => (FIT_ORDER.indexOf(b) > FIT_ORDER.indexOf(a) ? b : a), "suitable");
}

export function recommendation(rec: MockFieldRecord, seasonYear: number, uuid: () => string, kbEvidence: Record<string, string>): RotationRecommendation {
  const { field, traits } = rec;
  const disclaimers = [
    "Synthetic demo recommendation — the rules-based engine and cited crop knowledge base arrive in Phase 5.",
    "Not a yield, price or profit forecast.",
    "Factors marked “Regional context” cannot make a crop unsuitable on their own.",
  ];
  const base = {
    recommendation_id: uuid(), field_id: field.field_id,
    target_season: { label: `${seasonYear} season`, start: `${seasonYear - 1}-09-01`, end: `${seasonYear}-11-30` },
    engine_version: ENGINE_VERSION, kb_version: KB_VERSION, generated_at: `${DEMO_AS_OF}T09:00:00Z`, disclaimers,
  };
  if (traits.variant === "failed" || traits.variant === "processing_user") {
    return { ...base, status: traits.variant === "failed" ? "insufficient_data" : "pending", candidates: [], excluded: [] };
  }
  const soil = soilProfile(rec);
  const terr = terrainProfile(rec);
  const hist = traits.history;
  const last = hist[hist.length - 1];
  const recent = hist.slice(-5);
  const rng = createRng(`${field.field_id}:rec:${seasonYear}`);
  const candidates = CROPS.filter((c) => c.crop_code !== 61 && c.crop_code !== 236).map((crop) => {
    const pick = (): FitBand => { const r = rng.next(); return r < 0.68 ? "suitable" : r < 0.93 ? "marginal" : "unsuitable"; };
    const regional = (): FitBand => (rng.chance(0.75) ? "suitable" : "marginal");
    const fa = (factor: FactorAssessment["factor"], band: FitBand, observed: Quantity | null, support: "F" | "S" | "R"): FactorAssessment => ({
      factor, band, observed, requirement: PENDING_KB_REQUIREMENT, support_class: support, evidence_ids: kbEvidence[factor] ? [kbEvidence[factor]] : [],
    });
    const factors: FactorAssessment[] = [
      fa("ph", pick(), soil.layers[0].ph_h2o, "F"),
      fa("drainage", pick(), null, "F"),
      fa("water_holding", pick(), soil.aws_0_150, "F"),
      fa("slope", terr && terr.slope_p90_pct.value !== null ? pick() : "unknown", terr?.slope_p90_pct ?? null, "F"),
      fa("gdd", regional(), null, "R"),
      fa("regional_climate", regional(), null, "R"),
      fa("rotation_history", crop.crop_code === last ? "marginal" : "suitable", null, "F"),
    ];
    const effects: QualityFlag[] = [];
    if (crop.crop_code === last) effects.push({ code: "REPEATS_LAST_CROP", severity: "warning", message: `Would repeat ${LATEST_CROP_YEAR}'s crop (${cropName(last)}).` });
    if (!recent.includes(crop.crop_code)) effects.push({ code: "NEW_IN_RECENT_HISTORY", severity: "info", message: `Not grown on this field in ${LATEST_CROP_YEAR - 4}–${LATEST_CROP_YEAR} (synthetic history).` });
    const runOfLast = (() => { let n = 0; for (let i = hist.length - 1; i >= 0 && hist[i] === last; i--) n++; return n; })();
    if (crop.crop_code !== last && runOfLast >= 2) effects.push({ code: "BREAKS_RUN", severity: "info", message: `Breaks a ${runOfLast}-year ${cropName(last)} run.` });
    const overall = worst(factors.map((f) => f.band));
    const marginal = factors.filter((f) => f.band === "marginal").length;
    return {
      crop, factors, effects, overall, marginal,
      score: FIT_ORDER.indexOf(overall) * 10 + marginal - (crop.crop_code !== last ? 0.5 : 0) - (effects.some((e) => e.code === "BREAKS_RUN") ? 0.5 : 0),
    };
  });
  candidates.sort((a, b) => a.score - b.score);
  const out: RecommendationCandidate[] = candidates.slice(0, 5).map((c, i) => ({
    rank: i + 1,
    crop_code: c.crop.crop_code,
    crop_name: c.crop.name,
    overall: c.overall,
    confidence: c.factors.some((f) => f.band === "unknown") ? "low" : c.marginal > 1 ? "low" : "medium",
    factors: c.factors,
    rotation_effects: c.effects,
    reasons: [
      `Synthetic placeholder: limiting factor is ${c.overall === "suitable" ? "none (all factors suitable)" : c.factors.find((f) => f.band === c.overall)?.factor.replace("_", " ")}.`,
      "Cited reasons are generated by the Phase 5 rotation engine.",
    ],
  }));
  return {
    ...base,
    status: "computed",
    candidates: out,
    excluded: [
      { crop_code: 61, crop_name: "Fallow/Idle Cropland", reason: "Not offered as a crop option (fallow is evaluated inside rotation scenarios)." },
      { crop_code: 236, crop_name: "Dbl Crop WinWht/Sorghum", reason: "Knowledge-base entry incomplete in the synthetic KB." },
    ],
  };
}

export function evaluateScenario(rec: MockFieldRecord, sequence: ScenarioYear[]): ScenarioEvaluation {
  const key = `${rec.field.field_id}:${sequence.map((s) => s.crop_code).join("-")}`;
  const rng = createRng(key);
  const pick = (): FitBand => { const r = rng.next(); return r < 0.55 ? "suitable" : r < 0.88 ? "marginal" : "unsuitable"; };
  const dims: ScenarioEvaluation["dimensions"] = [
    { key: "agronomic_fit", band: pick(), explanation: "Synthetic placeholder band — per-year agronomic checks come from the Phase 5 knowledge base." },
    { key: "rotation_benefit", band: pick(), explanation: "Synthetic placeholder band — rotation rules (predecessor effects, breaks) are Phase 5." },
    { key: "water_risk", band: pick(), explanation: "Synthetic placeholder band — will combine crop water need with regional climate context." },
    { key: "diversity", band: new Set(sequence.map((s) => s.crop_code)).size >= 3 ? "suitable" : new Set(sequence.map((s) => s.crop_code)).size === 2 ? "marginal" : "unsuitable", explanation: `${new Set(sequence.map((s) => s.crop_code)).size} distinct crops across ${sequence.length} years (factual count).` },
  ];
  const hist = rec.traits.history;
  const yearFindings = sequence.map((s, i) => {
    const prev = i === 0 ? hist[hist.length - 1] : sequence[i - 1].crop_code;
    const messages: QualityFlag[] = [];
    if (s.crop_code === prev) messages.push({ code: "REPEAT", severity: "warning", message: `Repeats the previous year's crop (${cropName(prev)}).` });
    if (s.crop_code === 61) messages.push({ code: "FALLOW", severity: "info", message: "Fallow year." });
    if (CROPS.find((c) => c.crop_code === s.crop_code)?.is_double_crop) messages.push({ code: "DOUBLE_CROP", severity: "info", message: "Double-crop year — two harvests in one season." });
    if (!hist.includes(s.crop_code)) messages.push({ code: "NEW_CROP", severity: "info", message: "Not grown on this field since 2006 (synthetic history)." });
    return { year: s.year, band: messages.some((m) => m.severity === "warning") ? "marginal" as FitBand : pick(), messages, evidence_ids: [] };
  });
  const ov = worst(dims.map((d) => d.band));
  const interpretation: ScenarioInterpretation =
    ov === "suitable" ? "supported" : ov === "marginal" ? "conditional" : ov === "unsuitable" ? "not_recommended" : "insufficient_data";
  return {
    engine_version: ENGINE_VERSION,
    kb_version: KB_VERSION,
    overall: ov,
    interpretation,
    dimensions: dims,
    year_findings: yearFindings,
    warnings: [{ code: "SYNTHETIC_EVALUATION", severity: "warning", message: "Synthetic evaluation: bands are placeholders until the rules-based rotation engine arrives in Phase 5. Only the repeat/fallow/double-crop/new-crop notes are factual." }],
    evaluated_at: new Date().toISOString(),
  };
}

// ───────────────────────── Field evidence ─────────────────────────
export function fieldEvidence(rec: MockFieldRecord, indicators: EnvironmentalIndicator[], uuid: () => string): EvidenceItem[] {
  return indicators.map((ind) => ({
    evidence_id: uuid(),
    kind: "indicator",
    title: ind.label,
    summary: `Synthetic indicator for ${rec.field.name}. Method: ${ind.method.name}. Support: ${ind.spatial.support_class}.`,
    field_id: rec.field.field_id,
    dataset_id: "synthetic",
    product_version: "synthetic-0",
    citation: null,
    url: null,
    doi: null,
    accessed_at: DEMO_AS_OF,
    verification_status: "SYNTHETIC",
    spatial: ind.spatial,
    temporal: ind.temporal,
    related_ids: [ind.indicator_id, ind.key],
  }));
}

// ───────────────────────── Phase 6: Field Suitability ─────────────────────────
export const CROP_AGRONOMIC_DESCRIPTIONS: Record<string, string> = {
  CRP001: "Corn (Zea mays L.) is a warm-season annual C4 cereal requiring 1,167–1,556 GDD (Tbase 10°C, Tcap 30°C) and 500–800 mm water. Highly productive on fertile, well-drained loams with pH 6.0–6.8. Heavy user of nitrogen and soil moisture, with vulnerability to heat and drought stress during silking.",
  CRP002: "Soybean (Glycine max (L.) Merr.) is a warm-season annual legume requiring 1,000–1,450 GDD (Tbase 10°C) and 450–700 mm water. Fixes atmospheric nitrogen via Bradyrhizobium (70–140 kg N/ha) on soils with pH 6.0–6.8. Critical cash oilseed and break crop following corn or winter wheat; sensitive to high-pH chlorosis and waterlogging.",
  CRP003: "Winter Wheat (Triticum aestivum L.) is a cool-season annual cereal requiring vernalization (4–8 weeks at 0–7°C), 1,800–2,400 GDD (Tbase 0°C), and 350–550 mm water. Excellent winter ground cover and erosion barrier on soils with pH 6.0–7.0. Foundational high-plains cash cereal with moderate drought and cold tolerance.",
  CRP004: "Spring Wheat (Triticum aestivum L.) is a cool-season non-vernalizing annual cereal requiring 1,150–1,400 GDD (Tbase 0°C) and 250–500 mm water on well-drained soils with pH 6.0–7.0. Fast-maturing spring cash grain and flexible replant option; sensitive to high temperatures (>32°C) during flowering.",
  CRP005: "Grain Sorghum (Sorghum bicolor (L.) Moench) is a warm-season C4 grain requiring 944–1,333 GDD (Tbase 10°C) and 350–500 mm water on diverse soils with pH 5.5–7.8. Exemplary dryland cash crop with exceptional drought and heat tolerance via waxy leaf cuticles; ideal low-moisture break crop following wheat.",
  CRP006: "Cotton (Gossypium hirsutum L.) is a warm-season perennial grown as an annual fiber crop requiring 1,167–1,444 GDD (Tbase 15.6°C, Tcap 32°C) and 500–750 mm water. Requires deep well-drained loam (pH 6.0–7.0) and >180 frost-free days. Deep taproot aids subsoil moisture capture; sensitive to chilling injury and standing water.",
  CRP007: "Rice (Oryza sativa L.) is a semi-aquatic warm-season annual cereal requiring 1,167–1,556 GDD (Tbase 10°C) and 900–1,200 mm seasonal water. Adapted to poorly drained lowlands and claypan soils (pH 5.5–6.8) under flooding; agronomically unsuitable on well-drained upland fields without impoundments.",
  CRP008: "Barley (Hordeum vulgare L.) is a cool-season annual small grain requiring 1,100–1,600 GDD (Tbase 0°C) and 300–450 mm water on well-drained loams (pH 6.0–7.5). Short growing cycle allows early harvest; exhibits highest salinity and drought tolerance among small grains, but poor tolerance to waterlogged soils.",
  CRP009: "Cereal Rye (Secale cereale L.) is an exceptionally cold-hardy cool-season annual grass germinating near 1°C, requiring 900–1,400 GDD and 300–450 mm water. Thrives across marginal, acidic (pH 4.5–7.5) sandy soils. Premier cover crop offering massive biomass, weed suppression, and aggressive nitrate scavenging.",
  CRP010: "Oats (Avena sativa L.) is a cool-season annual cereal requiring 1,300–1,700 GDD (Tbase 4.4°C) and 350–500 mm water on soils with pH 6.0–7.0. Reliable non-winterhardy cover and nurse crop for alfalfa; rapid autumn biomass establishment and effective surface nutrient scavenging.",
  CRP011: "Alfalfa (Medicago sativa L.) is a perennial deep-rooted legume forage requiring 2,200–3,500 GDD across multiple cuts and 600–1,000 mm water on deep well-drained soils (pH 6.5–7.5). Fixes extensive nitrogen (150–250 kg N/ha/yr) and breaks subsoils via deep taproots; requires a 1–2 year rotational break due to autotoxicity.",
  CRP012: "Hairy Vetch (Vicia villosa Roth) is a winter-hardy annual legume cover crop requiring 1,100–1,600 GDD and 350–600 mm water on soils with pH 5.5–7.5. Fixes substantial atmospheric nitrogen (90–180 kg N/ha) released quickly to subsequent summer crops; outstanding winter-survival among annual legumes.",
  CRP013: "Crimson Clover (Trifolium incarnatum L.) is a cool-season annual legume cover crop requiring 1,000–1,500 GDD and 500–800 mm water on well-drained soils (pH 6.0–7.0). Rapid spring biomass development, moderate nitrogen fixation (70–140 kg N/ha), and early pollinator forage; easily terminated before summer planting.",
  CRP014: "Oilseed Radish (Raphanus sativus L. var. oleiferus) is a specialty brassica cover crop requiring 600–1,000 GDD and 300–500 mm water on medium soils with pH 6.0–7.5. Aggressive tuberous taproot performs biological subsoiling to alleviate plow pan compaction and scavenges up to 150–220 kg N/ha of residual nitrate; reliably winter-kills below -6°C.",
};

const CANONICAL_CROPS_SPEC = [
  { id: "CRP001", name: "Corn (Maize)", cdl: 1, family: "Poaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 6.8, 5.5, 7.8], gdd: [1167, 1556], p: [400, 1000] },
  { id: "CRP002", name: "Soybean", cdl: 5, family: "Fabaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 6.8, 5.8, 7.5], gdd: [1000, 1450], p: [400, 950] },
  { id: "CRP003", name: "Winter Wheat", cdl: 24, family: "Poaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 7.0, 5.5, 8.2], gdd: [1800, 2400], p: [300, 1000] },
  { id: "CRP004", name: "Spring Wheat", cdl: 24, family: "Poaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 7.0, 5.5, 8.2], gdd: [1150, 1400], p: [250, 750] },
  { id: "CRP005", name: "Grain Sorghum", cdl: 4, family: "Poaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 7.5, 5.2, 8.5], gdd: [944, 1333], p: [350, 800] },
  { id: "CRP006", name: "Cotton", cdl: 2, family: "Malvaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 7.0, 5.5, 8.2], gdd: [1167, 1444], p: [450, 1100] },
  { id: "CRP007", name: "Rice", cdl: 3, family: "Poaceae", role: "specialty_cash_grain", cover: false, ph: [5.5, 6.8, 4.8, 7.8], gdd: [1167, 1556], p: [200, 1000] },
  { id: "CRP008", name: "Barley", cdl: 21, family: "Poaceae", role: "primary_cash_grain", cover: false, ph: [6.0, 7.5, 5.5, 8.5], gdd: [1100, 2100], p: [250, 750] },
  { id: "CRP009", name: "Cereal Rye", cdl: 27, family: "Poaceae", role: "cool_season_cover", cover: true, ph: [6.0, 7.0, 4.5, 8.2], gdd: [900, 2200], p: [300, 900] },
  { id: "CRP010", name: "Oats", cdl: 28, family: "Poaceae", role: "cool_season_cover", cover: true, ph: [6.0, 7.0, 5.0, 8.0], gdd: [1300, 1700], p: [350, 850] },
  { id: "CRP011", name: "Alfalfa", cdl: 36, family: "Fabaceae", role: "forage_perennial", cover: false, ph: [6.5, 7.5, 6.0, 8.0], gdd: [2200, 3500], p: [450, 1200] },
  { id: "CRP012", name: "Hairy Vetch", cdl: null, family: "Fabaceae", role: "cool_season_cover", cover: true, ph: [6.0, 7.0, 5.2, 7.8], gdd: [1100, 1600], p: [350, 1100] },
  { id: "CRP013", name: "Crimson Clover", cdl: null, family: "Fabaceae", role: "cool_season_cover", cover: true, ph: [6.0, 7.0, 5.5, 7.5], gdd: [1000, 1500], p: [500, 1100] },
  { id: "CRP014", name: "Oilseed Radish", cdl: null, family: "Brassicaceae", role: "specialty_cover_crop", cover: true, ph: [6.0, 7.5, 5.5, 8.0], gdd: [600, 1000], p: [300, 600] },
];

export function fieldSuitability(rec: MockFieldRecord, seasonYear = 2026): FieldSuitabilityResponse {
  const phVal = rec.traits.ph;
  const drainVal = "moderately_well_drained";
  const gddObs = 2862;
  const pObs = 650;

  const crops: CropSuitabilityAssessment[] = CANONICAL_CROPS_SPEC.map((spec) => {
    const factors: SuitabilityFactorAssessment[] = [];
    const limiting: string[] = [];
    const favorable: string[] = [];

    // 1. pH
    const [optMin, optMax, tolMin, tolMax] = spec.ph;
    let phComp: SuitabilityFactorAssessment["compatibility"] = "optimal";
    let phSev: SuitabilityFactorAssessment["severity"] = "favorable";
    let phScore = 95;
    let phInterp = `Topsoil pH (${phVal.toFixed(1)}) is optimal (${optMin}–${optMax}).`;

    if (phVal < tolMin || phVal > tolMax) {
      phComp = "critical_limitation";
      phSev = "critical";
      phScore = 20;
      phInterp = `Topsoil pH (${phVal.toFixed(1)}) violates physiological limits (${tolMin}–${tolMax}).`;
      limiting.push(`[CRITICAL] Soil pH: ${phInterp}`);
    } else if (phVal < optMin || phVal > optMax) {
      phComp = "moderate_limitation";
      phSev = "moderate";
      phScore = 65;
      phInterp = `Topsoil pH (${phVal.toFixed(1)}) is sub-optimal; tolerated range is ${tolMin}–${tolMax}.`;
      limiting.push(`[MODERATE] Soil pH: ${phInterp}`);
    } else {
      favorable.push(`Soil pH: ${phInterp}`);
    }

    factors.push({
      factor_key: "soil_ph",
      factor_name: "Soil pH (0–30 cm)",
      category: "soil",
      observed_value: { value: phVal, unit: "pH", uncertainty: null, missing_reason: null },
      crop_requirement: `Optimal: ${optMin}–${optMax}; Tolerated: ${tolMin}–${tolMax}`,
      compatibility: phComp,
      is_limiting: phSev === "moderate" || phSev === "critical",
      is_favorable: phSev === "favorable",
      severity: phSev,
      score: phScore,
      interpretation: phInterp,
      evidence_ids: ["EV0008", "EV0042"],
      data_status: "available",
      support_class: "F",
    });

    // 2. Drainage
    let drainComp: SuitabilityFactorAssessment["compatibility"] = "optimal";
    let drainSev: SuitabilityFactorAssessment["severity"] = "favorable";
    let drainScore = 95;
    let drainInterp = `Drainage class (${drainVal}) provides adequate root aeration.`;

    if (spec.id === "CRP007") {
      // Rice prefers poor drainage
      if (drainVal.includes("poorly")) {
        drainComp = "optimal";
        drainSev = "favorable";
        drainScore = 95;
      } else {
        drainComp = "moderate_limitation";
        drainSev = "moderate";
        drainScore = 55;
        drainInterp = `Well-drained soil increases water loss for flooded paddy culture.`;
        limiting.push(`[MODERATE] Soil Drainage: ${drainInterp}`);
      }
    } else if (drainVal.includes("poorly")) {
      drainComp = spec.id === "CRP011" ? "critical_limitation" : "moderate_limitation";
      drainSev = spec.id === "CRP011" ? "critical" : "moderate";
      drainScore = spec.id === "CRP011" ? 20 : 55;
      drainInterp = `Poor drainage elevates root rot and seedling anoxia risk.`;
      limiting.push(`[${drainSev === "critical" ? "CRITICAL" : "MODERATE"}] Soil Drainage: ${drainInterp}`);
    } else {
      favorable.push(`Soil Drainage: ${drainInterp}`);
    }

    factors.push({
      factor_key: "soil_drainage",
      factor_name: "Soil Drainage Class",
      category: "soil",
      observed_value: { value: null, unit: "unitless", uncertainty: null, missing_reason: null },
      crop_requirement: spec.id === "CRP007" ? "Poorly drained / claypan" : "Well to moderately well drained",
      compatibility: drainComp,
      is_limiting: drainSev === "moderate" || drainSev === "critical",
      is_favorable: drainSev === "favorable",
      severity: drainSev,
      score: drainScore,
      interpretation: drainInterp,
      evidence_ids: ["EV0008", "EV0012"],
      data_status: "available",
      support_class: "F",
    });

    // 3. Thermal GDD
    factors.push({
      factor_key: "thermal_gdd",
      factor_name: "Growing Degree Days",
      category: "thermal",
      observed_value: { value: gddObs, unit: "degC_day", uncertainty: null, missing_reason: null },
      crop_requirement: `${spec.gdd[0]}–${spec.gdd[1]} °C-days`,
      compatibility: "optimal",
      is_limiting: false,
      is_favorable: true,
      severity: "favorable",
      score: 95,
      interpretation: `Observed GDD (${gddObs} °C-days) satisfies maturity requirements.`,
      evidence_ids: ["EV0003"],
      data_status: "available",
      support_class: "R",
    });
    favorable.push(`Thermal GDD: Observed ${gddObs} °C-days satisfies maturity requirements.`);

    // 4. Precipitation
    factors.push({
      factor_key: "water_precipitation",
      factor_name: "Seasonal Precipitation",
      category: "water_climate",
      observed_value: { value: pObs, unit: "mm", uncertainty: null, missing_reason: null },
      crop_requirement: `${spec.p[0]}–${spec.p[1]} mm`,
      compatibility: "optimal",
      is_limiting: false,
      is_favorable: true,
      severity: "favorable",
      score: 90,
      interpretation: `Observed seasonal precipitation (${pObs} mm) is within normal range (${spec.p[0]}–${spec.p[1]} mm).`,
      evidence_ids: ["EV0005"],
      data_status: "available",
      support_class: "R",
    });

    // Class & Score Determination
    const hasCrit = factors.some((f) => f.severity === "critical");
    const modCount = factors.filter((f) => f.severity === "moderate").length;
    let sClass: SuitabilityClass = "suitable";
    let score = 90.0;

    if (hasCrit) {
      sClass = "unsuitable";
      score = 25.0;
    } else if (modCount >= 3) {
      sClass = "limited_suitability";
      score = 52.0;
    } else if (modCount >= 1) {
      sClass = "conditionally_suitable";
      score = 68.0;
    } else {
      sClass = "suitable";
      score = 88.0;
    }

    return {
      crop_id: spec.id,
      crop_name: spec.name,
      cdl_code: spec.cdl,
      botanical_family: spec.family,
      portfolio_role: spec.role,
      is_cover_crop: spec.cover,
      assessment_status: "evaluated",
      suitability_class: sClass,
      suitability_score: score,
      score_methodology: `Multi-factor limiting-factor model for ${spec.name} (${score}/100).`,
      factor_assessments: factors,
      limiting_factors: limiting,
      favorable_factors: favorable,
      unknown_factors: [],
      data_quality: { status: "valid", completeness: 1.0, flags: [], missing_reason: null },
      spatial_support: { support_class: "F", native_resolution_m: 30, extraction_method: "vector_intersection", field_fraction_of_cell: null, cell_id: null, crs: "EPSG:4326" },
      temporal_support: { resolution: "season", period_start: `${seasonYear}-01-01`, period_end: `${seasonYear}-12-31`, aggregation: "mean", time_standard: "UTC" },
      evidence_ids: ["EV0001", "EV0003", "EV0008"],
      explanation: `${spec.name} is classified as ${sClass.replace("_", " ")}.\n\n${CROP_AGRONOMIC_DESCRIPTIONS[spec.id] ?? ""}${limiting.length ? `\n\nIdentified limitations (${limiting.length}):\n${limiting.map((l) => `• ${l}`).join("\n")}` : "\n\nFavorable conditions: High environmental compatibility."}`,
      limitations: [
        "Synthetic decision-support demonstration value.",
        "Does not guarantee commercial emergence or yield.",
      ],
    };
  });

  // Sort eligible crops by Phase 6 suitability score descending with deterministic tie-breaking (Task 8)
  crops.sort((a, b) => {
    const aUnsuitable = a.suitability_class === "unsuitable" ? 1 : 0;
    const bUnsuitable = b.suitability_class === "unsuitable" ? 1 : 0;
    if (aUnsuitable !== bUnsuitable) return aUnsuitable - bUnsuitable;
    const scoreDiff = (b.suitability_score ?? 0) - (a.suitability_score ?? 0);
    if (Math.abs(scoreDiff) > 1e-4) return scoreDiff;
    const limDiff = a.limiting_factors.length - b.limiting_factors.length;
    if (limDiff !== 0) return limDiff;
    return a.crop_name.localeCompare(b.crop_name);
  });

  return {
    field_id: rec.field.field_id,
    season_year: seasonYear,
    as_of: DEMO_AS_OF,
    engine_version: ENGINE_VERSION,
    kb_version: KB_VERSION,
    status: "evaluated",
    summary: {
      total_evaluated: crops.length,
      suitable: crops.filter((c) => c.suitability_class === "suitable").length,
      conditionally_suitable: crops.filter((c) => c.suitability_class === "conditionally_suitable").length,
      limited_suitability: crops.filter((c) => c.suitability_class === "limited_suitability").length,
      unsuitable: crops.filter((c) => c.suitability_class === "unsuitable").length,
      insufficient_data: crops.filter((c) => c.suitability_class === "insufficient_data").length,
    },
    crops,
    disclaimers: [
      "Synthetic demonstration: suitability indicators generated for offline UI evaluation.",
      "In live mode, evaluations run against USDA SSURGO, NASA POWER, NASA SRTM, and the Phase 5 Crop KB.",
    ],
  };
}

// ───────────────────────── Phase 7: Rotation Generator & Comparison ─────────────────────────
export function mockGenerateRotations(rec: MockFieldRecord, req: GenerateRotationsRequest): GenerateRotationsResponse {
  const horizon = Math.max(2, Math.min(5, req.horizon || 3));
  const startYear = req.start_year || 2026;
  const hist = rec.traits.history;
  const lastCode = hist.length > 0 ? hist[hist.length - 1] : 24;

  const candidateTemplates = [
    { name: "Wheat – Sorghum – Soybean", codes: [24, 4, 5, 27, 36] },
    { name: "Corn – Soybean – Winter Wheat", codes: [1, 5, 24, 4, 27] },
    { name: "Sorghum – Soybean – Cereal Rye", codes: [4, 5, 27, 24, 36] },
    { name: "Wheat – Fallow – Sorghum", codes: [24, 61, 4, 5, 27] },
    { name: "Oats – Alfalfa – Corn", codes: [28, 36, 1, 5, 24] },
  ];

  const maxCands = Math.min(candidateTemplates.length, req.max_candidates || 10);
  const candidates: GenerateCandidate[] = [];

  for (let i = 0; i < maxCands; i++) {
    const tpl = candidateTemplates[i];
    const cropCodes = tpl.codes.slice(0, horizon);
    const seq: ScenarioYear[] = cropCodes.map((code, idx) => ({
      year: startYear + idx,
      crop_code: code,
      crop_name: cropName(code),
    }));

    const evaluation = evaluateScenario(rec, seq);
    candidates.push({
      rank: i + 1,
      name: tpl.name,
      sequence: seq,
      evaluation,
      is_pareto_optimal: true,
      pareto_rank: 1,
      pareto_explanation: null,
    });
  }

  // Fast Non-dominated Sorting for Pareto frontier
  const bandScores: Record<string, number> = { suitable: 2, marginal: 1, unsuitable: 0, unknown: 0 };
  const dimKeys = ["agronomic_fit", "rotation_benefit", "water_risk", "diversity"];
  const n = candidates.length;
  const vectors = candidates.map((c) => {
    const dMap = Object.fromEntries(c.evaluation.dimensions.map((d) => [d.key, bandScores[d.band] ?? 0]));
    return dimKeys.map((k) => dMap[k] ?? 0);
  });

  const dominatedBy = new Array(n).fill(0);
  const dominates: number[][] = Array.from({ length: n }, () => []);

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      const vi = vectors[i];
      const vj = vectors[j];
      const ge = vi.every((x, idx) => x >= vj[idx]);
      const gt = vi.some((x, idx) => x > vj[idx]);
      if (ge && gt) {
        dominates[i].push(j);
        dominatedBy[j]++;
      }
    }
  }

  let currentFront = dominatedBy.map((count, idx) => (count === 0 ? idx : -1)).filter((idx) => idx !== -1);
  const ranks = new Array(n).fill(1);
  let frontNum = 1;

  while (currentFront.length > 0) {
    const nextFront: number[] = [];
    for (const i of currentFront) {
      ranks[i] = frontNum;
      for (const j of dominates[i]) {
        dominatedBy[j]--;
        if (dominatedBy[j] === 0) {
          nextFront.push(j);
        }
      }
    }
    if (nextFront.length > 0) {
      frontNum++;
    }
    currentFront = nextFront;
  }

  candidates.forEach((c, idx) => {
    const isOpt = ranks[idx] === 1;
    c.is_pareto_optimal = isOpt;
    c.pareto_rank = ranks[idx];
    if (isOpt) {
      const v = vectors[idx];
      c.pareto_explanation = v.every((x) => x === 2)
        ? "Pareto Nondominated (Frontier 1): Achieves maximum suitability across all 4 evaluation dimensions."
        : "Pareto Nondominated (Frontier 1): Multi-objective optimum; no candidate dominates this sequence across all dimensions.";
    } else {
      const domIdx = dominates.findIndex((list) => list.includes(idx));
      c.pareto_explanation = `Pareto Dominated (Frontier ${ranks[idx]}): Outperformed across evaluated dimensions by sequence #${candidates[domIdx >= 0 ? domIdx : 0].rank}.`;
    }
  });

  const antecedentCrop: ScenarioYear | null = hist.length > 0 ? {
    year: startYear - 1,
    crop_code: lastCode,
    crop_name: cropName(lastCode),
  } : null;

  return {
    field_id: rec.field.field_id,
    horizon,
    start_year: startYear,
    antecedent_crop: antecedentCrop,
    candidates,
    pareto_optimal_count: candidates.filter((c) => c.is_pareto_optimal).length,
    generated_at: new Date().toISOString(),
  };
}

export function mockCompareScenarios(fieldId: string, scenarios: RotationScenario[]): CompareScenariosResponse {
  const tradeoffs: TradeoffFinding[] = [
    {
      category: "diversity",
      summary: scenarios.length > 1
        ? `'${scenarios[0].name}' incorporates diverse grass and broadleaf families compared to '${scenarios[1].name}', mitigating soil-borne fungal pressure.`
        : "Single scenario evaluated for diversity.",
    },
    {
      category: "water_risk",
      summary: "Rotations featuring sorghum and winter wheat conserve subsoil moisture better under semiarid climate conditions.",
    },
    {
      category: "agronomic_fit",
      summary: "All compared scenarios meet the baseline biophysical suitability requirements of the field.",
    },
  ];

  return {
    field_id: fieldId,
    scenarios,
    tradeoffs,
  };
}


