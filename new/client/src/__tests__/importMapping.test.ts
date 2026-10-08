import { describe, it, expect } from "vitest";
import { autoDetectMapping, missingRequiredFields, normHeader } from "../utils/importMapping";

const F = (key: string, label: string, required = false) => ({ key, label, required });

describe("import column mapping", () => {
  it("reads template headers without tags and unit notes", () => {
    expect(normHeader("[Required] process_type")).toBe("process type");
    expect(normHeader("[T3-Tank] tank_gor")).toBe("tank gor");
    expect(normHeader("Bleed Rate (scf/hr)")).toBe("bleed rate");
  });

  it("maps a column to one field only", () => {
    const fields = [F("pneu_type", "Pneumatic Type"), F("factor_type", "Factor Type"), F("flare_type", "Flare Type"),
      F("unit", "Unit"), F("temp_unit", "Temp Unit"), F("press_unit", "Press Unit")];
    const m = autoDetectMapping(["Type", "Unit", "Factor Type"], fields);
    expect(m.factor_type).toBe("Factor Type");
    expect(m.unit).toBe("Unit");
    expect(m.temp_unit).toBeUndefined();
    expect(m.press_unit).toBeUndefined();
    expect(Object.values(m).filter((h) => h === "Type").length).toBeLessThanOrEqual(1);
  });

  it("maps the CSV template headers", () => {
    const fields = [F("date", "Date"), F("facility_name", "Region / Facility"), F("process", "Process Type"),
      F("fuel", "Activity / Fuel"), F("quantity", "Quantity"), F("unit", "Unit"), F("tank_gor", "Tank GOR"),
      F("c1", "C1 (Methane) mol%"), F("c10", "C10+ mol%")];
    const m = autoDetectMapping(["[Required] date", "[Required] facility_name", "[Required] process_type",
      "[Required] fuel", "[Required] quantity", "[Required] unit", "[T3-Tank] tank_gor", "[T3] c1", "[T3] c10"], fields);
    expect(m).toMatchObject({ date: "[Required] date", facility_name: "[Required] facility_name",
      process: "[Required] process_type", fuel: "[Required] fuel", tank_gor: "[T3-Tank] tank_gor",
      c1: "[T3] c1", c10: "[T3] c10" });
  });

  it("accepts a date column or year and month", () => {
    const fields = [F("date", "Date", true), F("facility_name", "Facility", true), F("year", "Year", true), F("month", "Month", true)];
    expect(missingRequiredFields(fields, { date: "d", facility_name: "f" })).toEqual([]);
    expect(missingRequiredFields(fields, { year: "y", month: "m", facility_name: "f" })).toEqual([]);
    const miss = missingRequiredFields(fields, { year: "y", facility_name: "f" });
    expect(miss.map((f) => f.key)).toEqual(["date"]);
    expect(miss[0].label).toBe("Date (or Year and Month)");
  });

  it("keeps year and month required where there is no date field", () => {
    const fields = [F("facility_id", "Region", true), F("year", "Year", true), F("month", "Month", true)];
    expect(missingRequiredFields(fields, { facility_id: "r", year: "y" }).map((f) => f.key)).toEqual(["month"]);
  });
});

describe("short headers", () => {
  it("maps a header that names exactly one field", () => {
    const fields = [F("facility_name", "Region / Facility", true), F("pneu_type", "Pneumatic Type"), F("flare_type", "Flare Type")];
    const m = autoDetectMapping(["Facility", "Type"], fields);
    expect(m.facility_name).toBe("Facility");
    expect(m.pneu_type).toBeUndefined();
    expect(m.flare_type).toBeUndefined();
  });
});

describe("generic single-word fields (S1K-F12)", () => {
  it("does not map Activity to activity_key or Hours to operating_hours", () => {
    const fields = [F("activity", "Activity"), F("pneu_hours", "Pneumatic Hours"), F("unload_press", "Shut-in Pressure")];
    const m = autoDetectMapping(["activity_key", "operating_hours", "blowdown_pressure"], fields);
    expect(m.activity).toBeUndefined();
    expect(m.pneu_hours).toBeUndefined();
    expect(m.unload_press).toBeUndefined();
  });

  it("still maps the exact header", () => {
    const m = autoDetectMapping(["Activity"], [F("activity", "Activity")]);
    expect(m.activity).toBe("Activity");
  });
});
