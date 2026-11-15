"use client";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { UnitSystem } from "@/lib/format";
import type { UUID } from "@/types/contracts";
import { useDataMode } from "./data-mode";

/** Per-viewer conveniences only (units, active farm). Never data that must persist (UI_ARCHITECTURE §4.8). */
interface Prefs {
  units: UnitSystem;
  setUnits: (u: UnitSystem) => void;
  activeFarmId: UUID | null;
  setActiveFarmId: (id: UUID) => void;
}

const Ctx = createContext<Prefs | null>(null);

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, v: string) {
  try {
    window.localStorage.setItem(key, v);
  } catch {
    /* storage unavailable — keep in memory */
  }
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { mode } = useDataMode();
  const [units, setUnitsState] = useState<UnitSystem>(() => {
    if (typeof window === "undefined") return "metric";
    const u = read("soilstice.units");
    return u === "us" || u === "metric" ? u : "metric";
  });

  const [farmByMode, setFarmByMode] = useState<Record<string, UUID | null>>(() => {
    if (typeof window === "undefined") return { api: null, mock: null };
    return {
      api: read("soilstice.farm.api") ?? read("soilstice.farm"),
      mock: read("soilstice.farm.mock") ?? read("soilstice.farm"),
    };
  });

  const activeFarmId = farmByMode[mode] ?? null;

  const setUnits = useCallback((u: UnitSystem) => {
    setUnitsState(u);
    write("soilstice.units", u);
  }, []);

  const setActiveFarmId = useCallback((id: UUID) => {
    setFarmByMode((prev) => ({ ...prev, [mode]: id }));
    write(`soilstice.farm.${mode}`, id);
    write("soilstice.farm", id);
  }, [mode]);

  const value = useMemo(() => ({ units, setUnits, activeFarmId, setActiveFarmId }), [units, setUnits, activeFarmId, setActiveFarmId]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePrefs(): Prefs {
  const v = useContext(Ctx);
  if (!v) throw new Error("usePrefs must be used inside PreferencesProvider");
  return v;
}
