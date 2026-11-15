"use client";
import Image from "next/image";
import { useMemo, useState } from "react";
import { ArrowRight, ChevronDown, GitCompare, Pencil, Plus, Trash2, X } from "lucide-react";
import type { CropHistory, CropOption, RecommendationCandidate, RotationRecommendation, RotationScenario, ScenarioEvaluation } from "@/types/contracts";
import { useCreateScenario, useCropHistory, useCrops, useDeleteScenario, useRecommendation, useScenarios, useUpdateScenario } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { isApiError } from "@/services";
import { useDataMode } from "@/hooks/data-mode";
import { cropColor, cropShort, FIT_STYLE } from "@/lib/vocab";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Badge, Button, Card, CardBody, CardHeader, Skeleton } from "@/components/ui/primitives";
import { EmptyState, ErrorState, StateBoundary } from "@/components/shared/state";
import { CropLegend, CropTimeline, IndicatorCard } from "@/components/shared/data-display";
import { FitBandPill, FlagList, QuantityValue, SupportBadge, SyntheticBadge } from "@/components/shared/provenance";
import { CropSuitabilitySection } from "./suitability-section";
import { LATEST_SEASON } from "./common";

const TARGET_SEASON = LATEST_SEASON + 1;

interface Draft { id: string | null; name: string; start_year: number; sequence: number[]; }
const emptyDraft = (): Draft => ({ id: null, name: "", start_year: TARGET_SEASON, sequence: [24, 4, 5] });

