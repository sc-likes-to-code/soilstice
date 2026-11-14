"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight, Bell, Plus } from "lucide-react";
import type { FarmOverview, FieldSummary, ScoreBand } from "@/types/contracts";
import { useActiveFarm } from "@/hooks/active-farm";
import { useFarmOverview } from "@/hooks/queries";
import { usePrefs } from "@/hooks/preferences";
import { qText } from "@/lib/format";
import { BAND_STYLE, DATASET_SHORT, cropColor } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { ButtonLink, Card, CardBody, CardHeader, PageHeader, Segmented, Select, Skeleton, Stat } from "@/components/ui/primitives";
import { EmptyState, ErrorState } from "@/components/shared/state";
import { FieldMap } from "@/components/shared/field-map";
import { IndicatorCard, CompletenessMeter } from "@/components/shared/data-display";
import { FlagList, ScoreBandPill, SyntheticBadge } from "@/components/shared/provenance";
import { LATEST_SEASON, seasonOptions } from "./common";
import { DATA_MODE } from "@/services";

export function DashboardView() {
  const { farm, isLoading: farmsLoading, error: farmsError, refetch } = useActiveFarm();
  const [season, setSeason] = useState(LATEST_SEASON);
  const overview = useFarmOverview(farm?.farm_id ?? null, season);

  if (farmsError) return <ErrorState error={farmsError} onRetry={refetch} />;
  return (
    <div>
      <PageHeader
        eyebrow="Dashboard"
        title={farm ? farm.name : <Skeleton className="h-10 w-72" />}
        description={farm ? `${farm.aoi.label} · season overview, field attention list and data coverage. Regional context is labelled as such.` : undefined}
        actions={<Select label="Season" value={season} onChange={setSeason} options={seasonOptions} />}
      />
      {farmsLoading || overview.isPending ? (
        <DashboardSkeleton />
      ) : overview.isError ? (
        <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />
      ) : overview.data.data.fields.length === 0 ? (
        <EmptyState title="No fields yet" description="Add a field by drawing its boundary in Farm & Settings." action={<ButtonLink href="/settings" variant="primary"><Plus className="h-4 w-4" /> Add a field</ButtonLink>} />
      ) : (
        <DashboardBody data={overview.data.data} season={season} />
      )}
    </div>
  );
}

