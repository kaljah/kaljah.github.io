import React from "react";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import OtherSourcesForm from "../components/scope1/OtherSourcesForm";

// GB RY2022 GB-045: fire suppression, wastewater, HFC and SF6 have a Scope 1 entry form; the record's activity
// (amount / unit) follows the method input the server reads.
describe("OtherSourcesForm", () => {
  afterEach(cleanup);

  it("sets the wastewater method default and sends the flow as the record's activity", () => {
    const onChange = vi.fn();
    const { container } = render(<OtherSourcesForm data={{ process_type: "wastewater" }} onChange={onChange} />);
    expect(onChange).toHaveBeenCalledWith("wastewater_method", "aerobic");
    const inputs = container.querySelectorAll('input[type="number"]');
    fireEvent.change(inputs[0], { target: { value: "1000" } }); // the flow is the first number field
    expect(onChange).toHaveBeenCalledWith("flow", "1000");
    expect(onChange).toHaveBeenCalledWith("amount", "1000");
  });

  it("offers the fire suppression agents and the released mass", () => {
    const onChange = vi.fn();
    const { container } = render(<OtherSourcesForm data={{ process_type: "fire_suppression" }} onChange={onChange} />);
    expect(onChange).toHaveBeenCalledWith("unit", "kg");
    const options = Array.from(container.querySelectorAll("option")).map((o) => o.getAttribute("value"));
    expect(options).toContain("co2");
    expect(options).toContain("hfc_227ea");
  });

  it("uses the unit count as the activity of the HFC charge method", () => {
    const onChange = vi.fn();
    const { container } = render(
      <OtherSourcesForm data={{ process_type: "refrigerant", refrigerant_method: "charge" }} onChange={onChange} />,
    );
    const inputs = container.querySelectorAll('input[type="number"]');
    fireEvent.change(inputs[0], { target: { value: "4" } }); // number of units
    expect(onChange).toHaveBeenCalledWith("equipment_count", "4");
    expect(onChange).toHaveBeenCalledWith("amount", "4");
    expect(onChange).toHaveBeenCalledWith("unit", "units");
  });
});
