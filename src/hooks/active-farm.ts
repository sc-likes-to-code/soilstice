"use client";
import { useEffect, useMemo } from "react";
import { useFarms } from "./queries";
import { usePrefs } from "./preferences";
import type { Farm } from "@/types/contracts";

/** Resolves the active farm: stored preference if it still exists, else the first farm. */
export function useActiveFarm(): { farm: Farm | null; farms: Farm[]; isLoading: boolean; error: unknown; refetch: () => void } {
  const { activeFarmId, setActiveFarmId } = usePrefs();
  const q = useFarms();
  const farms = useMemo(() => q.data?.data ?? [], [q.data?.data]);
  const farm = farms.find((f) => f.farm_id === activeFarmId) ?? farms[0] ?? null;

  useEffect(() => {
    if (farms.length > 0 && (!activeFarmId || !farms.some((f) => f.farm_id === activeFarmId))) {
      setActiveFarmId(farms[0].farm_id);
    }
  }, [farms, activeFarmId, setActiveFarmId]);

  return { farm, farms, isLoading: q.isLoading, error: q.error, refetch: () => void q.refetch() };
}
