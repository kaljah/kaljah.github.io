import { describe, expect, it } from "vitest";
import { hhvToBtu } from "../utils/hhv";

// S1K-F26: the form sends the HHV in Btu with its real basis; "BTU/unit" made the server read an MJ/kg
// value for a liquid fuel in the catalog's Btu/gal basis
describe("hhvToBtu", () => {
  it("keeps Btu/scf, Btu/gal and Btu/lb as entered", () => {
    expect(hhvToBtu(1020, "BTU/scf")).toEqual({ hhv: 1020, hhvUnit: "BTU/scf" });
    expect(hhvToBtu(138000, "BTU/gal")).toEqual({ hhv: 138000, hhvUnit: "BTU/gal" });
    expect(hhvToBtu(19000, "BTU/lb")).toEqual({ hhv: 19000, hhvUnit: "BTU/lb" });
  });

  it("converts MJ/kg to Btu/lb, never to a per-gallon basis", () => {
    const r = hhvToBtu(45.6, "MJ/kg");
    expect(r.hhvUnit).toBe("BTU/lb");
    expect(r.hhv).toBeCloseTo((45.6 * 947.817) / 2.20462, 6);
  });

  it("converts gas volume units to Btu/scf", () => {
    expect(hhvToBtu(38, "MJ/m3").hhvUnit).toBe("BTU/scf");
    expect(hhvToBtu(38, "MJ/m3").hhv).toBeCloseTo((38 * 947.817) / 35.3147, 6);
    expect(hhvToBtu(9000, "kcal/m3").hhv).toBeCloseTo((9000 * 3.96567) / 35.3147, 6);
  });
});
