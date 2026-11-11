import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SilentDefaultBanner, FactorLineageModal, FactorLineageItem } from "../components/common";

const MOCK_FACTOR: FactorLineageItem = {
  id: "SCP2-004",
  parameter_name: "Default Steam Boiler Efficiency",
  value: 0.92,
  unit: "fraction",
  basis: "92% boiler efficiency",
  source_document: "API Compendium (2021)",
  edition_year: "4th Edition (November 2021)",
  table_or_equation_ref: "Section 8.1.5 & Exhibit 8.3, pp. 8-17 to 8-19",
  verbatim_citation: "Assuming a 92% boiler efficiency reduced by 10% for steam transport losses gives an 82% net efficiency.",
  is_user_overridable: true,
  is_silent_default: true,
  warning_flag: "CAUTION_ASSUMPTION",
};

describe("SilentDefaultBanner component", () => {
  it("renders warning banner when isSilentDefault is true", () => {
    const onInspect = vi.fn();
    render(
      <SilentDefaultBanner
        factorId="SCP2-004"
        parameterName="Boiler Efficiency"
        defaultValue={0.82}
        defaultUnit="fraction"
        sourceCitation="API Compendium (2021) Exhibit 8.3"
        onInspect={onInspect}
        isSilentDefault={true}
      />
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Silent Default Applied/)).toBeInTheDocument();
    expect(screen.getByText(/SCP2-004/)).toBeInTheDocument();
    expect(screen.getByText(/API Compendium \(2021\) Exhibit 8.3/)).toBeInTheDocument();

    const btn = screen.getByRole("button", { name: /Inspect Provenance & Override/i });
    fireEvent.click(btn);
    expect(onInspect).toHaveBeenCalledTimes(1);
  });

  it("does not render when isSilentDefault is false", () => {
    const { container } = render(
      <SilentDefaultBanner
        factorId="SCP2-004"
        parameterName="Boiler Efficiency"
        defaultValue={0.82}
        sourceCitation="API Compendium"
        onInspect={vi.fn()}
        isSilentDefault={false}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("FactorLineageModal component", () => {
  it("displays verbatim citation and allows user override input", () => {
    const onClose = vi.fn();
    const onApply = vi.fn();

    render(
      <FactorLineageModal
        isOpen={true}
        onClose={onClose}
        factors={[MOCK_FACTOR]}
        onApplyOverride={onApply}
      />
    );

    expect(screen.getByText("Default Steam Boiler Efficiency")).toBeInTheDocument();
    expect(
      screen.getByText(/Assuming a 92% boiler efficiency reduced by 10% for steam transport losses gives an 82% net efficiency./)
    ).toBeInTheDocument();
    expect(screen.getByText("Section 8.1.5 & Exhibit 8.3, pp. 8-17 to 8-19")).toBeInTheDocument();

    // Check override input
    const input = screen.getByPlaceholderText("Default: 0.92");
    fireEvent.change(input, { target: { value: "0.85" } });

    const saveBtn = screen.getByRole("button", { name: /Save & Apply Overrides/i });
    fireEvent.click(saveBtn);

    expect(onApply).toHaveBeenCalledWith({
      "SCP2-004": {
        value: 0.85,
        justification: "Facility-specific engineering override",
      },
    });
  });
});
