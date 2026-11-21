import React from "react";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import GasCompositionCalculator from "../components/GasCompositionCalculator";

// GB RY2022 GB-035 / GB-051: flaring keeps 96.5 % carbon to CO2 but destroys 98 % of the CH4 (Compendium 2021,
// December 2025 corrections); C7 / C8 are entered as such and N2O is not a gas component.
describe("GasCompositionCalculator flaring defaults", () => {
  afterEach(cleanup);

  it("applies 2 % CH4 slip by default and offers C7 to C10+ but not N2O", () => {
    const onApply = vi.fn();
    render(<GasCompositionCalculator isOpen onClose={() => {}} onApply={onApply} processType="flaring" />);
    const type = (name: string, value: string) =>
      fireEvent.change(document.querySelector(`input[name="${name}"]`) as HTMLInputElement, { target: { value } });
    expect(document.querySelector('input[name="N2O"]')).toBeNull();
    expect(document.querySelector('input[name="C8H18"]')).not.toBeNull();
    expect((document.querySelector('input[name="destructionEff"]') as HTMLInputElement).value).toBe("0.98");
    type("CH4", "100");
    fireEvent.click(screen.getByRole("button", { name: /calculate results/i }));
    fireEvent.click(screen.getByRole("button", { name: /apply as kg\/kg/i }));
    // pure methane: 2 % of each kg survives the flare
    expect(Number(onApply.mock.calls[0][0].ch4)).toBeCloseTo(0.02, 6);
    // 96.5 % of the carbon (12.011 / 16.04 of the mass) leaves as CO2
    expect(Number(onApply.mock.calls[0][0].co2)).toBeCloseTo((12.011 / 16.04) * 0.965 * (44.01 / 12.011), 4);
  });
});
