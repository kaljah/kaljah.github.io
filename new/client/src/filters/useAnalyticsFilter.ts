import { useCallback, useSyncExternalStore } from "react";
import {
  FILTER_KEYS,
  activeFilterCount,
  getFilters,
  resetFilters,
  setFilter,
  subscribe,
  type FilterKey,
  type AnalyticsFilters,
} from "./filterStore";

/** Drop-in replacement for useState("all") for one shared filter: const [year, setYear] = useAnalyticsFilter("year"). */
export const useAnalyticsFilter = (
  key: FilterKey,
): [string, (next: string | ((prev: string) => string)) => void] => {
  if (import.meta.env.DEV && !(FILTER_KEYS as readonly string[]).includes(key)) {
    throw new Error(`Unknown analytics filter: ${key}`);
  }
  const value = useSyncExternalStore(subscribe, () => getFilters()[key]);
  const set = useCallback(
    (next: string | ((prev: string) => string)) => {
      setFilter(key, typeof next === "function" ? next(getFilters()[key]) : next);
    },
    [key],
  );
  return [value, set];
};

export interface AnalyticsFilterSummary {
  filters: AnalyticsFilters;
  activeCount: number;
  reset: () => void;
}

export const useAnalyticsFilterSummary = (): AnalyticsFilterSummary => {
  const filters = useSyncExternalStore(subscribe, getFilters);
  return { filters, activeCount: activeFilterCount(filters), reset: resetFilters };
};
