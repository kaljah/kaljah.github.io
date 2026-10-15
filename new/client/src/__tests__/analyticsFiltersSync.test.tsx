import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import AnalyticsFiltersSync from "../filters/AnalyticsFiltersSync";
import { getFilters, resetFilters, setFilters } from "../filters/filterStore";

let currentSearch = "";
const LocationProbe: React.FC = () => {
  currentSearch = useLocation().search;
  return null;
};

// bug hunt 2026-10-15 #19: a deep link was merged with the stored filters and the URL kept only its own keys
describe("AnalyticsFiltersSync deep links", () => {
  beforeEach(() => {
    resetFilters();
    currentSearch = "";
  });

  it("a deep link replaces the stored filters and the URL shows the filters in force", async () => {
    setFilters({ region: "5", segment: "Upstream" });
    render(
      <MemoryRouter initialEntries={["/carbon-intensity?year=2023"]}>
        <AnalyticsFiltersSync />
        <LocationProbe />
      </MemoryRouter>,
    );
    await waitFor(() => expect(getFilters().year).toBe("2023"));
    expect(getFilters().region).toBe("all");
    expect(getFilters().segment).toBe("all");
    await waitFor(() => expect(currentSearch).toBe("?year=2023"));
  });

  it("without filter keys in the URL the stored filters are published to it", async () => {
    setFilters({ region: "7" });
    render(
      <MemoryRouter initialEntries={["/carbon-intensity"]}>
        <AnalyticsFiltersSync />
        <LocationProbe />
      </MemoryRouter>,
    );
    await waitFor(() => expect(currentSearch).toBe("?region=7"));
    expect(getFilters().region).toBe("7");
  });
});
