"use client";
import { useState } from "react";
import { CloudRain, Droplets, Leaf, Mountain } from "lucide-react";
import type { ClimateProfile, SoilProfile, TerrainProfile, VegetationIndex, VegetationProfile } from "@/types/contracts";
import { useClimate, useSoil, useTerrain, useVegetation } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { formatDate, missingText, pct } from "@/lib/format";
import { DATASET_SHORT } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Badge, Card, CardBody, CardHeader, Segmented, Select, Skeleton } from "@/components/ui/primitives";
import { EmptyState, ErrorState, StateBoundary } from "@/components/shared/state";
import { IndicatorCard } from "@/components/shared/data-display";
import { ChartLegend, TimeSeriesChart } from "@/components/shared/charts";
import { FlagList, QualityIndicator, QuantityValue, SourceList, SupportBadge } from "@/components/shared/provenance";
import { LATEST_SEASON, seasonOptions } from "./common";

type Tab = "climate" | "moisture" | "vegetation" | "soil";
const TABS: { value: Tab; label: string; icon: typeof Leaf }[] = [
  { value: "climate", label: "Climate", icon: CloudRain },
  { value: "moisture", label: "Soil moisture", icon: Droplets },
  { value: "vegetation", label: "Vegetation", icon: Leaf },
  { value: "soil", label: "Soil & terrain", icon: Mountain },
];

export function EnvironmentView() {
  const fieldId = useFieldId();
  const [tab, setTab] = useState<Tab>("climate");
  const [season, setSeason] = useState(LATEST_SEASON);
  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Environmental sections" className="flex flex-wrap gap-1.5">
          {TABS.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              role="tab"
              aria-selected={tab === value}
              onClick={() => setTab(value)}
              className={cn("inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] font-semibold transition-colors", tab === value ? "border-forest-700 bg-forest-800 text-paper" : "border-line bg-paper text-ink-soft hover:border-line-strong hover:text-ink")}
            >
              <Icon className="h-4 w-4" aria-hidden /> {label}
            </button>
          ))}
        </div>
        {tab !== "soil" && <Select label="Season" value={season} onChange={setSeason} options={seasonOptions} />}
      </div>
      {tab === "climate" && <ClimateTab fieldId={fieldId} season={season} />}
      {tab === "moisture" && <MoistureTab fieldId={fieldId} season={season} />}
      {tab === "vegetation" && <VegetationTab fieldId={fieldId} season={season} />}
      {tab === "soil" && <SoilTerrainTab fieldId={fieldId} />}
    </div>
  );
}

const sk = <div className="grid gap-4 md:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-72 md:col-span-3" /></div>;

function ClimateTab({ fieldId, season }: { fieldId: string; season: number }) {
  const q = useClimate(fieldId, season);
  return <StateBoundary query={q} skeleton={sk}>{(c) => <Climate c={c} />}</StateBoundary>;
}

