"use client";
import { useState } from "react";
import { ChevronDown, AlertTriangle, CheckCircle2, HelpCircle, XCircle, ShieldAlert, BookOpen, Trophy, Award, Info } from "lucide-react";
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

export const CROP_AGRONOMIC_DESCRIPTIONS: Record<string, string> = {
  CRP001: "Corn (Zea mays L.) is a warm-season annual C4 cereal grain requiring 1,167–1,556 GDD (Tbase 10°C, Tcap 30°C) and 500–800 mm water. Highly productive on fertile, well-drained loams with pH 6.0–6.8. Serves as a primary cash grain in rotation with soybeans or small grains; heavy user of nitrogen and soil moisture, with high vulnerability to mid-season heat and drought stress during silking.",
  CRP002: "Soybean (Glycine max (L.) Merr.) is a warm-season annual legume requiring 1,000–1,450 GDD (Tbase 10°C) and 450–700 mm water. Fixes atmospheric nitrogen via Bradyrhizobium symbiosis (70–140 kg N/ha) on soils with pH 6.0–6.8. Critical cash oilseed and rotational break crop following corn or winter wheat, breaking cereal pathogen cycles; sensitive to iron-deficiency chlorosis in high-pH calcareous soils and waterlogging.",
  CRP003: "Winter Wheat (Triticum aestivum L.) is a cool-season annual cereal requiring vernalization (4–8 weeks at 0–7°C), 1,800–2,400 GDD (Tbase 0°C), and 350–550 mm water. Excellent winter ground cover and erosion barrier on soils with pH 6.0–7.0. Foundational high-plains cash cereal and dual-purpose graze-grain crop; breaks summer weed cycles, possessing moderate drought and cold tolerance with vulnerability to wet foot and fungal root rots.",
  CRP004: "Spring Wheat (Triticum aestivum L.) is a cool-season non-vernalizing annual cereal requiring 1,150–1,400 GDD (Tbase 0°C) and 250–500 mm water on well-drained soils with pH 6.0–7.0. Fast-maturing spring cash grain and flexible replant option following winter-kill; lower total moisture demand than summer grains, but highly sensitive to high ambient temperatures (>32°C) during flowering and grain fill.",
  CRP005: "Grain Sorghum (Sorghum bicolor (L.) Moench) is a warm-season C4 grain requiring 944–1,333 GDD (Tbase 10°C) and 350–500 mm water, thriving on diverse soils with pH 5.5–7.8. Exemplary dryland cash crop with exceptional drought and heat tolerance through osmotic adjustment and waxy leaf epicuticle; ideal low-moisture break crop following wheat, but sensitive to cold soils (<15°C) at planting and early autumn frost.",
  CRP006: "Cotton (Gossypium hirsutum L.) is a warm-season perennial grown as an annual fiber crop requiring 1,167–1,444 GDD (Tbase 15.6°C, Tcap 32°C) and 500–750 mm water. Requires deep, well-drained loam to sandy loam with pH 6.0–7.0 and >180 frost-free days. Deep taproot aids subsoil moisture capture and breaks grass disease cycles; highly sensitive to chilling injury, seedling damping-off, and waterlogged anaerobic root zones.",
  CRP007: "Rice (Oryza sativa L.) is a semi-aquatic warm-season annual cereal requiring 1,167–1,556 GDD (Tbase 10°C) and 900–1,200 mm seasonal water. Specifically adapted to poorly drained lowlands and claypan soils with pH 5.5–6.8 under continuous flooding or furrow irrigation. Unique wetland cash crop breaking terrestrial disease cycles; agronomically unsuitable on well-drained, permeable upland fields without impoundment infrastructure.",
  CRP008: "Barley (Hordeum vulgare L.) is a cool-season annual small grain requiring 1,100–1,600 GDD (Tbase 0°C) and 300–450 mm water on well-drained loams with pH 6.0–7.5. Short growing cycle allows early harvest and double-cropping; exhibits the highest salinity and drought tolerance among small grains, but poor tolerance to waterlogged soils, acidic conditions (pH < 5.8), and high humidity during heading.",
  CRP009: "Cereal Rye (Secale cereale L.) is an exceptionally cold-hardy cool-season annual grass germinating near 1°C, requiring 900–1,400 GDD and 300–450 mm water. Thrives across marginal, acidic (pH 4.5–7.5), sandy soils. Premier cover crop and late-season forage; provides massive biomass, allelopathic weed suppression, and aggressive nitrate scavenging before summer legumes, but termination must be managed to preserve corn soil moisture.",
  CRP010: "Oats (Avena sativa L.) is a cool-season annual cereal requiring 1,300–1,700 GDD (Tbase 4.4°C) and 350–500 mm water on soils with pH 6.0–7.0. Non-winterhardy cover and companion nurse crop that reliably winter-kills in colder latitudes; rapid autumn biomass establishment and effective surface nutrient scavenging, though sensitive to hot, dry weather during grain fill.",
  CRP011: "Alfalfa (Medicago sativa L.) is a perennial deep-rooted legume forage requiring 2,200–3,500 GDD across multiple cuts and 600–1,000 mm water on deep, well-drained soils with pH 6.5–7.5. Exceptional biological nitrogen fixation (150–250 kg N/ha/yr) and subsoil biopores via 2–4 m taproots; medicarpin autotoxicity prevents immediate re-seeding into existing stands (mandating a 1–2 year rotational break).",
  CRP012: "Hairy Vetch (Vicia villosa Roth) is a winter-hardy annual legume cover crop requiring 1,100–1,600 GDD and 350–600 mm water on moderately fertile soils with pH 5.5–7.5. Fixes substantial atmospheric nitrogen (90–180 kg N/ha) released quickly to subsequent corn or sorghum crops; outstanding winter-survival among annual legumes, but vining habit requires proper spring termination to prevent hard-seed volunteer contamination.",
  CRP013: "Crimson Clover (Trifolium incarnatum L.) is a cool-season annual legume cover crop requiring 1,000–1,500 GDD and 500–800 mm water on well-drained sandy loams and loams with pH 6.0–7.0. Rapid spring biomass development, moderate nitrogen fixation (70–140 kg N/ha), and prolific early pollinator forage; easily terminated mechanically or chemically before summer planting, but vulnerable to severe freeze without snow cover.",
  CRP014: "Oilseed Radish (Raphanus sativus L. var. oleiferus) is a specialty brassica cover crop requiring 600–1,000 GDD and 300–500 mm water on medium soils with pH 6.0–7.5. Aggressive tuberous taproot performs biological subsoiling to alleviate plow pan compaction and scavenges up to 150–220 kg N/ha of residual profile nitrate; reliably winter-kills at temperatures below -6°C to -9°C, facilitating spring no-till seeding without herbicide burndown.",
};

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

  // Task 8: Separate eligible crops and unsuitable / disqualified crops
  const eligibleCrops = data.crops.filter((c) => c.suitability_class !== "unsuitable");
  const unsuitableCrops = data.crops.filter((c) => c.suitability_class === "unsuitable");

  // Deterministic sorting for eligible crops:
  // 1. Suitability score DESC
  // 2. High confidence / valid data DESC
  // 3. Limiting factors count ASC (fewer is better)
  // 4. Alphabetical by crop_name ASC
  const sortedEligible = [...eligibleCrops].sort((a, b) => {
    const diff = (b.suitability_score ?? 0) - (a.suitability_score ?? 0);
    if (Math.abs(diff) > 1e-4) return diff;
    const aValid = a.data_quality?.status === "valid" ? 1 : 0;
    const bValid = b.data_quality?.status === "valid" ? 1 : 0;
    if (aValid !== bValid) return bValid - aValid;
    const limDiff = a.limiting_factors.length - b.limiting_factors.length;
    if (limDiff !== 0) return limDiff;
    return a.crop_name.localeCompare(b.crop_name);
  });

  const rankMap = new Map<string, number>();
  sortedEligible.forEach((c, idx) => {
    rankMap.set(c.crop_id, idx + 1);
  });

  const filterFn = (c: CropSuitabilityAssessment) => {
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
  };

  const displayedEligible = sortedEligible.filter(filterFn);
  const displayedUnsuitable = unsuitableCrops.filter(filterFn);

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

      {/* Ranking & Tie-Breaking Methodology Notice (Task 8) */}
      <div className="flex items-start gap-2.5 rounded-lg border border-line/80 bg-parchment/40 p-3 text-[12px] leading-relaxed text-ink-soft">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-forest-700" />
        <div>
          <span className="font-semibold text-ink">Deterministic Crop Ranking: </span>
          Eligible crops are ranked by Phase 6 biophysical suitability score (100–0).
          Ties are broken deterministically by: (1) higher data confidence, (2) fewer limiting factors, and (3) alphabetical by crop name.
          Unsuitable crops violating physiological thresholds are disqualified from ranking.
        </div>
      </div>

      {/* Eligible Ranked Crop Cards */}
      {displayedEligible.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-[13px] font-semibold uppercase tracking-wider text-forest-800">
              Ranked Eligible Crops ({displayedEligible.length})
            </h4>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {displayedEligible.map((crop) => (
              <CropCard key={crop.crop_id} crop={crop} rank={rankMap.get(crop.crop_id) ?? null} />
            ))}
          </div>
        </div>
      )}

      {/* Disqualified / Unsuitable Crops Section (Task 8 Req 4) */}
      {displayedUnsuitable.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-line/80">
          <div className="flex items-center gap-2 text-rose-800">
            <ShieldAlert className="h-4 w-4" />
            <h4 className="text-[13px] font-semibold uppercase tracking-wider">
              Disqualified / Unsuitable Crops ({displayedUnsuitable.length})
            </h4>
          </div>
          <p className="text-[12px] text-stone-500">
            These crops violate non-negotiable physiological tolerance limits or soil/drainage requirements for this parcel (Liebig&apos;s Law of the Minimum) and are disqualified from ranking.
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            {displayedUnsuitable.map((crop) => (
              <CropCard key={crop.crop_id} crop={crop} rank={null} />
            ))}
          </div>
        </div>
      )}

      {displayedEligible.length === 0 && displayedUnsuitable.length === 0 && (
        <div className="py-8 text-center text-[13px] text-ink-soft">
          No crops matched the selected filters.
        </div>
      )}
    </div>
  );
}

