"use client";
import { Database, ExternalLink, FlaskConical } from "lucide-react";
import type { Confidence, FitBand, QualityFlag, QualityInfo, ScoreBand, SourceRef, SpatialSupport, TemporalSupport, Quantity } from "@/types/contracts";
import { cn } from "@/lib/cn";
import { BAND_STYLE, CONFIDENCE_LABEL, FIT_STYLE, SEVERITY_STYLE, SUPPORT_STYLE } from "@/lib/vocab";
import { formatDate, formatQuantity, missingText, pct, resolutionText } from "@/lib/format";
import { usePrefs } from "@/hooks/preferences";
import { Badge, Dot, Tip } from "@/components/ui/primitives";

const EXTRACTION_TEXT: Record<SpatialSupport["extraction_method"], string> = {
  zonal_polygon: "Zonal statistics over the field polygon",
  zonal_polygon_inward_buffer: "Zonal statistics over the field polygon, 15 m inward buffer",
  containing_cell: "Value of the grid cell containing the field",
  api_point_query: "Point query at the field centroid",
  vector_intersection: "Intersection of survey polygons with the field",
  attribute_join: "Attribute join",
  not_applicable: "Not applicable",
};

/** Field / local grid / regional context badge (UI_ARCHITECTURE §3.3). */
export function SupportBadge({ spatial, className }: { spatial: SpatialSupport; className?: string }) {
  const s = SUPPORT_STYLE[spatial.support_class];
  const res = resolutionText(spatial.native_resolution_m);
  const label = spatial.support_class === "R" ? `Regional · ${res}` : spatial.support_class === "S" ? `Local grid · ${res}` : `Field · ${res}`;
  return (
    <Tip
      content={
        <span className="block space-y-1">
          <span className="block font-semibold">{s.long}</span>
          <span className="block text-forest-200">{EXTRACTION_TEXT[spatial.extraction_method]}.</span>
          <span className="block text-forest-200">Native resolution: {res}{spatial.crs ? ` · ${spatial.crs}` : ""}</span>
          {spatial.field_fraction_of_cell !== null && <span className="block text-forest-200">This field covers {pct(spatial.field_fraction_of_cell, 1)} of the grid cell.</span>}
          {spatial.support_class === "R" && <span className="block text-wheat-200">Describes the surrounding region — not measured in this field.</span>}
        </span>
      }
    >
      <Badge className={cn("border", s.bg, s.fg, s.border, className)}>
        <span className={cn("h-1.5 w-1.5 rounded-full", spatial.support_class === "F" ? "bg-forest-500" : spatial.support_class === "S" ? "bg-sky-500" : "bg-wheat-500")} />
        {label}
      </Badge>
    </Tip>
  );
}

export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <Badge className={cn("border border-clay-100 bg-clay-100/70 text-clay-600", className)} title="Synthetic demo data — not an observation">
      <FlaskConical className="h-3 w-3" aria-hidden /> Synthetic
    </Badge>
  );
}

/** Source chip: product + version; synthetic variant (rule R6). */
export function SourceChip({ source, className }: { source: SourceRef; className?: string }) {
  const synthetic = source.dataset_id === "synthetic";
  return (
    <Tip
      content={
        <span className="block space-y-1">
          <span className="block font-semibold">{source.product}</span>
          <span className="block text-forest-200">Version {source.product_version}{source.doi ? ` · DOI ${source.doi}` : ""}</span>
          {synthetic && <span className="block text-wheat-200">Synthetic demo value generated in Phase 1. Real ingestion arrives in Phase 3.</span>}
          {source.retrieved_at && <span className="block text-forest-200">Retrieved {formatDate(source.retrieved_at, "long")}</span>}
        </span>
      }
    >
      <Badge className={cn("border", synthetic ? "border-clay-100 bg-clay-100/50 text-clay-600" : "border-line bg-parchment/60 text-ink-soft", className)}>
        {synthetic ? <FlaskConical className="h-3 w-3" aria-hidden /> : <Database className="h-3 w-3" aria-hidden />}
        {synthetic ? source.product.replace("Synthetic stand-in for ", "Synthetic · ") : `${source.product} ${source.product_version}`}
      </Badge>
    </Tip>
  );
}

export function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      {sources.map((s, i) => (
        <SourceChip key={i} source={s} />
      ))}
    </span>
  );
}