function Climate({ c }: { c: ClimateProfile }) {
  const s = (v: string) => c.series.find((x) => x.variable === v);
  const precip = s("precipitation"), tmax = s("tmax"), tmin = s("tmin"), gdd = s("gdd_cumulative"), et0 = s("et0");
  const climate = c.indicators.filter((i) => i.category === "climate");
  const water = c.indicators.filter((i) => i.category === "water");
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-wheat-200 bg-wheat-100/50 px-4 py-3 text-[12.5px] text-ink-soft">
        <Badge className="bg-wheat-200/70 text-wheat-600">Authoritative source</Badge>
        Precipitation: <strong className="text-ink">{DATASET_SHORT[c.authoritative_source.precipitation]}</strong> · Temperature: <strong className="text-ink">{DATASET_SHORT[c.authoritative_source.temperature]}</strong>
        <span className="text-stone-500">— ~55 km regional grid; PRISM (4 km) replaces it once integrated (P1).</span>
        <QualityIndicator quality={c.quality} className="ml-auto" />
      </div>
      <p className="text-[12.5px] text-stone-500">{c.season.label}</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{climate.map((i) => <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />)}</div>
      <div className="grid gap-6 lg:grid-cols-2">
        {precip && (
          <Card>
            <CardHeader eyebrow="Precipitation" title="Monthly totals vs normal" actions={<SupportBadge spatial={precip.spatial} />} />
            <CardBody>
              <TimeSeriesChart specs={[{ series: precip, kind: "bar", color: "#4f7c8a", showReference: true, name: "Precipitation" }]} />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2"><ChartLegend items={[{ label: "Monthly total", color: "#4f7c8a" }, { label: "Synthetic 1991–2020 normal", color: "#a59c88", dashed: true }]} /><SourceList sources={precip.sources} /></div>
            </CardBody>
          </Card>
        )}
        {tmax && tmin && (
          <Card>
            <CardHeader eyebrow="Temperature" title="Monthly mean maximum & minimum" actions={<SupportBadge spatial={tmax.spatial} />} />
            <CardBody>
              <TimeSeriesChart specs={[{ series: tmax, kind: "line", color: "#b4623a", name: "Tmax" }, { series: tmin, kind: "line", color: "#4f7c8a", name: "Tmin" }]} />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2"><ChartLegend items={[{ label: "Mean Tmax", color: "#b4623a" }, { label: "Mean Tmin", color: "#4f7c8a" }]} /><SourceList sources={tmax.sources} /></div>
            </CardBody>
          </Card>
        )}
        {gdd && (
          <Card>
            <CardHeader eyebrow="Heat accumulation" title="Cumulative growing degree days" description="Placeholder base 10 °C / cap 30 °C. Per-crop parameters come from the cited crop knowledge base (D5.6)." actions={<SupportBadge spatial={gdd.spatial} />} />
            <CardBody><TimeSeriesChart specs={[{ series: gdd, kind: "area", color: "#c99a3e", name: "Cumulative GDD" }]} /></CardBody>
          </Card>
        )}
        {et0 && precip && (
          <Card>
            <CardHeader eyebrow="Water demand" title="Reference ET₀ vs precipitation" actions={<SupportBadge spatial={et0.spatial} />} />
            <CardBody>
              <TimeSeriesChart specs={[{ series: et0, kind: "line", color: "#366645", name: "ET₀" }, { series: precip, kind: "bar", color: "#a3c19f", name: "Precipitation" }]} />
              <div className="mt-3"><ChartLegend items={[{ label: "Reference ET₀", color: "#366645" }, { label: "Precipitation", color: "#a3c19f" }]} /></div>
            </CardBody>
          </Card>
        )}
      </div>
      <div>
        <h3 className="mb-3 font-display text-[18px] text-ink">Water balance</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{water.map((i) => <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />)}</div>
      </div>
    </div>
  );
}

function MoistureTab({ fieldId, season }: { fieldId: string; season: number }) {
  const q = useClimate(fieldId, season);
  return (
    <StateBoundary query={q} skeleton={sk}>
      {(c) => {
        const sm = c.series.find((x) => x.variable === "sm_rootzone");
        const inds = c.indicators.filter((i) => i.category === "soil_moisture");
        const valid = sm?.points.filter((p) => p.value !== null).length ?? 0;
        return (
          <div className="space-y-6">
            <div className="flex items-start gap-3 rounded-xl border border-wheat-200 bg-wheat-100/60 p-4 text-[13px] leading-relaxed text-ink-soft">
              <Droplets className="mt-0.5 h-4 w-4 shrink-0 text-wheat-600" aria-hidden />
              <p><strong className="text-ink">Regional context — not a field measurement.</strong> SMAP L4 soil moisture is a 9 km model-assimilated estimate. One grid cell is about 8,100 ha; this field covers roughly {sm?.spatial.field_fraction_of_cell !== null && sm ? pct(sm.spatial.field_fraction_of_cell, 1) : "—"} of it.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">{inds.map((i) => <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />)}</div>
            {sm && (
              <Card>
                <CardHeader eyebrow="SMAP L4 · SPL4SMGP" title="Daily root-zone soil moisture (0–100 cm)" description="Gaps are missing retrievals, shown as breaks — never as zero." actions={<><SupportBadge spatial={sm.spatial} /><SourceList sources={sm.sources} /></>} />
                <CardBody>
                  {valid === 0 ? (
                    <EmptyState title="No soil-moisture data for this season" description={missingText(sm.points[0]?.missing_reason)} />
                  ) : (
                    <TimeSeriesChart x="date" height={280} specs={[{ series: sm, kind: "area", color: "#4f7c8a", name: "Root-zone SM" }]} />
                  )}
                  <p className="mt-2 text-[11.5px] text-stone-500">{valid} of {sm.points.length} days with values · UTC days</p>
                </CardBody>
              </Card>
            )}
          </div>
        );
      }}
    </StateBoundary>
  );
}

