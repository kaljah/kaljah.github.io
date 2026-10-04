import { beforeEach, describe, expect, it, vi } from "vitest";
import { activeFilterCount, getFilters, resetFilters, setFilter, setFilters, subscribe } from "../filterStore";

describe("filterStore", () => {
  beforeEach(() => resetFilters());

  it("starts at all and normalizes empty values to all", () => {
    expect(getFilters().year).toBe("all");
    setFilter("year", "2026");
    expect(getFilters().year).toBe("2026");
    setFilter("year", "");
    expect(getFilters().year).toBe("all");
  });

  it("applies several setters in one handler without losing updates", () => {
    setFilter("activity", "EP");
    setFilter("division", "Production");
    setFilter("region", "3");
    expect(getFilters()).toMatchObject({ activity: "EP", division: "Production", region: "3" });
  });

  it("notifies subscribers only on real changes and persists to sessionStorage", () => {
    const listener = vi.fn();
    const off = subscribe(listener);
    setFilter("year", "2025");
    setFilter("year", "2025");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(JSON.parse(sessionStorage.getItem("ct.analyticsFilters")).year).toBe("2025");
    off();
    setFilter("year", "2024");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("counts active filters and resets them", () => {
    setFilters({ year: "2026", segment: "Upstream" });
    expect(activeFilterCount()).toBe(2);
    resetFilters();
    expect(activeFilterCount()).toBe(0);
  });
});
