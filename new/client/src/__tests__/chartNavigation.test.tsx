import React from "react";
import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { BarChart, WaterfallChart } from "../components/charts";
import { recordsLink } from "../utils/reportLinks";

describe("recordsLink", () => {
  it("builds a Reports deep link and drops empty parts", () => {
    expect(recordsLink({ facilityId: 3, year: 2025 })).toBe("/reports?facility=3&year=2025");
    expect(recordsLink({ year: 2025, scope: "2" })).toBe("/reports?year=2025&scope=2");
    expect(recordsLink({})).toBe("/reports");
  });
  it("keeps year=all so Reports does not jump to the latest year", () => {
    expect(recordsLink({ facilityId: 1, year: "all" })).toBe("/reports?facility=1&year=all");
  });
});

describe("chart click-through has a keyboard path", () => {
  it("BarChart exposes one button per bar and reports the row", () => {
    const onSelect = vi.fn();
    render(
      <BarChart
        data={[
          { id: 1, name: "Alpha", value: 5 },
          { id: 2, name: "Beta", value: 9 },
        ]}
        dataKey="value"
        xKey="name"
        horizontal
        sortDesc
        onSelect={onSelect}
        selectLabel={(r) => `Open ${r.name} records`}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Open Beta records", "Open Alpha records"]);
    fireEvent.click(buttons[0]);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 2, name: "Beta" }));
  });

  it("WaterfallChart exposes the change steps but not the totals", () => {
    const onSelectStep = vi.fn();
    render(
      <WaterfallChart
        startLabel="2024"
        endLabel="2025"
        start={100}
        end={110}
        steps={[
          { name: "Flaring", delta: 15 },
          { name: "Scope 2", delta: -5 },
        ]}
        onSelectStep={onSelectStep}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Open Flaring records", "Open Scope 2 records"]);
    fireEvent.click(buttons[1]);
    expect(onSelectStep).toHaveBeenCalledWith({ name: "Scope 2", delta: -5 });
  });
});
