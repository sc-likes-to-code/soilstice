"use client";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowLeft, FileText, LayoutGrid, Leaf, RefreshCw, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";
import { useField, useFields, useCoverage } from "@/hooks/queries";
import { usePrefs } from "@/hooks/preferences";
import { qText } from "@/lib/format";
import { Badge, Select, Skeleton } from "@/components/ui/primitives";
import { ErrorState } from "@/components/shared/state";
import { CompletenessMeter } from "@/components/shared/data-display";
import { SyntheticBadge } from "@/components/shared/provenance";
import type { Field } from "@/types/contracts";

export function useFieldId(): string {
  const p = useParams<{ fieldId: string }>();
  return p.fieldId;
}

const TABS = [
  { seg: "", label: "Overview", icon: LayoutGrid },
  { seg: "environment", label: "Environment", icon: Leaf },
  { seg: "resilience", label: "Resilience", icon: ShieldCheck },
  { seg: "rotation", label: "Rotation Lab", icon: RefreshCw },
  { seg: "report", label: "Report", icon: FileText },
];

const STATUS_STYLE: Record<Field["processing_status"], string> = {
  ready: "bg-forest-100 text-forest-800",
  partial: "bg-wheat-100 text-wheat-600",
  processing: "bg-sky-100 text-sky-600",
  failed: "bg-clay-100 text-clay-600",
};

export function FieldLayoutClient({ children }: { children: ReactNode }) {
  const fieldId = useFieldId();
  const pathname = usePathname();
  const router = useRouter();
  const { units } = usePrefs();
  const field = useField(fieldId);
  const siblings = useFields(field.data?.data.farm_id ?? null);
  const cov = useCoverage(fieldId);
  const base = `/fields/${fieldId}`;
  const current = pathname.replace(base, "").replace(/^\//, "").split("/")[0] ?? "";

  if (field.isError) {
    return (
      <div className="mx-auto max-w-xl py-16">
        <ErrorState error={field.error} onRetry={() => void field.refetch()} title="Field not available" />
        <Link href="/fields" className="mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold text-forest-700"><ArrowLeft className="h-4 w-4" /> Back to Field Explorer</Link>
      </div>
    );
  }
  const f = field.data?.data;

  return (
    <div>
      <div className="no-print mb-5 animate-[var(--animate-fade-up)]">
        <Link href="/fields" className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-stone-500 hover:text-forest-700">
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Field Explorer
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            {f ? (
              <>
                <h1 className="font-display text-[30px] font-normal leading-tight text-ink md:text-[36px]">{f.name}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[12.5px] text-ink-soft">
                  <span className="font-semibold tabular text-ink">{qText(f.area, units)}</span>
                  <span className="text-line-strong">/</span>
                  <span>County FIPS {f.state_fips}{f.county_fips}</span>
                  <span className="text-line-strong">/</span>
                  <span className="font-mono text-[11.5px] tabular">{f.centroid[1].toFixed(4)}°N, {Math.abs(f.centroid[0]).toFixed(4)}°W</span>
                  <Badge className={STATUS_STYLE[f.processing_status]}>{f.processing_status}</Badge>
                  <Badge className="border border-line bg-paper text-ink-soft">{f.source === "user" ? "User-drawn" : f.source === "csb" ? "CSB polygon" : "Synthetic geometry"}</Badge>
                  {f.source !== "csb" && <SyntheticBadge />}
                </div>
              </>
            ) : (
              <>
                <Skeleton className="h-9 w-64" />
                <Skeleton className="mt-3 h-4 w-96 max-w-full" />
              </>
            )}
          </div>
          <div className="flex items-center gap-4">
            {cov.data && (
              <div>
                <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-stone-500">P0 data coverage</p>
                <CompletenessMeter value={cov.data.data.completeness} />
              </div>
            )}
            {siblings.data && f && (
              <Select
                label="Switch field"
                value={f.field_id}
                onChange={(id) => router.push(`/fields/${id}${current ? `/${current}` : ""}`)}
                options={siblings.data.data.map((s) => ({ value: s.field_id, label: s.name }))}
              />
            )}
          </div>
        </div>
        <nav aria-label="Field sections" className="mt-5 flex gap-1 overflow-x-auto overflow-y-hidden border-b border-line [scrollbar-width:none]">
          {TABS.map(({ seg, label, icon: Icon }) => {
            const on = current === seg;
            return (
              <Link
                key={seg || "overview"}
                href={seg ? `${base}/${seg}` : base}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3.5 py-2.5 text-[13px] font-semibold transition-colors",
                  on ? "border-forest-700 text-forest-800" : "border-transparent text-stone-500 hover:text-ink",
                )}
              >
                <Icon className="h-4 w-4" aria-hidden /> {label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div key={fieldId} className="animate-[var(--animate-fade-up)]">{children}</div>
    </div>
  );
}

export function FieldLayoutSkeleton() {
  return (
    <div>
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-4 h-10 w-72" />
      <Skeleton className="mt-3 h-4 w-96 max-w-full" />
      <Skeleton className="mt-6 h-10 w-full" />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}
