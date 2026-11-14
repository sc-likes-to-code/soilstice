"use client";
import { Printer } from "lucide-react";
import type { EvidenceItem, FieldProfile, ResilienceProfile, RotationRecommendation, SourceRef } from "@/types/contracts";
import { CONTRACT_VERSION } from "@/types/contracts";
import { useEvidence, useFieldProfile, useRecommendation, useResilience } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { usePrefs } from "@/hooks/preferences";
import { formatDateTime, missingText, qText } from "@/lib/format";
import { DATASET_SHORT, COVERAGE_STYLE } from "@/lib/vocab";
import { Button, Skeleton } from "@/components/ui/primitives";
import { ErrorState } from "@/components/shared/state";
import { CropLegend, CropTimeline } from "@/components/shared/data-display";
import { FieldMap } from "@/components/shared/field-map";
import { FitBandPill, QuantityValue, ScoreBandPill, SupportBadge } from "@/components/shared/provenance";
import { LATEST_SEASON } from "./common";

export function ReportView() {
  const fieldId = useFieldId();
  const profile = useFieldProfile(fieldId, LATEST_SEASON);
  const res = useResilience(fieldId);
  const rec = useRecommendation(fieldId, LATEST_SEASON + 1);
  const ev = useEvidence(fieldId, "dataset");
  if (profile.isPending) return <Skeleton className="h-[900px]" />;
  if (profile.isError) return <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />;
  return (
    <Report
      p={profile.data.data}
      generatedAt={profile.data.meta.generated_at}
      dataMode={profile.data.meta.data_mode}
      res={res.data?.data ?? null}
      rec={rec.data?.data ?? null}
      datasets={ev.data?.data ?? []}
    />
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="print-avoid border-t border-line pt-5">
      <h2 className="mb-3 font-display text-[19px] text-ink">{title}</h2>
      {children}
    </section>
  );
}

function NotAvailable({ reason }: { reason: string }) {
  return <p className="text-[12.5px] italic text-stone-500">Not available: {reason}</p>;
}

