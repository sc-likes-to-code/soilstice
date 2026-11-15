"use client";
import Link from "next/link";
import { ArrowRight, Droplets, Leaf, Mountain, RefreshCw, ShieldCheck } from "lucide-react";
import type { FieldProfile } from "@/types/contracts";
import { useFieldProfile } from "@/hooks/queries";
import { useFieldId } from "@/components/layout/field-layout";
import { missingText, formatDate } from "@/lib/format";
import { DATASET_SHORT } from "@/lib/vocab";
import { Card, CardBody, CardHeader, Skeleton } from "@/components/ui/primitives";
import { EmptyState, ErrorState } from "@/components/shared/state";
import { CoverageTable, CropLegend, CropTimeline, IndicatorCard } from "@/components/shared/data-display";
import { FieldMap } from "@/components/shared/field-map";
import { QuantityValue, ScoreBandPill, SourceList, SupportBadge } from "@/components/shared/provenance";
import { LATEST_SEASON } from "./common";

export function FieldOverviewView() {
  const fieldId = useFieldId();
  const profile = useFieldProfile(fieldId, LATEST_SEASON);
  if (profile.isPending) return <OverviewSkeleton />;
  if (profile.isError) return <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />;
  return <Overview p={profile.data.data} />;
}

function Unavailable({ dataset, p }: { dataset: keyof typeof DATASET_SHORT; p: FieldProfile }) {
  const c = p.coverage.datasets.find((d) => d.dataset_id === dataset);
  let desc = c?.missing_reason ? missingText(c.missing_reason) : c?.note ?? "This dataset has not been processed for this field.";
  if (dataset === "nasa_srtm_gl1") {
    desc = "NASA Earthdata Login required (SOILSTICE_EARTHDATA_TOKEN) to acquire SRTM GL1 30 m elevation rasters.";
  }
  return <EmptyState title={`${DATASET_SHORT[dataset]} not available`} description={desc} />;
}

