"use client";
import { Database, FlaskConical } from "lucide-react";
import { DATA_MODE } from "@/services";

/**
 * State-aware environment banner (UI_ARCHITECTURE §1, rule R6).
 * In mock mode: informs the user that data is synthetic demonstration data.
 * In API mode: informs the user that live provider data is active (SSURGO, CDL, POWER).
 */
export function DataModeBanner() {
  if (DATA_MODE === "mock") {
    return (
      <div
        role="status"
        className="no-print relative z-40 flex items-center justify-center gap-2 border-b border-soil-700 bg-soil-800 px-4 py-1.5 text-center text-[12px] font-medium text-wheat-100 shadow-sm"
      >
        <FlaskConical className="h-3.5 w-3.5 shrink-0 text-wheat-300" aria-hidden />
        <span>
          <strong className="font-semibold text-wheat-200">Demonstration environment · Synthetic data, not field observations.</strong>{" "}
          <span className="text-wheat-200/80 max-sm:hidden">
            Switch to Live API mode in settings for verified USDA &amp; NASA observations.
          </span>
        </span>
      </div>
    );
  }

  return (
    <div
      role="status"
      className="no-print relative z-40 flex items-center justify-center gap-2 border-b border-forest-900/60 bg-forest-950/90 px-4 py-1 text-center text-[11.5px] font-medium text-forest-100 backdrop-blur"
    >
      <Database className="h-3 w-3 shrink-0 text-emerald-400" aria-hidden />
      <span>
        <strong className="font-semibold text-emerald-300">Live data environment</strong>
        <span className="text-forest-200/90"> · Dataset availability varies by field (USDA SSURGO, USDA CDL, NASA POWER operational)</span>
      </span>
    </div>
  );
}