export function RotationView() {
  const fieldId = useFieldId();
  const history = useCropHistory(fieldId);
  const rec = useRecommendation(fieldId, TARGET_SEASON);
  const crops = useCrops();
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [builderOpen, setBuilderOpen] = useState(false);

  const startFrom = (code: number) => {
    setDraft({ id: null, name: `${cropShort(code)}-led rotation`, start_year: TARGET_SEASON, sequence: [code, ...(code === 24 ? [4, 5] : [24, 4])] });
    setBuilderOpen(true);
    setTimeout(() => document.getElementById("scenario-builder")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader eyebrow="1 · Understand the history" title="Crop sequence on this field" description="Majority Cropland Data Layer class per year, with diversity metrics derived from it." />
        <CardBody>
          <StateBoundary query={history} skeleton={<Skeleton className="h-28" />}>{(h) => <History h={h} />}</StateBoundary>
        </CardBody>
      </Card>

      <section>
        <SectionTitle n="2" title={`Crop Suitability Intelligence (${LATEST_SEASON} Baseline Season)`} description="Independent factor-by-factor environmental suitability evaluation across all 14 canonical crops using Phase 5 knowledge and field data." />
        <CropSuitabilitySection fieldId={fieldId} seasonYear={LATEST_SEASON} />
      </section>

      <section>
        <SectionTitle n="3" title={`Explained options for the ${TARGET_SEASON} season`} description="Each option is classed by its most limiting factor. Regional factors cannot rule a crop out on their own." />
        <StateBoundary query={rec} skeleton={<div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-64" /><Skeleton className="h-64" /></div>}>
          {(r) => <Recommendations r={r} onUse={startFrom} />}
        </StateBoundary>
      </section>

      <section id="scenario-builder" className="scroll-mt-24">
        <SectionTitle n="4" title="Compare rotations" description="Build multi-year sequences and compare their evaluations side by side." />
        <div className="mb-4 rounded-lg border border-line bg-cream/60 p-3 text-[12.5px] text-ink-soft">
          <span className="font-semibold text-ink">Upcoming Phase 7 Engine:</span> Interactive multi-year scenario sequence authoring is enabled below. Algorithmic sequence optimization, nitrogen credit carryover, and economic rotation scoring arrive in Phase 7.
        </div>
        {crops.isError ? <ErrorState error={crops.error} onRetry={() => void crops.refetch()} /> : (
          <Scenarios fieldId={fieldId} crops={crops.data?.data ?? []} draft={draft} setDraft={setDraft} builderOpen={builderOpen} setBuilderOpen={setBuilderOpen} />
        )}
      </section>
    </div>
  );
}

function SectionTitle({ n, title, description }: { n: string; title: string; description: string }) {
  return (
    <div className="mb-4 flex items-start gap-3">
      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-forest-800 font-mono text-[12px] font-semibold text-paper">{n}</span>
      <div>
        <h2 className="font-display text-[22px] leading-tight text-ink">{title}</h2>
        <p className="mt-1 text-[13px] text-ink-soft">{description}</p>
      </div>
    </div>
  );
}

function History({ h }: { h: CropHistory }) {
  return (
    <div className="space-y-4">
      <CropTimeline years={h.years} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CropLegend codes={h.years.map((y) => y.majority.crop_code ?? 0)} />
        <SupportBadge spatial={h.spatial} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">{h.metrics.map((m) => <IndicatorCard key={m.indicator_id} indicator={m} size="sm" />)}</div>
    </div>
  );
}

function Recommendations({ r, onUse }: { r: RotationRecommendation; onUse: (code: number) => void }) {
  const { isMock } = useDataMode();
  if (r.status !== "computed") {
    return <EmptyState title={r.status === "pending" ? "Recommendations pending" : "Not enough data for recommendations"} description={r.status === "pending" ? "Waiting for this field's datasets to finish processing." : "Soil, terrain or climate inputs are missing for this field."} />;
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[11.5px] text-stone-500">
        {isMock && <SyntheticBadge />} engine {r.engine_version} · KB {r.kb_version} · generated {formatDate(r.generated_at, "long")}
      </div>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {r.candidates.map((c) => <CandidateCard key={c.crop_code} c={c} onUse={() => onUse(c.crop_code)} />)}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="bg-cream/60">
          <CardBody className="pt-5">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Not offered</p>
            <ul className="space-y-1.5 text-[12.5px] text-ink-soft">
              {r.excluded.map((e) => <li key={e.crop_code}><span className="font-semibold text-ink">{e.crop_name}</span> — {e.reason}</li>)}
            </ul>
          </CardBody>
        </Card>
        <Card className="bg-cream/60">
          <CardBody className="pt-5">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">How to read this</p>
            <ul className="space-y-1.5 text-[12.5px] leading-relaxed text-ink-soft">{r.disclaimers.map((d) => <li key={d}>• {d}</li>)}</ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

const FACTOR_LABEL: Record<string, string> = { ph: "Soil pH", drainage: "Drainage", water_holding: "Water holding", gdd: "Heat units (GDD)", slope: "Slope", rotation_history: "Rotation history", regional_climate: "Regional climate" };

const CROP_PHOTOS: Record<number, string> = {
  24: "/images/crops/wheat.jpg",
  1: "/images/crops/corn.jpg",
  5: "/images/crops/soybeans.jpg",
  36: "/images/crops/alfalfa.jpg",
  4: "/images/crops/sorghum.jpg",
};

function CandidateCard({ c, onUse }: { c: RecommendationCandidate; onUse: () => void }) {
  const [open, setOpen] = useState(c.rank === 1);
  const s = FIT_STYLE[c.overall];
  const photo = CROP_PHOTOS[c.crop_code];
  return (
    <Card className={cn("overflow-hidden", c.rank === 1 && "ring-1 ring-forest-300 shadow-md")}>
      <div className="flex items-start gap-4 p-5">
        <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl border border-line shadow-inner">
          {photo ? (
            <Image src={photo} alt={c.crop_name} fill sizes="56px" className="object-cover" />
          ) : (
            <div className="grid h-full w-full place-items-center text-[11px] font-bold uppercase text-white" style={{ background: cropColor(c.crop_code) }}>
              #{c.rank}
            </div>
          )}
          <span className="absolute bottom-0 right-0 rounded-tl-md bg-forest-950/80 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white backdrop-blur-xs">
            #{c.rank}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-display text-[20px] leading-tight text-ink">{c.crop_name}</p>
          <div className="mt-1.5"><FitBandPill band={c.overall} confidence={c.confidence} /></div>
        </div>
        <Button size="sm" variant="secondary" onClick={onUse}><Plus className="h-3.5 w-3.5" /> Use in scenario</Button>
      </div>
      <div className="space-y-3 px-5 pb-4">
        <ul className="space-y-1 text-[12.5px] leading-relaxed text-ink-soft">{c.reasons.map((r) => <li key={r} className="flex gap-2"><span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", s.dot)} />{r}</li>)}</ul>
        {c.rotation_effects.length > 0 && <FlagList flags={c.rotation_effects} />}
        <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="inline-flex items-center gap-1 text-[12px] font-semibold text-forest-700">
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} /> Factor assessment ({c.factors.length})
        </button>
        {open && (
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full min-w-[480px] text-left text-[12px]">
              <thead className="bg-cream/70"><tr className="text-[10.5px] uppercase tracking-[0.1em] text-stone-500"><th className="px-3 py-2 font-semibold">Factor</th><th className="px-3 py-2 font-semibold">Class</th><th className="px-3 py-2 font-semibold">Observed</th><th className="px-3 py-2 font-semibold">Support</th></tr></thead>
              <tbody>
                {c.factors.map((f) => (
                  <tr key={f.factor} className="border-t border-line/70" title={f.requirement}>
                    <td className="px-3 py-2 font-semibold text-ink">{FACTOR_LABEL[f.factor] ?? f.factor}</td>
                    <td className="px-3 py-2"><FitBandPill band={f.band} /></td>
                    <td className="px-3 py-2">{f.observed ? <QuantityValue q={f.observed} /> : <span className="text-stone-400">—</span>}</td>
                    <td className="px-3 py-2"><Badge className={f.support_class === "R" ? "bg-wheat-100 text-wheat-600" : "bg-forest-50 text-forest-800"}>{f.support_class === "R" ? "Regional" : "Field"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-line/70 bg-cream/50 px-3 py-2 text-[11.5px] text-stone-500">Requirement for every factor: {c.factors[0]?.requirement}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// ───────────────────────── Scenarios ─────────────────────────
function Scenarios({ fieldId, crops, draft, setDraft, builderOpen, setBuilderOpen }: {
  fieldId: string; crops: CropOption[]; draft: Draft; setDraft: (d: Draft) => void; builderOpen: boolean; setBuilderOpen: (b: boolean) => void;
}) {
  const list = useScenarios(fieldId);
  const del = useDeleteScenario(fieldId);
  const [compare, setCompare] = useState<string[]>([]);
  const scenarios = useMemo(() => list.data?.data ?? [], [list.data]);
  const toggleCompare = (id: string) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c.slice(-1), id]));
  const compared = scenarios.filter((s) => compare.includes(s.scenario_id));

  return (
    <div className="space-y-5">
      {builderOpen ? (
        <Builder fieldId={fieldId} crops={crops} draft={draft} setDraft={setDraft} onDone={() => { setBuilderOpen(false); setDraft(emptyDraft()); }} />
      ) : (
        <Button variant="primary" onClick={() => { setDraft(emptyDraft()); setBuilderOpen(true); }}><Plus className="h-4 w-4" /> New rotation scenario</Button>
      )}
      <StateBoundary
        query={list}
        skeleton={<Skeleton className="h-40" />}
        isEmpty={(d) => d.length === 0}
        empty={<EmptyState icon={<Plus className="h-6 w-6" />} title="Build your first rotation" description="Start from a recommended crop above or create a sequence from scratch." />}
      >
        {() => (
          <div className="grid items-start gap-4 lg:grid-cols-2">
            {scenarios.map((s) => (
              <ScenarioCard
                key={s.scenario_id}
                s={s}
                comparing={compare.includes(s.scenario_id)}
                onCompare={() => toggleCompare(s.scenario_id)}
                onEdit={() => { setDraft({ id: s.scenario_id, name: s.name, start_year: s.start_year, sequence: s.sequence.map((y) => y.crop_code) }); setBuilderOpen(true); }}
                onDelete={() => del.mutate(s.scenario_id)}
                deleting={del.isPending && del.variables === s.scenario_id}
              />
            ))}
          </div>
        )}
      </StateBoundary>
      {compared.length === 2 && <CompareTable a={compared[0]} b={compared[1]} onClose={() => setCompare([])} />}
      {compare.length === 1 && <p className="text-center text-[12.5px] text-stone-500">Select one more scenario to compare.</p>}
    </div>
  );
}

function Builder({ fieldId, crops, draft, setDraft, onDone }: { fieldId: string; crops: CropOption[]; draft: Draft; setDraft: (d: Draft) => void; onDone: () => void }) {
  const create = useCreateScenario(fieldId);
  const update = useUpdateScenario(fieldId);
  const m = draft.id ? update : create;
  const err = m.error;
  const errField = isApiError(err) ? (err.details?.field as string | undefined) : undefined;
  const setYear = (i: number, code: number) => setDraft({ ...draft, sequence: draft.sequence.map((c, j) => (j === i ? code : c)) });
  const save = () => {
    const req = { name: draft.name, start_year: draft.start_year, sequence: draft.sequence.map((c, i) => ({ year: draft.start_year + i, crop_code: c })) };
    if (draft.id) update.mutate({ id: draft.id, req }, { onSuccess: onDone });
    else create.mutate(req, { onSuccess: onDone });
  };
  return (
    <Card className="border-forest-200">
      <CardHeader eyebrow={draft.id ? "Edit scenario" : "New scenario"} title="Rotation builder" description="2–8 years. Saving computes the multi-year agronomic evaluation." actions={<Button size="sm" variant="ghost" onClick={onDone}><X className="h-4 w-4" /> Close</Button>} />
      <CardBody className="space-y-5">
        <div className="flex flex-wrap gap-4">
          <label className="block min-w-[240px] flex-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Name</span>
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="e.g. Wheat – sorghum – soybean" aria-invalid={errField === "name"} className={cn("mt-1 h-10 w-full rounded-lg border bg-paper px-3 text-[13.5px]", errField === "name" ? "border-clay-500" : "border-line-strong")} />
          </label>
          <label className="block w-36">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Start year</span>
            <input type="number" min={2026} max={2035} value={draft.start_year} onChange={(e) => setDraft({ ...draft, start_year: Number(e.target.value) || TARGET_SEASON })} className="mt-1 h-10 w-full rounded-lg border border-line-strong bg-paper px-3 text-[13.5px] tabular" />
          </label>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Sequence</p>
          <div className="flex flex-wrap items-stretch gap-2">
            {draft.sequence.map((code, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-[150px] rounded-xl border border-line bg-paper p-2.5">
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="font-mono text-[11px] font-semibold text-stone-500">{draft.start_year + i}</span>
                    {draft.sequence.length > 2 && <button aria-label={`Remove ${draft.start_year + i}`} onClick={() => setDraft({ ...draft, sequence: draft.sequence.filter((_, j) => j !== i) })} className="text-stone-400 hover:text-clay-600"><X className="h-3.5 w-3.5" /></button>}
                  </div>
                  <select aria-label={`Crop for ${draft.start_year + i}`} value={code} onChange={(e) => setYear(i, Number(e.target.value))} className="h-9 w-full rounded-lg border-0 px-2 text-[12.5px] font-semibold text-white" style={{ background: cropColor(code) }}>
                    {crops.map((c) => <option key={c.crop_code} value={c.crop_code} className="bg-paper text-ink">{c.name}</option>)}
                  </select>
                </div>
                {i < draft.sequence.length - 1 && <ArrowRight className="h-4 w-4 text-stone-400" aria-hidden />}
              </div>
            ))}
            {draft.sequence.length < 8 && (
              <button onClick={() => setDraft({ ...draft, sequence: [...draft.sequence, 24] })} className="grid w-[110px] place-items-center rounded-xl border border-dashed border-line-strong text-[12.5px] font-semibold text-forest-700 hover:bg-forest-50">
                <span className="inline-flex items-center gap-1"><Plus className="h-4 w-4" /> Add year</span>
              </button>
            )}
          </div>
        </div>
        {err && <ErrorState error={err} compact />}
        <div className="flex gap-2">
          <Button variant="primary" onClick={save} disabled={m.isPending}>{m.isPending ? "Evaluating…" : draft.id ? "Save & re-evaluate" : "Save & evaluate"}</Button>
          <Button variant="ghost" onClick={onDone}>Cancel</Button>
        </div>
      </CardBody>
    </Card>
  );
}

const DIM_LABEL: Record<string, string> = { agronomic_fit: "Agronomic fit", rotation_benefit: "Rotation benefit", water_risk: "Water risk", diversity: "Diversity" };

function ScenarioCard({ s, comparing, onCompare, onEdit, onDelete, deleting }: { s: RotationScenario; comparing: boolean; onCompare: () => void; onEdit: () => void; onDelete: () => void; deleting: boolean }) {
  const e = s.evaluation;
  return (
    <Card className={cn(comparing && "ring-2 ring-forest-500")}>
      <CardHeader
        eyebrow={`${s.start_year}–${s.start_year + s.sequence.length - 1}`}
        title={s.name}
        actions={
          <>
            <Button size="sm" variant={comparing ? "primary" : "ghost"} onClick={onCompare} aria-pressed={comparing}><GitCompare className="h-3.5 w-3.5" /> Compare</Button>
            <Button size="sm" variant="ghost" onClick={onEdit} aria-label="Edit scenario"><Pencil className="h-3.5 w-3.5" /></Button>
            <Button size="sm" variant="ghost" onClick={onDelete} disabled={deleting} aria-label="Delete scenario"><Trash2 className="h-3.5 w-3.5" /></Button>
          </>
        }
      />
      <CardBody className="space-y-4">
        <div className="flex gap-1">
          {s.sequence.map((y) => (
            <div key={y.year} className="min-w-0 flex-1 rounded-lg px-2 py-2 text-center" style={{ background: cropColor(y.crop_code) }}>
              <p className="font-mono text-[10px] font-semibold text-white/85">{y.year}</p>
              <p className="truncate text-[11.5px] font-bold text-white">{cropShort(y.crop_code)}</p>
            </div>
          ))}
        </div>
        {e ? <Evaluation e={e} /> : <p className="text-[12.5px] text-stone-500">Not evaluated yet.</p>}
      </CardBody>
    </Card>
  );
}

function Evaluation({ e }: { e: ScenarioEvaluation }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><span className="text-[12px] font-semibold text-ink-soft">Overall</span><FitBandPill band={e.overall} /></div>
      <div className="grid grid-cols-2 gap-2">
        {e.dimensions.map((d) => (
          <div key={d.key} className="rounded-lg border border-line/80 bg-cream/40 px-3 py-2" title={d.explanation}>
            <p className="text-[11px] font-semibold text-stone-500">{DIM_LABEL[d.key]}</p>
            <div className="mt-1"><FitBandPill band={d.band} /></div>
          </div>
        ))}
      </div>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="inline-flex items-center gap-1 text-[12px] font-semibold text-forest-700">
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} /> Year-by-year findings
      </button>
      {open && (
        <ul className="space-y-2">
          {e.year_findings.map((y) => (
            <li key={y.year} className="rounded-lg border border-line/70 px-3 py-2">
              <div className="flex items-center gap-2"><span className="font-mono text-[11.5px] font-semibold text-ink">{y.year}</span><FitBandPill band={y.band} /></div>
              {y.messages.length > 0 && <ul className="mt-1 text-[12px] text-ink-soft">{y.messages.map((m) => <li key={m.code}>• {m.message}</li>)}</ul>}
            </li>
          ))}
        </ul>
      )}
      <FlagList flags={e.warnings} />
    </div>
  );
}

function CompareTable({ a, b, onClose }: { a: RotationScenario; b: RotationScenario; onClose: () => void }) {
  const dims = ["agronomic_fit", "rotation_benefit", "water_risk", "diversity"] as const;
  const band = (s: RotationScenario, k: string) => s.evaluation?.dimensions.find((d) => d.key === k)?.band ?? "unknown";
  return (
    <Card className="animate-[var(--animate-fade-up)]">
      <CardHeader eyebrow="Side by side" title="Scenario comparison" description="Dimension bands only — no hidden totals." actions={<Button size="sm" variant="ghost" onClick={onClose}><X className="h-4 w-4" /> Close</Button>} />
      <CardBody className="overflow-x-auto pt-2">
        <table className="w-full min-w-[520px] text-left text-[13px]">
          <thead>
            <tr className="border-b border-line"><th className="py-2 pr-3 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-stone-500">Dimension</th><th className="py-2 pr-3 font-display text-[15px] font-normal">{a.name}</th><th className="py-2 font-display text-[15px] font-normal">{b.name}</th></tr>
          </thead>
          <tbody>
            <tr className="border-b border-line/60">
              <td className="py-2.5 pr-3 font-semibold text-ink-soft">Sequence</td>
              <td className="py-2.5 pr-3 text-[12px]">{a.sequence.map((y) => cropShort(y.crop_code)).join(" → ")}</td>
              <td className="py-2.5 text-[12px]">{b.sequence.map((y) => cropShort(y.crop_code)).join(" → ")}</td>
            </tr>
            {dims.map((k) => (
              <tr key={k} className="border-b border-line/60">
                <td className="py-2.5 pr-3 font-semibold text-ink-soft">{DIM_LABEL[k]}</td>
                <td className="py-2.5 pr-3"><FitBandPill band={band(a, k)} /></td>
                <td className="py-2.5"><FitBandPill band={band(b, k)} /></td>
              </tr>
            ))}
            <tr>
              <td className="py-2.5 pr-3 font-semibold text-ink">Overall</td>
              <td className="py-2.5 pr-3"><FitBandPill band={a.evaluation?.overall ?? "unknown"} /></td>
              <td className="py-2.5"><FitBandPill band={b.evaluation?.overall ?? "unknown"} /></td>
            </tr>
          </tbody>
        </table>
        <p className="mt-3 text-[11.5px] text-stone-500">Both evaluations are synthetic placeholders until the Phase 5 rotation engine is connected.</p>
      </CardBody>
    </Card>
  );
}
