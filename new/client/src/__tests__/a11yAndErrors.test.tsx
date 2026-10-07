import React, { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CustomDropdown from "../components/CustomDropdown";
import { linkFormLabels } from "../utils/a11yLabels";
import { apiError } from "../utils/apiError";

const OPTS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
];

function Harness({ onChange }: { onChange: (val: any) => void }) {
  const [v, setV] = useState("");
  return (
    <div className="input-group">
      <label>Region</label>
      <CustomDropdown options={OPTS} value={v} onChange={(x: any) => { setV(x); onChange(x); }} />
    </div>
  );
}

describe("BUG-107 keyboard and labels", () => {
  it("CustomDropdown is a labelled button operable by keyboard", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    const trigger = screen.getByRole("button", { name: /region/i });
    expect(trigger.getAttribute("aria-haspopup")).toBe("listbox");
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    fireEvent.keyDown(trigger, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("links bare labels to the control in their group", () => {
    const { container } = render(
      <div>
        <div className="input-group"><label>Quantity</label><input type="number" /></div>
        <div className="input-group"><label>Notes</label><textarea /></div>
      </div>,
    );
    linkFormLabels(container);
    expect(screen.getByLabelText("Quantity").tagName).toBe("INPUT");
    expect(screen.getByLabelText("Notes").tagName).toBe("TEXTAREA");
  });
});

describe("BUG-115 server messages", () => {
  it("prefers the server error text", () => {
    expect(apiError({ response: { data: { error: "Production must be >= 0" } } }, "Failed")).toBe("Production must be >= 0");
    expect(apiError({ response: { data: {} } }, "Failed to save")).toBe("Failed to save");
    expect(apiError(new Error("network"), "Failed")).toBe("Failed");
  });
});
