"use client";

import { useRouter } from "next/navigation";
import { Database, FlaskConical } from "lucide-react";
import { useDataMode } from "@/hooks/data-mode";
import { cn } from "@/lib/cn";

interface DataModeToggleProps {
  className?: string;
  showLabels?: boolean;
}

export function DataModeToggle({ className, showLabels = true }: DataModeToggleProps) {
  const { isApi, isMock, setMode } = useDataMode();
  const router = useRouter();

  const handleModeSwitch = (mode: "api" | "mock") => {
    setMode(mode);
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/fields/")) {
      router.push("/fields");
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label="Data source mode"
      className={cn(
        "inline-flex items-center rounded-lg border border-line bg-paper/95 p-0.5 shadow-xs transition-colors",
        className,
      )}
    >
      <button
        type="button"
        role="radio"
        aria-checked={isApi}
        tabIndex={isApi ? 0 : -1}
        onClick={() => handleModeSwitch("api")}
        title="Live API: Connect to FastAPI backend for verified USDA (SSURGO, CDL) and NASA (POWER, SRTM) observations"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest-600 cursor-pointer",
          isApi
            ? "bg-forest-800 text-paper shadow-xs"
            : "text-stone-500 hover:text-ink hover:bg-parchment/60",
        )}
      >
        <Database className={cn("h-3.5 w-3.5 shrink-0 transition-colors", isApi ? "text-emerald-400" : "text-stone-400")} />
        {showLabels && <span>Live API</span>}
        {isApi && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" aria-hidden />}
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={isMock}
        tabIndex={isMock ? 0 : -1}
        onClick={() => handleModeSwitch("mock")}
        title="Mock Data: Use synthetic demonstration world (Reno Demo Farm & Finney Demo Farm, 14 parcels)"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 cursor-pointer",
          isMock
            ? "bg-clay-600 text-white shadow-xs"
            : "text-stone-500 hover:text-ink hover:bg-parchment/60",
        )}
      >
        <FlaskConical className={cn("h-3.5 w-3.5 shrink-0 transition-colors", isMock ? "text-wheat-200" : "text-stone-400")} />
        {showLabels && <span>Mock Data</span>}
        {isMock && <span className="h-1.5 w-1.5 rounded-full bg-amber-300" aria-hidden />}
      </button>
    </div>
  );
}
