import { describe, it, expect } from "vitest";
import { addRow, analysisRowStatus, emptyCompositionCheck, mapsAnAnalysis, readNumber } from "../utils/compositionTotals";

const MAP = { c1: "C1", c2: "C2", co2_mol: "CO2", n2_mol: "N2" };

describe("readNumber", () => {
  it("reads the file's decimal mark", () => {
    expect(readNumber("87,5", "comma")).toBe(87.5);
    expect(readNumber("1.234,5", "comma")).toBe(1234.5);
    expect(readNumber("87.5", "point")).toBe(87.5);
    expect(readNumber("1,234.5", "point")).toBe(1234.5);
    expect(readNumber("85 %", "point")).toBe(85);
  });
  it("returns null for empty or unreadable cells", () => {
    expect(readNumber("", "point")).toBeNull();
    expect(readNumber("-", "point")).toBeNull();
    expect(readNumber("n/a", "point")).toBeNull();
  });
});

describe("analysisRowStatus (the server's rule: two or more components must total 100 %, 99.5 to 100.5)", () => {
  it("accepts 100 % and the rounding limits", () => {
    expect(analysisRowStatus({ C1: "90", C2: "5", CO2: "3", N2: "2" }, MAP, "point").off).toBe(false);
    expect(analysisRowStatus({ C1: "90", C2: "9.5" }, MAP, "point").off).toBe(false);
    expect(analysisRowStatus({ C1: "90", C2: "10.5" }, MAP, "point").off).toBe(false);
  });
  it("flags a total short of or over 100 %", () => {
    const short = analysisRowStatus({ C1: "90", C2: "5" }, MAP, "point");
    expect(short.off).toBe(true);
    expect(short.total).toBe(95);
    expect(analysisRowStatus({ C1: "95", C2: "6" }, MAP, "point").off).toBe(true);
    expect(analysisRowStatus({ C1: "90", C2: "9.4" }, MAP, "point").off).toBe(true);
  });
  it("reads a fractional analysis (every value 1 or less) as fractions", () => {
    expect(analysisRowStatus({ C1: "0.9", C2: "0.1" }, MAP, "point")).toMatchObject({ isAnalysis: true, off: false });
    expect(analysisRowStatus({ C1: "0.9", C2: "0.05" }, MAP, "point").off).toBe(true);
  });
  it("does not check one component or the CH4 + CO2 content short form", () => {
    expect(analysisRowStatus({ C1: "80" }, MAP, "point")).toMatchObject({ isAnalysis: false, off: false });
    expect(analysisRowStatus({ CH4: "80", CO2c: "5" }, { ch4_content: "CH4", co2_content: "CO2c" }, "point")).toMatchObject({
      isAnalysis: false,
      off: false,
    });
  });
});

describe("addRow / mapsAnAnalysis", () => {
  it("counts rows, analysis rows and the first off rows with their file line", () => {
    const check = emptyCompositionCheck();
    const rows = [
      { C1: "90", C2: "10" },
      { C1: "90", C2: "5" },
      { C1: "80" },
      { C1: "70", N2: "20" },
    ];
    rows.forEach((r, i) => addRow(check, r, i + 1, MAP, "point"));
    expect(check).toEqual({ rows: 4, analysisRows: 3, offRows: 2, examples: [{ line: 3, total: 95 }, { line: 5, total: 90 }] });
  });
  it("only an analysis when two analysis columns are mapped", () => {
    expect(mapsAnAnalysis({ c1: "C1" })).toBe(false);
    expect(mapsAnAnalysis({ ch4_content: "x", co2_content: "y" })).toBe(false);
    expect(mapsAnAnalysis({ c1: "C1", n2_mol: "N2" })).toBe(true);
  });
});
