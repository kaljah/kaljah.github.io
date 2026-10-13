import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LdarTab } from "../pages/manage-data/LdarTab";
import api from "../api";

vi.mock("../api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../components/Toast", () => ({
  useToast: () => ({
    show: vi.fn(),
  }),
}));

describe("LdarTab segmented controls and filter buttons", () => {
  const mockFacilities = [
    { id: 1, name: "Al-Noor Central Station", activity: "EP", division: "Production", region_identifier: "North" },
    { id: 2, name: "Basra South Terminal", activity: "RPC", division: "Refining", region_identifier: "South" },
  ];

  const mockSurveys = [
    {
      id: 101,
      facility_id: 1,
      facility_name: "Al-Noor Central Station",
      survey_method: "Method 21",
      survey_date: "2026-05-10",
      screening_value_ppm: 2500,
      leak_status: "Leaking",
      leaking_hours: 120,
      notes: "Flange packing leak",
    },
    {
      id: 102,
      facility_id: 1,
      facility_name: "Al-Noor Central Station",
      survey_method: "OGI",
      survey_date: "2026-05-12",
      screening_value_ppm: 0,
      leak_status: "Non-leaking",
      leaking_hours: 0,
      notes: "Clean scan",
    },
    {
      id: 103,
      facility_id: 2,
      facility_name: "Basra South Terminal",
      survey_method: "Acoustic",
      survey_date: "2026-05-15",
      screening_value_ppm: 80,
      leak_status: "Repaired",
      repair_date: "2026-05-16",
      leaking_hours: 24,
      notes: "Re-torqued bolts",
    },
  ];

  const mockComponents = [
    {
      id: 201,
      facility_id: 1,
      equipment_type: "Valves",
      component_type: "Gate Valve",
      service_type: "Gas",
      quantity: 12,
      operating_hours: 8760,
      status: "Active",
    },
    {
      id: 202,
      facility_id: 2,
      equipment_type: "Pumps",
      component_type: "Centrifugal Pump",
      service_type: "Light Liquid",
      quantity: 4,
      operating_hours: 4380,
      status: "Active",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockImplementation((url: string) => {
      if (url === "/ldar/surveys") {
        return Promise.resolve({ data: { surveys: mockSurveys } });
      }
      if (url === "/ldar/components") {
        return Promise.resolve({ data: { components: mockComponents } });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it("renders segmented subtab switcher and displays surveys by default", async () => {
    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText(/Surveys & Repairs/)).toBeInTheDocument();
      expect(screen.getByText(/Component Inventory/)).toBeInTheDocument();
    });

    // Check segmented status filter buttons
    expect(screen.getByRole("button", { name: /All Statuses/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Leaking/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Repaired/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Non-leaking/i })).toBeInTheDocument();

    // Check table rows
    expect(screen.getAllByText("Al-Noor Central Station").length).toBeGreaterThan(0);
    expect(screen.getByText("2,500 ppm")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mark Repaired/i })).toBeInTheDocument();
  });

  it("filters surveys by status when segmented status pill is clicked", async () => {
    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText("2,500 ppm")).toBeInTheDocument();
    });

    // Click Leaking filter button
    const leakingPill = screen.getByRole("button", { name: /^Leaking/i });
    await userEvent.click(leakingPill);

    // Only leaking survey should be in the table
    expect(screen.getByText("2,500 ppm")).toBeInTheDocument();
    expect(screen.queryByText("2026-05-12")).not.toBeInTheDocument();
    expect(screen.queryByText("2026-05-15")).not.toBeInTheDocument();

    // Click Reset button to return to all
    const resetBtn = screen.getByRole("button", { name: /Reset/i });
    await userEvent.click(resetBtn);

    expect(screen.getByText("2026-05-12")).toBeInTheDocument();
    expect(screen.getByText("2026-05-15")).toBeInTheDocument();
  });

  it("switches to Component Inventory tab and renders equipment filters", async () => {
    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText(/Component Inventory/)).toBeInTheDocument();
    });

    const compTabBtn = screen.getByRole("button", { name: /Component Inventory/i });
    await userEvent.click(compTabBtn);

    // Should display Equipment segmented filter pills
    expect(screen.getByRole("button", { name: /All Equipment/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Valves$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Pumps$/i })).toBeInTheDocument();

    // Should display components
    expect(screen.getByText("Gate Valve")).toBeInTheDocument();
    expect(screen.getByText("Centrifugal Pump")).toBeInTheDocument();

    // Filter by Valves
    await userEvent.click(screen.getByRole("button", { name: /^Valves$/i }));
    expect(screen.getByText("Gate Valve")).toBeInTheDocument();
    expect(screen.queryByText("Centrifugal Pump")).not.toBeInTheDocument();
  });

  it("supports component selection and bulk updating", async () => {
    (api.post as any).mockResolvedValue({ data: { updated_count: 2 } });

    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText(/Component Inventory/)).toBeInTheDocument();
    });

    // Switch to Component Inventory
    await userEvent.click(screen.getByRole("button", { name: /Component Inventory/i }));

    // Select all components checkbox
    const selectAllCheckbox = screen.getByRole("checkbox", { name: /Select all components/i });
    expect(selectAllCheckbox).toBeInTheDocument();
    await userEvent.click(selectAllCheckbox);

    // Bulk action bar should appear
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Component bulk actions/i })).toBeInTheDocument();
      expect(screen.getByText(/2 component\(s\) selected/i)).toBeInTheDocument();
    });

    // Open Bulk Update Modal
    const bulkUpdateBtn = screen.getByRole("button", { name: /Bulk Update/i });
    await userEvent.click(bulkUpdateBtn);

    expect(screen.getByRole("heading", { name: /Bulk Update Components/i })).toBeInTheDocument();

    // Select Broken status in bulk modal
    const statusSelect = screen.getByRole("combobox", { name: /^Status$/i });
    await userEvent.selectOptions(statusSelect, "Broken");

    // Click Apply Bulk Update
    const applyBtn = screen.getByRole("button", { name: /Apply Bulk Update/i });
    await userEvent.click(applyBtn);

    expect(api.post).toHaveBeenCalledWith(
      "/ldar/components/bulk-update",
      expect.objectContaining({
        ids: expect.arrayContaining([201, 202]),
        status: "Broken",
      })
    );
  });

  it("supports survey selection and bulk repair", async () => {
    (api.post as any).mockResolvedValue({ data: { updated_count: 1 } });

    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText("2,500 ppm")).toBeInTheDocument();
    });

    // Select individual survey checkbox
    const surveyCheckbox = screen.getByRole("checkbox", { name: /Select survey 101/i });
    await userEvent.click(surveyCheckbox);

    // Bulk action bar appears
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Survey bulk actions/i })).toBeInTheDocument();
      expect(screen.getByText(/1 survey\(s\) selected/i)).toBeInTheDocument();
    });

    // Open Bulk Repair modal
    const bulkRepairBtn = screen.getByRole("button", { name: /Bulk Mark Repaired \/ Update/i });
    await userEvent.click(bulkRepairBtn);

    expect(screen.getByRole("heading", { name: /Bulk Update Surveys/i })).toBeInTheDocument();

    // Submit bulk repair
    const applyBtn = screen.getByRole("button", { name: /Apply Bulk Update/i });
    await userEvent.click(applyBtn);

    expect(api.post).toHaveBeenCalledWith(
      "/ldar/surveys/bulk-update",
      expect.objectContaining({
        ids: [101],
        leak_status: "Repaired",
      })
    );
  });

  it("allows adding a broken component with status 'Broken'", async () => {
    (api.post as any).mockResolvedValue({ data: { component: { id: 999, status: "Broken" } } });

    render(<LdarTab facilities={mockFacilities} isPrivileged={true} />);

    await waitFor(() => {
      expect(screen.getByText(/Component Inventory/)).toBeInTheDocument();
    });

    // Switch to Component Inventory
    await userEvent.click(screen.getByRole("button", { name: /Component Inventory/i }));

    // Click Add Component button
    const addCompBtn = screen.getByRole("button", { name: /Add Component/i });
    await userEvent.click(addCompBtn);

    expect(screen.getByRole("heading", { name: /Add Component to Inventory/i })).toBeInTheDocument();

    // Find and select facility
    const facilitySelect = screen.getByRole("combobox", { name: /^Facility$/i });
    await userEvent.selectOptions(facilitySelect, "1");

    // Change status to Broken
    const statusSelect = screen.getByRole("combobox", { name: /^Status$/i });
    await userEvent.selectOptions(statusSelect, "Broken");

    // Click Save Component
    const saveBtn = screen.getByRole("button", { name: /Save Component/i });
    await userEvent.click(saveBtn);

    expect(api.post).toHaveBeenCalledWith(
      "/ldar/components",
      expect.objectContaining({
        facility_id: 1,
        status: "Broken",
      })
    );
  });
});
