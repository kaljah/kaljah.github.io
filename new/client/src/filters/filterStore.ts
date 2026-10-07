// Shared analytics filters (year, segment, activity, division, region).
// A tiny external store: every setter updates one object, so several setters called in one event handler
// never overwrite each other. The value survives page changes (sessionStorage) and is mirrored into the URL
// by AnalyticsFiltersSync on the analytics routes.

export const FILTER_KEYS = ["year", "segment", "activity", "division", "region"] as const;

export type FilterKey = (typeof FILTER_KEYS)[number];

export type AnalyticsFilters = Record<FilterKey, string>;

const STORAGE_KEY = "ct.analyticsFilters";

const DEFAULTS: AnalyticsFilters = {
  year: "all",
  segment: "all",
  activity: "all",
  division: "all",
  region: "all",
};

const read = (): AnalyticsFilters => {
  try {
    const raw = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
    const parsed: Partial<AnalyticsFilters> = {};
    for (const k of FILTER_KEYS) {
      if (typeof raw[k] === "string") {
        parsed[k] = raw[k];
      }
    }
    return { ...DEFAULTS, ...parsed };
  } catch {
    return { ...DEFAULTS };
  }
};

let state: AnalyticsFilters = read();
const listeners = new Set<() => void>();

const persist = (): void => {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // storage unavailable: filters just do not persist across pages
  }
};

export const getFilters = (): AnalyticsFilters => state;

export const setFilter = (key: FilterKey, value: unknown): void => {
  const next = value === undefined || value === null || value === "" ? "all" : String(value);
  if (state[key] === next) return;
  state = { ...state, [key]: next };
  persist();
  listeners.forEach((l) => l());
};

export const setFilters = (patch: Partial<Record<FilterKey | string, unknown>>): void => {
  let changed = false;
  const next = { ...state };
  for (const k of FILTER_KEYS) {
    if (k in patch && patch[k] !== undefined && next[k] !== String(patch[k])) {
      next[k] = String(patch[k]);
      changed = true;
    }
  }
  if (!changed) return;
  state = next;
  persist();
  listeners.forEach((l) => l());
};

export const resetFilters = (): void => setFilters(DEFAULTS);

export const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

export const activeFilterCount = (filters: AnalyticsFilters = state): number =>
  FILTER_KEYS.filter((k) => filters[k] !== "all").length;