function DashboardBody({ data, season }: { data: FarmOverview; season: number }) {
  const { units } = usePrefs();
  const router = useRouter();
  const [colorBy, setColorBy] = useState<"band" | "crop">("band");
  const [selected, setSelected] = useState<string | null>(null);
  const bands = useMemo(() => {
    const c: Record<ScoreBand, number> = { high: 0, moderate: 0, low: 0, unknown: 0 };
    data.fields.forEach((f) => (c[f.resilience_band] += 1));
    return c;
  }, [data.fields]);
  const avgCoverage = data.fields.length ? data.fields.reduce((a, f) => a + (f.coverage_completeness ?? 0), 0) / data.fields.length : null;

  return (
    <div className="space-y-6">
      <Card className="animate-[var(--animate-fade-up)]">
        <div className="grid grid-cols-2 gap-6 p-5 md:grid-cols-4">
          <Stat label="Fields" value={data.farm.field_count} sub={<span>{data.fields.filter((f) => f.processing_status === "ready").length} ready · {data.fields.filter((f) => f.processing_status !== "ready").length} need attention</span>} />
          <Stat label="Total area" value={qText(data.farm.total_area, units)} sub="Computed from field polygons" />
          <Stat label="Avg. P0 coverage" value={avgCoverage === null ? "—" : `${Math.round(avgCoverage * 100)}%`} sub={<CompletenessMeter value={avgCoverage} />} />
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">Resilience bands</p>
            <div className="mt-2 flex h-3 overflow-hidden rounded-full bg-parchment">
              {(["high", "moderate", "low", "unknown"] as ScoreBand[]).map((b) => bands[b] > 0 && <div key={b} style={{ width: `${(bands[b] / data.fields.length) * 100}%`, background: BAND_STYLE[b].fill }} title={`${BAND_STYLE[b].label}: ${bands[b]}`} />)}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11.5px] text-ink-soft">
              {(["high", "moderate", "low", "unknown"] as ScoreBand[]).map((b) => (
                <span key={b} className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: BAND_STYLE[b].fill }} />{BAND_STYLE[b].label} {bands[b]}</span>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader
            eyebrow="Fields"
            title="Geospatial farm map"
            description="Interactive satellite view of field parcels with resilience scores. Click a field to inspect."
            actions={<Segmented label="Colour fields by" size="sm" value={colorBy} onChange={setColorBy} options={[{ value: "band", label: "Resilience" }, { value: "crop", label: `Crop ${season}` }]} />}
          />
          <CardBody>
            <FieldMap
              height={450}
              fields={data.fields.map((f) => ({ field_id: f.field_id, name: f.name, geometry: f.geometry, band: f.resilience_band, crop: f.latest_crop?.crop_code ?? null }))}
              colorBy={colorBy}
              selectedId={selected}
              onSelect={setSelected}
              caption={DATA_MODE === "mock" ? "Satellite view · Synthetic parcel geometry" : "Satellite view · Field boundaries from API"}
            />
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Attention" title="Field roster" description="Sorted by data completeness. Select any field to open its profile." />
          <CardBody className="pt-2">
            <FieldTable fields={data.fields} selected={selected} onHover={setSelected} onOpen={(id) => router.push(`/fields/${id}`)} />
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Card>
          <CardHeader eyebrow="Alerts" title={<span className="inline-flex items-center gap-2"><Bell className="h-4 w-4 text-wheat-600" /> What needs attention</span>} />
          <CardBody>
            {data.alerts.length ? <FlagList flags={data.alerts} /> : <EmptyState title="No alerts" description="All fields have complete P0 coverage for this season." />}
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Regional context" title={`${data.farm.aoi.label} · ${season}`} description="Area-level climate and soil-moisture context. These describe the surrounding region, not individual fields." actions={DATA_MODE === "mock" ? <SyntheticBadge /> : undefined} />
          <CardBody className="grid gap-3 sm:grid-cols-2">
            {data.regional_context.map((i) => (
              <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />
            ))}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader eyebrow="Data coverage" title="P0 dataset availability across fields" description="Fields with available or partial data for each essential dataset." />
        <CardBody className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.coverage_summary.map((c) => (
            <div key={c.dataset_id}>
              <div className="flex justify-between text-[12.5px]">
                <span className="font-semibold text-ink">{DATASET_SHORT[c.dataset_id]}</span>
                <span className="tabular text-ink-soft">{c.fields_available} / {c.fields_total}</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-parchment">
                <div className="h-full rounded-full bg-forest-500" style={{ width: `${(c.fields_available / Math.max(c.fields_total, 1)) * 100}%` }} />
              </div>
            </div>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}

function FieldTable({ fields, selected, onHover, onOpen }: { fields: FieldSummary[]; selected: string | null; onHover: (id: string | null) => void; onOpen: (id: string) => void }) {
  const { units } = usePrefs();
  const sorted = [...fields].sort((a, b) => (a.coverage_completeness ?? 0) - (b.coverage_completeness ?? 0));
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-[12.5px] [&_td]:whitespace-nowrap">
        <thead>
          <tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500">
            <th className="py-2 pr-2 font-semibold">Field</th>
            <th className="py-2 pr-2 font-semibold">Area</th>
            <th className="py-2 pr-2 font-semibold">Latest crop</th>
            <th className="py-2 pr-2 font-semibold">Resilience</th>
            <th className="py-2 font-semibold">Coverage</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f) => (
            <tr
              key={f.field_id}
              onMouseEnter={() => onHover(f.field_id)}
              onClick={() => onOpen(f.field_id)}
              className={cn("cursor-pointer border-b border-line/60 transition-colors last:border-0 hover:bg-forest-50/70", selected === f.field_id && "bg-forest-50")}
            >
              <td className="py-2.5 pr-2">
                <Link href={`/fields/${f.field_id}`} className="font-semibold text-ink hover:text-forest-700" onClick={(e) => e.stopPropagation()}>{f.name}</Link>
                {f.processing_status !== "ready" && <span className="ml-1.5 text-[10.5px] font-semibold uppercase text-wheat-600">{f.processing_status}</span>}
              </td>
              <td className="py-2.5 pr-2 tabular text-ink-soft">{qText(f.area, units)}</td>
              <td className="py-2.5 pr-2">
                {f.latest_crop ? (
                  <span className="inline-flex items-center gap-1.5 text-ink-soft"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: cropColor(f.latest_crop.crop_code) }} />{f.latest_crop.crop_name}</span>
                ) : <span className="text-stone-400">Pending</span>}
              </td>
              <td className="py-2.5 pr-2"><ScoreBandPill band={f.resilience_band} /></td>
              <td className="py-2.5"><CompletenessMeter value={f.coverage_completeness} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <Link href="/fields" className="mt-3 inline-flex items-center gap-1 text-[12.5px] font-semibold text-forest-700">Open Field Explorer <ArrowRight className="h-3.5 w-3.5" /></Link>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full" />
      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Skeleton className="h-[520px]" />
        <Skeleton className="h-[520px]" />
      </div>
    </div>
  );
}
