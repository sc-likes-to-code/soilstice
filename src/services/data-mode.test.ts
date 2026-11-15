import { describe, it, expect, beforeEach } from "vitest";
import {
  getDataMode,
  setDataMode,
  subscribeDataMode,
  getServices,
  type DataMode,
} from "./index";

describe("runtime data mode controller", () => {
  beforeEach(() => {
    // Reset to api mode before each test
    setDataMode("api");
  });

  it("defaults to api mode or matches configured mode", () => {
    const mode = getDataMode();
    expect(["api", "mock"]).toContain(mode);
  });

  it("switches to mock mode and notifies subscribers", () => {
    const notifications: DataMode[] = [];
    const unsubscribe = subscribeDataMode((m) => notifications.push(m));

    setDataMode("mock");
    expect(getDataMode()).toBe("mock");
    expect(notifications).toEqual(["mock"]);

    setDataMode("api");
    expect(getDataMode()).toBe("api");
    expect(notifications).toEqual(["mock", "api"]);

    unsubscribe();
    setDataMode("mock");
    // Should not receive further notifications after unsubscribe
    expect(notifications).toEqual(["mock", "api"]);
  });

  it("does not notify if setting the same mode", () => {
    setDataMode("api");
    const notifications: DataMode[] = [];
    const unsubscribe = subscribeDataMode((m) => notifications.push(m));

    setDataMode("api");
    expect(notifications.length).toBe(0);

    unsubscribe();
  });

  it("ignores invalid modes gracefully", () => {
    const original = getDataMode();
    // @ts-expect-error Testing invalid runtime input
    setDataMode("invalid_mode");
    expect(getDataMode()).toBe(original);
  });

  it("returns mock services when mode is mock and creates mock responses", async () => {
    setDataMode("mock");
    const svc = getServices();
    const farms = await svc.farms.listFarms();
    expect(farms.meta.data_mode).toBe("synthetic");
    expect(farms.data.length).toBe(2);
    expect(farms.data.map((f) => f.name)).toContain("Reno Demo Farm");
    expect(farms.data.map((f) => f.name)).toContain("Finney Demo Farm");
  });

  it("returns explicit service instance when explicitMode is supplied", async () => {
    setDataMode("api");
    const mockSvc = getServices("mock");
    const farms = await mockSvc.farms.listFarms();
    expect(farms.meta.data_mode).toBe("synthetic");
    expect(farms.data[0].name).toContain("Demo Farm");
  });
});
