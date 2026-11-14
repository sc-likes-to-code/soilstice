import type { ApiErrorCode, ApiErrorResponse } from "@/types/contracts";

/** Typed error thrown by every service implementation (API_CONTRACTS §7). */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly retryable: boolean;
  readonly requestId: string;
  readonly details: Record<string, unknown> | null;

  constructor(code: ApiErrorCode, message: string, opts?: { retryable?: boolean; requestId?: string; details?: Record<string, unknown> | null }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = opts?.retryable ?? (code === "UPSTREAM_UNAVAILABLE" || code === "RATE_LIMITED" || code === "INTERNAL");
    this.requestId = opts?.requestId ?? "unknown";
    this.details = opts?.details ?? null;
  }

  static fromResponse(body: ApiErrorResponse): ApiError {
    const e = body.error;
    return new ApiError(e.code, e.message, { retryable: e.retryable, requestId: e.request_id, details: e.details });
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export const API_ERROR_CODES: readonly ApiErrorCode[] = [
  "NOT_FOUND", "VALIDATION_ERROR", "OUTSIDE_AOI", "GEOMETRY_INVALID", "FIELD_TOO_LARGE",
  "NOT_EDITABLE", "UPSTREAM_UNAVAILABLE", "RATE_LIMITED", "NOT_IMPLEMENTED", "INTERNAL",
] as const;
