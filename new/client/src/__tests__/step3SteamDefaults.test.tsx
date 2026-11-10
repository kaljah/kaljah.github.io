import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Scope2FormNewElectricityEntry from "../components/scope2-form/Scope2FormNewElectricityEntry";

function renderSteamEntry(boilerEff: string | number = 0.8, transLoss: string | number = 0.0) {
  return render(
    <Scope2FormNewElectricityEntry
      activity="Upstream"
      allocationMethod="wri_efficiency"
      amount="100"
      boilerEff={boilerEff}
      division="Production"
      facilityId="1"
      field="Basin Alpha"
      getFacilityOptions={() => [{ value: "1", label: "Facility A-1" }]}
      getGridOptions={() => [{ value: "DZ", label: "Algerian Grid" }]}
      gridRegion=""
      handleAddEntry={vi.fn()}
      handleSourceTypeChange={vi.fn()}
      heatEff=""
      heatOutput=""
      marketFactor=""
      marketInstrument=""
      month={1}
      powerEff=""
      powerOutput=""
      setAllocationMethod={vi.fn()}
      setAmount={vi.fn()}
      setBoilerEff={vi.fn()}
      setFacilityId={vi.fn()}
      setGridRegion={vi.fn()}
      setHeatEff={vi.fn()}
      setHeatOutput={vi.fn()}
      setMarketFactor={vi.fn()}
      setMarketInstrument={vi.fn()}
      setMonth={vi.fn()}
      setPowerEff={vi.fn()}
      setPowerOutput={vi.fn()}
      setTransLoss={vi.fn()}
      setUnit={vi.fn()}
      setYear={vi.fn()}
      sourceType="indirect_steam"
      submitting={false}
      transLoss={transLoss}
      unit="mmbtu"
      unitOptions={[{ value: "mmbtu", label: "MMBtu" }]}
      year={2025}
    />
  );
}

describe("Scope2FormNewElectricityEntry UNV-06/07 steam defaults", () => {
  it("shows 80% / 0% defaults with Exhibit 8.3 (82%/10%) documented as optional example", () => {
    renderSteamEntry(0.8, 0.0);

    expect(screen.getByPlaceholderText("Default: 0.80 (e.g. 0.82 per Exhibit 8.3)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Default: 0.00 (e.g. 0.10 per Exhibit 8.3)")).toBeInTheDocument();
    expect(screen.getByText(/Boiler Efficiency \(80%\) & Transmission Loss \(0%\)/)).toBeInTheDocument();
    expect(screen.getByText(/80% Net/)).toBeInTheDocument();
  });

  it("hides silent default banner when user configures custom values like Exhibit 8.3 (0.82 / 0.10)", () => {
    renderSteamEntry(0.82, 0.10);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
