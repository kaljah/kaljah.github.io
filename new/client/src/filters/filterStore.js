// Shared analytics filters (year, segment, activity, division, region).
// A tiny external store: every setter updates one object, so several setters called in one event handler
// never overwrite each other. The value survives page changes (sessionStorage) and is mirrored into the URL
// by AnalyticsFiltersSync on the analytics routes.
export const FILTER_KEYS = ["year", "segment", "activity", "division", "region"];
const STORAGE_KEY = "ct.analyticsFilters";
const DEFAULTS = Object.fromEntries(FILTER_KEYS.map((k) => [k, "all"]));

const read = () => {
  try {
    const raw = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
    return { ...DEFAULTS, ...Object.fromEntries(FILTER_KEYS.filter((k) => typeof raw[k] === "string").map((k) => [k, raw[k]])) };
  } catch {
    return { ...DEFAULTS };
  }
};

let state = read();
const listeners = new Set();

const persist = () => {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // storage unavailable: filters just do not persist across pages
  }
};

export const getFilters = () => state;

export const setFilter = (key, value) => {
  const next = value === undefined || value === null || value === "" ? "all" : String(value);
  if (state[key] === next) return;
  state = { ...state, [key]: next };
  persist();
  listeners.forEach((l) => l());
};

export const setFilters = (patch) => {
  let changed = false;
  const next = { ...state };
  for (const k of FILTER_KEYS) {
    if (k in patch && next[k] !== String(patch[k])) {
      next[k] = String(patch[k]);
      changed = true;
    }
  }
  if (!changed) return;
  state = next;
  persist();
  listeners.forEach((l) => l());
};

export const resetFilters = () => setFilters(DEFAULTS);

export const subscribe = (listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export const activeFilterCount = (filters = state) => FILTER_KEYS.filter((k) => filters[k] !== "all").length;
