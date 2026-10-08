import { describe, expect, it } from "vitest";
import { fittingMappings, withSavedMapping } from "../utils/savedMappings";

const sap = { id: 1, name: "SAP", headers: ["Month", "Site", "Amount", "UoM"], mapping: { date: "Month", facility_name: "Site", quantity: "Amount", unit: "UoM" } };
const pi = { id: 2, name: "PI", headers: ["Month", "Site", "Amount", "UoM", "Tag"], mapping: { date: "Month", quantity: "Amount" } };
const other = { id: 3, name: "Other", headers: ["Periode", "Usine"], mapping: { date: "Periode" } };

describe("saved mappings", () => {
  it("offers only mappings whose columns are all in the file, the same column set first", () => {
    expect(fittingMappings([pi, sap, other], ["Month", "Site", "Amount", "UoM"]).map((m) => m.id)).toEqual([1, 2]);
    expect(fittingMappings([sap, pi], ["Month", "Site", "Amount", "UoM", "Tag"]).map((m) => m.id)).toEqual([2, 1]);
    expect(fittingMappings([sap], ["Month", "Amount"])).toEqual([]);
    expect(fittingMappings([sap], [])).toEqual([]);
  });

  it("applies the best saved mapping over the automatic one", () => {
    const { mapping, applied } = withSavedMapping({ date: "Month", fuel: "Fuel" }, [sap], ["Month", "Site", "Amount", "UoM", "Fuel"]);
    expect(applied?.id).toBe(1);
    expect(mapping).toEqual({ date: "Month", fuel: "Fuel", facility_name: "Site", quantity: "Amount", unit: "UoM" });
    expect(withSavedMapping({ date: "A" }, [other], ["A"])).toEqual({ mapping: { date: "A" }, applied: null });
  });
});
