/**
 * Service factory — the ONLY module allowed to import `services/mock/*` (enforced by ESLint).
 * Mode is selected by NEXT_PUBLIC_DATA_MODE = "mock" | "api" (default "mock" in Phase 1).
 */
import type { Services } from "./types";
import { createHttpServices } from "./http/services";
import { createMockServices } from "./mock/services";

export type { Services } from "./types";
export { ApiError, isApiError } from "./errors";

export const DATA_MODE: "mock" | "api" = process.env.NEXT_PUBLIC_DATA_MODE === "api" ? "api" : "mock";

let instance: Services | null = null;

export function getServices(): Services {
  if (!instance) instance = DATA_MODE === "api" ? createHttpServices() : createMockServices();
  return instance;
}
