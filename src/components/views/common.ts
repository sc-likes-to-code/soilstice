export const LATEST_SEASON = 2025;
export const SEASONS = Array.from({ length: 16 }, (_, i) => LATEST_SEASON - i); // 2025 … 2010
export const seasonOptions = SEASONS.map((y) => ({ value: y, label: `${y} season` }));