const INDEXES: VegetationIndex[] = ["NDVI", "EVI", "NDMI"];

function VegetationTab({ fieldId, season }: { fieldId: string; season: number }) {
  const [index, setIndex] = useState<VegetationIndex>("NDVI");
  const q = useVegetation(fieldId, season, index);
  return (
    <div className="space-y-4">
      <Segmented label="Vegetation index" value={index} onChange={setIndex} options={INDEXES.map((i) => ({ value: i, label: i }))} />
      <StateBoundary query={q} skeleton={sk}>{(v) => <Vegetation v={v} />}</StateBoundary>
    </div>
  );
}

function Vegetation({ v }: { v: VegetationProfile }) {
  const accepted = v.scenes.filter((s) => s.accepted).length;
  const ph = v.phenology;
  if (v.scenes.length === 0) {
    return <EmptyState title={`No ${v.index} scenes for ${v.year}`} description={missingText(v.quality.missing_reason)} />;
  }
  const allPoints = {
    ...v.series,
    series_id: v.series.series_id + ":all",
    label: "All scenes (incl. rejected)",
    points: v.scenes.map((s) => ({ t: s.acquired_at.slice(0, 10), value: s.median, quality_status: s.accepted ? ("valid" as const) : ("flagged" as const), missing_reason: s.missing_reason })),
  };
  const markers = [ph.greenup_date && { t: ph.greenup_date, label: "Green-up", color: "#4b8158" }, ph.peak_date && { t: ph.peak_date, label: "Peak", color: "#1d3a29" }, ph.senescence_date && { t: ph.senescence_date, label: "Senescence", color: "#a87a24" }].filter(Boolean) as { t: string; label: string; color: string }[];
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MiniStat label={`Peak ${v.index}`} value={<QuantityValue q={ph.peak_value} />} sub={ph.peak_date ? formatDate(ph.peak_date, "long") : missingText(ph.missing_reason)} />
        <MiniStat label="Green-up" value={formatDate(ph.greenup_date, "long")} sub="Half-amplitude crossing" />
        <MiniStat label="Senescence" value={formatDate(ph.senescence_date, "long")} sub="Half-amplitude crossing" />
        <MiniStat label="Accepted scenes" value={`${accepted} / ${v.scenes.length}`} sub="≥ 70% clear field pixels" />
      </div>
      {v.quality.flags.length > 0 && <FlagList flags={v.quality.flags} />}
      <Card>
        <CardHeader eyebrow="HLS-VI · L30 + S30" title={`${v.index} through the ${v.year} season`} description="Accepted scenes form the line; rejected (cloud-limited) scenes appear as faint points." actions={<><SupportBadge spatial={v.spatial} /><SourceList sources={v.sources} /></>} />
        <CardBody>
          <TimeSeriesChart x="date" height={300} markers={markers} specs={[{ series: allPoints, kind: "scatter", color: "#cfc3aa", name: "All scenes" }, { series: v.series, kind: "line", color: "#366645", name: "Accepted scenes", connect: true }]} />
          <div className="mt-3"><ChartLegend items={[{ label: "Accepted scene median", color: "#366645" }, { label: "All scenes", color: "#cfc3aa" }]} /></div>
          <p className="mt-2 text-[11.5px] text-stone-500">{ph.method.name}: {ph.method.description}</p>
        </CardBody>
      </Card>
      <Card>
        <CardHeader eyebrow="Scene log" title="Every scene, with cloud-mask accounting" description="Fmask bits 1–3 (cloud, adjacent, shadow) are masked; scenes need ≥ 70% clear field pixels." />
        <CardBody className="pt-2">
          <div className="max-h-[360px] overflow-auto">
            <table className="w-full min-w-[640px] text-left text-[12px]">
              <thead className="sticky top-0 bg-paper">
                <tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500">
                  <th className="py-2 pr-3 font-semibold">Date</th><th className="py-2 pr-3 font-semibold">Granule</th><th className="py-2 pr-3 font-semibold">Median</th><th className="py-2 pr-3 font-semibold">Clear</th><th className="py-2 pr-3 font-semibold">Masked (cloud / adj. / shadow)</th><th className="py-2 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {v.scenes.map((s) => (
                  <tr key={s.granule_id} className="border-b border-line/50">
                    <td className="py-1.5 pr-3 tabular">{formatDate(s.acquired_at, "long")}</td>
                    <td className="py-1.5 pr-3 font-mono text-[10.5px] text-stone-500">{s.granule_id.replace("SYNTHETIC.", "")}</td>
                    <td className="py-1.5 pr-3 tabular">{s.median === null ? "—" : s.median.toFixed(3)}</td>
                    <td className="py-1.5 pr-3"><span className="inline-flex items-center gap-2"><span className="h-1.5 w-12 overflow-hidden rounded-full bg-parchment"><span className={cn("block h-full", s.accepted ? "bg-forest-500" : "bg-wheat-500")} style={{ width: `${s.clear_fraction * 100}%` }} /></span><span className="tabular">{pct(s.clear_fraction)}</span></span></td>
                    <td className="py-1.5 pr-3 tabular text-stone-500">{s.mask_counts.cloud} / {s.mask_counts.cloud_adjacent} / {s.mask_counts.cloud_shadow}</td>
                    <td className="py-1.5">{s.accepted ? <Badge className="bg-forest-100 text-forest-800">Accepted</Badge> : <Badge className="bg-wheat-100 text-wheat-600">{s.missing_reason === "QA_MASKED_CLOUD" ? "Cloud" : "Rejected"}</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function MiniStat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">{label}</p>
      <p className="mt-1.5 font-display text-[22px] leading-none text-ink">{value}</p>
      {sub && <p className="mt-1.5 text-[11.5px] text-stone-500">{sub}</p>}
    </div>
  );
}

