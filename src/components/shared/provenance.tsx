"use client";
import { CheckCircle2, Clock, Database, ExternalLink, FlaskConical, HelpCircle, MapPin } from "lucide-react";
import type { Confidence, FitBand, QualityFlag, QualityInfo, ScoreBand, SourceRef, SpatialSupport, TemporalSupport, Quantity } from "@/types/contracts";
import { cn } from "@/lib/cn";
import { BAND_STYLE, CONFIDENCE_LABEL, DATASET_SHORT, FIT_STYLE, SEVERITY_STYLE, SUPPORT_STYLE } from "@/lib/vocab";
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
      <Badge className={cn("border font-medium", s.bg, s.fg, s.border, className)}>
        <span className={cn("h-1.5 w-1.5 rounded-full", spatial.support_class === "F" ? "bg-forest-500" : spatial.support_class === "S" ? "bg-sky-500" : "bg-wheat-500")} />
        {label}
      </Badge>
    </Tip>
  );
}

/** Field-supported badge (explicit green badge for field-resolved layers). */
export function FieldSupportedBadge({ resolution = "30 m", className }: { resolution?: string; className?: string }) {
  return (
    <Tip content="Field-resolved spatial support: measurement or classification mapped directly to this field's boundary.">
      <Badge className={cn("border border-forest-300 bg-forest-50 text-forest-800", className)}>
        <MapPin className="h-3 w-3 text-forest-600" aria-hidden /> Field · {resolution}
      </Badge>
    </Tip>
  );
}

/** Regional context badge (explicit badge for coarse-grid layers). */
export function RegionalContextBadge({ resolution = "~55 km", className }: { resolution?: string; className?: string }) {
  return (
    <Tip content="Regional context: describes conditions in the surrounding macro-climate or regional grid cell, not an in-situ field measurement.">
      <Badge className={cn("border border-wheat-300 bg-wheat-50 text-wheat-900", className)}>
        <span className="h-1.5 w-1.5 rounded-full bg-wheat-600" /> Regional · {resolution}
      </Badge>
    </Tip>
  );
}

/** Live provider data badge. */
export function ProviderDataBadge({ provider, className }: { provider?: string; className?: string }) {
  return (
    <Badge className={cn("border border-emerald-300 bg-emerald-50 text-emerald-800 font-medium", className)} title="Verified live observation from upstream provider">
      <CheckCircle2 className="h-3 w-3 text-emerald-600" aria-hidden /> {provider ? `${provider} live` : "Provider data"}
    </Badge>
  );
}

/** Synthetic demonstration badge. */
export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <Badge className={cn("border border-clay-200 bg-clay-100/70 text-clay-700 font-medium", className)} title="Synthetic demonstration data — not a field observation">
      <FlaskConical className="h-3 w-3 text-clay-600" aria-hidden /> Synthetic demo
    </Badge>
  );
}

/** Partial coverage badge. */
export function PartialBadge({ className }: { className?: string }) {
  return (
    <Badge className={cn("border border-wheat-300 bg-wheat-100 text-wheat-800 font-medium", className)} title="Partial coverage across requested years or extent">
      <HelpCircle className="h-3 w-3 text-wheat-600" aria-hidden /> Partial
    </Badge>
  );
}

/** Missing data badge. */
export function MissingBadge({ reason, className }: { reason?: string; className?: string }) {
  return (
    <Badge className={cn("border border-line bg-parchment/60 text-stone-500 font-medium", className)} title={reason ?? "Dataset currently missing or unavailable"}>
      Missing
    </Badge>
  );
}

/** Pending ingestion badge. */
export function PendingBadge({ className }: { className?: string }) {
  return (
    <Badge className={cn("border border-sky-300 bg-sky-50 text-sky-700 font-medium", className)} title="Dataset processing is scheduled or in progress">
      <Clock className="h-3 w-3 text-sky-600" aria-hidden /> Pending
    </Badge>
  );
}

/** Source chip: product + version; synthetic variant (rule R6). */
export function SourceChip({ source, className }: { source: SourceRef; className?: string }) {
  const synthetic = source.dataset_id === "synthetic";
  const shortName = DATASET_SHORT[source.dataset_id] ?? source.product;

  let versionLabel = source.product_version ?? "";
  if (versionLabel.includes("SDA live database")) {
    const surveyMatch = versionLabel.match(/\(([^)]+)\)/);
    versionLabel = surveyMatch ? `SDA (${surveyMatch[1].split(" saverest")[0]})` : "SDA";
  } else if (versionLabel.length > 24) {
    versionLabel = versionLabel.slice(0, 22) + "…";
  }

  const chipLabel = synthetic
    ? source.product.replace("Synthetic stand-in for ", "Synthetic · ")
    : `${shortName}${versionLabel ? ` · ${versionLabel}` : ""}`;

  return (
    <Tip
      content={
        <span className="block space-y-1">
          <span className="block font-semibold">{source.product}</span>
          <span className="block text-forest-200">Version {source.product_version}{source.doi ? ` · DOI ${source.doi}` : ""}</span>
          {synthetic ? (
            <span className="block text-wheat-200">Synthetic demonstration data generated for prototype evaluation. Live observations are retrieved via USDA and NASA endpoints in API mode.</span>
          ) : (
            <span className="block text-emerald-300">Live observation retrieved from {source.product}.</span>
          )}
          {source.retrieved_at && <span className="block text-forest-200">Retrieved {formatDate(source.retrieved_at, "long")}</span>}
        </span>
      }
    >
      <Badge
        className={cn(
          "max-w-full truncate border text-[11px] transition-colors",
          synthetic ? "border-clay-200 bg-clay-100/60 text-clay-700" : "border-line bg-parchment/60 text-ink-soft hover:border-line-strong",
          className
        )}
      >
        {synthetic ? <FlaskConical className="h-3 w-3 shrink-0 text-clay-600" aria-hidden /> : <Database className="h-3 w-3 shrink-0 text-forest-600" aria-hidden />}
        <span className="truncate max-w-[220px]">{chipLabel}</span>
      </Badge>
    </Tip>
  );
}

export function SourceList({ sources, className }: { sources: SourceRef[]; className?: string }) {
  const uniqueSources = sources.filter(
    (s, idx, arr) =>
      arr.findIndex(
        (x) =>
          x.dataset_id === s.dataset_id &&
          x.product === s.product &&
          x.product_version === s.product_version
      ) === idx
  );

  return (
    <span className={cn("inline-flex flex-wrap items-center gap-1.5 max-w-full", className)}>
      {uniqueSources.map((s, i) => (
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
      <Badge className={cn(s.bg, s.fg, "font-semibold")}>
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
      <Badge className={cn(s.bg, s.fg, "font-semibold")}>
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
  const res: Record<TemporalSupport["resolution"], string> = { PT1H: "hourly", PT3H: "3-hourly", P1D: "daily", P1M: "monthly", season: "season", P1Y: "annual", static: "static", irregular: "per scene" };
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
