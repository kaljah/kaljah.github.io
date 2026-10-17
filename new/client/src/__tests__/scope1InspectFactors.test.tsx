import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Scope1Form from "../components/Scope1Form";
import api from "../api";

vi.mock("../api", () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: { id: 1, name: "Test User", role: "admin", default_facility_id: "1" } }),
}));

vi.mock("../components/Toast", () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn(), show: vi.fn() }),
}));

// 50,000 scf natural gas at 1,020 Btu/scf and 53.06 kg CO2/MMBtu = 2.70606 t CO2
const RECORD = {
  id: "s1_7", scope: 1, year: 2025, month: 3, facility_id: 1, facility_name: "Hub",
  process_type: "combustion", fuel: "Natural Gas", amount: 50000, unit: "scf",
  co2_emissions: 2.70606, ch4_emissions: 0.000051, n2o_emissions: 0.0000051, co2e_total: 2.70894,
  ef_used_co2: 53.06, ef_used_ch4: 0.001, ef_used_n2o: 0.0001, status: "Verified", factor_type: "default",
};

describe("Scope 1 calculation details", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockImplementation((url: string) => {
      const headers = { "x-total-count": "1" };
      if (url.includes("/facilities")) return Promise.resolve({ data: [{ id: 1, name: "Hub" }], headers });
      if (url.startsWith("/emissions?")) return Promise.resolve({ data: { emissions: [RECORD], total: 1 }, headers });
      return Promise.resolve({ data: [], headers });
    });
  });

  it("shows the factor applied per record unit, not the catalog factor under the record unit", async () => {
    render(<Scope1Form />);
    const inspect = await screen.findByTitle("Inspect Calculation Details");
    fireEvent.click(inspect);
    await waitFor(() => expect(screen.getByText("Carbon Dioxide Factor")).toBeInTheDocument());
    // 2.70606 t x 1000 / 50,000 scf
    expect(screen.getByText("0.054121 kg/scf")).toBeInTheDocument();
    // the stored 53.06 is kg per MMBtu: it was printed as "53.060000 kg/scf"
    expect(screen.queryByText(/53\.06\d* kg\/scf/)).toBeNull();
  });
});
