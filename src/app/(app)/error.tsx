"use client";
import { AlertTriangle, RefreshCw } from "lucide-react";

/** Route-level error boundary: an unexpected render error never blanks the app. */
export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl py-16">
      <div role="alert" className="rounded-2xl border border-clay-100 bg-clay-100/40 p-6">
        <p className="flex items-center gap-2 font-display text-[20px] text-clay-600"><AlertTriangle className="h-5 w-5" /> Something went wrong on this page</p>
        <p className="mt-2 text-[13.5px] text-ink-soft">{error.message || "An unexpected error occurred."}</p>
        {error.digest && <p className="mt-1 font-mono text-[11px] text-stone-500">digest {error.digest}</p>}
        <button onClick={reset} className="mt-4 inline-flex h-9 items-center gap-1.5 rounded-lg bg-forest-800 px-3.5 text-[13px] font-semibold text-paper"><RefreshCw className="h-4 w-4" /> Try again</button>
      </div>
    </div>
  );
}
