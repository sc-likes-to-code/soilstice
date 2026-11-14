import type { AoiId } from "@/types/contracts";
import type { Bbox } from "./geo";

/**
 * Approximate county extents for the two MVP AOIs (PHASE_0_DECISIONS D2, T20).
 * Used for client-side pre-validation of drawn fields and to frame maps; the backend performs the authoritative check.
 */
export const AOI_BBOX: Record<AoiId, Bbox> = {
  ks_reno: [-98.472, 37.732, -97.698, 38.173],
  ks_finney: [-101.103, 37.732, -100.215, 38.264],
};

export const MAX_FIELD_HA = 260;
