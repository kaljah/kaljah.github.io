import { describe, it, expect } from "vitest";
import { CATEGORY_ACTIVITIES } from "../utils/scope3Factors";

// Expected values re-derived from the source tables (AR5: CH4 28, N2O 265)
const MI = 1.609344;
const SHORT_TON_MILE = 0.90718474 * MI; // tonne-km
const epa = (co2: number, ch4G: number, n2oG: number, per: number) =>
  (co2 + (ch4G * 28) / 1000 + (n2oG * 265) / 1000) / per;
const find = (cat: number, name: string) =>
  CATEGORY_ACTIVITIES[cat].find((a) => a.value === name)!.factor;

describe("Scope 3 factors", () => {
  it("transport = EPA Emission Factors Hub 2025 Table 8 (per short ton-mile)", () => {
    for (const cat of [4, 9]) {
      expect(find(cat, "Truck Transport")).toBeCloseTo(epa(0.186, 0.0016, 0.0054, SHORT_TON_MILE), 4);
      expect(find(cat, "Rail Transport")).toBeCloseTo(epa(0.021, 0.0016, 0.0005, SHORT_TON_MILE), 4);
      expect(find(cat, "Ship Transport")).toBeCloseTo(epa(0.077, 0.031, 0.002, SHORT_TON_MILE), 4);
      expect(find(cat, "Air Freight")).toBeCloseTo(epa(1.086, 0, 0.0334, SHORT_TON_MILE), 4);
    }
  });

  it("travel and commuting = EPA Hub Table 10", () => {
    expect(find(6, "Air - Short Haul (< 300 mi)")).toBeCloseTo(epa(0.207, 0.0064, 0.0066, MI), 4);
    expect(find(6, "Air - Long Haul (>= 2300 mi)")).toBeCloseTo(epa(0.163, 0.0006, 0.0052, MI), 4);
    expect(find(6, "Passenger Car")).toBeCloseTo(epa(0.297, 0.0059, 0.0053, MI), 4);
    expect(find(7, "Bus")).toBeCloseTo(epa(0.066, 0.0046, 0.0019, MI), 4);
  });

  it("waste = EPA Hub Table 9 (t CO2e / short ton)", () => {
    expect(find(5, "Landfill (mixed MSW)")).toBeCloseTo(0.58 / 0.90718474, 3);
    expect(find(5, "Incineration (mixed MSW)")).toBeCloseTo(0.43 / 0.90718474, 3);
    expect(find(12, "Recycling (mixed recyclables)")).toBeCloseTo(0.09 / 0.90718474, 3);
  });

  it("use of sold fuels = API Compendium Tables 4-5 / 4-6", () => {
    expect(find(11, "Crude Oil")).toBeCloseTo(42 * 0.138 * (74.54 + 0.003 * 28 + 0.0006 * 265), 1);
    expect(find(11, "Natural Gas")).toBeCloseTo(1.02 * (53.06 + 0.001 * 28 + 0.0001 * 265), 1);
    expect(find(11, "NGL - Butane")).toBeCloseTo(0.103 * (64.77 + 0.003 * 28 + 0.0006 * 265), 2);
  });

  it("spend rows = EPA Supply Chain GHG Emission Factors v1.3.0 (with margins)", () => {
    expect(find(1, "Iron & steel products (NAICS 331110)")).toBe(0.787);
    expect(find(1, "Cement (NAICS 327310)")).toBe(3.924);
    expect(find(2, "Oil & gas field machinery (NAICS 333132)")).toBe(0.219);
    expect(find(3, "Purchased natural gas, upstream (NAICS 211130)")).toBe(0.405);
    expect(find(13, "Downstream leased buildings (rent) (NAICS 531120)")).toBe(0.246);
  });

  it("has no default where no published factor exists", () => {
    expect(find(10, "Processing (Electricity)")).toBeNull();
    expect(find(15, "Equity Investments")).toBeNull();
    expect(find(14, "Franchise operations")).toBeNull();
  });

  it("drops the unsourced rows", () => {
    const all = Object.values(CATEGORY_ACTIVITIES).flat().map((a) => a.value);
    for (const gone of ["Pipeline Transport", "Teleworking", "Car - Diesel", "Air - Domestic", "Steel", "Cement", "Leased Office Space", "Retail Franchise"]) {
      expect(all).not.toContain(gone);
    }
  });
});