function Overview({ p }: { p: FieldProfile }) {
  const { field, soil, terrain, crop_history: hist, resilience: res } = p;
  const base = `/fields/${field.field_id}`;
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <Card>
          <CardHeader
            eyebrow="Crop history · CDL"
            title={hist ? `${hist.period.start_year}–${hist.period.end_year} majority crop per year` : "Crop history"}
            description="Majority Cropland Data Layer class within the field each year. Hover a year for class shares."
            actions={<Link href={`${base}/rotation`} className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-forest-700">Rotation Lab <ArrowRight className="h-3.5 w-3.5" /></Link>}
          />
          <CardBody>
            {hist ? (
              <div className="space-y-4">
                <CropTimeline years={hist.years} />
                <CropLegend codes={hist.years.map((y) => y.majority.crop_code ?? 0)} />
                <div className="grid gap-3 sm:grid-cols-3">
                  {hist.metrics.map((m) => <IndicatorCard key={m.indicator_id} indicator={m} size="sm" />)}
                </div>
              </div>
            ) : <Unavailable dataset="usda_nass_cdl" p={p} />}
          </CardBody>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader eyebrow="Soil · SSURGO" title={<span className="inline-flex items-center gap-2"><Droplets className="h-4 w-4 text-sky-500" /> Soil summary</span>} actions={soil && <SupportBadge spatial={soil.spatial} />} />
            <CardBody>
              {soil ? (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-[13px]">
                  <Item label="Texture (0–30 cm)" value={soil.layers[0]?.texture_class ?? "—"} />
                  <Item label="Available water 0–150 cm" value={<QuantityValue q={soil.aws_0_150} />} />
                  <Item label="pH (0–30 cm)" value={<QuantityValue q={soil.layers[0]?.ph_h2o} />} />
                  <Item label="Organic matter (0–30 cm)" value={<QuantityValue q={soil.layers[0]?.om_pct} />} />
                  <Item label="Drainage class" value={soil.drainage_class.value ?? "—"} />
                  <Item label="Hydrologic group" value={soil.hydrologic_group.value ?? "—"} />
                  <div className="col-span-2 flex flex-wrap items-center gap-2 border-t border-line/70 pt-3"><SourceList sources={soil.sources} /><span className="text-[11.5px] text-stone-500">{soil.map_units.length} map unit{soil.map_units.length > 1 ? "s" : ""}</span></div>
                </dl>
              ) : <Unavailable dataset="usda_nrcs_ssurgo_sda" p={p} />}
            </CardBody>
          </Card>
          <Card>
            <CardHeader eyebrow="Terrain · SRTM" title={<span className="inline-flex items-center gap-2"><Mountain className="h-4 w-4 text-soil-500" /> Terrain summary</span>} actions={terrain && <SupportBadge spatial={terrain.spatial} />} />
            <CardBody>
              {terrain && terrain.quality.status !== "missing" ? (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-[13px]">
                  <Item label="Mean elevation" value={<QuantityValue q={terrain.elevation_mean} />} />
                  <Item label="Elevation range" value={<span className="tabular"><QuantityValue q={terrain.elevation_min} /> – <QuantityValue q={terrain.elevation_max} /></span>} />
                  <Item label="Mean slope" value={<QuantityValue q={terrain.slope_mean_pct} />} />
                  <Item label="Slope (90th pct)" value={<QuantityValue q={terrain.slope_p90_pct} />} />
                  <div className="col-span-2 border-t border-line/70 pt-3"><SourceList sources={terrain.sources} /></div>
                </dl>
              ) : <Unavailable dataset="nasa_srtm_gl1" p={p} />}
            </CardBody>
          </Card>
        </div>

        <Card>
          <CardHeader
            eyebrow={`Season ${LATEST_SEASON}`}
            title={<span className="inline-flex items-center gap-2"><Leaf className="h-4 w-4 text-forest-500" /> Environment at a glance</span>}
            description="Climate indicators are regional context; vegetation indicators are field-resolved."
            actions={<Link href={`${base}/environment`} className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-forest-700">Environmental Intelligence <ArrowRight className="h-3.5 w-3.5" /></Link>}
          />
          <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...p.climate_summary, ...p.vegetation_summary].map((i) => <IndicatorCard key={i.indicator_id} indicator={i} size="sm" />)}
            {p.climate_summary.length + p.vegetation_summary.length === 0 && <div className="sm:col-span-3"><Unavailable dataset="nasa_power_daily_ag" p={p} /></div>}
          </CardBody>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <CardBody className="pt-5">
            <FieldMap height={240} fields={[{ field_id: field.field_id, name: field.name, geometry: field.geometry, band: res?.composite.band ?? "unknown" }]} colorBy="none" focusId={field.field_id} caption={field.source === "synthetic" ? "Synthetic parcel geometry" : "Field boundary · Live API"} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Resilience" title={<span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-forest-600" /> Field resilience</span>} />
          <CardBody>
            {res && res.status === "computed" ? (
              <div>
                <div className="flex items-end gap-3">
                  <span className="font-display text-[44px] leading-none text-ink"><QuantityValue q={res.composite.score} /></span>
                  <ScoreBandPill band={res.composite.band} confidence={res.composite.confidence} />
                </div>
                <p className="mt-2 text-[12.5px] text-ink-soft">{res.composite.components_used} of {res.composite.components_total} components · model {res.model_version}</p>
              </div>
            ) : (
              <EmptyState title={res?.status === "insufficient_data" ? "Insufficient data" : "Not computed yet"} description={res?.limitations.map((l) => l.message).join(" ") || "Resilience needs at least 4 of 5 components."} />
            )}
            <Link href={`${base}/resilience`} className="mt-4 inline-flex items-center gap-1 text-[12.5px] font-semibold text-forest-700">View component breakdown <ArrowRight className="h-3.5 w-3.5" /></Link>
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Next step" title={<span className="inline-flex items-center gap-2"><RefreshCw className="h-4 w-4 text-wheat-600" /> Compare rotations</span>} description="See explained next-season options and test alternative sequences." />
          <CardBody><Link href={`${base}/rotation`} className="inline-flex items-center gap-1 text-[13px] font-semibold text-forest-700">Open Rotation Lab <ArrowRight className="h-3.5 w-3.5" /></Link></CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Data coverage" title="Essential datasets" description={`Last updated ${formatDate(p.coverage.datasets.find((d) => d.last_updated)?.last_updated, "long")}`} />
          <CardBody className="pt-2"><CoverageTable coverage={p.coverage} condensed /></CardBody>
        </Card>
      </div>
    </div>
  );
}

function Item({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">{label}</dt>
      <dd className="mt-1 text-[15px] font-semibold text-ink">{value}</dd>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="space-y-6"><Skeleton className="h-64" /><div className="grid gap-6 lg:grid-cols-2"><Skeleton className="h-56" /><Skeleton className="h-56" /></div></div>
      <div className="space-y-6"><Skeleton className="h-64" /><Skeleton className="h-48" /></div>
    </div>
  );
}
