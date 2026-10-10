import { describe, expect, it } from "vitest";
import { editRequest, editScope } from "../components/modals/editEmissionRequest";

const form = { year: 2026, month: 6, facility_id: "7", process_type: "Category 1: Purchased Goods and Services",
  fuel: "Chemicals, Catalysts & Drilling Mud", amount: "8551", unit: "USD" };

describe("edit dialog endpoint", () => {
  it("sends a Scope 3 record to the Scope 3 route, never to Scope 1", () => {
    const { url, payload } = editRequest({ id: "s3_28", scope: 3 }, form);
    expect(url).toBe("/scope3/28");
    expect(payload).toMatchObject({ year: 2026, facility_id: 7, activity_data: 8551, unit: "USD",
      category: form.process_type, sub_category: form.fuel });
    expect(payload).not.toHaveProperty("month");
    expect(payload).not.toHaveProperty("process_type");
  });

  it("reads the scope from the id prefix first", () => {
    expect(editScope({ id: "s3_28", scope: 1 })).toBe(3);
    expect(editScope({ id: "s2_4" })).toBe(2);
    expect(editScope({ id: "s1_9", grid_region: "DZ" })).toBe(1);
    expect(editScope({ id: 12, scope: "Scope 3" })).toBe(3);
    expect(editScope({ id: 12, grid_region: "DZ" })).toBe(2);
    expect(editScope({ id: 12 })).toBe(1);
  });

  it("keeps Scope 1 and Scope 2 routes and fields", () => {
    const s1 = editRequest({ id: "s1_12" }, { ...form, process_type: "stationary_combustion", fuel: "Diesel", amount: "1000", unit: "L" });
    expect(s1.url).toBe("/emissions/12");
    expect(s1.payload).toMatchObject({ month: 6, fuel_type: "Diesel", amount: 1000, recalculate: true });
    const s2 = editRequest({ id: "s2_4", scope: 2 }, { ...form, amount: "5000", grid_region: "DZ" });
    expect(s2.url).toBe("/scope2/4");
    expect(s2.payload).toMatchObject({ month: 6, electricity_kwh: 5000, grid_region: "DZ" });
  });
});
