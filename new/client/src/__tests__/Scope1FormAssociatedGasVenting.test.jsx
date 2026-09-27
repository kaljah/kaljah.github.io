import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Scope1Form from "../components/Scope1Form";
import api from "../api";

vi.mock("../api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, name: "Test User", role: "engineer", default_facility_id: "1" },
  }),
}));

const mockToast = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  show: vi.fn(),
};

vi.mock("../components/Toast", () => ({
  useToast: () => mockToast,
}));

describe("Scope1Form Associated Gas Venting Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    api.get.mockImplementation((url) => {
      const headers = { "x-total-count": "0" };
      if (url.includes("/facilities")) {
        return Promise.resolve({
          data: [
            {
              id: 1,
              name: "Permian Production Hub",
              activity: "Exploration & Production",
              division: "Permian Division",
              field: "Midland Field",
            },
          ],
          headers,
        });
      }
      if (url.includes("/emissions")) {
        return Promise.resolve({ data: [], total: 0, headers });
      }
      if (url.includes("/custom-factors")) {
        return Promise.resolve({ data: [], headers });
      }
      if (url.includes("/sources")) {
        return Promise.resolve({ data: [], headers });
      }
      if (url.includes("/emission-factors/process-types")) {
        return Promise.resolve({ data: ["associated_gas_venting", "combustion"], headers });
      }
      return Promise.resolve({ data: [], headers });
    });

    api.post.mockResolvedValue({
      data: {
        id: 101,
        emissions: {
          ch4_emissions: 65.0,
          co2_emissions: 0.0,
          co2e_total: 1820.0,
        },
      },
    });
  });

  it("selects Associated Gas Venting, populates Tier 1 data, and submits successfully", async () => {
    render(<Scope1Form />);

    await waitFor(() => {
      expect(screen.getByText("New entry")).toBeInTheDocument();
    });

    // 1. Select Process Type: Click dropdown
    const processDropdown = screen.getByText("Stationary Combustion", { selector: ".dropdown-selected *" });
    fireEvent.click(processDropdown);

    // Find and click "Associated Gas Venting" option
    const agvOption = (await screen.findAllByText("Associated Gas Venting", { selector: "[role=option], [role=option] *" }))[0];
    fireEvent.click(agvOption);

    // Verify Associated Gas Venting form is rendered
    // the emission UI shows no API Compendium / table citations (user request)
    expect(screen.queryByText(/Compendium|Table 6-8/i)).toBeNull();
    // one tier selector: the page-level Calculation Methodology control (the form has no tier buttons)
    expect(screen.getByRole("button", { name: /Regional Default/ })).toBeInTheDocument();

    // Fill in crude oil throughput
    const spinInputs = screen.getAllByRole("spinbutton");
    const oilInput = spinInputs.find((input) => input.placeholder === "e.g. 5000");
    expect(oilInput).toBeDefined();

    fireEvent.change(oilInput, { target: { value: "10000" } });

    // Submit the entry
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalled();
    });

    const [endpoint, payload] = api.post.mock.calls[0];
    expect(endpoint).toBe("/emissions");
    expect(payload.process_type).toBe("associated_gas_venting");
    expect(payload.facility_id).toBe(1);
    expect(payload.calc_inputs.associated_gas_venting).toBeDefined();
    expect(payload.calc_inputs.associated_gas_venting.oil_production).toBe(10000);
    expect(payload.calc_inputs.associated_gas_venting.tier).toBe("tier1");
    expect(mockToast.success).toHaveBeenCalledWith("Scope 1 entry added successfully");
  });

  it("selects Tier 2 GOR Balance, fills engineering parameters, and submits payload", async () => {
    render(<Scope1Form />);

    await waitFor(() => {
      expect(screen.getByText("New entry")).toBeInTheDocument();
    });

    // Select Process
    const processDropdown = screen.getByText("Stationary Combustion", { selector: ".dropdown-selected *" });
    fireEvent.click(processDropdown);
    const agvOption = (await screen.findAllByText("Associated Gas Venting", { selector: "[role=option], [role=option] *" }))[0];
    fireEvent.click(agvOption);

    // Click Tier 2: GOR Balance
    const tier2Btn = screen.getByRole("button", { name: /GOR Balance/ });
    fireEvent.click(tier2Btn);

    // Enter GOR
    const spinInputs = screen.getAllByRole("spinbutton");
    const gorInput = spinInputs.find((input) => input.placeholder === "e.g. 800");
    expect(gorInput).toBeDefined();
    fireEvent.change(gorInput, { target: { value: "750" } });

    // Enter Oil Production
    const oilInput = spinInputs.find((input) => input.placeholder === "e.g. 500");
    expect(oilInput).toBeDefined();
    fireEvent.change(oilInput, { target: { value: "1200" } });

    // Submit
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalled();
    });

    const [endpoint, payload] = api.post.mock.calls[0];
    expect(endpoint).toBe("/emissions");
    expect(payload.process_type).toBe("associated_gas_venting");
    const agvInputs = payload.calc_inputs.associated_gas_venting;
    expect(agvInputs.tier).toBe("tier2");
    expect(agvInputs.oil_production).toBe(1200);
    expect(agvInputs.gor).toBe(750);
    expect(agvInputs.gor_unit).toBe("scf/bbl");
  });
});
