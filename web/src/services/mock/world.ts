/**
 * Synthetic demo world: farms, fields and per-field latent traits.
 * Geometry is synthetic (rectangles / pivot circles inside an approximate AOI bbox) — NOT copied from CSB
 * (API_CONTRACTS §8 rule 5). Nothing here is an observation.
 */
import type { AoiId, CropCode, Farm, Field, GeoJSONMultiPolygon } from "@/types/contracts";
import { centroidOfRing, multiPolygonAreaHa, rectangleFromMetres, ringToMultiPolygon, type LngLat } from "@/lib/geo";
import { createRng, round, type Rng } from "./rng";
import { DEMO_AS_OF, q, synthSource } from "./catalog";

export const SEED = "soilstice-demo-v1";

export { AOI_BBOX } from "@/lib/aoi";

export const AOI_META: Record<AoiId, { label: string; county_fips: string[]; farmName: string; center: LngLat }> = {
  ks_reno: { label: "Reno County, Kansas", county_fips: ["20155"], farmName: "Reno Demo Farm", center: [-98.06, 37.95] },
  ks_finney: { label: "Finney County, Kansas", county_fips: ["20055"], farmName: "Finney Demo Farm", center: [-100.72, 38.02] },
};

export type FieldVariant = "full" | "cloudy" | "insufficient" | "failed" | "processing_user";

export interface FieldTraits {
  aoi: AoiId;
  variant: FieldVariant;
  textureClass: string;
  ph: number;
  om: number;
  slopeMean: number;
  elevation: number;
  history: CropCode[]; // 2006..2025
  purity: number[];
  csbDisagree: number[]; // years where CSB disagrees
  climateBias: number;
  irrigatedLook: boolean;
}

export interface MockFieldRecord {
  field: Field;
  traits: FieldTraits;
}

const ROTATION_TEMPLATES: Record<AoiId, CropCode[][]> = {
  ks_reno: [[24, 26, 4], [24, 4, 5], [1, 5], [24, 236, 5, 1], [24, 24, 4], [36, 36, 36, 36, 24, 4], [5, 24, 4]],
  ks_finney: [[24, 4, 61], [1, 1, 24, 61], [24, 61], [1, 1, 1, 5], [36, 36, 36, 36, 1], [24, 4, 61, 24, 61]],
};
const AOI_CROPS: Record<AoiId, CropCode[]> = {
  ks_reno: [24, 1, 4, 5, 26, 36, 236],
  ks_finney: [24, 1, 4, 61, 36, 5],
};
const TEXTURES: Record<AoiId, string[]> = {
  ks_reno: ["Silt loam", "Loam", "Silty clay loam", "Fine sandy loam"],
  ks_finney: ["Silt loam", "Loam", "Fine sandy loam", "Loamy fine sand"],
};

/** Field plan per AOI: [grid col, grid row, shape, variant, source] */
type Shape = "quarter" | "half" | "pivot" | "eighty";
const PLAN: Record<AoiId, [number, number, Shape, FieldVariant, "synthetic" | "user"][]> = {
  ks_reno: [
    [0, 0, "quarter", "full", "synthetic"],
    [1, 0, "half", "full", "synthetic"],
    [3, 0, "quarter", "cloudy", "synthetic"],
    [0, 1, "quarter", "full", "synthetic"],
    [2, 1, "quarter", "insufficient", "synthetic"],
    [3, 1, "eighty", "full", "synthetic"],
    [1, 2, "quarter", "failed", "synthetic"],
    [2, 2, "quarter", "processing_user", "user"],
  ],
  ks_finney: [
    [0, 0, "pivot", "full", "synthetic"],
    [1, 0, "pivot", "full", "synthetic"],
    [2, 0, "half", "full", "synthetic"],
    [0, 1, "pivot", "cloudy", "synthetic"],
    [1, 1, "quarter", "full", "synthetic"],
    [2, 1, "pivot", "insufficient", "synthetic"],
  ],
};

const MILE = 1609.34;

function shapeGeometry(sw: LngLat, shape: Shape, rng: Rng): GeoJSONMultiPolygon {
  const inset = 25 + rng.range(0, 25);
  const metresToDeg = (m: number, lat: number): LngLat => [m / (111320 * Math.cos((lat * Math.PI) / 180)), m / 110540];
  const [dx, dy] = metresToDeg(inset, sw[1]);
  const origin: LngLat = [sw[0] + dx, sw[1] + dy];
  const half = MILE / 2 - inset * 2;
  switch (shape) {
    case "quarter":
      return rectangleFromMetres(origin, half, half);
    case "eighty":
      return rectangleFromMetres(origin, half, half / 2);
    case "half":
      return rectangleFromMetres(origin, MILE - inset * 2, half);
    case "pivot": {
      const r = half / 2;
      const [cx, cy] = metresToDeg(r, sw[1]);
      const c: LngLat = [origin[0] + cx, origin[1] + cy];
      const ring: LngLat[] = [];
      for (let i = 0; i <= 64; i++) {
        const a = (i / 64) * Math.PI * 2;
        const [ox, oy] = metresToDeg(r, c[1]);
        ring.push([c[0] + ox * Math.cos(a), c[1] + oy * Math.sin(a)]);
      }
      ring[64] = ring[0];
      return ringToMultiPolygon(ring);
    }
  }
}

