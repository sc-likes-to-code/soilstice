"use client";
import { useState } from "react";
import { CloudRain, Droplets, Mountain } from "lucide-react";
import type { ClimateProfile, EnvironmentalIndicator, SoilProfile, TerrainProfile, TimeSeries } from "@/types/contracts";
import { useClimate, useSoil, useTerrain } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { pct } from "@/lib/format";
import { DATASET_SHORT } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Badge, Card, CardBody, CardHeader, Select, Skeleton } from "@/components/ui/primitives";
import { EmptyState, ErrorState, StateBoundary } from "@/components/shared/state";
import { IndicatorCard } from "@/components/shared/data-display";
import { ChartLegend, TimeSeriesChart } from "@/components/shared/charts";
import { QualityIndicator, QuantityValue, SourceList, SupportBadge } from "@/components/shared/provenance";
import { LATEST_SEASON, seasonOptions } from "./common";

type Tab = "climate" | "moisture" | "soil";
const TABS: { value: Tab; label: string; icon: typeof Mountain }[] = [
  { value: "climate", label: "Climate", icon: CloudRain },
  { value: "moisture", label: "Soil moisture", icon: Droplets },
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
  const isExcluded = (i: EnvironmentalIndicator) =>
    i.key === "et_actual_season" ||
    i.key === "sm_rootzone_percentile" ||
    i.label.toLowerCase().includes("actual et") ||
    i.label.toLowerCase().includes("openet");
  const climate = c.indicators.filter((i) => i.category === "climate" && !isExcluded(i));
  const water = c.indicators.filter((i) => i.category === "water" && !isExcluded(i));
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
            <CardHeader eyebrow="Heat accumulation" title="Cumulative growing degree days" description="Standard warm-season baseline (base 10 °C / cap 30 °C). Per-crop parameters come from the cited crop knowledge base." actions={<SupportBadge spatial={gdd.spatial} />} />
            <CardBody><TimeSeriesChart specs={[{ series: gdd, kind: "area", color: "#c99a3e", name: "Cumulative GDD" }]} /></CardBody>
          </Card>
        )}
        {et0 && precip && (
          <Card>
            <CardHeader eyebrow="Climatic water balance" title="Reference ET₀ vs precipitation" actions={<SupportBadge spatial={et0.spatial} />} />
            <CardBody>
              <TimeSeriesChart specs={[{ series: et0, kind: "line", color: "#366645", name: "Reference ET₀" }, { series: precip, kind: "bar", color: "#a3c19f", name: "Precipitation" }]} />
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
        const smSurface = c.series.find((x) => x.variable === "sm_surface");
        const smShallow = c.series.find((x) => x.variable === "sm_shallow");
        const smRoot = c.series.find((x) => x.variable === "sm_rootzone");
        const smDeep = c.series.find((x) => x.variable === "sm_deep");

        const isMeteomatics = c.indicators.some((i) => i.sources.some((s) => s.dataset_id === "meteomatics")) ||
          c.series.some((s) => s.sources.some((src) => src.dataset_id === "meteomatics"));

        const smIndicators = c.indicators.filter((i) => i.category === "soil_moisture");
        const indMap = new Map(smIndicators.map((i) => [i.indicator_id.split(":").pop() ?? "", i]));

        const surfInd = indMap.get("sm_surface_mean_season");
        const shallowInd = indMap.get("sm_shallow_mean_season");
        const rootInd = indMap.get("sm_middepth_mean_season") ?? indMap.get("sm_rootzone_mean_season");
        const deepInd = indMap.get("sm_deep_mean_season");
        const compInd = indMap.get("sm_rootzone_composite_season") ?? indMap.get("sm_rootzone_mean_season");
        const cvInd = indMap.get("sm_rootzone_cv");
        const dryInd = indMap.get("sm_dry_days_count") ?? indMap.get("sm_rootzone_dry_days");

        const depthSpecs = [
          smSurface && { series: smSurface, kind: "line" as const, color: "#789dbc", name: "Surface (-5 cm)" },
          smShallow && { series: smShallow, kind: "line" as const, color: "#4f7c8a", name: "Shallow (-15 cm)" },
          smRoot && { series: smRoot, kind: "line" as const, color: "#2d5466", name: "Root-zone (-50 cm)" },
          smDeep && { series: smDeep, kind: "line" as const, color: "#193240", name: "Deep drainage (-150 cm)" },
        ].filter(Boolean) as { series: TimeSeries; kind: "line" | "area"; color: string; name: string }[];

        const primarySeries = smRoot ?? smSurface;
        const valid = primarySeries?.points.filter((p) => p.value !== null).length ?? 0;

        return (
          <div className="space-y-6">
            <div className="flex items-start gap-3 rounded-xl border border-wheat-200 bg-wheat-100/60 p-4 text-[13px] leading-relaxed text-ink-soft">
              <Droplets className="mt-0.5 h-4 w-4 shrink-0 text-wheat-600" aria-hidden />
              <div>
                <p>
                  <strong className="text-ink">
                    {isMeteomatics ? "Meteomatics Multi-Depth Soil Moisture Model (~9 km)." : "Regional context — not a field measurement."}
                  </strong>{" "}
                  {isMeteomatics
                    ? "ECMWF-assimilated continuous volumetric soil water content across 4 standard soil layers (-5 cm, -15 cm, -50 cm, -150 cm). Depth-weighted root-zone integration applies a 0.10 / 0.20 / 0.70 profile composite."
                    : `SMAP L4 soil moisture is a 9 km model-assimilated estimate. One grid cell is about 8,100 ha; this field covers roughly ${primarySeries?.spatial.field_fraction_of_cell !== null && primarySeries ? pct(primarySeries.spatial.field_fraction_of_cell, 1) : "—"} of it.`}
                </p>
              </div>
            </div>

            {/* 4 Standard Depths + Composite Cards */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <MiniStat
                label="Surface (-5 cm)"
                value={surfInd?.value ? <QuantityValue q={surfInd.value} /> : "—"}
                sub="Mean volumetric water (m³/m³)"
              />
              <MiniStat
                label="Shallow (-15 cm)"
                value={shallowInd?.value ? <QuantityValue q={shallowInd.value} /> : "—"}
                sub="Mean volumetric water (m³/m³)"
              />
              <MiniStat
                label="Mid-depth (-50 cm)"
                value={rootInd?.value ? <QuantityValue q={rootInd.value} /> : "—"}
                sub="Root-zone core layer"
              />
              <MiniStat
                label="Deep (-150 cm)"
                value={deepInd?.value ? <QuantityValue q={deepInd.value} /> : "—"}
                sub="Sub-root drainage boundary"
              />
              <MiniStat
                label="Root Composite"
                value={compInd?.value ? <QuantityValue q={compInd.value} /> : "—"}
                sub="0.10·S + 0.20·M + 0.70·D"
              />
            </div>

            {/* Additional Indicators */}
            {smIndicators.length > 0 && (
              <div>
                <h3 className="mb-3 font-display text-[16px] text-ink">Moisture dynamics & risk indicators</h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  {cvInd && <IndicatorCard indicator={cvInd} size="sm" />}
                  {dryInd && <IndicatorCard indicator={dryInd} size="sm" />}
                  {smIndicators.filter((i) => ![
                    "sm_surface_mean_season", "sm_shallow_mean_season", "sm_rootzone_mean_season",
                    "sm_deep_mean_season", "sm_rootzone_composite_season", "sm_rootzone_cv", "sm_dry_days_count", "sm_rootzone_dry_days",
                  ].includes(i.indicator_id.split(":").pop() ?? "")).map((i) => (
                    <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />
                  ))}
                </div>
              </div>
            )}

            {/* Time Series Multi-Depth Chart */}
            {primarySeries && (
              <Card>
                <CardHeader
                  eyebrow={isMeteomatics ? "Meteomatics · Multi-Depth Hydrology" : "SMAP L4 · SPL4SMGP"}
                  title="Daily volumetric soil water time series"
                  description={isMeteomatics ? "Continuous time series across four soil depths. Gaps appear as breaks, never zeros." : "Daily root-zone soil moisture (0–100 cm)."}
                  actions={
                    <div className="flex flex-wrap items-center gap-1.5">
                      <SupportBadge spatial={primarySeries.spatial} />
                      <SourceList sources={primarySeries.sources} />
                    </div>
                  }
                />
                <CardBody>
                  {valid === 0 ? (
                    <EmptyState
                      title="No soil-moisture observations for this season"
                      description="Soil moisture time series is not yet available for this season range."
                    />
                  ) : (
                    <>
                      <TimeSeriesChart
                        x="date"
                        height={300}
                        specs={depthSpecs.length > 0 ? depthSpecs : [{ series: primarySeries, kind: "area", color: "#4f7c8a", name: "Soil moisture" }]}
                      />
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                        <ChartLegend
                          items={depthSpecs.length > 0 ? depthSpecs.map((s) => ({ label: s.name, color: s.color })) : [{ label: "Root-zone SM", color: "#4f7c8a" }]}
                        />
                        <p className="text-[11.5px] text-stone-500">{valid} observations in season · UTC</p>
                      </div>
                    </>
                  )}
                </CardBody>
              </Card>
            )}
          </div>
        );
      }}
    </StateBoundary>
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
        <CardHeader
          eyebrow="SSURGO · area × component-percent weighting"
          title="Soil profile by depth"
          description="Representative values with SSURGO low–high ranges in brackets."
          actions={
            <div className="flex flex-wrap items-center gap-1.5">
              <SupportBadge spatial={s.spatial} />
              <SourceList sources={s.sources} />
              <QualityIndicator quality={s.quality} />
            </div>
          }
        />
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
  const isMeteomatics = t.sources.some((s) => s.dataset_id === "meteomatics") || t.method.method_id.includes("meteomatics");
  const slopeWithheld = t.slope_p90_pct.value === null || t.slope_p90_pct.missing_reason !== null;

  return (
    <Card>
      <CardHeader
        eyebrow={isMeteomatics ? "Meteomatics · Elevation Model" : "SRTM GL1 · 30 m"}
        title="Terrain & Elevation"
        description={t.method.description}
        actions={
          <div className="flex flex-wrap items-center gap-1.5">
            <SupportBadge spatial={t.spatial} />
            <SourceList sources={t.sources} />
            <QualityIndicator quality={t.quality} />
          </div>
        }
      />
      <CardBody className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <MiniStat label="Mean elevation" value={<QuantityValue q={t.elevation_mean} />} />
          <MiniStat label="Min elevation" value={<QuantityValue q={t.elevation_min} />} />
          <MiniStat label="Max elevation" value={<QuantityValue q={t.elevation_max} />} />
          <MiniStat label="Mean slope" value={<QuantityValue q={t.slope_mean_pct} />} />
          <MiniStat label="Slope p90" value={<QuantityValue q={t.slope_p90_pct} />} />
        </div>
        {slopeWithheld && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[12.5px] text-amber-900">
            <span className="font-semibold">Conditional Slope Derivation:</span> Slope and 90th percentile slope are withheld when spatial grid resolution is inadequate for robust slope modeling (&lt; 9 field points or flat spatial variance). Erosion hazard scoring is accordingly withheld.
          </div>
        )}
        {t.quality.status === "missing" && (
          <p className="text-[12.5px] text-stone-600 sm:col-span-2 lg:col-span-5">
            <span className="font-semibold text-clay-700">Terrain Data Unavailable:</span> {t.quality.missing_reason ?? "Elevation model unavailable."}
          </p>
        )}
      </CardBody>
    </Card>
  );
}
