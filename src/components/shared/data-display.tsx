"use client";
import { useState } from "react";
import { ChevronDown, Info } from "lucide-react";
import type { CropYear, DataCoverage, EnvironmentalIndicator, EvidenceItem } from "@/types/contracts";
import { cn } from "@/lib/cn";
import { COVERAGE_STYLE, DATASET_SHORT, VERIFICATION_STYLE, cropAbbr, cropColor, cropShort } from "@/lib/vocab";
import { formatQuantity, missingText, pct, resolutionText } from "@/lib/format";
import { usePrefs } from "@/hooks/preferences";
import { Badge, Dot, Tip } from "@/components/ui/primitives";
import { DocLink, FlagList, QualityIndicator, QuantityValue, SourceList, SupportBadge, TemporalText } from "./provenance";

/** Indicator card: label, value, reference delta, support badge, source chip, method popover. */
export function IndicatorCard({ indicator, className, size = "md" }: { indicator: EnvironmentalIndicator; className?: string; size?: "sm" | "md" }) {
  const { units } = usePrefs();
  const [open, setOpen] = useState(false);
  const ref = indicator.reference_value;
  const hasDelta = ref && ref.value !== null && indicator.value.value !== null;
  const delta = hasDelta ? indicator.value.value! - ref!.value! : null;
  const flags = indicator.quality.flags.filter((f) => f.code !== "SYNTHETIC");
  return (
    <div className={cn("flex flex-col min-w-0 max-w-full overflow-hidden rounded-xl border border-line bg-paper p-4 transition-shadow hover:shadow-[var(--shadow-card)]", className)}>
      <div className="flex items-start justify-between gap-2 min-w-0">
        <p className="min-w-0 flex-1 truncate text-[12.5px] font-semibold leading-snug text-ink-soft" title={indicator.label}>{indicator.label}</p>
        <SupportBadge spatial={indicator.spatial} className="shrink-0" />
      </div>
      <div className={cn("mt-2 min-w-0 truncate font-display font-medium leading-none text-ink", size === "sm" ? "text-[22px]" : "text-[28px]")}>
        <QuantityValue q={indicator.value} signed={indicator.key === "precip_anomaly_pct" || indicator.key === "water_balance_season"} />
      </div>
      <div className="mt-2 min-h-[18px] text-[12px] text-ink-soft min-w-0">
        {indicator.value.value === null ? (
          <span className="text-stone-500 truncate block">{missingText(indicator.value.missing_reason)}</span>
        ) : hasDelta ? (
          <span className="truncate block">
            Normal {formatQuantity(ref, units).text} {formatQuantity(ref, units).unit} ·{" "}
            <span className={cn("font-semibold", delta! >= 0 ? "text-forest-700" : "text-clay-600")}>{delta! >= 0 ? "+" : ""}{formatQuantity({ ...ref!, value: delta }, units).text}</span>
          </span>
        ) : (
          <span className="truncate block"><TemporalText t={indicator.temporal} /></span>
        )}
      </div>
      <div className="mt-3 flex min-w-0 flex-wrap items-center gap-1.5 border-t border-line/70 pt-3">
        <div className="min-w-0 max-w-[calc(100%-80px)] flex-1 overflow-hidden">
          <SourceList sources={indicator.sources} />
        </div>
        <QualityIndicator quality={indicator.quality} className="ml-auto shrink-0" />
      </div>
      <button onClick={() => setOpen((o) => !o)} className="mt-2 inline-flex items-center gap-1 self-start text-[11.5px] font-semibold text-forest-700 hover:text-forest-900" aria-expanded={open}>
        <Info className="h-3 w-3" aria-hidden /> Method {open ? "▴" : "▾"}
      </button>
      {open && (
        <div className="mt-2 space-y-2 rounded-lg bg-cream/70 p-3 text-[12px] leading-relaxed text-ink-soft break-words">
          <p><span className="font-semibold text-ink">{indicator.method.name}</span> · v{indicator.method.version}</p>
          <p className="break-words">{indicator.method.description}</p>
          <p className="text-stone-500">Nature: {indicator.nature.replace("_", " ")} · <TemporalText t={indicator.temporal} /></p>
          <FlagList flags={flags} />
        </div>
      )}
    </div>
  );
}

