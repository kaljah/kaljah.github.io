import { describe, expect, it } from "vitest";
import { hhvToBtu } from "../utils/hhv";

// Backend values from calculations/units.py convert(): 1 MJ = 947.8171203133172 Btu,
// 1 m3 = 35.314666721 scf, 1 kg = 2.2046226218487757 lb.
const close = (a: number, b: number) => expect(Math.abs(a - b)).toBeLessThanOrEqual(1e-9 * Math.abs(b));

describe("hhvToBtu matches the server's unit table", () => {
  it("MJ/m3 -> BTU/scf", () => {
    const r = hhvToBtu(38.5, "MJ/m3");
    close(r.hhv, (38.5 * 947.8171203133172) / 35.314666721);
    expect(r.hhvUnit).toBe("BTU/scf");
  });
  it("MJ/kg -> BTU/lb", () => {
    close(hhvToBtu(50, "MJ/kg").hhv, (50 * 947.8171203133172) / 2.2046226218487757);
  });
  it("kcal/m3 -> BTU/scf uses 4184 J per kcal", () => {
    close(hhvToBtu(9000, "kcal/m3").hhv, (9000 * (4184 / 1055.05585262)) / 35.314666721);
  });
  it("Btu units pass through", () => {
    expect(hhvToBtu(1020, "BTU/scf").hhv).toBe(1020);
    expect(hhvToBtu(130000, "BTU/gal")).toEqual({ hhv: 130000, hhvUnit: "BTU/gal" });
    expect(hhvToBtu(20000, "BTU/lb")).toEqual({ hhv: 20000, hhvUnit: "BTU/lb" });
  });
});
