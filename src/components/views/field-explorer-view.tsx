"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, Search, X } from "lucide-react";
import type { FieldProcessingStatus, FieldSource, FieldSummary, ScoreBand } from "@/types/contracts";
import { useActiveFarm } from "@/hooks/active-farm";
import { useFields } from "@/hooks/queries";
import { usePrefs } from "@/hooks/preferences";
import { qText } from "@/lib/format";
import { cropColor, cropShort } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { ButtonLink, Card, PageHeader, Segmented, Select, Skeleton } from "@/components/ui/primitives";
import { EmptyState, ErrorState } from "@/components/shared/state";
import { FieldMap } from "@/components/shared/field-map";
import { CompletenessMeter } from "@/components/shared/data-display";
import { ScoreBandPill } from "@/components/shared/provenance";
import { DATA_MODE } from "@/services";

type Any<T> = T | "all";

export function FieldExplorerView() {
  const { farm, error: farmErr, refetch } = useActiveFarm();
  const fields = useFields(farm?.farm_id ?? null);
  const { units } = usePrefs();
  const [search, setSearch] = useState("");
  const [source, setSource] = useState<Any<FieldSource>>("all");
  const [status, setStatus] = useState<Any<FieldProcessingStatus>>("all");
  const [band, setBand] = useState<Any<ScoreBand>>("all");
  const [crop, setCrop] = useState<number | "all">("all");
  const [colorBy, setColorBy] = useState<"band" | "crop">("crop");
  const [selected, setSelected] = useState<string | null>(null);

  const all = useMemo(() => fields.data?.data ?? [], [fields.data]);
  const crops = useMemo(() => [...new Set(all.map((f) => f.latest_crop?.crop_code).filter((c): c is number => c !== null && c !== undefined))], [all]);
  const filtered = all.filter(
    (f) =>
      (!search || f.name.toLowerCase().includes(search.toLowerCase())) &&
      (source === "all" || f.source === source) &&
      (status === "all" || f.processing_status === status) &&
      (band === "all" || f.resilience_band === band) &&
      (crop === "all" || f.latest_crop?.crop_code === crop),
  );
  const activeFilters = [search, source !== "all", status !== "all", band !== "all", crop !== "all"].filter(Boolean).length;
  const sel = all.find((f) => f.field_id === selected) ?? null;

  if (farmErr) return <ErrorState error={farmErr} onRetry={refetch} />;

  return (
    <div>
      <PageHeader
        eyebrow="Field Explorer"
        title="Find a field"
        description="Search and filter fields, then open one to explore its environment, crop history, resilience and rotation options."
        actions={<Segmented label="Colour by" size="sm" value={colorBy} onChange={setColorBy} options={[{ value: "crop", label: "Latest crop" }, { value: "band", label: "Resilience" }]} />}
      />
      <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
        <Card className="flex max-h-[720px] flex-col overflow-hidden">
          <div className="space-y-3 border-b border-line p-4">
            <label className="relative block">
              <span className="sr-only">Search fields</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" aria-hidden />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name" className="h-10 w-full rounded-lg border border-line-strong bg-paper pl-9 pr-3 text-[13.5px] placeholder:text-stone-400" />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <Select label="Source" value={source} onChange={setSource} options={[{ value: "all", label: "All sources" }, { value: "synthetic", label: "Synthetic" }, { value: "user", label: "User-drawn" }, { value: "csb", label: "CSB" }]} />
              <Select label="Status" value={status} onChange={setStatus} options={[{ value: "all", label: "All statuses" }, { value: "ready", label: "Ready" }, { value: "partial", label: "Partial" }, { value: "processing", label: "Processing" }, { value: "failed", label: "Failed" }]} />
              <Select label="Resilience" value={band} onChange={setBand} options={[{ value: "all", label: "Any resilience" }, { value: "high", label: "High" }, { value: "moderate", label: "Moderate" }, { value: "low", label: "Low" }, { value: "unknown", label: "Unknown" }]} />
              <Select label="Latest crop" value={crop} onChange={setCrop} options={[{ value: "all", label: "Any crop" }, ...crops.map((c) => ({ value: c, label: cropShort(c) }))]} />
            </div>
            {activeFilters > 0 && (
              <button onClick={() => { setSearch(""); setSource("all"); setStatus("all"); setBand("all"); setCrop("all"); }} className="inline-flex items-center gap-1 text-[12px] font-semibold text-forest-700">
                <X className="h-3.5 w-3.5" /> Clear {activeFilters} filter{activeFilters > 1 ? "s" : ""}
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto">
            {fields.isPending ? (
              <div className="space-y-2 p-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
            ) : fields.isError ? (
              <div className="p-4"><ErrorState error={fields.error} onRetry={() => void fields.refetch()} compact /></div>
            ) : all.length === 0 ? (
              <div className="p-4"><EmptyState title="No fields" description="Add a field in Farm & Settings." /></div>
            ) : filtered.length === 0 ? (
              <div className="p-4"><EmptyState title="No fields match these filters" /></div>
            ) : (
              <ul>
                {filtered.map((f) => (
                  <FieldRow key={f.field_id} f={f} active={selected === f.field_id} onSelect={() => setSelected(f.field_id)} units={units} />
                ))}
              </ul>
            )}
          </div>
          <p className="border-t border-line px-4 py-2.5 text-[11.5px] text-stone-500">{filtered.length} of {all.length} fields</p>
        </Card>

        <div className="space-y-4">
          <FieldMap
            height={600}
            fields={all.map((f) => ({ field_id: f.field_id, name: f.name, geometry: f.geometry, band: f.resilience_band, crop: f.latest_crop?.crop_code ?? null, muted: !filtered.some((x) => x.field_id === f.field_id) }))}
            colorBy={colorBy}
            selectedId={selected}
            onSelect={setSelected}
            focusId={selected}
            caption={DATA_MODE === "mock" ? "Geospatial view · Synthetic field boundaries" : "Geospatial view · Operational field boundaries"}
          />
          {sel ? (
            <Card className="animate-[var(--animate-fade-up)]">
              <div className="flex flex-wrap items-center gap-5 p-5">
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Selected field</p>
                  <p className="mt-1 font-display text-[22px] text-ink">{sel.name}</p>
                  <p className="mt-1 text-[12.5px] text-ink-soft">{qText(sel.area, units)} · {sel.latest_crop ? `${sel.latest_crop.year}: ${sel.latest_crop.crop_name}` : "crop history pending"}</p>
                </div>
                <ScoreBandPill band={sel.resilience_band} />
                <CompletenessMeter value={sel.coverage_completeness} />
                <ButtonLink href={`/fields/${sel.field_id}`} variant="primary">Open field <ArrowRight className="h-4 w-4" /></ButtonLink>
              </div>
            </Card>
          ) : (
            <p className="text-center text-[12.5px] text-stone-500">Select a field on the map or in the list.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function FieldRow({ f, active, onSelect, units }: { f: FieldSummary; active: boolean; onSelect: () => void; units: "metric" | "us" }) {
  return (
    <li>
      <button onClick={onSelect} className={cn("flex w-full items-center gap-3 border-b border-line/60 px-4 py-3 text-left transition-colors hover:bg-forest-50/70", active && "bg-forest-50")}>
        <span className="h-9 w-1.5 shrink-0 rounded-full" style={{ background: cropColor(f.latest_crop?.crop_code ?? null) }} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13.5px] font-semibold text-ink">{f.name}</span>
          <span className="mt-0.5 block text-[12px] text-ink-soft">
            {qText(f.area, units)} · {f.latest_crop?.crop_name ?? "History pending"}
            {f.processing_status !== "ready" && <span className="ml-1.5 font-semibold uppercase text-wheat-600 text-[10.5px]">{f.processing_status}</span>}
          </span>
        </span>
        <ScoreBandPill band={f.resilience_band} />
      </button>
      {active && (
        <div className="border-b border-line/60 bg-forest-50 px-4 pb-3">
          <Link href={`/fields/${f.field_id}`} className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-forest-700">Open field <ArrowRight className="h-3.5 w-3.5" /></Link>
        </div>
      )}
    </li>
  );
}