function Report({ p, generatedAt, dataMode, res, rec, datasets }: { p: FieldProfile; generatedAt: string; dataMode: string; res: ResilienceProfile | null; rec: RotationRecommendation | null; datasets: EvidenceItem[] }) {
  const { units } = usePrefs();
  const { field, soil, terrain, crop_history: hist } = p;
  const sources = new Map<string, SourceRef>();
  const add = (s: SourceRef[] | undefined) => s?.forEach((x) => sources.set(`${x.product}|${x.product_version}`, x));
  add(soil?.sources); add(terrain?.sources); p.climate_summary.forEach((i) => add(i.sources)); p.vegetation_summary.forEach((i) => add(i.sources)); hist?.years.slice(-1).forEach((y) => add([y.source]));
  const used = new Set(p.coverage.datasets.filter((d) => d.status === "available" || d.status === "partial").map((d) => d.dataset_id));

  return (
    <div>
      <div className="no-print mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-ink-soft">A printable field summary. Use your browser’s print dialog to save it as PDF.</p>
        <Button variant="primary" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print / save PDF</Button>
      </div>
      <article className="print-plain mx-auto max-w-[900px] space-y-5 rounded-[var(--radius-card)] border border-line bg-paper p-5 shadow-[var(--shadow-card)] md:p-8 print:max-w-none print:border-0 print:p-0">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-forest-600">SOILSTICE field report</p>
            <h1 className="mt-1 font-display text-[30px] leading-tight text-ink">{field.name}</h1>
            <p className="mt-1 text-[12.5px] text-ink-soft">{qText(field.area, units)} · County FIPS {field.state_fips}{field.county_fips} · {field.centroid[1].toFixed(4)}°N {Math.abs(field.centroid[0]).toFixed(4)}°W</p>
          </div>
          {dataMode === "synthetic" && (
            <div className="rounded-lg border-2 border-clay-500 px-3 py-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-clay-600">Synthetic demo data<br /><span className="font-normal normal-case tracking-normal">Not observations</span></div>
          )}
        </header>

        <div className="grid gap-5 md:grid-cols-[260px_1fr]">
          <FieldMap
            height={200}
            fields={[{ field_id: field.field_id, name: field.name, geometry: field.geometry }]}
            colorBy="none"
            focusId={field.field_id}
            caption={field.source === "synthetic" ? "Synthetic parcel geometry" : "Satellite view · USDA/NASA observations"}
          />
          <div>
            <h2 className="mb-2 font-display text-[17px] text-ink">Data coverage</h2>
            <table className="w-full text-[12px] [overflow-wrap:anywhere]">
              <tbody>
                {p.coverage.datasets.filter((d) => d.priority === "P0").map((d) => (
                  <tr key={d.dataset_id} className="border-b border-line/60">
                    <td className="py-1 pr-2 font-semibold">{DATASET_SHORT[d.dataset_id]}</td>
                    <td className={`py-1 pr-2 ${COVERAGE_STYLE[d.status].fg}`}>{COVERAGE_STYLE[d.status].label}</td>
                    <td className="py-1 text-stone-500">{d.support_class} · {d.missing_reason ? missingText(d.missing_reason) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <Section title="Soil & terrain">
          {soil ? (
            <div className="grid gap-x-6 gap-y-2 text-[12.5px] sm:grid-cols-3">
              <p>Texture (0–30 cm): <strong>{soil.layers[0]?.texture_class ?? "—"}</strong></p>
              <p>AWS 0–150 cm: <strong><QuantityValue q={soil.aws_0_150} /></strong></p>
              <p>pH (0–30 cm): <strong><QuantityValue q={soil.layers[0]?.ph_h2o} showRange={false} /></strong></p>
              <p>Organic matter: <strong><QuantityValue q={soil.layers[0]?.om_pct} showRange={false} /></strong></p>
              <p>Drainage: <strong>{soil.drainage_class.value ?? "—"}</strong></p>
              <p>Hydrologic group: <strong>{soil.hydrologic_group.value ?? "—"}</strong></p>
              {terrain && <p>Mean slope: <strong><QuantityValue q={terrain.slope_mean_pct} /></strong></p>}
              {terrain && <p>Mean elevation: <strong><QuantityValue q={terrain.elevation_mean} /></strong></p>}
            </div>
          ) : <NotAvailable reason="soil profile not processed" />}
        </Section>

        <Section title={`Season ${LATEST_SEASON} climate & vegetation`}>
          {p.climate_summary.length + p.vegetation_summary.length ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {[...p.climate_summary, ...p.vegetation_summary].map((i) => (
                <div key={i.indicator_id} className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 py-1.5 text-[12.5px]">
                  <span>{i.label}</span>
                  <span className="flex items-center gap-2"><strong><QuantityValue q={i.value} /></strong><SupportBadge spatial={i.spatial} /></span>
                </div>
              ))}
            </div>
          ) : <NotAvailable reason="climate and vegetation not processed" />}
        </Section>

        <Section title="Crop history">
          {hist ? <div className="space-y-2"><CropTimeline years={hist.years} compact /><CropLegend codes={hist.years.map((y) => y.majority.crop_code ?? 0)} /></div> : <NotAvailable reason="crop history pending" />}
        </Section>

        <Section title="Resilience">
          {res && res.status === "computed" ? (
            <div className="space-y-2 text-[12.5px]">
              <p className="flex flex-wrap items-center gap-2">Composite <strong className="font-display text-[20px]"><QuantityValue q={res.composite.score} /></strong> <ScoreBandPill band={res.composite.band} confidence={res.composite.confidence} /></p>
              <ul className="grid gap-1 sm:grid-cols-2">{res.components.map((c) => <li key={c.key} className="flex flex-wrap justify-between gap-x-2 border-b border-line/60 py-1"><span>{c.label}</span><span className="flex items-center gap-2"><QuantityValue q={c.score} /><ScoreBandPill band={c.band} /></span></li>)}</ul>
            </div>
          ) : <NotAvailable reason={res?.status === "insufficient_data" ? "fewer than 4 of 5 components available" : "not yet computed"} />}
        </Section>

        <Section title={`Next-season options (${LATEST_SEASON + 1})`}>
          {rec && rec.status === "computed" ? (
            <ol className="space-y-1 text-[12.5px]">
              {rec.candidates.map((c) => <li key={c.crop_code} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line/60 py-1"><span className="w-5 font-mono text-stone-500">{c.rank}.</span><span className="flex-1 font-semibold">{c.crop_name}</span><FitBandPill band={c.overall} confidence={c.confidence} /></li>)}
            </ol>
          ) : <NotAvailable reason="recommendations not available for this field" />}
          {rec && <p className="mt-2 text-[11.5px] text-stone-500">{rec.disclaimers.join(" ")}</p>}
        </Section>

        <Section title="Sources">
          <ul className="space-y-1 text-[11.5px] text-ink-soft [overflow-wrap:anywhere]">
            {[...sources.values()].map((s) => <li key={s.product + s.product_version}>{s.product} · version {s.product_version}{s.doi ? ` · doi:${s.doi}` : ""}</li>)}
            {datasets.filter((d) => d.dataset_id && used.has(d.dataset_id)).map((d) => <li key={d.evidence_id}>{d.citation}{d.doi ? ` doi:${d.doi}` : ""} {d.url ? `— ${d.url}` : ""}</li>)}
          </ul>
        </Section>

        <footer className="border-t border-line pt-4 font-mono text-[10.5px] leading-relaxed text-stone-500">
          Generated {formatDateTime(generatedAt)} · contract {CONTRACT_VERSION} · model {res?.model_version ?? "—"} · KB {rec?.kb_version ?? "—"} · data mode {dataMode}
        </footer>
      </article>
    </div>
  );
}
