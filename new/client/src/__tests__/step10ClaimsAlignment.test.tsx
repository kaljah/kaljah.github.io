import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
};

const mockUser = { id: 1, fullName: "Demo Admin", role: "admin", location: "Global" };

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: false,
  }),
}));

vi.mock("../components/Toast", () => ({
  useToast: () => toastMock,
}));

vi.mock("../hooks/useGwpStandard", () => ({
  useGwpStandard: () => ({ standard: "AR5" }),
}));

const apiGetMock = vi.fn();
const apiPostMock = vi.fn();

vi.mock("../api", () => ({
  default: {
    get: (...args: any[]) => apiGetMock(...args),
    post: (...args: any[]) => apiPostMock(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

import { LayoutProvider } from "../context/LayoutContext";
import MethaneIntensityOGMP20Level from "../pages/methane-intensity/MethaneIntensityOGMP20Level";
import MethaneIntensityOGMP20Gold from "../pages/methane-intensity/MethaneIntensityOGMP20Gold";
import OgmpTab from "../pages/manage-data/OgmpTab";
import ManageData from "../pages/ManageData";
import { CbamSection } from "../pages/carbon-intensity/CarbonIntensitySections";
import Reports from "../pages/Reports";
import Emissions from "../pages/Emissions";
import UncertaintyAssessment from "../pages/UncertaintyAssessment";
import { RoleHomeBanner } from "../components/RoleHomeBanner";
import Scope1ImportWizard from "../components/Scope1ImportWizard";
import Scope3ImportWizard from "../components/Scope3ImportWizard";
import { TooltipProvider } from "../ui/Tooltip";
import { GLOSSARY_ITEMS, GlossaryHelpTip } from "../ui/HelpTip";

describe("Step 10: Claims alignment & Preview / Roadmap badges", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: [] });
      if (url === "/filters/available") return Promise.resolve({ data: { years: [2025], regions: [] } });
      if (url === "/dashboard/base-year") return Promise.resolve({ data: { year: 2020 } });
      if (url === "/emissions") return Promise.resolve({ data: { emissions: [], total: 0, pages: 1 } });
      if (url === "/reports/master-report/regions") return Promise.resolve({ data: { status: "success", regions: [] } });
      if (url.startsWith("/dashboard/uncertainty")) {
        return Promise.resolve({
          data: {
            inventory_uncertainty_pct: "5.2",
            confidence_level_pct: 95,
            coverage_factor: 2,
            total_inventory_emissions: 1000,
            categories: [
              {
                category: "Stationary Combustion",
                total_emissions: 1000,
                uncertainty_decimal: 0.052,
                uncertainty_pct: "±5.2%",
                level: "low",
                top_contributors: [],
              },
            ],
            monte_carlo: {
              mean: 1000,
              median: 998,
              std: 26,
              ci_lower: 948,
              ci_upper: 1052,
              p5: 948,
              p95: 1052,
              relative_uncertainty_95pct: 5.2,
              iterations: 2500,
              histogram: [],
              percentiles: {},
            },
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("shows Preview / Roadmap badge and development copy on OGMP 2.0 Level 4/5 reconciliation sections and tab", async () => {
    render(
      <MemoryRouter>
        <MethaneIntensityOGMP20Level
          globalThreshold={20}
          ogmpCollapsed={false}
          ogmpSurveys={[]}
          regionalData={[]}
          setOgmpCollapsed={vi.fn()}
        />
        <MethaneIntensityOGMP20Gold
          facilities={[]}
          globalThreshold={20}
          ogmpRoadmapData={[]}
          ogmpSurveys={[]}
          roadmapCollapsed={false}
          selectedBaselineYear={2023}
          selectedYear={2025}
          setRoadmapCollapsed={vi.fn()}
          setSelectedBaselineYear={vi.fn()}
        />
        <OgmpTab
          ACTIVITY_LABELS={{ EP: "Exploration & Production" }}
          ITEMS_PER_PAGE={10}
          NON_OG_ACTIVITIES={[]}
          currentPage={1}
          editingOgmpId={null}
          facilities={[]}
          filteredOgmp={[]}
          getAvailableActivities={() => []}
          getAvailableDivisions={() => []}
          handleDeleteOgmpSurvey={vi.fn()}
          handleSaveOgmpSurvey={vi.fn()}
          ogmpForm={{}}
          setCurrentPage={vi.fn()}
          setEditingOgmpId={vi.fn()}
          setOgmpForm={vi.fn()}
        />
      </MemoryRouter>,
    );

    const badges = screen.getAllByText(/Preview \/ Roadmap/i);
    expect(badges.length).toBeGreaterThanOrEqual(3);
    expect(screen.getAllByText(/preview, reconciliation logic in development/i).length).toBeGreaterThanOrEqual(3);
  });

  it("shows Preview / Roadmap badge on the Manage Data OGMP 2.0 Surveys navigation tab", async () => {
    render(
      <MemoryRouter>
        <ManageData />
      </MemoryRouter>,
    );

    const ogmpNavTab = await screen.findByTestId("manage-nav-ogmp");
    expect(ogmpNavTab).toHaveTextContent(/OGMP 2\.0 Surveys/i);
    expect(ogmpNavTab).toHaveTextContent(/Preview \/ Roadmap/i);
  });

  it("shows Preview / Roadmap badge on CBAM XML export button and Reports export menu item", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CbamSection products={[]} facilities={[]} selectedYear="2025" selectedFacility="all" />
        <Reports />
      </MemoryRouter>,
    );

    const xmlBtn = screen.getByRole("button", { name: /Export CBAM XML/i });
    expect(xmlBtn).toHaveTextContent(/Preview \/ Roadmap/i);

    const exportMenuTrigger = screen.getByRole("button", { name: /^Export$/i });
    await user.click(exportMenuTrigger);

    const cbamXmlMenuItem = await screen.findByText(/EU CBAM Declaration \(XML\)/i);
    expect(cbamXmlMenuItem.closest("[role='menuitem']") ?? cbamXmlMenuItem.parentElement).toHaveTextContent(
      /Preview \/ Roadmap/i,
    );
  });

  it("aligns UI copy for Scope 3, uncertainty, ingestion, and OGMP 2.0", async () => {
    mockUser.role = "auditor";
    try {
      render(
        <TooltipProvider>
          <LayoutProvider>
            <MemoryRouter>
              <Emissions />
              <UncertaintyAssessment />
              <RoleHomeBanner pendingCount={0} />
              <Scope1ImportWizard onClose={vi.fn()} />
              <Scope3ImportWizard onClose={vi.fn()} />
              <GlossaryHelpTip term="Monte Carlo Uncertainty" />
            </MemoryRouter>
          </LayoutProvider>
        </TooltipProvider>,
      );

      // Scope 3 -> spend-based screening
      expect(screen.getAllByText(/spend-based screening/i).length).toBeGreaterThanOrEqual(2);

      // Uncertainty -> basic error propagation (Monte Carlo planned)
      await waitFor(() => {
        expect(screen.getAllByText(/basic error propagation \(Monte Carlo planned\)/i).length).toBeGreaterThanOrEqual(2);
      });
      const mcGlossary = GLOSSARY_ITEMS.find((g) => g.term === "Monte Carlo Uncertainty");
      expect(mcGlossary?.definition).toMatch(/basic error propagation \(Monte Carlo planned\)/i);

      // Ingestion -> in-process background processing
      expect(screen.getAllByText(/in-process background processing/i).length).toBeGreaterThanOrEqual(1);
    } finally {
      mockUser.role = "admin";
    }
  });
});
