/**
 * Service factory — the ONLY module allowed to import `services/mock/*` (enforced by ESLint).
 * Supports both static default configuration and instant runtime switching between "api" and "mock" modes.
 */
import type { Services } from "./types";
import { createHttpServices } from "./http/services";
import { createMockServices } from "./mock/services";

export type { Services } from "./types";
export { ApiError, isApiError } from "./errors";

export type DataMode = "mock" | "api";

const STORAGE_KEY = "soilstice.data_mode";

function resolveDefaultMode(): DataMode {
  return process.env.NEXT_PUBLIC_DATA_MODE === "mock" ? "mock" : "api";
}

function resolveInitialMode(): DataMode {
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "api" || stored === "mock") return stored;
    } catch {
      // localStorage unavailable (e.g. security sandbox)
    }
  }
  return resolveDefaultMode();
}

let currentMode: DataMode = resolveInitialMode();
const listeners = new Set<(mode: DataMode) => void>();

let httpInstance: Services | null = null;
let mockInstance: Services | null = null;

export function getDataMode(): DataMode {
  return currentMode;
}

export function setDataMode(mode: DataMode): void {
  if (mode !== "api" && mode !== "mock") return;
  if (currentMode === mode) return;
  currentMode = mode;
  DATA_MODE = mode;

  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // storage unavailable
    }
  }

  listeners.forEach((fn) => {
    try {
      fn(mode);
    } catch (e) {
      console.error("Error in data mode listener:", e);
    }
  });
}

export function subscribeDataMode(listener: (mode: DataMode) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * Returns the active service implementation.
 * When explicitMode is provided, returns that specific implementation.
 */
export function getServices(explicitMode?: DataMode): Services {
  const targetMode = explicitMode ?? currentMode;
  if (targetMode === "api") {
    if (!httpInstance) httpInstance = createHttpServices();
    return httpInstance;
  }
  if (!mockInstance) mockInstance = createMockServices();
  return mockInstance;
}

// Mutable export for backwards compatibility
export let DATA_MODE: DataMode = currentMode;
