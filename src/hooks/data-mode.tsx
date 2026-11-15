"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getDataMode,
  setDataMode as setServiceDataMode,
  subscribeDataMode,
  type DataMode,
} from "@/services";

export type { DataMode } from "@/services";

interface DataModeContextValue {
  mode: DataMode;
  isApi: boolean;
  isMock: boolean;
  setMode: (mode: DataMode) => void;
  toggleMode: () => void;
}

const DataModeContext = createContext<DataModeContextValue | null>(null);

function getServerSnapshot(): DataMode {
  return process.env.NEXT_PUBLIC_DATA_MODE === "mock" ? "mock" : "api";
}

export function DataModeProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();

  const mode = useSyncExternalStore(
    subscribeDataMode,
    getDataMode,
    getServerSnapshot,
  );

  const setMode = useCallback(
    (newMode: DataMode) => {
      if (newMode !== "api" && newMode !== "mock") return;
      if (newMode === getDataMode()) return;

      // 1. Update services factory mode and localStorage
      setServiceDataMode(newMode);

      // 2. Clear entire query cache to prevent any mixed/stale data between modes
      qc.clear();
      qc.resetQueries();
    },
    [qc],
  );

  const toggleMode = useCallback(() => {
    setMode(mode === "api" ? "mock" : "api");
  }, [mode, setMode]);

  const value = useMemo<DataModeContextValue>(
    () => ({
      mode,
      isApi: mode === "api",
      isMock: mode === "mock",
      setMode,
      toggleMode,
    }),
    [mode, setMode, toggleMode],
  );

  return (
    <DataModeContext.Provider value={value}>
      {children}
    </DataModeContext.Provider>
  );
}

export function useDataMode(): DataModeContextValue {
  const ctx = useContext(DataModeContext);
  if (!ctx) {
    const current = getDataMode();
    return {
      mode: current,
      isApi: current === "api",
      isMock: current === "mock",
      setMode: setServiceDataMode,
      toggleMode: () => setServiceDataMode(current === "api" ? "mock" : "api"),
    };
  }
  return ctx;
}
