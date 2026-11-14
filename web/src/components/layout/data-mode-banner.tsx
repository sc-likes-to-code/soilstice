"use client";
import { FlaskConical } from "lucide-react";
import { DATA_MODE } from "@/services";

/** Non-dismissable synthetic-data banner (UI_ARCHITECTURE §1, rule R6). */
export function DataModeBanner() {
  if (DATA_MODE !== "mock") return null;
  return (
    <div role="status" className="no-print relative z-40 flex items-center justify-center gap-2 bg-soil-600 px-4 py-1.5 text-center text-[12px] font-medium text-wheat-100">
      <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        <strong className="font-semibold">Synthetic demo data — not observations.</strong>{" "}
        <span className="text-wheat-200/90 max-sm:hidden">Values are generated for the Phase 1 interface; NASA/USDA ingestion arrives in Phase 3.</span>
      </span>
    </div>
  );
}
