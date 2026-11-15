"use client";
import { useState } from "react";
import { ChevronDown, AlertTriangle, CheckCircle2, HelpCircle, XCircle, ShieldAlert, BookOpen } from "lucide-react";
import type {
  CropSuitabilityAssessment,
  FieldSuitabilityResponse,
  SuitabilityClass,
  FactorCompatibility,
  SuitabilityFactorAssessment,
} from "@/types/contracts";
import { useFieldSuitability } from "@/hooks/queries";
import { Button, Card, CardBody, CardHeader, Skeleton } from "@/components/ui/primitives";
import { StateBoundary } from "@/components/shared/state";
import { cn } from "@/lib/cn";

const CLASS_BADGE: Record<SuitabilityClass, { label: string; bg: string; text: string; border: string }> = {
  suitable: { label: "Suitable", bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-300" },
  conditionally_suitable: { label: "Conditionally Suitable", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-300" },
  limited_suitability: { label: "Limited Suitability", bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-300" },
  unsuitable: { label: "Unsuitable", bg: "bg-rose-50", text: "text-rose-800", border: "border-rose-300" },
  insufficient_data: { label: "Insufficient Data", bg: "bg-stone-50", text: "text-stone-700", border: "border-stone-300" },
};

const COMPAT_BADGE: Record<FactorCompatibility, { label: string; badgeClass: string }> = {
  optimal: { label: "Optimal", badgeClass: "bg-emerald-100 text-emerald-800" },
  compatible: { label: "Compatible", badgeClass: "bg-teal-100 text-teal-800" },
  moderate_limitation: { label: "Moderate Limitation", badgeClass: "bg-orange-100 text-orange-800" },
  critical_limitation: { label: "Critical Limitation", badgeClass: "bg-rose-100 text-rose-800 font-bold" },
  unknown: { label: "Unknown (No Data)", badgeClass: "bg-stone-100 text-stone-600" },
};

interface SuitabilitySectionProps {
  fieldId: string;
  seasonYear?: number;
}

export function CropSuitabilitySection({ fieldId, seasonYear }: SuitabilitySectionProps) {
  const query = useFieldSuitability(fieldId, seasonYear);
  const [filterClass, setFilterClass] = useState<SuitabilityClass | "all">("all");
  const [search, setSearch] = useState("");

  return (
    <Card className="border-forest-200">
      <CardHeader
        eyebrow="Phase 6 · Crop Suitability Engine"
        title="Crop Suitability Evaluation"
        description="Factor-by-factor compatibility analysis across 14 canonical crops based on field-level environmental indicators and USDA/FAO crop requirements."
      />
      <CardBody>
        <StateBoundary
          query={query}
          skeleton={
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <div className="grid gap-4 md:grid-cols-2">
                <Skeleton className="h-64" />
                <Skeleton className="h-64" />
              </div>
            </div>
          }
        >
          {(data: FieldSuitabilityResponse) => (
            <SuitabilityContent
              data={data}
              filterClass={filterClass}
              setFilterClass={setFilterClass}
              search={search}
              setSearch={setSearch}
            />
          )}
        </StateBoundary>
      </CardBody>
    </Card>
  );
}

function SuitabilityContent({
  data,
  filterClass,
  setFilterClass,
  search,
  setSearch,
}: {
  data: FieldSuitabilityResponse;
  filterClass: SuitabilityClass | "all";
  setFilterClass: (c: SuitabilityClass | "all") => void;
  search: string;
  setSearch: (s: string) => void;
}) {
  const counts = data.summary;
  const filteredCrops = data.crops.filter((c) => {
    if (filterClass !== "all" && c.suitability_class !== filterClass) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        c.crop_name.toLowerCase().includes(q) ||
        c.crop_id.toLowerCase().includes(q) ||
        (c.botanical_family && c.botanical_family.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Summary Counts Bar */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 text-center">
        <button
          onClick={() => setFilterClass(filterClass === "suitable" ? "all" : "suitable")}
          className={cn(
            "rounded-lg border p-3 text-left transition-all",
            filterClass === "suitable" ? "border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500" : "border-line bg-paper hover:bg-parchment/40"
          )}
        >
          <div className="flex items-center justify-between text-emerald-700">
            <span className="text-[12px] font-semibold">Suitable</span>
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="mt-1 text-2xl font-bold text-ink">{counts.suitable}</div>
        </button>

        <button
          onClick={() => setFilterClass(filterClass === "conditionally_suitable" ? "all" : "conditionally_suitable")}
          className={cn(
            "rounded-lg border p-3 text-left transition-all",
            filterClass === "conditionally_suitable" ? "border-amber-500 bg-amber-50 ring-1 ring-amber-500" : "border-line bg-paper hover:bg-parchment/40"
          )}
        >
          <div className="flex items-center justify-between text-amber-700">
            <span className="text-[12px] font-semibold">Conditional</span>
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="mt-1 text-2xl font-bold text-ink">{counts.conditionally_suitable}</div>
        </button>

        <button
          onClick={() => setFilterClass(filterClass === "limited_suitability" ? "all" : "limited_suitability")}
          className={cn(
            "rounded-lg border p-3 text-left transition-all",
            filterClass === "limited_suitability" ? "border-orange-500 bg-orange-50 ring-1 ring-orange-500" : "border-line bg-paper hover:bg-parchment/40"
          )}
        >
          <div className="flex items-center justify-between text-orange-700">
            <span className="text-[12px] font-semibold">Limited</span>
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="mt-1 text-2xl font-bold text-ink">{counts.limited_suitability}</div>
        </button>

        <button
          onClick={() => setFilterClass(filterClass === "unsuitable" ? "all" : "unsuitable")}
          className={cn(
            "rounded-lg border p-3 text-left transition-all",
            filterClass === "unsuitable" ? "border-rose-500 bg-rose-50 ring-1 ring-rose-500" : "border-line bg-paper hover:bg-parchment/40"
          )}
        >
          <div className="flex items-center justify-between text-rose-700">
            <span className="text-[12px] font-semibold">Unsuitable</span>
            <XCircle className="h-4 w-4" />
          </div>
          <div className="mt-1 text-2xl font-bold text-ink">{counts.unsuitable}</div>
        </button>

        <button
          onClick={() => setFilterClass(filterClass === "insufficient_data" ? "all" : "insufficient_data")}
          className={cn(
            "rounded-lg border p-3 text-left transition-all",
            filterClass === "insufficient_data" ? "border-stone-500 bg-stone-100 ring-1 ring-stone-500" : "border-line bg-paper hover:bg-parchment/40"
          )}
        >
          <div className="flex items-center justify-between text-stone-600">
            <span className="text-[12px] font-semibold">No Data</span>
            <HelpCircle className="h-4 w-4" />
          </div>
          <div className="mt-1 text-2xl font-bold text-ink">{counts.insufficient_data}</div>
        </button>
      </div>

      {/* Filter & Search Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={filterClass === "all" ? "primary" : "secondary"}
            onClick={() => setFilterClass("all")}
          >
            All Crops ({data.crops.length})
          </Button>
          <input
            type="text"
            placeholder="Search crop or family..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 rounded-lg border border-line px-3 text-[12.5px] focus:outline-none focus:ring-1 focus:ring-forest-500"
          />
        </div>
        <div className="flex items-center gap-2 text-[11.5px] text-stone-500">
          <span>Engine v{data.engine_version}</span>
          <span>·</span>
          <span>KB v{data.kb_version}</span>
          <span>·</span>
          <span>Status: {data.status}</span>
        </div>
      </div>

      {/* Crop Cards */}
      <div className="grid gap-4 lg:grid-cols-2">
        {filteredCrops.map((crop) => (
          <CropCard key={crop.crop_id} crop={crop} />
        ))}
      </div>

      {filteredCrops.length === 0 && (
        <div className="py-8 text-center text-[13px] text-ink-soft">
          No crops matched the selected filters.
        </div>
      )}
    </div>
  );
}

function CropCard({ crop }: { crop: CropSuitabilityAssessment }) {
  const [expanded, setExpanded] = useState(false);
  const badgeStyle = CLASS_BADGE[crop.suitability_class];

  return (
    <Card className="overflow-hidden border border-line transition-shadow hover:shadow-md">
      <div className="p-5 space-y-3">
        {/* Top header row */}
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-[19px] font-semibold text-ink">{crop.crop_name}</h3>
              <span className="font-mono text-[11px] text-stone-500">[{crop.crop_id}]</span>
              {crop.cdl_code && (
                <span className="rounded bg-parchment px-1.5 py-0.5 font-mono text-[10px] text-ink-soft">
                  CDL {crop.cdl_code}
                </span>
              )}
            </div>
            {crop.botanical_family && (
              <p className="text-[12px] italic text-stone-500">{crop.botanical_family}</p>
            )}
          </div>

          <div className="flex flex-col items-end gap-1.5">
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11.5px] font-semibold tracking-wide",
                badgeStyle.bg,
                badgeStyle.text,
                badgeStyle.border
              )}
            >
              {badgeStyle.label}
            </span>

            {crop.suitability_score !== null ? (
              <span
                className="font-mono text-[13px] font-bold text-forest-800"
                title={crop.score_methodology ?? undefined}
              >
                Score: {crop.suitability_score}/100
                {crop.suitability_class === "unsuitable" && (
                  <span className="ml-1 text-[10.5px] font-sans font-normal text-rose-600">
                    (Disqualified Index)
                  </span>
                )}
                {crop.assessment_status === "provisional" && crop.suitability_class !== "unsuitable" && (
                  <span className="ml-1 text-[10.5px] font-sans font-normal text-amber-600">
                    (Provisional)
                  </span>
                )}
              </span>
            ) : (
              <span className="text-[11px] font-medium text-stone-500 italic" title={crop.score_methodology ?? undefined}>
                Score Withheld (Liebig Cap / Missing Data)
              </span>
            )}
          </div>
        </div>

        {/* Narrative explanation */}
        <p className="text-[12.5px] leading-relaxed text-ink-soft">{crop.explanation}</p>

        {/* Limiting Factors Badges */}
        {crop.limiting_factors.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-rose-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Limiting Factors ({crop.limiting_factors.length}):</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {crop.limiting_factors.map((lf, idx) => (
                <span
                  key={idx}
                  className="rounded bg-rose-50 border border-rose-200 px-2 py-0.5 text-[11.5px] text-rose-800"
                >
                  {lf}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Favorable Factors Badges */}
        {crop.favorable_factors.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Favorable Factors ({crop.favorable_factors.length}):</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {crop.favorable_factors.slice(0, 3).map((ff, idx) => (
                <span
                  key={idx}
                  className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11.5px] text-emerald-800"
                >
                  {ff}
                </span>
              ))}
              {crop.favorable_factors.length > 3 && (
                <span className="text-[11px] text-emerald-600 self-center">
                  +{crop.favorable_factors.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Evidence & Details Toggle */}
        <div className="pt-2 flex items-center justify-between border-t border-line text-[12px]">
          <div className="flex items-center gap-1.5 text-stone-500">
            <BookOpen className="h-3.5 w-3.5" />
            <span>{crop.evidence_ids.length} Evidence Records</span>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 font-semibold text-forest-700 hover:text-forest-800"
          >
            <span>{expanded ? "Hide Details" : "Inspect All Factors"}</span>
            <ChevronDown className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")} />
          </button>
        </div>
      </div>

      {/* Expanded Factor Table & Scientific Limitations */}
      {expanded && (
        <div className="border-t border-line bg-cream/40 p-4 space-y-4">
          <div className="overflow-x-auto rounded border border-line bg-paper">
            <table className="w-full min-w-[580px] text-left text-[12px]">
              <thead className="bg-cream/70 text-[10.5px] uppercase tracking-wider text-stone-600">
                <tr>
                  <th className="px-3 py-2 font-semibold">Factor</th>
                  <th className="px-3 py-2 font-semibold">Support</th>
                  <th className="px-3 py-2 font-semibold">Status</th>
                  <th className="px-3 py-2 font-semibold">Observed</th>
                  <th className="px-3 py-2 font-semibold">Requirement</th>
                  <th className="px-3 py-2 font-semibold">Interpretation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {crop.factor_assessments.map((fa: SuitabilityFactorAssessment) => (
                  <tr key={fa.factor_key} className="hover:bg-cream/20">
                    <td className="px-3 py-2">
                      <div className="font-medium text-ink">{fa.factor_name}</div>
                      <div className="text-[10px] text-stone-400 capitalize">{fa.category}</div>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "inline-block rounded px-1.5 py-0.5 text-[10px] font-mono font-medium",
                          fa.support_class === "F"
                            ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                            : "bg-sky-50 text-sky-800 border border-sky-200"
                        )}
                        title={fa.support_class === "F" ? "Field-scale support (SSURGO/CDL/SRTM)" : "Regional reanalysis grid (NASA POWER/ERA5)"}
                      >
                        {fa.support_class === "F" ? "Field" : "Regional"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "inline-block rounded px-2 py-0.5 text-[10.5px] font-semibold",
                          COMPAT_BADGE[fa.compatibility]?.badgeClass ?? "bg-stone-100 text-stone-600"
                        )}
                      >
                        {COMPAT_BADGE[fa.compatibility]?.label ?? fa.compatibility}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-[11.5px] text-ink">
                      {fa.observed_value.value !== null ? `${fa.observed_value.value} ${fa.observed_value.unit !== "unitless" ? fa.observed_value.unit : ""}` : "—"}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-ink-soft max-w-xs truncate" title={fa.crop_requirement ?? undefined}>
                      {fa.crop_requirement ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-stone-600 max-w-xs truncate" title={fa.interpretation}>
                      {fa.interpretation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Scientific Limitations List */}
          {crop.limitations.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-1">
              <div className="flex items-center gap-1.5 text-[11.5px] font-semibold text-amber-800">
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Scientific Constraints & Methodological Notes:</span>
              </div>
              <ul className="list-disc pl-5 text-[11.5px] leading-relaxed text-amber-900 space-y-0.5">
                {crop.limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence Registry Tag List */}
          {crop.evidence_ids.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 text-[11px] text-stone-500">
              <span className="font-semibold text-stone-600">KB Citations:</span>
              {crop.evidence_ids.map((evId) => (
                <span key={evId} className="rounded bg-cream border border-line px-1.5 py-0.5 font-mono text-[10px]">
                  {evId}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
