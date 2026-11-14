/** Presentation vocabularies: colours and labels keyed by contract enums. No analytics here. */
import type { Confidence, CoverageStatus, CropCode, DatasetId, FitBand, ScoreBand, Severity, SupportClass, VerificationStatus } from "@/types/contracts";

export const CROP_COLORS: Record<number, string> = {
  1: "#d9a92e", // Corn
  4: "#b8642f", // Sorghum
  5: "#4f7d3a", // Soybeans
  24: "#9c6b37", // Winter wheat
  26: "#7c8a3c", // Dbl WW/Soy
  236: "#a5743a", // Dbl WW/Sorghum
  36: "#8a6f9e", // Alfalfa
  61: "#bdb29b", // Fallow
  176: "#c9c2a3", // Grassland/Pasture
};
export function cropColor(code: CropCode | null | undefined): string {
  return code === null || code === undefined ? "#d8d0bd" : CROP_COLORS[code] ?? "#a59c88";
}

export const CROP_SHORT: Record<number, string> = {
  1: "Corn", 4: "Sorghum", 5: "Soy", 24: "Wheat", 26: "Wheat/Soy", 236: "Wheat/Sorg", 36: "Alfalfa", 61: "Fallow", 176: "Grass",
};
export const CROP_ABBR: Record<number, string> = { 1: "CRN", 4: "SRG", 5: "SOY", 24: "WHT", 26: "W/S", 236: "W/SG", 36: "ALF", 61: "FAL", 176: "GRS" };
export const cropAbbr = (code: CropCode | null | undefined) => (code === null || code === undefined ? "—" : CROP_ABBR[code] ?? String(code));

export const cropShort = (code: CropCode | null | undefined, fallback?: string | null) =>
  code === null || code === undefined ? fallback ?? "—" : CROP_SHORT[code] ?? fallback ?? `CDL ${code}`;

export const BAND_STYLE: Record<ScoreBand, { label: string; fg: string; bg: string; dot: string; fill: string }> = {
  high: { label: "High", fg: "text-forest-800", bg: "bg-forest-100", dot: "bg-forest-600", fill: "#366645" },
  moderate: { label: "Moderate", fg: "text-wheat-600", bg: "bg-wheat-100", dot: "bg-wheat-500", fill: "#c99a3e" },
  low: { label: "Low", fg: "text-clay-600", bg: "bg-clay-100", dot: "bg-clay-500", fill: "#b4623a" },
  unknown: { label: "Unknown", fg: "text-stone-600", bg: "bg-parchment", dot: "bg-stone-400", fill: "#a59c88" },
};

export const FIT_STYLE: Record<FitBand, { label: string; fg: string; bg: string; dot: string }> = {
  suitable: { label: "Suitable", fg: "text-forest-800", bg: "bg-forest-100", dot: "bg-forest-600" },
  marginal: { label: "Marginal", fg: "text-wheat-600", bg: "bg-wheat-100", dot: "bg-wheat-500" },
  unsuitable: { label: "Unsuitable", fg: "text-clay-600", bg: "bg-clay-100", dot: "bg-clay-500" },
  unknown: { label: "Unknown", fg: "text-stone-600", bg: "bg-parchment", dot: "bg-stone-400" },
};

export const CONFIDENCE_LABEL: Record<Confidence, string> = { high: "High confidence", medium: "Medium confidence", low: "Low confidence" };

export const SUPPORT_STYLE: Record<SupportClass, { short: string; long: string; fg: string; bg: string; border: string }> = {
  F: { short: "Field", long: "Field-resolved", fg: "text-forest-800", bg: "bg-forest-50", border: "border-forest-200" },
  S: { short: "Local grid", long: "Sub-regional grid", fg: "text-sky-600", bg: "bg-sky-100/60", border: "border-sky-100" },
  R: { short: "Regional", long: "Regional context — not a field measurement", fg: "text-wheat-600", bg: "bg-wheat-100/70", border: "border-wheat-200" },
};

export const SEVERITY_STYLE: Record<Severity, { fg: string; bg: string; border: string }> = {
  info: { fg: "text-sky-600", bg: "bg-sky-100/50", border: "border-sky-100" },
  warning: { fg: "text-wheat-600", bg: "bg-wheat-100/60", border: "border-wheat-200" },
  critical: { fg: "text-clay-600", bg: "bg-clay-100/70", border: "border-clay-100" },
};

export const COVERAGE_STYLE: Record<CoverageStatus, { label: string; fg: string; dot: string }> = {
  available: { label: "Available", fg: "text-forest-700", dot: "bg-forest-500" },
  partial: { label: "Partial", fg: "text-wheat-600", dot: "bg-wheat-500" },
  missing: { label: "Missing", fg: "text-clay-600", dot: "bg-clay-500" },
  pending: { label: "Pending", fg: "text-sky-600", dot: "bg-sky-500" },
  not_applicable: { label: "Not applicable", fg: "text-stone-500", dot: "bg-stone-400" },
  not_integrated: { label: "Not yet integrated", fg: "text-stone-500", dot: "bg-line-strong" },
};

export const VERIFICATION_STYLE: Record<VerificationStatus, { label: string; fg: string; bg: string }> = {
  LIVE: { label: "Live-tested", fg: "text-forest-800", bg: "bg-forest-100" },
  CMR: { label: "NASA CMR", fg: "text-forest-800", bg: "bg-forest-100" },
  DOC: { label: "Official docs", fg: "text-sky-600", bg: "bg-sky-100" },
  UNVERIFIED: { label: "Unverified", fg: "text-wheat-600", bg: "bg-wheat-100" },
  SYNTHETIC: { label: "Synthetic", fg: "text-clay-600", bg: "bg-clay-100" },
};

export const DATASET_SHORT: Record<DatasetId, string> = {
  nasa_power_daily_ag: "NASA POWER", usda_nrcs_ssurgo_sda: "SSURGO", usda_nass_cdl: "CDL", usda_nass_csb: "CSB",
  nasa_hls: "HLS SR", nasa_hls_vi: "HLS-VI", nasa_smap_spl4smgp: "SMAP L4", nasa_srtm_gl1: "SRTM",
  prism_daily: "PRISM", openet: "OpenET", usda_nass_quickstats: "Quick Stats", nasa_smap_spl3smp_e: "SMAP L3",
  nasa_gpm_imerg: "IMERG", fao_gaez_v5: "GAEZ v5", soilstice_derived: "SOILSTICE", user_input: "User input", synthetic: "Synthetic",
};