/** Per-dataset coverage table (UI_ARCHITECTURE §3.3). */
export function CoverageTable({ coverage, condensed }: { coverage: DataCoverage; condensed?: boolean }) {
  // Filter out not_applicable, not_integrated, and globally remove NDVI/NDMI entries (Tasks 1 & 2)
  const activeDatasets = coverage.datasets.filter(
    (d) =>
      d.status !== "not_applicable" &&
      d.status !== "not_integrated" &&
      d.dataset_id !== "nasa_hls_vi" &&
      d.dataset_id !== "nasa_hls" &&
      !d.label.toLowerCase().includes("ndvi") &&
      !d.label.toLowerCase().includes("ndmi")
  );
  const rows = condensed ? activeDatasets.filter((d) => d.priority === "P0") : activeDatasets;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-[12.5px]">
        <thead>
          <tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500">
            <th className="py-2 pr-3 font-semibold">Dataset</th>
            <th className="py-2 pr-3 font-semibold">Status</th>
            <th className="py-2 pr-3 font-semibold">Support</th>
            {!condensed && <th className="py-2 pr-3 font-semibold">Coverage</th>}
            <th className="py-2 font-semibold">Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => {
            const s = COVERAGE_STYLE[d.status];
            return (
              <tr key={d.dataset_id} className="border-b border-line/60 last:border-0">
                <td className="py-2.5 pr-3">
                  <span className="font-semibold text-ink">{DATASET_SHORT[d.dataset_id]}</span>
                  <span className="ml-1.5 font-mono text-[10.5px] text-stone-500">{d.priority}</span>
                </td>
                <td className="py-2.5 pr-3">
                  <span className={cn("inline-flex items-center gap-1.5 font-semibold", s.fg)}><Dot className={s.dot} /> {s.label}</span>
                </td>
                <td className="py-2.5 pr-3 text-ink-soft">{d.support_class} · {resolutionText(d.native_resolution_m)}</td>
                {!condensed && (
                  <td className="py-2.5 pr-3 tabular text-ink-soft">
                    {d.temporal_coverage.start ? d.temporal_coverage.start.slice(0, 4) : "—"}–{d.temporal_coverage.end ? d.temporal_coverage.end.slice(0, 4) : "now"}
                  </td>
                )}
                <td className="py-2.5 text-ink-soft">{d.missing_reason ? missingText(d.missing_reason) : d.note}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function CompletenessMeter({ value, className }: { value: number | null; className?: string }) {
  const v = value ?? 0;
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-parchment" role="meter" aria-valuenow={Math.round(v * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Data completeness">
        <div className="h-full rounded-full bg-forest-500 transition-all" style={{ width: `${v * 100}%` }} />
      </div>
      <span className="tabular text-[11.5px] font-semibold text-ink-soft">{value === null ? "—" : pct(value)}</span>
    </div>
  );
}

/** Year strip coloured by crop; low purity hatched; CSB disagreement marker. */
export function CropTimeline({ years, compact, highlightYear }: { years: CropYear[]; compact?: boolean; highlightYear?: number }) {
  return (
    <div>
      <div className={cn("grid gap-[3px]", compact ? "h-9" : "h-14")} style={{ gridTemplateColumns: `repeat(${years.length}, minmax(0, 1fr))` }}>
        {years.map((y) => (
          <Tip
            key={y.year}
            className="block h-full w-full"
            content={
              <span className="block space-y-0.5">
                <span className="block font-semibold">{y.year} · {y.majority.crop_name ?? "Unknown"}</span>
                <span className="block text-forest-200">Majority purity {pct(y.purity)}{y.low_purity ? " (low)" : ""}</span>
                {y.histogram.slice(1).map((h) => (
                  <span key={h.crop_code} className="block text-forest-200">{h.crop_name}: {pct(h.area_fraction)}</span>
                ))}
                {y.agrees_with_csb === false && <span className="block text-wheat-200">CSB records a different crop this year.</span>}
                {y.native_resolution_m === null && <span className="block text-forest-200">Native pixel size to be confirmed at ingest.</span>}
              </span>
            }
          >
            <span
              className={cn("relative block h-full w-full rounded-[3px] ring-offset-1 transition-transform hover:-translate-y-0.5", y.low_purity && "hatch", highlightYear === y.year && "ring-2 ring-forest-800")}
              style={{ backgroundColor: cropColor(y.majority.crop_code) }}
              aria-label={`${y.year}: ${y.majority.crop_name}`}
            >
              {y.agrees_with_csb === false && <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full border border-paper bg-clay-500" />}
              {!compact && <span className="absolute inset-x-0 bottom-1 text-center text-[9px] font-bold uppercase tracking-tight text-white/90 [text-shadow:0_1px_1px_rgba(0,0,0,0.35)] max-md:hidden">{cropAbbr(y.majority.crop_code)}</span>}
            </span>
          </Tip>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-stone-500 tabular">
        <span>{years[0]?.year}</span>
        <span>{years[Math.floor(years.length / 2)]?.year}</span>
        <span>{years[years.length - 1]?.year}</span>
      </div>
    </div>
  );
}

export function CropLegend({ codes }: { codes: number[] }) {
  const uniq = [...new Set(codes)];
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1.5">
      {uniq.map((c) => (
        <span key={c} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink-soft">
          <span className="h-2.5 w-2.5 rounded-[3px]" style={{ backgroundColor: cropColor(c) }} /> {cropShort(c)}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5 text-[11.5px] text-ink-soft"><span className="hatch h-2.5 w-2.5 rounded-[3px] bg-stone-400" /> Low purity</span>
      <span className="inline-flex items-center gap-1.5 text-[11.5px] text-ink-soft"><span className="h-2 w-2 rounded-full bg-clay-500" /> CSB disagrees</span>
    </div>
  );
}

/** Evidence list grouped by kind with verification status. */
export function EvidenceList({ items, groupByKind = true }: { items: EvidenceItem[]; groupByKind?: boolean }) {
  const order: EvidenceItem["kind"][] = ["dataset", "method", "kb_rule", "indicator", "literature"];
  const titles: Record<EvidenceItem["kind"], string> = { dataset: "Datasets", method: "Methods", kb_rule: "Knowledge-base rules", indicator: "Indicators", literature: "Literature" };
  const groups = groupByKind ? order.map((k) => ({ k, list: items.filter((i) => i.kind === k) })).filter((g) => g.list.length) : [{ k: "all" as const, list: items }];
  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <EvidenceGroup key={g.k} title={g.k === "all" ? null : titles[g.k as EvidenceItem["kind"]]} items={g.list} />
      ))}
    </div>
  );
}

function EvidenceGroup({ title, items }: { title: string | null; items: EvidenceItem[] }) {
  const [expanded, setExpanded] = useState(items.length <= 8);
  const shown = expanded ? items : items.slice(0, 6);
  return (
    <div>
      {title && <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-stone-500">{title} <span className="text-stone-400">· {items.length}</span></h4>}
      <ul className="divide-y divide-line/70 rounded-xl border border-line bg-paper">
        {shown.map((e) => {
          const v = VERIFICATION_STYLE[e.verification_status];
          return (
            <li key={e.evidence_id} className="flex flex-wrap items-start gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-ink">{e.title}</p>
                <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-soft">{e.summary}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11.5px]">
                  {e.citation && <span className="text-stone-500">{e.citation}</span>}
                  {e.doi && <span className="font-mono text-stone-500">doi:{e.doi}</span>}
                  {e.url && <DocLink href={e.url}>Documentation</DocLink>}
                  {e.spatial && <SupportBadge spatial={e.spatial} />}
                </div>
              </div>
              <Badge className={cn(v.bg, v.fg)}>{v.label}</Badge>
            </li>
          );
        })}
      </ul>
      {items.length > 6 && (
        <button onClick={() => setExpanded((x) => !x)} className="mt-2 inline-flex items-center gap-1 text-[12px] font-semibold text-forest-700">
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} aria-hidden /> {expanded ? "Show fewer" : `Show all ${items.length}`}
        </button>
      )}
    </div>
  );
}