export function QualityIndicator({ quality, className }: { quality: QualityInfo; className?: string }) {
  const color = quality.status === "valid" ? "bg-forest-500" : quality.status === "partial" ? "bg-wheat-500" : quality.status === "flagged" ? "bg-wheat-600" : "bg-clay-500";
  const label = quality.status === "valid" ? "Valid" : quality.status === "partial" ? "Partial" : quality.status === "flagged" ? "Flagged" : "Missing";
  const flags = quality.flags.filter((f) => f.code !== "SYNTHETIC");
  return (
    <Tip
      content={
        <span className="block space-y-1">
          <span className="block font-semibold">Quality: {label}</span>
          {quality.completeness !== null && <span className="block text-forest-200">Completeness {pct(quality.completeness)}</span>}
          {quality.missing_reason && <span className="block text-wheat-200">{missingText(quality.missing_reason)}</span>}
          {flags.map((f) => (
            <span key={f.code} className="block text-forest-200">• {f.message}</span>
          ))}
        </span>
      }
    >
      <span className={cn("inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-ink-soft", className)}>
        <Dot className={color} /> {label}
        {quality.completeness !== null && quality.status !== "valid" && <span className="text-stone-500">· {pct(quality.completeness)}</span>}
      </span>
    </Tip>
  );
}

/** Formats any Quantity; null values show an em dash with the missing reason (rule R5). */
export function QuantityValue({ q, className, unitClassName, signed, showRange = true }: { q: Quantity | null | undefined; className?: string; unitClassName?: string; signed?: boolean; showRange?: boolean }) {
  const { units } = usePrefs();
  const f = formatQuantity(q, units, { signed });
  if (f.missing) {
    return (
      <Tip content={missingText(f.reason)}>
        <span className={cn("tabular text-stone-400", className)} aria-label={`Unavailable: ${missingText(f.reason)}`}>—</span>
      </Tip>
    );
  }
  return (
    <span className={cn("tabular", className)}>
      {f.text}
      {f.unit && <span className={cn("ml-0.5 text-[0.62em] font-normal text-stone-500", unitClassName)}>{f.unit === "%" ? "%" : ` ${f.unit}`}</span>}
      {showRange && f.range && <span className="ml-1.5 text-[0.6em] font-normal text-stone-500">({f.range})</span>}
    </span>
  );
}

export function ScoreBandPill({ band, confidence, className }: { band: ScoreBand; confidence?: Confidence; className?: string }) {
  const s = BAND_STYLE[band];
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <Badge className={cn(s.bg, s.fg)}>
        <Dot className={s.dot} /> {s.label}
      </Badge>
      {confidence && <span className="text-[11px] font-medium text-stone-500">{CONFIDENCE_LABEL[confidence]}</span>}
    </span>
  );
}

export function FitBandPill({ band, confidence, className }: { band: FitBand; confidence?: Confidence; className?: string }) {
  const s = FIT_STYLE[band];
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <Badge className={cn(s.bg, s.fg)}>
        <Dot className={s.dot} /> {s.label}
      </Badge>
      {confidence && <span className="text-[11px] font-medium text-stone-500">{CONFIDENCE_LABEL[confidence]}</span>}
    </span>
  );
}

export function FlagList({ flags, hideSynthetic = true, className }: { flags: QualityFlag[]; hideSynthetic?: boolean; className?: string }) {
  const list = hideSynthetic ? flags.filter((f) => f.code !== "SYNTHETIC") : flags;
  if (!list.length) return null;
  return (
    <ul className={cn("space-y-1.5", className)}>
      {list.map((f, i) => {
        const s = SEVERITY_STYLE[f.severity];
        return (
          <li key={`${f.code}-${i}`} className={cn("rounded-lg border px-3 py-2 text-[12.5px] leading-relaxed", s.bg, s.border)}>
            <span className={cn("mr-1.5 font-mono text-[10.5px] font-semibold uppercase", s.fg)}>{f.code.replaceAll("_", " ")}</span>
            <span className="text-ink-soft">{f.message}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function TemporalText({ t }: { t: TemporalSupport }) {
  const res: Record<TemporalSupport["resolution"], string> = { PT3H: "3-hourly", P1D: "daily", P1M: "monthly", season: "season", P1Y: "annual", static: "static", irregular: "per scene" };
  const period = t.period_start ? `${formatDate(t.period_start, "month")}${t.period_end ? ` – ${formatDate(t.period_end, "month")}` : ""}` : "";
  return (
    <span className="text-[11.5px] text-stone-500">
      {res[t.resolution]}
      {t.aggregation !== "none" ? ` · ${t.aggregation.replace("_", " ")}` : ""}
      {period ? ` · ${period}` : ""}
      {t.time_standard !== "not_applicable" ? ` · ${t.time_standard}` : ""}
    </span>
  );
}

export function DocLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-forest-700 underline decoration-forest-300 underline-offset-2 hover:text-forest-900">
      {children} <ExternalLink className="h-3 w-3" aria-hidden />
    </a>
  );
}