function SoilTerrainTab({ fieldId }: { fieldId: string }) {
  const soil = useSoil(fieldId);
  const terrain = useTerrain(fieldId);
  return (
    <div className="space-y-6">
      <StateBoundary query={soil} skeleton={<Skeleton className="h-80" />}>{(s) => <Soil s={s} />}</StateBoundary>
      {terrain.isPending ? <Skeleton className="h-40" /> : terrain.isError ? <ErrorState error={terrain.error} onRetry={() => void terrain.refetch()} title="Terrain unavailable" /> : <Terrain t={terrain.data.data} />}
    </div>
  );
}

function Soil({ s }: { s: SoilProfile }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader eyebrow="SSURGO · area × component-percent weighting" title="Soil profile by depth" description="Representative values with SSURGO low–high ranges in brackets." actions={<><SupportBadge spatial={s.spatial} /><SourceList sources={s.sources} /><QualityIndicator quality={s.quality} /></>} />
        <CardBody className="pt-2">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-[12.5px]">
              <thead>
                <tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500">
                  <th className="py-2 pr-3 font-semibold">Depth</th><th className="py-2 pr-3 font-semibold">Texture</th><th className="py-2 pr-3 font-semibold">Sand</th><th className="py-2 pr-3 font-semibold">Silt</th><th className="py-2 pr-3 font-semibold">Clay</th><th className="py-2 pr-3 font-semibold">pH</th><th className="py-2 pr-3 font-semibold">OM</th><th className="py-2 font-semibold">AWC</th>
                </tr>
              </thead>
              <tbody>
                {s.layers.map((l) => (
                  <tr key={l.top_cm} className="border-b border-line/60 last:border-0">
                    <td className="py-3 pr-3 font-semibold tabular">{l.top_cm}–{l.bottom_cm} cm</td>
                    <td className="py-3 pr-3">{l.texture_class ?? "—"}</td>
                    <td className="py-3 pr-3"><QuantityValue q={l.sand_pct} /></td>
                    <td className="py-3 pr-3"><QuantityValue q={l.silt_pct} /></td>
                    <td className="py-3 pr-3"><QuantityValue q={l.clay_pct} /></td>
                    <td className="py-3 pr-3"><QuantityValue q={l.ph_h2o} /></td>
                    <td className="py-3 pr-3"><QuantityValue q={l.om_pct} /></td>
                    <td className="py-3"><QuantityValue q={l.awc} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 grid gap-4 border-t border-line/70 pt-4 sm:grid-cols-4">
            <MiniStat label="AWS 0–100 cm" value={<QuantityValue q={s.aws_0_100} />} />
            <MiniStat label="AWS 0–150 cm" value={<QuantityValue q={s.aws_0_150} />} />
            <MiniStat label="Drainage" value={<span className="text-[16px]">{s.drainage_class.value ?? "—"}</span>} sub={s.drainage_class.weight_share !== null ? `${pct(s.drainage_class.weight_share)} of weight` : undefined} />
            <MiniStat label="Hydrologic group" value={s.hydrologic_group.value ?? "—"} sub={s.hydrologic_group.weight_share !== null ? `${pct(s.hydrologic_group.weight_share)} of weight` : undefined} />
          </div>
        </CardBody>
      </Card>
      <Card>
        <CardHeader eyebrow="Map units" title="Soil map units intersecting the field" description={`${s.method.name} · null-weight fraction ${pct(s.null_weight_fraction)}`} />
        <CardBody className="space-y-3">
          {s.map_units.map((m) => (
            <div key={m.mukey} className="flex items-center gap-4">
              <div className="w-20 shrink-0 text-right font-display text-[20px] tabular text-ink">{pct(m.area_fraction)}</div>
              <div className="min-w-0 flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-parchment"><div className="h-full rounded-full bg-soil-500" style={{ width: `${m.area_fraction * 100}%` }} /></div>
                <p className="mt-1.5 text-[12.5px] text-ink">{m.muname}</p>
                <p className="text-[11.5px] text-stone-500">mukey {m.mukey} · {m.major_components.map((c) => `${c.compname} ${c.comppct_r ?? "—"}%`).join(", ")}</p>
              </div>
            </div>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}

function Terrain({ t }: { t: TerrainProfile }) {
  return (
    <Card>
      <CardHeader eyebrow="SRTM GL1 · 30 m" title="Terrain" description={t.method.description} actions={<><SupportBadge spatial={t.spatial} /><SourceList sources={t.sources} /><QualityIndicator quality={t.quality} /></>} />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MiniStat label="Mean elevation" value={<QuantityValue q={t.elevation_mean} />} />
        <MiniStat label="Min elevation" value={<QuantityValue q={t.elevation_min} />} />
        <MiniStat label="Max elevation" value={<QuantityValue q={t.elevation_max} />} />
        <MiniStat label="Mean slope" value={<QuantityValue q={t.slope_mean_pct} />} />
        <MiniStat label="Slope p90" value={<QuantityValue q={t.slope_p90_pct} />} />
        {t.quality.status === "missing" && <p className="text-[12.5px] text-clay-600 sm:col-span-2 lg:col-span-5">{missingText(t.quality.missing_reason)}</p>}
      </CardBody>
    </Card>
  );
}
