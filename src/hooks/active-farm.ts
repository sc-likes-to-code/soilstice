"use client";
import { useFarms } from "./queries";
import { usePrefs } from "./preferences";
import type { Farm } from "@/types/contracts";

/** Resolves the active farm: stored preference if it still exists, else the first farm. */
export function useActiveFarm(): { farm: Farm | null; farms: Farm[]; isLoading: boolean; error: unknown; refetch: () => void } {
  const { activeFarmId } = usePrefs();
  const q = useFarms();
  const farms = q.data?.data ?? [];
  const farm = farms.find((f) => f.farm_id === activeFarmId) ?? farms[0] ?? null;
  return { farm, farms, isLoading: q.isLoading, error: q.error, refetch: () => void q.refetch() };
}
