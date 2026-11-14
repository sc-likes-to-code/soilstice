/**
 * Small, dependency-free geometry helpers (presentation + client-side validation only).
 * Authoritative area/AOI checks happen in the backend (EPSG:5070); these are approximations for UX.
 */
import type { GeoJSONMultiPolygon } from "@/types/contracts";

export type LngLat = [number, number];
export type Bbox = [number, number, number, number]; // [west, south, east, north]

const R = 6378137; // WGS84 semi-major axis (m)

/** Spherical-excess polygon area of a closed or open ring, in square metres (good to <1% at field scale). */
export function ringAreaM2(ring: LngLat[]): number {
  const pts = closeRing(ring);
  if (pts.length < 4) return 0;
  let sum = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [lon1, lat1] = pts[i];
    const [lon2, lat2] = pts[i + 1];
    sum += toRad(lon2 - lon1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)));
  }
  return Math.abs((sum * R * R) / 2);
}

export function multiPolygonAreaHa(geom: GeoJSONMultiPolygon): number {
  let m2 = 0;
  for (const poly of geom.coordinates) {
    poly.forEach((ring, i) => {
      const a = ringAreaM2(ring as LngLat[]);
      m2 += i === 0 ? a : -a;
    });
  }
  return m2 / 10_000;
}

export function closeRing(ring: LngLat[]): LngLat[] {
  if (ring.length === 0) return ring;
  const [f, l] = [ring[0], ring[ring.length - 1]];
  return f[0] === l[0] && f[1] === l[1] ? ring : [...ring, f];
}

export function bboxOf(geom: GeoJSONMultiPolygon | GeoJSONMultiPolygon[]): Bbox {
  const geoms = Array.isArray(geom) ? geom : [geom];
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const g of geoms)
    for (const poly of g.coordinates)
      for (const ring of poly)
        for (const [x, y] of ring) {
          if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y;
        }
  return [w, s, e, n];
}

export function pointInBbox([x, y]: LngLat, [w, s, e, n]: Bbox): boolean {
  return x >= w && x <= e && y >= s && y <= n;
}

export function centroidOfRing(ring: LngLat[]): LngLat {
  const pts = closeRing(ring).slice(0, -1);
  const x = pts.reduce((a, p) => a + p[0], 0) / pts.length;
  const y = pts.reduce((a, p) => a + p[1], 0) / pts.length;
  return [x, y];
}

function segmentsIntersect(a: LngLat, b: LngLat, c: LngLat, d: LngLat): boolean {
  const o = (p: LngLat, q: LngLat, r: LngLat) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]));
  return o(a, b, c) !== o(a, b, d) && o(c, d, a) !== o(c, d, b);
}

/** True if a simple (non-self-intersecting) ring with ≥3 distinct vertices. */
export function isSimpleRing(ring: LngLat[]): boolean {
  const pts = closeRing(ring);
  const n = pts.length - 1;
  if (n < 3) return false;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(i - j) <= 1 || (i === 0 && j === n - 1)) continue;
      if (segmentsIntersect(pts[i], pts[i + 1], pts[j], pts[j + 1])) return false;
    }
  }
  return true;
}

export function ringToMultiPolygon(ring: LngLat[]): GeoJSONMultiPolygon {
  return { type: "MultiPolygon", coordinates: [[closeRing(ring)]] };
}

/** Axis-aligned rectangle in degrees from a SW corner and size in metres (synthetic geometry only). */
export function rectangleFromMetres(sw: LngLat, widthM: number, heightM: number): GeoJSONMultiPolygon {
  const dLat = (heightM / R) * (180 / Math.PI);
  const dLon = (widthM / (R * Math.cos(toRad(sw[1])))) * (180 / Math.PI);
  const [x, y] = sw;
  return ringToMultiPolygon([[x, y], [x + dLon, y], [x + dLon, y + dLat], [x, y + dLat], [x, y]]);
}

function toRad(d: number) {
  return (d * Math.PI) / 180;
}

export type FieldDraftIssue = "TOO_FEW_VERTICES" | "SELF_INTERSECTING" | "OUTSIDE_AOI" | "FIELD_TOO_LARGE" | "FIELD_TOO_SMALL";

/** Client-side pre-validation mirroring the E8 422 codes (PHASE_0_DECISIONS T20). */
export function validateFieldDraft(ring: LngLat[], aoiBbox: Bbox, maxHa = 260): { ok: boolean; issues: FieldDraftIssue[]; areaHa: number } {
  const issues: FieldDraftIssue[] = [];
  const distinct = ring.filter((p, i) => i === 0 || p[0] !== ring[i - 1][0] || p[1] !== ring[i - 1][1]);
  if (distinct.length < 3) return { ok: false, issues: ["TOO_FEW_VERTICES"], areaHa: 0 };
  if (!isSimpleRing(distinct)) issues.push("SELF_INTERSECTING");
  if (!distinct.every((p) => pointInBbox(p, aoiBbox))) issues.push("OUTSIDE_AOI");
  const areaHa = ringAreaM2(distinct) / 10_000;
  if (areaHa > maxHa) issues.push("FIELD_TOO_LARGE");
  if (areaHa < 0.5) issues.push("FIELD_TOO_SMALL");
  return { ok: issues.length === 0, issues, areaHa };
}
