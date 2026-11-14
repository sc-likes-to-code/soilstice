"use client";
import type { UseQueryResult } from "@tanstack/react-query";
import { AlertTriangle, CircleDashed, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import type { ApiResponse } from "@/types/contracts";
import { isApiError } from "@/services";
import { cn } from "@/lib/cn";
import { Button, Skeleton } from "@/components/ui/primitives";

/** Uniform loading / error / empty handling for a single query (UI_ARCHITECTURE §3.4). */
export function StateBoundary<T>({
  query, children, skeleton, empty, isEmpty, compact,
}: {
  query: UseQueryResult<ApiResponse<T>>;
  children: (data: T, meta: ApiResponse<T>["meta"]) => ReactNode;
  skeleton?: ReactNode;
  empty?: ReactNode;
  isEmpty?: (data: T) => boolean;
  compact?: boolean;
}) {
  if (query.isPending) return <>{skeleton ?? <DefaultSkeleton />}</>;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} compact={compact} />;
  const d = query.data.data;
  if (isEmpty && isEmpty(d)) return <>{empty ?? <EmptyState title="Nothing to show yet" />}</>;
  return <>{children(d, query.data.meta)}</>;
}

export function DefaultSkeleton({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={cn("h-4", i === 0 ? "w-2/5" : i % 2 ? "w-full" : "w-4/5")} />
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry, compact, title }: { error: unknown; onRetry?: () => void; compact?: boolean; title?: string }) {
  const api = isApiError(error) ? error : null;
  const retryable = api ? api.retryable : true;
  return (
    <div role="alert" className={cn("flex items-start gap-3 rounded-xl border border-clay-100 bg-clay-100/40 text-[13px]", compact ? "p-3" : "p-4")}>
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-clay-600" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-clay-600">{title ?? (api?.code === "NOT_FOUND" ? "Not found" : "Couldn’t load this")}</p>
        <p className="mt-0.5 text-ink-soft">{api?.message ?? (error instanceof Error ? error.message : "Unexpected error.")}</p>
        {api && <p className="mt-1 font-mono text-[11px] text-stone-500">{api.code} · request {api.requestId}</p>}
      </div>
      {onRetry && retryable && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden /> Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, description, icon, action, className }: { title: ReactNode; description?: ReactNode; icon?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-xl border border-dashed border-line-strong bg-cream/40 px-6 py-8 text-center", className)}>
      <div className="mb-3 text-stone-400">{icon ?? <CircleDashed className="h-6 w-6" aria-hidden />}</div>
      <p className="font-display text-[16px] text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-ink-soft">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
