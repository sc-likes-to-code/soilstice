"use client";
import { useMemo, useState } from "react";
import type { DatasetDescriptor } from "@/types/contracts";
import { useDatasets, useEvidence, useFields } from "@/hooks/queries";
import { useActiveFarm } from "@/hooks/active-farm";
import { formatDate, resolutionText } from "@/lib/format";
import { DATASET_SHORT, SUPPORT_STYLE, VERIFICATION_STYLE } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Badge, Card, CardBody, CardHeader, PageHeader, Segmented, Skeleton } from "@/components/ui/primitives";
import { StateBoundary } from "@/components/shared/state";
import { EvidenceList } from "@/components/shared/data-display";
import { DocLink } from "@/components/shared/provenance";

const LIMITATIONS = [
  "Coarse-grid products (SMAP 9 km, POWER ~55 km meteorology / ~110 km solar, IMERG ~11 km, GAEZ ~1 km) describe the surrounding region, not the field.",
  "SMAP L4 is a model-assimilated estimate, not a direct measurement; SMAP L3 retrievals are gappy and quality-filtered.",
  "The Cropland Data Layer is a classification, not ground truth; accuracy varies by crop and state, and is lower for minor and double-crop classes.",
  "Crop Sequence Boundaries are crop segments, not ownership or legal field boundaries.",
  "SSURGO values are representative values for map-unit components, often estimated; low–high ranges are shown as uncertainty.",
  "SRTM dates from February 2000 and is a radar surface model; tree lines and buildings inflate it.",
  "HLS vegetation-index back-processing for 2013–2019 must be confirmed; Fmask bits 4–5 are masked only after confirmation.",
  "MODIS Terra/Aqua science collection is planned to end in 2027; no P0 feature depends on MODIS.",
];

export function EvidenceView() {
  const datasets = useDatasets();
  const { farm } = useActiveFarm();
  const fields = useFields(farm?.farm_id ?? null);
  const anyField = fields.data?.data[0]?.field_id ?? null;
  const evidence = useEvidence(anyField);
  const [priority, setPriority] = useState<"all" | "P0" | "P1" | "P2">("all");

  return (
    <div>
      <PageHeader eyebrow="Reports & Evidence" title="Evidence & data sources" description="Every dataset and method SOILSTICE relies on, with verified live providers and Phase 0/Phase 2 verification records." />
      <div className="space-y-6">
        <Card>
          <CardHeader
            eyebrow="Dataset registry"
            title="NASA, USDA and partner datasets"
            description="Comprehensive registry of NASA, USDA, and scientific partner datasets. Operational live providers: NASA POWER (daily agrometeorology), USDA NRCS SSURGO (soil survey), and USDA NASS CDL (crop classification); SRTM terrain verified; SMAP and HLS staged for Phase 3."
            actions={<Segmented label="Priority" size="sm" value={priority} onChange={setPriority} options={[{ value: "all", label: "All" }, { value: "P0", label: "P0" }, { value: "P1", label: "P1" }, { value: "P2", label: "P2" }]} />}
          />
          <CardBody className="pt-2">
            <StateBoundary query={datasets} skeleton={<Skeleton className="h-80" />}>
              {(d) => <DatasetTable rows={priority === "all" ? d : d.filter((x) => x.priority === priority)} />}
            </StateBoundary>
          </CardBody>
        </Card>
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card>
            <CardHeader eyebrow="Methods & rules" title="How values are produced" />
            <CardBody>
              <StateBoundary query={evidence} skeleton={<Skeleton className="h-60" />}>
                {(items) => <EvidenceList items={items.filter((i) => i.field_id === null && i.kind !== "dataset")} />}
              </StateBoundary>
            </CardBody>
          </Card>
          <Card>
            <CardHeader eyebrow="Known limitations" title="What this data cannot tell you" />
            <CardBody>
              <ul className="space-y-3 text-[12.5px] leading-relaxed text-ink-soft">
                {LIMITATIONS.map((l) => <li key={l} className="flex gap-2.5"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-wheat-500" />{l}</li>)}
              </ul>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

function DatasetTable({ rows }: { rows: DatasetDescriptor[] }) {
  const sorted = useMemo(() => [...rows].sort((a, b) => a.priority.localeCompare(b.priority)), [rows]);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] text-left text-[12.5px]">
        <thead>
          <tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500">
            <th className="py-2 pr-3 font-semibold">Dataset</th><th className="py-2 pr-3 font-semibold">Product · version</th><th className="py-2 pr-3 font-semibold">Priority</th><th className="py-2 pr-3 font-semibold">Support</th><th className="py-2 pr-3 font-semibold">Coverage</th><th className="py-2 pr-3 font-semibold">Verified</th><th className="py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((d) => {
            const v = VERIFICATION_STYLE[d.verification_status];
            const s = SUPPORT_STYLE[d.support_class];
            return (
              <tr key={d.dataset_id} className="border-b border-line/60 align-top last:border-0">
                <td className="py-3 pr-3">
                  <p className="font-semibold text-ink">{d.title}</p>
                  <p className="text-[11.5px] text-stone-500">{d.publisher} · <DocLink href={d.documentation_url}>docs</DocLink></p>
                </td>
                <td className="py-3 pr-3 font-mono text-[11.5px] text-ink-soft">{d.product}<br />{d.product_version}{d.doi && <><br />doi:{d.doi}</>}</td>
                <td className="py-3 pr-3"><Badge className={cn(d.priority === "P0" ? "bg-forest-800 text-paper" : d.priority === "P1" ? "bg-forest-100 text-forest-800" : "bg-parchment text-ink-soft")}>{d.priority}</Badge></td>
                <td className="py-3 pr-3"><Badge className={cn("border", s.bg, s.fg, s.border)}>{s.short}</Badge><p className="mt-1 text-[11.5px] text-stone-500">{resolutionText(d.native_resolution_m)} · {d.temporal_resolution}</p></td>
                <td className="py-3 pr-3 tabular text-ink-soft">{d.temporal_coverage.start?.slice(0, 4) ?? "—"}–{d.temporal_coverage.end?.slice(0, 4) ?? "now"}</td>
                <td className="py-3 pr-3"><Badge className={cn(v.bg, v.fg)}>{v.label}</Badge><p className="mt-1 text-[11px] text-stone-500">{formatDate(d.last_verified, "long")}</p></td>
                <td className="py-3 text-[12px] font-semibold text-stone-500">{d.integration_status === "planned" ? "Planned" : "Integrated"} <span className="font-normal">· {DATASET_SHORT[d.dataset_id]}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