function CropCard({ crop, rank }: { crop: CropSuitabilityAssessment; rank?: number | null }) {
  const [expanded, setExpanded] = useState(false);
  const badgeStyle = CLASS_BADGE[crop.suitability_class];
  const agronomicDesc = CROP_AGRONOMIC_DESCRIPTIONS[crop.crop_id];

  // Distinct visual rank styling (Task 8)
  const isRank1 = rank === 1;
  const isRank2 = rank === 2;
  const isRank3 = rank === 3;

  return (
    <Card
      className={cn(
        "overflow-hidden border transition-shadow hover:shadow-md",
        isRank1 && "border-amber-300 ring-2 ring-amber-300/60 bg-gradient-to-b from-amber-50/20 to-transparent",
        isRank2 && "border-slate-300 ring-1 ring-slate-300/80 bg-gradient-to-b from-slate-50/20 to-transparent",
        isRank3 && "border-orange-300 ring-1 ring-orange-300/80 bg-gradient-to-b from-orange-50/20 to-transparent",
        !rank && crop.suitability_class === "unsuitable" && "border-rose-200 bg-rose-50/10"
      )}
    >
      <div className="p-5 space-y-3.5">
        {/* Top header row with Rank Badge */}
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              {/* Visual Rank Indicator */}
              {rank !== null && rank !== undefined ? (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold tracking-tight shadow-xs",
                    isRank1 && "bg-amber-100 text-amber-950 border border-amber-300 ring-1 ring-amber-400",
                    isRank2 && "bg-slate-200 text-slate-900 border border-slate-300",
                    isRank3 && "bg-orange-100 text-orange-950 border border-orange-300",
                    rank > 3 && "bg-stone-100 text-stone-700 border border-stone-200 font-mono"
                  )}
                >
                  {isRank1 && <Trophy className="h-3 w-3 text-amber-600" />}
                  {isRank2 && <Award className="h-3 w-3 text-slate-600" />}
                  {isRank3 && <Award className="h-3 w-3 text-orange-600" />}
                  Rank #{rank}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-md bg-rose-100 border border-rose-300 px-2 py-0.5 text-[10.5px] font-semibold text-rose-800">
                  <XCircle className="h-3 w-3" /> Disqualified
                </span>
              )}

              <h3 className="font-display text-[19px] font-semibold text-ink">{crop.crop_name}</h3>
              <span className="font-mono text-[11px] text-stone-500">[{crop.crop_id}]</span>
              {crop.cdl_code && (
                <span className="rounded bg-parchment px-1.5 py-0.5 font-mono text-[10px] text-ink-soft">
                  CDL {crop.cdl_code}
                </span>
              )}
            </div>
            {crop.botanical_family && (
              <p className="mt-0.5 text-[12px] italic text-stone-500">{crop.botanical_family}</p>
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

        {/* Distinctive Agronomic Profile (Task 7) */}
        {agronomicDesc && (
          <div className="rounded-lg border border-line/70 bg-parchment/30 p-2.5 text-[12px] leading-relaxed text-ink-soft">
            <span className="font-semibold text-ink">Agronomic Profile: </span>
            {agronomicDesc}
          </div>
        )}

        {/* Narrative explanation */}
        <p className="text-[12.5px] leading-relaxed text-ink-soft whitespace-pre-line">{crop.explanation}</p>

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
