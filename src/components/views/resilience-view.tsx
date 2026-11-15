"use client";
import { useState } from "react";
import { ChevronRight, ShieldCheck } from "lucide-react";
import type { ResilienceComponent, ResilienceProfile } from "@/types/contracts";
import { useEvidence, useResilience } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { BAND_STYLE, SUPPORT_STYLE } from "@/lib/vocab";
import { formatDate, missingText } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Badge, Card, CardBody, CardHeader, Skeleton } from "@/components/ui/primitives";
import { EmptyState, StateBoundary } from "@/components/shared/state";
import { EvidenceList } from "@/components/shared/data-display";
import { FlagList, QuantityValue, ScoreBandPill } from "@/components/shared/provenance";
import { CONFIDENCE_LABEL } from "@/lib/vocab";

export function ResilienceView() {
  const fieldId = useFieldId();
  const q = useResilience(fieldId);
  return (
    <StateBoundary query={q} skeleton={<div className="grid gap-6 lg:grid-cols-[360px_1fr]"><Skeleton className="h-80" /><Skeleton className="h-[480px]" /></div>}>
      {(r) => <Resilience r={r} fieldId={fieldId} />}
    </StateBoundary>
  );
}

function Gauge({ score, band }: { score: number | null; band: ResilienceProfile["composite"]["band"] }) {
  const r = 70, c = Math.PI * r;
  const frac = score === null ? 0 : score / 100;
  return (
    <svg viewBox="0 0 180 104" className="w-full max-w-[240px]" aria-hidden>
      <path d="M20 94 A70 70 0 0 1 160 94" fill="none" stroke="#ece4d3" strokeWidth="14" strokeLinecap="round" />
      {[40, 70].map((t) => {
        const a = Math.PI * (1 - t / 100);
        return <line key={t} x1={90 + 58 * Math.cos(a)} y1={94 - 58 * Math.sin(a)} x2={90 + 82 * Math.cos(a)} y2={94 - 82 * Math.sin(a)} stroke="#cfc3aa" strokeWidth="1.5" />;
      })}
      <path d="M20 94 A70 70 0 0 1 160 94" fill="none" stroke={BAND_STYLE[band].fill} strokeWidth="14" strokeLinecap="round" strokeDasharray={`${c * frac} ${c}`} style={{ transition: "stroke-dasharray 700ms cubic-bezier(.22,1,.36,1)" }} />
    </svg>
  );
}

