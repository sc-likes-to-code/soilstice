import type { ApiErrorResponse, ApiResponse } from "@/types/contracts";
import { ApiError } from "@/services/errors";

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export function apiBaseUrl(): string {
  return BASE;
}

type Query = Record<string, string | number | undefined>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(BASE + path);
  if (query) {
    for (const [k, v] of Object.entries(query)) if (v !== undefined) url.searchParams.set(k, String(v));
  }
  return url.toString();
}

/** Thin fetch wrapper: returns the contract envelope or throws a typed ApiError. */
export async function request<T>(method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE", path: string, opts?: { query?: Query; body?: unknown }): Promise<ApiResponse<T>> {
  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts?.query), {
      method,
      headers: opts?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: opts?.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError("UPSTREAM_UNAVAILABLE", `The SOILSTICE API at ${BASE} is not reachable.`, { retryable: true });
  }
  let json: unknown = null;
  try {
    json = await res.json();
  } catch {
    // fall through to status handling
  }
  if (!res.ok) {
    if (json && typeof json === "object" && "error" in json) throw ApiError.fromResponse(json as ApiErrorResponse);
    throw new ApiError(res.status === 404 ? "NOT_FOUND" : "INTERNAL", `API request failed with HTTP ${res.status}.`);
  }
  if (!json || typeof json !== "object" || !("data" in json) || !("meta" in json)) {
    throw new ApiError("INTERNAL", "API response did not match the contract envelope.");
  }
  return json as ApiResponse<T>;
}
