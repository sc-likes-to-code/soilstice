/** Presentation formatting. The API is metric-canonical (rule R2); imperial is display-only. */
import type { MissingReason, Quantity, Unit } from "@/types/contracts";

export type UnitSystem = "metric" | "us";

const METRIC_LABEL: Record<Unit, string> = {
  mm: "mm", degC: "°C", degC_day: "°C·d", percent: "%", "MJ_m-2_day-1": "MJ m⁻² d⁻¹", "MJ_m-2": "MJ m⁻²",
  "m3_m-3": "m³ m⁻³", wetness_0_1: "(0–1)", cm: "cm", "cm_cm-1": "cm cm⁻¹", m: "m", degree: "°", pH: "", ha: "ha",
  day: "days", year: "yr", count: "", percentile: "th pct", unitless: "", score_0_100: "/ 100",
};

interface Converted { value: number; label: string; }

function convert(value: number, unit: Unit, system: UnitSystem): Converted {
  if (system === "metric") return { value, label: METRIC_LABEL[unit] };
  switch (unit) {
    case "mm": return { value: value / 25.4, label: "in" };
    case "cm": return { value: value / 2.54, label: "in" };
    case "m": return { value: value * 3.28084, label: "ft" };
    case "ha": return { value: value * 2.47105, label: "ac" };
    case "degC": return { value: value * 1.8 + 32, label: "°F" };
    case "degC_day": return { value: value * 1.8, label: "°F·d" };
    default: return { value, label: METRIC_LABEL[unit] };
  }
}

function decimals(unit: Unit, v: number, system: UnitSystem): number {
  if (system === "us" && (unit === "mm" || unit === "cm")) return Math.abs(v) < 10 ? 2 : 1;
  switch (unit) {
    case "m3_m-3": case "cm_cm-1": case "wetness_0_1": return 2;
    case "unitless": return Math.abs(v) < 10 ? 2 : 1;
    case "pH": return 1;
    case "count": case "day": case "year": case "percentile": case "score_0_100": case "degC_day": case "MJ_m-2": return 0;
    case "mm": return Math.abs(v) >= 100 ? 0 : 1;
    default: return Math.abs(v) >= 100 ? 0 : 1;
  }
}

export function formatNumber(v: number, dp: number): string {
  return v.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export interface FormattedQuantity {
  text: string;
  unit: string;
  missing: boolean;
  reason: MissingReason | null;
  range: string | null;
}

export function formatQuantity(q: Quantity | null | undefined, system: UnitSystem = "metric", opts?: { signed?: boolean }): FormattedQuantity {
  if (!q || q.value === null) {
    return { text: "—", unit: q ? convert(0, q.unit, system).label : "", missing: true, reason: q?.missing_reason ?? "NOT_COMPUTED", range: null };
  }
  const c = convert(q.value, q.unit, system);
  const dp = decimals(q.unit, c.value, system);
  const sign = opts?.signed && c.value > 0 ? "+" : "";
  let range: string | null = null;
  const u = q.uncertainty;
  if (u && (u.kind === "range" || u.kind === "ci95") && u.low !== null && u.high !== null) {
    const lo = convert(u.low, q.unit, system).value;
    const hi = convert(u.high, q.unit, system).value;
    range = `${formatNumber(lo, dp)}–${formatNumber(hi, dp)}`;
  } else if (u && u.kind === "std" && u.value !== null) {
    range = `± ${formatNumber(u.value, dp)}`;
  }
  return { text: sign + formatNumber(c.value, dp), unit: c.label, missing: false, reason: null, range };
}

/** "123 mm" convenience string. */
export function qText(q: Quantity | null | undefined, system: UnitSystem = "metric", opts?: { signed?: boolean }): string {
  const f = formatQuantity(q, system, opts);
  if (f.missing) return "—";
  if (!f.unit) return f.text;
  return f.unit === "%" || f.unit.startsWith("th") ? `${f.text}${f.unit}` : `${f.text} ${f.unit}`;
}

export function unitLabel(unit: Unit, system: UnitSystem = "metric"): string {
  return convert(1, unit, system).label;
}

export function convertValue(v: number | null, unit: Unit, system: UnitSystem): number | null {
  return v === null ? null : convert(v, unit, system).value;
}

export const MISSING_REASON_TEXT: Record<MissingReason, string> = {
  NO_DATA_SOURCE: "No data source covers this location.",
  FILL_VALUE: "The source reported a fill (no-data) value.",
  QA_MASKED_CLOUD: "Masked by cloud in the quality band.",
  QA_MASKED_SHADOW: "Masked by cloud shadow.",
  QA_MASKED_SNOW: "Masked by snow or ice.",
  QA_LOW_QUALITY_RETRIEVAL: "Retrieval flagged as low quality.",
  INSUFFICIENT_COVERAGE: "Not enough valid observations to compute this.",
  OUT_OF_TEMPORAL_RANGE: "Outside the dataset's temporal coverage.",
  UPSTREAM_ERROR: "The upstream data service failed for this request.",
  NOT_YET_PUBLISHED: "The source has not published this period yet.",
  NOT_COMPUTED: "Not computed yet.",
  OUTSIDE_AOI: "Outside the supported area of interest.",
  PENDING_PROCESSING: "Waiting for processing to finish.",
};

export function missingText(reason: MissingReason | null | undefined): string {
  return reason ? MISSING_REASON_TEXT[reason] : "Value unavailable.";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(iso: string | null | undefined, style: "short" | "long" | "month" = "short"): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (style === "month") return `${MONTHS[m - 1]} ${y}`;
  if (style === "long") return `${MONTHS[m - 1]} ${d}, ${y}`;
  return `${MONTHS[m - 1]} ${d}`;
}

export function monthLabel(iso: string): string {
  return MONTHS[Number(iso.slice(5, 7)) - 1];
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const dt = new Date(iso);
  return `${formatDate(iso, "long")} · ${String(dt.getUTCHours()).padStart(2, "0")}:${String(dt.getUTCMinutes()).padStart(2, "0")} UTC`;
}

export function pct(v: number | null | undefined, dp = 0): string {
  return v === null || v === undefined ? "—" : `${formatNumber(v * 100, dp)}%`;
}

export function resolutionText(m: number | null | undefined): string {
  if (m === null || m === undefined) return "vector";
  if (m >= 1000) return `${formatNumber(m / 1000, m % 1000 === 0 ? 0 : 1)} km`;
  return `${m} m`;
}
