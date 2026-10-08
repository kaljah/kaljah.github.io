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

describe("chart export", () => {
  it("builds CSV with quoting and formula protection", async () => {
    const { toCsv } = await import("../utils/chartExport");
    expect(toCsv(["name", "value"], [["Plain", 1], ['A, "B"', 2], ["=SUM(A1)", 3]])).toBe(
      'name,value\r\nPlain,1\r\n"A, ""B""",2\r\n\'=SUM(A1),3',
    );
  });
  it("shows export buttons only when a chart opts in", () => {
    const { rerender } = render(<BarChart data={[{ name: "A", value: 1 }]} dataKey="value" xKey="name" />);
    expect(screen.queryByLabelText(/as CSV/)).toBeNull();
    rerender(<BarChart data={[{ name: "A", value: 1 }]} dataKey="value" xKey="name" exportName="demo" />);
    expect(screen.getByLabelText("Download demo data as CSV")).toBeInTheDocument();
    expect(screen.getByLabelText("Download demo as an image")).toBeInTheDocument();
  });
});
