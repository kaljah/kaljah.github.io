import React from "react";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import GasCompositionCalculator from "../components/GasCompositionCalculator";

// The server refuses a gas analysis that does not total 100 % (99.5 to 100.5 is rounding):
// the calculator must say so before the analysis is applied to a record.
function setup() {
  const onApply = vi.fn();
  render(<GasCompositionCalculator isOpen onClose={() => {}} onApply={onApply} />);
  const type = (name: string, value: string) => {
    const input = document.querySelector(`input[name="${name}"]`) as HTMLInputElement;
    fireEvent.change(input, { target: { value } });
  };
  const calculate = () => screen.getByRole("button", { name: /calculate results/i }) as HTMLButtonElement;
  return { type, calculate, onApply };
}

describe("GasCompositionCalculator total", () => {
  afterEach(cleanup);

  it("blocks the calculation and explains it while the analysis is short of 100 %", () => {
    const { type, calculate } = setup();
    type("CH4", "90");
    type("C2H6", "5");
    expect(calculate().disabled).toBe(true);
    expect(screen.getByRole("alert").textContent).toMatch(/must total 100/i);
  });

  it("blocks an analysis over 100.5 %", () => {
    const { type, calculate } = setup();
    type("CH4", "95");
    type("C2H6", "6");
    expect(calculate().disabled).toBe(true);
  });

  it.each([
    ["90", "10"],
    ["90", "9.5"],
    ["90", "10.5"],
  ])("allows CH4 %s + N2 %s (100 %% within the 99.5 / 100.5 rounding)", (ch4, n2) => {
    const { type, calculate } = setup();
    type("CH4", ch4);
    type("N2", n2);
    expect(calculate().disabled).toBe(false);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
