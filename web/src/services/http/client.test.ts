import { afterEach, describe, expect, it, vi } from "vitest";
import { request } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("http client (api mode)", () => {
  it("maps an unreachable backend to a retryable UPSTREAM_UNAVAILABLE ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(request("GET", "/farms")).rejects.toMatchObject({ code: "UPSTREAM_UNAVAILABLE", retryable: true });
  });

  it("passes through contract error bodies", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "OUTSIDE_AOI", message: "outside", details: null, request_id: "r1", retryable: false } }), { status: 422 })));
    await expect(request("POST", "/farms/x/fields", { body: {} })).rejects.toMatchObject({ code: "OUTSIDE_AOI", requestId: "r1", retryable: false });
  });

  it("rejects responses that are not the contract envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ hello: "world" }), { status: 200 })));
    await expect(request("GET", "/farms")).rejects.toMatchObject({ code: "INTERNAL" });
  });

  it("returns the envelope on success", async () => {
    const body = { data: [], meta: { request_id: "r", generated_at: "2026-11-14T00:00:00Z", api_version: "v1", contract_version: "1.0.0-phase0", data_mode: "live", warnings: [] } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })));
    await expect(request("GET", "/farms")).resolves.toEqual(body);
  });
});