function Resilience({ r, fieldId }: { r: ResilienceProfile; fieldId: string }) {
  const [open, setOpen] = useState<string | null>(null);
  if (r.status === "pending") {
    return <EmptyState icon={<ShieldCheck className="h-6 w-6" />} title="Resilience analysis not yet computed" description={r.limitations.map((l) => l.message).join(" ") || "Waiting for input datasets."} />;
  }
  const missing = r.components.filter((c) => c.score.value === null);
  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <div className="space-y-6">
        <Card>
          <CardHeader eyebrow="Composite" title="Field resilience" description={`As of ${formatDate(r.as_of, "long")}`} />
          <CardBody>
            {r.status === "computed" ? (
              <div className="flex flex-col items-center text-center">
                <div className="relative w-full max-w-[240px]">
                  <Gauge score={r.composite.score.value} band={r.composite.band} />
                  <div className="absolute inset-x-0 bottom-1 font-display text-[44px] leading-none text-ink"><QuantityValue q={r.composite.score} unitClassName="text-[14px]" /></div>
                </div>
                <ScoreBandPill className="mt-3" band={r.composite.band} confidence={r.composite.confidence} />
                <p className="mt-3 text-[12.5px] text-ink-soft">Equal-weight mean of {r.composite.components_used} of {r.composite.components_total} components. Bands: low &lt; 40 · moderate 40–70 · high &gt; 70.</p>
              </div>
            ) : (
              <div className="rounded-xl border border-wheat-200 bg-wheat-100/50 p-4 text-[13px] leading-relaxed text-ink-soft">
                <p className="font-display text-[18px] text-ink">Composite withheld</p>
                <p className="mt-1">{r.composite.components_used} of {r.composite.components_total ?? 4} components are available; the framework needs at least 3. Missing: {missing.map((m) => m.label).join(", ")}.</p>
              </div>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Limitations" title="Read before relying on this" />
          <CardBody className="space-y-4">
            <FlagList flags={r.limitations} />
            <ul className="space-y-2 text-[12.5px] leading-relaxed text-ink-soft">
              {r.disclaimers.map((d) => <li key={d} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-stone-400" />{d}</li>)}
            </ul>
            <p className="font-mono text-[11px] text-stone-500">model {r.model_version}</p>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader eyebrow="Components" title="Why this field scores the way it does" description="Each component maps its inputs through a documented breakpoint table. Regional components carry low confidence by design." />
        <CardBody className="space-y-3">
          {r.components.map((c) => (
            <ComponentRow key={c.key} c={c} open={open === c.key} onToggle={() => setOpen(open === c.key ? null : c.key)} fieldId={fieldId} />
          ))}
        </CardBody>
      </Card>
    </div>
  );
}

function ComponentRow({ c, open, onToggle, fieldId }: { c: ResilienceComponent; open: boolean; onToggle: () => void; fieldId: string }) {
  const v = c.score.value;
  const s = SUPPORT_STYLE[c.support_class];
  return (
    <div className={cn("rounded-xl border bg-paper transition-shadow", open ? "border-forest-200 shadow-[var(--shadow-card)]" : "border-line")}>
      <button onClick={onToggle} aria-expanded={open} className="flex w-full flex-wrap items-center gap-4 p-4 text-left">
        <div className="min-w-[180px] flex-1">
          <p className="text-[14px] font-semibold text-ink">{c.label}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <ScoreBandPill band={c.band} />
            <Badge className={cn("border", s.bg, s.fg, s.border)}>{s.short}</Badge>
            <span className="text-[11px] font-medium text-stone-500">{CONFIDENCE_LABEL[c.confidence]}</span>
          </div>
        </div>
        <div className="flex w-full items-center gap-3 sm:w-64">
          <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-parchment">
            <div className="absolute inset-y-0 left-[40%] w-px bg-line-strong" />
            <div className="absolute inset-y-0 left-[70%] w-px bg-line-strong" />
            {v !== null && <div className="h-full rounded-full transition-all duration-700" style={{ width: `${v}%`, background: BAND_STYLE[c.band].fill }} />}
          </div>
          <span className="w-12 text-right font-display text-[20px] tabular text-ink">{v === null ? "—" : v}</span>
          <ChevronRight className={cn("h-4 w-4 text-stone-400 transition-transform", open && "rotate-90")} aria-hidden />
        </div>
      </button>
      {open && <ComponentDetail c={c} fieldId={fieldId} />}
    </div>
  );
}

function ComponentDetail({ c, fieldId }: { c: ResilienceComponent; fieldId: string }) {
  const ev = useEvidence(fieldId, "indicator");
  const keys = c.input_indicator_ids.map((id) => id.split(":")[1]);
  return (
    <div className="space-y-3 border-t border-line/70 px-4 pb-4 pt-3 text-[12.5px] leading-relaxed text-ink-soft">
      <p>{c.score.value === null ? missingText(c.score.missing_reason) : c.explanation}</p>
      <p className="text-stone-500">Rule: {c.rule_ref.name} · v{c.rule_ref.version} — {c.rule_ref.description}</p>
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Input evidence</p>
        <StateBoundary query={ev} compact>
          {(items) => {
            const rel = items.filter((e) => e.related_ids.some((r) => keys.includes(r)));
            return rel.length ? <EvidenceList items={rel} groupByKind={false} /> : <p className="text-stone-500">No evidence items for these inputs.</p>;
          }}
        </StateBoundary>
      </div>
    </div>
  );
}