function buildHistory(aoi: AoiId, rng: Rng): { history: CropCode[]; purity: number[]; csbDisagree: number[] } {
  const tpl = rng.pick(ROTATION_TEMPLATES[aoi]);
  const offset = rng.int(0, tpl.length - 1);
  const history: CropCode[] = [];
  const purity: number[] = [];
  for (let i = 0; i < 20; i++) {
    let c = tpl[(i + offset) % tpl.length];
    if (rng.chance(0.12)) c = rng.pick(AOI_CROPS[aoi]);
    history.push(c);
    purity.push(rng.chance(0.08) ? round(rng.range(0.46, 0.58), 2) : round(rng.range(0.66, 0.97), 2));
  }
  const csbDisagree = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025].filter(() => rng.chance(0.08));
  return { history, purity, csbDisagree };
}

export interface World {
  farms: Farm[];
  fields: MockFieldRecord[];
  uuid: () => string;
}

export function buildWorld(): World {
  const rng = createRng(SEED);
  const uuid = () => rng.uuid();
  const farms: Farm[] = [];
  const fields: MockFieldRecord[] = [];
  const letters = "ABCDEFGHIJKLMNOP";

  (Object.keys(PLAN) as AoiId[]).forEach((aoi) => {
    const meta = AOI_META[aoi];
    const farm_id = uuid();
    const created = "2026-11-01T09:00:00Z";
    const farmFields: MockFieldRecord[] = [];
    const originLon = meta.center[0] - (2 * MILE) / (111320 * Math.cos((meta.center[1] * Math.PI) / 180));
    const originLat = meta.center[1] - (1.5 * MILE) / 110540;

    PLAN[aoi].forEach(([col, row, shape, variant, source], idx) => {
      const frng = createRng(`${SEED}:${aoi}:${idx}`);
      const sw: LngLat = [
        originLon + (col * MILE) / (111320 * Math.cos((meta.center[1] * Math.PI) / 180)),
        originLat + (row * MILE) / 110540,
      ];
      const geometry = shapeGeometry(sw, shape, frng);
      const ring = geometry.coordinates[0][0] as LngLat[];
      const centroid = centroidOfRing(ring);
      const { history, purity, csbDisagree } = buildHistory(aoi, frng);
      const traits: FieldTraits = {
        aoi,
        variant,
        textureClass: frng.pick(TEXTURES[aoi]),
        ph: round(frng.range(5.9, 7.6), 1),
        om: round(frng.range(1.1, 2.9), 1),
        slopeMean: round(frng.range(0.3, 3.6), 1),
        elevation: round(aoi === "ks_reno" ? frng.range(450, 495) : frng.range(860, 905), 0),
        history,
        purity,
        csbDisagree,
        climateBias: frng.range(-0.04, 0.04),
        irrigatedLook: shape === "pivot",
      };
      const prefix = aoi === "ks_reno" ? "" : "F-";
      const isUser = source === "user";
      const field: Field = {
        field_id: uuid(),
        farm_id,
        name: isUser ? `Demo User Field ${prefix}${letters[idx]}` : `Demo Field ${prefix}${letters[idx]}`,
        geometry,
        centroid: [round(centroid[0], 5), round(centroid[1], 5)],
        area: q(round(multiPolygonAreaHa(geometry), 1), "ha"),
        state_fips: "20",
        county_fips: meta.county_fips[0].slice(2),
        source,
        source_ref: isUser ? null : synthSource("usda_nass_csb"),
        csb_id: null,
        editable: isUser,
        processing_status: variant === "failed" ? "failed" : variant === "processing_user" ? "processing" : variant === "cloudy" || variant === "insufficient" ? "partial" : "ready",
        latest_job_id: null,
        created_at: created,
      };
      farmFields.push({ field, traits });
    });

    const total = farmFields.reduce((a, f) => a + (f.field.area.value ?? 0), 0);
    farms.push({
      farm_id,
      name: meta.farmName,
      aoi: { aoi_id: aoi, label: meta.label, county_fips: meta.county_fips, state: "KS" },
      field_count: farmFields.length,
      total_area: q(round(total, 1), "ha"),
      created_at: created,
      updated_at: `${DEMO_AS_OF}T09:00:00Z`,
    });
    fields.push(...farmFields);
  });

  return { farms, fields, uuid };
}

export function traitsForNewUserField(aoi: AoiId, seed: string): FieldTraits {
  const frng = createRng(seed);
  const { history, purity, csbDisagree } = buildHistory(aoi, frng);
  return {
    aoi,
    variant: "processing_user",
    textureClass: frng.pick(TEXTURES[aoi]),
    ph: round(frng.range(5.9, 7.6), 1),
    om: round(frng.range(1.1, 2.9), 1),
    slopeMean: round(frng.range(0.3, 3.6), 1),
    elevation: round(aoi === "ks_reno" ? frng.range(450, 495) : frng.range(860, 905), 0),
    history,
    purity,
    csbDisagree,
    climateBias: frng.range(-0.04, 0.04),
    irrigatedLook: false,
  };
}
