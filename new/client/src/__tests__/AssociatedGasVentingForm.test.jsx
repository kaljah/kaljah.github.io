import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AssociatedGasVentingForm, { TABLE_6_8_BASINS } from "../components/scope1/AssociatedGasVentingForm";
import { API_FACTORS, PROCESS_GROUPS } from "../utils/EmissionFactors";

describe("AssociatedGasVentingForm & Table 6-8 API Reference Integrity", () => {
  it("verifies all 6 API Table 6-8 regional basin factors are cataloged with correct values", () => {
    expect(TABLE_6_8_BASINS).toHaveLength(6);

    const usAvg = API_FACTORS["Associated Gas Venting - US Average"];
    expect(usAvg).toBeDefined();
    expect(usAvg.ch4).toBe(1.4);
    expect(usAvg.whole_gas_ef).toBe(89.0);
    expect(usAvg.unit).toBe("kg CH4/bbl");

    const gulfCoast = API_FACTORS["Associated Gas Venting - Gulf Coast Basin (Basin 220)"];
    expect(gulfCoast).toBeDefined();
    expect(gulfCoast.ch4).toBe(0.7);
    expect(gulfCoast.whole_gas_ef).toBe(47.0);

    const anadarko = API_FACTORS["Associated Gas Venting - Anadarko Basin (Basin 360)"];
    expect(anadarko).toBeDefined();
    expect(anadarko.ch4).toBe(9.7);
    expect(anadarko.whole_gas_ef).toBe(622.0);

    const williston = API_FACTORS["Associated Gas Venting - Williston Basin (Basin 395)"];
    expect(williston).toBeDefined();
    expect(williston.ch4).toBe(8.9);
    expect(williston.whole_gas_ef).toBe(570.0);

    const permian = API_FACTORS["Associated Gas Venting - Permian Basin (Basin 430)"];
    expect(permian).toBeDefined();
    expect(permian.ch4).toBe(6.5);
    expect(permian.whole_gas_ef).toBe(419.0);

    const otherBasins = API_FACTORS["Associated Gas Venting - Other US Basins"];
    expect(otherBasins).toBeDefined();
    expect(otherBasins.ch4).toBe(0.4);
    expect(otherBasins.whole_gas_ef).toBe(26.0);

    // Verify Upstream process group includes associated_gas_venting
    const upstreamGroup = PROCESS_GROUPS.find((g) => g.id === "Upstream");
    expect(upstreamGroup).toBeDefined();
    expect(upstreamGroup.options).toContain("associated_gas_venting");
  });

  it("renders Tier 1 Table 6-8 form with regional basin selector and crude throughput", () => {
    const handleChange = vi.fn();
    const handleSetSourceType = vi.fn();

    const data = {
      tier: "tier1",
      basin: "Associated Gas Venting - Permian Basin (Basin 430)",
      amount: 10000,
      oil_production: 10000,
      oil_unit: "bbl",
    };

    render(
      <AssociatedGasVentingForm
        data={data}
        onChange={handleChange}
        sourceType="default"
        setSourceType={handleSetSourceType}
      />
    );

    expect(screen.getByText("Associated Gas Venting")).toBeInTheDocument();
    // the emission UI shows no API Compendium / table citations (user request)
    expect(screen.queryByText(/Compendium|Table 6-8/i)).toBeNull();
    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.queryByRole("button", { name: /Tier 1/ })).toBeNull();

    // Check factor details badge
    // the factor details badge was removed on request
    expect(screen.queryByText(/kg CH₄ \/ bbl crude/i)).toBeNull();

    // Change crude oil throughput
    const inputs = screen.getAllByRole("spinbutton");
    const oilInput = inputs[0];
    fireEvent.change(oilInput, { target: { value: "15000" } });
    expect(handleChange).toHaveBeenCalledWith("oil_production", "15000");
    expect(handleChange).toHaveBeenCalledWith("amount", "15000");
  });

  it("renders Tier 2 Engineering GOR Balance with disposition partitioning and zero double-counting", () => {
    const handleChange = vi.fn();
    const handleSetSourceType = vi.fn();

    const data = {
      tier: "tier2",
      oil_production: 1000,
      oil_unit: "bbl/day",
      gor: 800,
      gor_unit: "scf/bbl",
      venting_duration: 365,
      recovered_gas_volume: 500000,
      flared_gas_volume: 200000,
      gas_volume_unit: "scf",
      ch4_content: 70.0,
      co2_content: 10.0,
    };

    render(
      <AssociatedGasVentingForm
        data={data}
        onChange={handleChange}
        sourceType="custom"
        setSourceType={handleSetSourceType}
      />
    );

    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.queryByText("Tier 2: GOR Balance")).toBeNull();
    expect(screen.getByText(/Gas Disposition Partitioning & Mass Balance/i)).toBeInTheDocument();
    expect(screen.getByText(/Zero Double-Counting Verified/i)).toBeInTheDocument();

    // Check Net Vented Calculation display
    // Total produced = 1000 * 365 * 800 = 292,000,000 scf
    // Net vented = 292,000,000 - 500,000 - 200,000 = 291,300,000 scf
    expect(screen.getByText(/291,300,000.0 scf/i)).toBeInTheDocument();
  });

  it("detects mass balance violations when recovered + flared gas exceeds total produced", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier2",
      oil_production: 100,
      oil_unit: "bbl",
      gor: 500, // 50,000 scf total produced
      gor_unit: "scf/bbl",
      venting_duration: 365,
      recovered_gas_volume: 40000,
      flared_gas_volume: 20000, // 40,000 + 20,000 = 60,000 > 50,000
      gas_volume_unit: "scf",
    };

    render(
      <AssociatedGasVentingForm
        data={data}
        onChange={handleChange}
        sourceType="custom"
      />
    );

    expect(screen.getByText(/Mass Balance Violation:/i)).toBeInTheDocument();
    expect(screen.getByText(/exceeds total produced associated gas/i)).toBeInTheDocument();
  });

  it("detects physical gas composition errors when sum of CH4 and CO2 exceeds 100%", () => {
    const handleChange = vi.fn();

    const data = {
      tier: "tier2",
      oil_production: 1000,
      gor: 500,
      ch4_content: 85.0,
      co2_content: 25.0, // 85 + 25 = 110% > 100%
    };

    render(
      <AssociatedGasVentingForm
        data={data}
        onChange={handleChange}
        sourceType="custom"
      />
    );

    expect(screen.getByText(/Gas Composition Error:/i)).toBeInTheDocument();
    expect(screen.getByText(/exceeds 100%/i)).toBeInTheDocument();
  });

  it("renders Tier 3 Direct Measurement with vent rate and total volume modes", () => {
    const handleChange = vi.fn();
    const handleSetSourceType = vi.fn();

    const data = {
      tier: "tier3",
      tier3_mode: "rate",
      vent_rate: 150,
      vent_rate_unit: "scfh",
      venting_duration: 72,
      ch4_content: 88.0,
      co2_content: 2.0,
    };

    const { rerender } = render(
      <AssociatedGasVentingForm
        data={data}
        onChange={handleChange}
        sourceType="specific"
        setSourceType={handleSetSourceType}
      />
    );

    expect(screen.getByText("Mode A: Measured Vent Flow Rate × Duration")).toBeInTheDocument();
    expect(screen.getByText("Mode B: Total Measured Vent Volume")).toBeInTheDocument();
    expect(screen.getByText(/Tier 3: CEMS \/ Meter/i)).toBeInTheDocument();

    // Switch to volume mode
    rerender(
      <AssociatedGasVentingForm
        data={{ ...data, tier3_mode: "volume", vent_volume: 50000, vent_volume_unit: "scf" }}
        onChange={handleChange}
        sourceType="specific"
        setSourceType={handleSetSourceType}
      />
    );

    expect(screen.getByText(/Total Measured Vent Gas Volume/i)).toBeInTheDocument();
  });

  it("follows the page-level tier selector (sourceType) and keeps data.tier / calc_method in sync", () => {
    const handleChange = vi.fn();
    const data = { tier: "tier1", oil_production: 1000 };

    const { rerender } = render(
      <AssociatedGasVentingForm data={data} onChange={handleChange} sourceType="default" />
    );
    expect(screen.queryByText("Tier 2: GOR Balance")).toBeNull();

    rerender(<AssociatedGasVentingForm data={data} onChange={handleChange} sourceType="custom" />);
    expect(handleChange).toHaveBeenCalledWith("tier", "tier2");
    expect(handleChange).toHaveBeenCalledWith("calc_method", "api_equation_6_8_6_9");

    rerender(<AssociatedGasVentingForm data={data} onChange={handleChange} sourceType="specific" />);
    expect(handleChange).toHaveBeenCalledWith("tier", "tier3");
    expect(handleChange).toHaveBeenCalledWith("calc_method", "api_equation_6_8_direct");
  });
});
