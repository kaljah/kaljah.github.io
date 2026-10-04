import { useCallback, useSyncExternalStore } from "react";
import { FILTER_KEYS, activeFilterCount, getFilters, resetFilters, setFilter, subscribe } from "./filterStore";

/** Drop-in replacement for useState("all") for one shared filter: const [year, setYear] = useAnalyticsFilter("year"). */
export const useAnalyticsFilter = (key) => {
  if (import.meta.env.DEV && !FILTER_KEYS.includes(key)) throw new Error(`Unknown analytics filter: ${key}`);
  const value = useSyncExternalStore(subscribe, () => getFilters()[key]);
  const set = useCallback((next) => setFilter(key, typeof next === "function" ? next(getFilters()[key]) : next), [key]);
  return [value, set];
};

export const useAnalyticsFilterSummary = () => {
  const filters = useSyncExternalStore(subscribe, getFilters);
  return { filters, activeCount: activeFilterCount(filters), reset: resetFilters };
};
