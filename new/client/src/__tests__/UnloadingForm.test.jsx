import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import UnloadingForm from "../components/scope1/UnloadingForm";
import { API_FACTORS } from "../utils/EmissionFactors";

describe("UnloadingForm & API Compendium 2021 Reference Integrity", () => {
  it("verifies API Table 6-11 per-well default factors in EmissionFactors catalog", () => {
    const plunger = API_FACTORS["Liquids Unloading - Plunger Lift"];
    expect(plunger).toBeDefined();
    expect(plunger.ch4).toBe(1.774);
    expect(plunger.unit).toBe("tonnes CH4/well-year");
    expect(plunger.baseUnit).toBe("wells");
    expect(plunger.whole_gas_ef).toBe(113466);

    const nonPlunger = API_FACTORS["Liquids Unloading - Non-Plunger"];
    expect(nonPlunger).toBeDefined();
    expect(nonPlunger.ch4).toBe(2.792);
    expect(nonPlunger.unit).toBe("tonnes CH4/well-year");
    expect(nonPlunger.baseUnit).toBe("wells");
    expect(nonPlunger.whole_gas_ef).toBe(178531);
  });

  it("verifies API Table 6-10 event-based factors in EmissionFactors catalog", () => {
    const pLe100 = API_FACTORS["Liquids Unloading - Plunger (≤100 events/yr)"];
    expect(pLe100).toBeDefined();
    expect(pLe100.ch4).toBe(0.185);
    expect(pLe100.unit).toBe("tonnes/event");

    const npLe10 = API_FACTORS["Liquids Unloading - Non-Plunger (≤10 events/yr)"];
    expect(npLe10).toBeDefined();
    expect(npLe10.ch4).toBe(0.412);
    expect(npLe10.unit).toBe("tonnes/event");

    const np10To50 = API_FACTORS["Liquids Unloading - Non-Plunger (10-50 events/yr)"];
    expect(np10To50).toBeDefined();
    expect(np10To50.ch4).toBe(0.462);

    const npGt50 = API_FACTORS["Liquids Unloading - Non-Plunger (>50 events/yr)"];
    expect(npGt50).toBeDefined();
    expect(npGt50.ch4).toBe(0.670);
  });

  it("renders Tier 1 form and updates well count and unloading type", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier1",
      unloading_type: "plunger",
      wells: 5,
      amount: 5,
      unit: "wells",
      ch4_content: 81.6,
      co2_content: 1.0,
      control_efficiency: 0,
    };

    render(
      <UnloadingForm
        data={data}
        onChange={handleChange}
        sourceType="default"
      />
    );

    // Verify Tier 1 elements
    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.queryByText(/Tier 1: Per-Well/i)).toBeNull();
    expect(screen.getByText(/^Wells/)).toBeInTheDocument();
    expect(screen.getByText(/^Plunger lift$/)).toBeInTheDocument();

    // Change well count
    const wellsInput = screen.getByDisplayValue("5");
    fireEvent.change(wellsInput, { target: { value: "10" } });
    expect(handleChange).toHaveBeenCalledWith("well_count", "10");
  });

  it("switches to Tier 2 tab and handles event frequency inputs", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier2",
      unloading_type: "non_plunger",
      events: 15,
      region: "Average",
      well_count: 2,
    };

    render(
      <UnloadingForm
        data={data}
        onChange={handleChange}
        sourceType="custom"
      />
    );

    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.queryByText(/Tier 2: Event-Based/i)).toBeNull();
    expect(screen.getByText(/^Events/)).toBeInTheDocument();
    expect(screen.getByText(/Region \/ Basin/i)).toBeInTheDocument();

    const eventsInput = screen.getByDisplayValue("15");
    fireEvent.change(eventsInput, { target: { value: "25" } });
    expect(handleChange).toHaveBeenCalledWith("events", "25");
  });

  it("switches to Tier 3 tab and renders Equation 6-10 engineering parameters", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier3",
      calc_method: "api_equation_6_10",
      unload_depth: 12000,
      unload_diam: 10,
      unload_press: 250,
      sfr: 35000,
      hours_open: 1.0,
      unload_events: 12,
      unload_type: "non_plunger",
    };

    render(
      <UnloadingForm
        data={data}
        onChange={handleChange}
        sourceType="specific"
      />
    );

    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.queryByText(/Tier 3: Engineering/i)).toBeNull();
    expect(screen.getByText(/Events per year/i)).toBeInTheDocument();
    // Eq 6-10 for a non-plunger well: casing diameter, well depth, flow-line pressure and rate (Exhibit 6-8)
    expect(screen.getByText(/Casing diameter \(in\)/i)).toBeInTheDocument();
    expect(screen.getByText(/^Well depth \(ft\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Flow-line pressure \(psig\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Flow-line gas rate \(scf\/hr\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Hours open to atmosphere \(h\/event\)/i)).toBeInTheDocument();
  });

  it("renders Equation 6-11 parameters when automated plunger lift is selected", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier3",
      calc_method: "api_equation_6_11",
      p_shut: 150,
      p_line: 100,
      p_sep: 50,
      sfr_p: 10000,
      t_p: 0.5,
      unload_events: 20,
    };

    render(
      <UnloadingForm
        data={data}
        onChange={handleChange}
        sourceType="specific"
      />
    );

    expect(screen.getByText(/Shut-In Pressure Pshut \(psia\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Flow-Line Pressure Pline \(psia\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Separator Pressure Psep \(psia\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Gas Production Rate SFRp \(scf\/hr\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Venting Time Tp \(hours\/event\)/i)).toBeInTheDocument();
  });

  it("renders Equation 6-3 volume-based decompression method", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier3",
      calc_method: "api_equation_6_3",
      well_depth: 8000,
      diameter: 3.5,
      pressure: 300,
      events: 8,
    };

    render(
      <UnloadingForm
        data={data}
        onChange={handleChange}
        sourceType="specific"
      />
    );

    // no equation / API citation is displayed (user request)
    expect(screen.queryByText(/API Equation|Equation 6-3/i)).toBeNull();
    expect(screen.getByText(/Frequency \(events\/yr\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Tubing diameter \(in\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Surface Pressure \(psig\)/i)).toBeInTheDocument();
  });
});
