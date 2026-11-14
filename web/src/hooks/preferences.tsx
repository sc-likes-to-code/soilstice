"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { UnitSystem } from "@/lib/format";
import type { UUID } from "@/types/contracts";

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
  const [units, setUnitsState] = useState<UnitSystem>("metric");
  const [activeFarmId, setFarm] = useState<UUID | null>(null);

  useEffect(() => {
    const u = read("soilstice.units");
    const f = read("soilstice.farm");
    // Hydrate per-viewer preferences after mount (localStorage is browser-only).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (u === "us" || u === "metric") setUnitsState(u);
    if (f) setFarm(f);
  }, []);

  const setUnits = useCallback((u: UnitSystem) => {
    setUnitsState(u);
    write("soilstice.units", u);
  }, []);
  const setActiveFarmId = useCallback((id: UUID) => {
    setFarm(id);
    write("soilstice.farm", id);
  }, []);

  const value = useMemo(() => ({ units, setUnits, activeFarmId, setActiveFarmId }), [units, setUnits, activeFarmId, setActiveFarmId]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePrefs(): Prefs {
  const v = useContext(Ctx);
  if (!v) throw new Error("usePrefs must be used inside PreferencesProvider");
  return v;
}
