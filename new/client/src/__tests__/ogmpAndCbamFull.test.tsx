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

vi.mock("../components/Toast", () => ({
  useToast: () => toastMock,
}));

vi.mock("../hooks/useGwpStandard", () => ({
  useGwpStandard: () => ({ standard: "AR5" }),
}));

const apiGetMock = vi.fn();
const apiPostMock = vi.fn();
const apiDeleteMock = vi.fn();

vi.mock("../api", () => ({
  default: {
    get: (...args: any[]) => apiGetMock(...args),
    post: (...args: any[]) => apiPostMock(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: (...args: any[]) => apiDeleteMock(...args),
  },
}));

import OgmpTab from "../pages/manage-data/OgmpTab";
import { CbamSection } from "../pages/carbon-intensity/CarbonIntensitySections";

const MOCK_FACILITIES = [
  { id: 1, name: "Facility A-1", segment: "Upstream", activity: "EP", division: "Production" },
  { id: 3, name: "Facility C-3", segment: "Midstream", activity: "LNG", division: "Terminal & Export" },
];

const MOCK_CATALOG = {
  upstream: [
    {
      code: "UP-02",
      name: "Flaring (Routine, Non-Routine & Safety Flares)",
      category: "Flaring",
      default_ef_ref: "VISR / Volumetric Meter",
    },
    {
      code: "UP-11",
      name: "Equipment Leaks & Component Fugitives",
      category: "Fugitive",
      default_ef_ref: "OGI + Hi-Flow EN 15446",
    },
  ],
  mid_downstream: [
    {
      code: "MD-01",
      name: "Compressor Station Seals & Unit Blowdowns",
      category: "Fugitive",
      default_ef_ref: "Direct Seal Vent Flowmeter",
    },
  ],
  active: [],
  pathways: [
    { code: "1", title: "Pathway 1 (Coarse L4 + Annual L5)", description: "Annual site reconciliation." },
    { code: "3", title: "Pathway 3 (Facility Direct Reconciliation)", description: "Direct L4/L5 match." },
  ],
  status_flags: ["Quantified", "MI", "N/A"],
  measurement_modes: ["Instantaneous", "Annualized"],
  option_modes: ["Option 1", "Option 2"],
};

const SAMPLE_XML =
  '<?xml version="1.0" encoding="UTF-8"?><CBAM_Declaration><Quarter>Q1</Quarter><PeriodStart>2025-01-01</PeriodStart></CBAM_Declaration>';

describe("Full OGMP 2.0 Level 4/5 Workspace and EU CBAM Validation & XML Inspector", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    Object.defineProperty(window.URL, "createObjectURL", {
      writable: true,
      value: vi.fn(() => "blob:mock-cbam-url"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      writable: true,
      value: vi.fn(),
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });

    apiGetMock.mockImplementation((url: string, config?: any) => {
      if (url === "/ogmp/catalogs") return Promise.resolve({ data: MOCK_CATALOG });
      if (url === "/ogmp/entities") {
        return Promise.resolve({
          data: [
            {
              id: 10,
              facility_id: 1,
              facility_name: "Facility A-1",
              entity_name: "Demo Operator - Basin Alpha CPF",
              segment: "Upstream",
              operator_status: "operated",
              working_interest_pct: 60,
              membership_year: 2023,
              target_gold_year: 2026,
              is_nojv_material_excluded: false,
              is_member_reported_nojv: false,
            },
            {
              id: 11,
              facility_id: 3,
              facility_name: "Facility C-3",
              entity_name: "Demo JV Satellite Gathering (Minor NOJV)",
              segment: "Midstream",
              operator_status: "non_operated",
              working_interest_pct: 3.5,
              membership_year: 2024,
              target_gold_year: 2029,
              is_nojv_material_excluded: true,
              is_member_reported_nojv: true,
            },
          ],
        });
      }
      if (url === "/ogmp/targets") {
        return Promise.resolve({
          data: [
            {
              id: 1,
              reporting_entity_id: 10,
              entity_name: "Demo Operator - Basin Alpha CPF",
              target_year: 2025,
              upstream_target_pct: 0.2,
              midstream_target_pct: 0.05,
              notes: "Gold Standard Pathway 1 target",
            },
          ],
        });
      }
      if (url === "/ogmp/emission-sources") {
        return Promise.resolve({
          data: [
            {
              id: 21,
              facility_id: 1,
              facility_name: "Facility A-1",
              year: new Date().getFullYear(),
              segment: "Upstream",
              source_code: "UP-02",
              source_name: "Flaring (Routine, Non-Routine & Safety Flares)",
              ogmp_level: 4,
              status_flag: "Quantified",
              ch4_tonnes: 122.0,
              uncertainty_pct: 11.5,
              yoy_change_pct: -14.08,
              yoy_explanation: "Flare Gas Recovery Unit commissioned",
            },
          ],
        });
      }
      if (url === "/ogmp/site-measurements") {
        return Promise.resolve({
          data: [
            {
              id: 31,
              facility_id: 1,
              facility_name: "Facility A-1",
              year: new Date().getFullYear(),
              campaign_date: "2025-05-18",
              survey_type: "Aircraft / Hyperspectral Imaging",
              measurement_mode: "Annualized",
              option_mode: "Option 2",
              measured_rate_kg_hr: 40.9,
              operating_hours_year: 8760,
              annualized_tch4: 358.284,
              uncertainty_pct: 14,
              ci_low_tch4: 308.12,
              ci_high_tch4: 408.44,
            },
          ],
        });
      }
      if (url === "/ogmp/annual-reports") {
        return Promise.resolve({
          data: [
            {
              id: 41,
              facility_id: 1,
              facility_name: "Facility A-1",
              year: new Date().getFullYear(),
              reporting_level: 5,
              status: "Submitted",
              total_bottom_up_tch4: 357.5,
              total_top_down_tch4: 358.3,
              bu_uncertainty_pct: 8.9,
              bu_ci_low_tch4: 325.7,
              bu_ci_high_tch4: 389.3,
              td_uncertainty_pct: 14.0,
              td_ci_low_tch4: 308.1,
              td_ci_high_tch4: 408.5,
              ci_overlaps: true,
              variance_pct: -0.22,
              variance_flag: false,
              reconciliation_status: "Reconciled",
              l4_materiality_pct: 93.8,
              pathway_code: "1",
              measurement_mode: "Annualized",
              option_mode: "Option 2",
            },
          ],
        });
      }
      if (url === "/ogmp/implementation-plans") {
        return Promise.resolve({
          data: [
            {
              id: 51,
              facility_id: 1,
              facility_name: "Facility A-1",
              operator_status: "operated",
              base_year: 2023,
              milestone_horizon: "Y3",
              planned_year: 2026,
              target_level: 5,
              methodology_upgrade: "Operated assets achieve L4/L5 Gold Standard",
              milestone_status: "In Progress",
            },
          ],
        });
      }
      if (url === "/ogmp/portfolio-materiality") {
        return Promise.resolve({
          data: {
            total_equity_ch4_tch4: 538.9,
            included_equity_ch4_tch4: 534.4,
            excluded_equity_ch4_tch4: 4.5,
            included_coverage_pct: 99.16,
            meets_95pct_threshold: true,
            nojv_exclusion_count: 1,
            nojv_exclusions: [],
            member_reported_nojv_count: 1,
            member_reported_nojvs: [],
            entities: [],
          },
        });
      }
      if (url === "/ogmp/audit-trail") {
        return Promise.resolve({
          data: [
            {
              id: 61,
              facility_id: 1,
              entity_type: "OgmpAnnualReport",
              entity_id: "41",
              action: "RECONCILE",
              actor_name: "Demo Administrator",
              summary: "Computed Level 5 RSS 95% CI reconciliation.",
              created_at: "2026-01-15T10:00:00Z",
            },
          ],
        });
      }
      if (url === "/reports/cbam-validate") {
        const q = config?.params?.quarter || "Q1-Q4";
        return Promise.resolve({
          data: {
            ready: true,
            quarter: q,
            period_start: q === "Q1" ? "2025-01-01" : "2025-01-01",
            period_end: q === "Q1" ? "2025-03-31" : "2025-12-31",
            year: "2025",
            assurance_level: "Pre-Assurance / Internal Review",
            assurance_provider: "Internal MRV Team",
            record_count: 1,
            errors: [],
            warnings: [],
            checks: [
              {
                id: "cn_codes",
                label: "EU CN Code & Nomenclature Formatting",
                status: "pass",
                detail: "All exported goods carry valid CN codes.",
              },
            ],
            summary: {
              total_quantity_tonnes: 18500,
              total_embedded_emissions_tco2e: 32190,
              total_captured_co2_tonnes: 2450,
              total_carbon_price_paid_eur: 18.5,
              complex_goods_count: 1,
            },
            records: [
              {
                id: 101,
                facility_id: 3,
                facility_name: "Facility C-3",
                product_name: "Clean Hydrogen (Demo ATR)",
                cn_code: "2804 10 00",
                year: 2025,
                quarter: q === "Q1-Q4" ? "Q1" : q,
                quantity_tonnes: 9800,
                gross_direct_see: 4.2,
                ccs_reduction_see: 0.25,
                net_direct_see: 3.95,
                indirect_see: 0.31,
                precursor_see: 0.57,
                total_see: 4.83,
                total_embedded_tco2e: 47334,
                has_scope1_data: true,
                has_scope2_data: true,
              },
            ],
          },
        });
      }
      if (url.startsWith("/reports/cbam-export")) {
        return Promise.resolve({ data: SAMPLE_XML });
      }
      return Promise.resolve({ data: [] });
    });

    apiPostMock.mockImplementation((url: string) => {
      if (url === "/ogmp/reconcile") {
        return Promise.resolve({
          data: {
            annual_report: {
              reporting_level: 5,
              reconciliation_status: "Reconciled",
              status: "Pending",
            },
          },
        });
      }
      return Promise.resolve({ data: { id: 999 } });
    });
    apiDeleteMock.mockResolvedValue({ data: { ok: true } });
  });

  it("navigates all OGMP L4/L5 workspace sub-tabs and submits source, reconcile, and Y0–Y10 plan actions", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <OgmpTab
          ACTIVITY_LABELS={{ EP: "Exploration & Production", LNG: "LNG Terminal" }}
          ITEMS_PER_PAGE={10}
          NON_OG_ACTIVITIES={[]}
          currentPage={1}
          editingOgmpId={null}
          facilities={MOCK_FACILITIES}
          filteredOgmp={[]}
          getAvailableActivities={() => ["EP", "LNG"]}
          getAvailableDivisions={() => ["Production"]}
          handleDeleteOgmpSurvey={vi.fn()}
          handleSaveOgmpSurvey={vi.fn()}
          ogmpForm={{}}
          setCurrentPage={vi.fn()}
          setEditingOgmpId={vi.fn()}
          setOgmpForm={vi.fn()}
        />
      </MemoryRouter>,
    );

    // 1. L1-L4 Source Catalog sub-tab
    await user.click(screen.getByRole("button", { name: /L1–L4 Source Catalog/i }));
    await waitFor(() => {
      expect(apiGetMock).toHaveBeenCalledWith("/ogmp/emission-sources");
    });
    expect(screen.getAllByText(/UP-02/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/122\.00/).length).toBeGreaterThanOrEqual(2);

    await user.type(screen.getByLabelText(/Source Code \*/i), "UP-11");
    await user.type(screen.getByLabelText(/Source Name \*/i), "Equipment Leaks");
    await user.type(screen.getByLabelText(/CH₄ Emissions \(tCH₄\)/i), "45.5");
    await user.click(screen.getByRole("button", { name: /Add Source Disclosure/i }));

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith(
        "/ogmp/emission-sources",
        expect.objectContaining({
          facility_id: 1,
          source_code: "UP-11",
          ch4_tonnes: 45.5,
        }),
      );
    });

    // 2. L5 Campaigns & RSS Reconciliation sub-tab
    await user.click(screen.getByRole("button", { name: /L5 Campaigns & RSS Reconciliation/i }));
    expect(screen.getByText(/^P1$/)).toBeInTheDocument();
    expect(screen.getByText(/357\.50 t/i)).toBeInTheDocument();
    expect(screen.getByText(/^Overlap$/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Run L4\/L5 Reconciliation/i }));
    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith(
        "/ogmp/reconcile",
        expect.objectContaining({
          facility_id: 1,
          option_mode: "Option 1",
        }),
      );
    });
    expect(toastMock.success).toHaveBeenCalledWith(
      "Reconciliation complete: Level 5 (Reconciled), saved as Pending for review.",
    );

    // 3. Entities & 95% Portfolio sub-tab
    await user.click(screen.getByRole("button", { name: /Entities & 95% Portfolio/i }));
    expect(screen.getByText(/99\.2%/i)).toBeInTheDocument();
    expect(screen.getByText(/≥ 95% Materiality Met/i)).toBeInTheDocument();

    // 4. Y0-Y10 Plan & Audit sub-tab
    await user.click(screen.getByRole("button", { name: /Y0–Y10 Plan & Audit/i }));
    expect(screen.getByText(/RECONCILE/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Generate Y0–Y10 Default Plan/i }));
    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/ogmp/implementation-plans", {
        facility_id: 1,
        generate_default: true,
      });
    });

    // Regenerating over existing milestones asks first, and sends confirm only after a yes
    apiPostMock.mockRejectedValueOnce({
      response: { status: 409, data: { requires_confirmation: true, existing_count: 11, error: "x" } },
    });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValueOnce(false);
    await user.click(screen.getByRole("button", { name: /Generate Y0–Y10 Default Plan/i }));
    await waitFor(() => expect(confirmSpy).toHaveBeenCalledTimes(1));
    expect(apiPostMock).not.toHaveBeenCalledWith(
      "/ogmp/implementation-plans",
      expect.objectContaining({ confirm: true }),
    );
    apiPostMock.mockRejectedValueOnce({
      response: { status: 409, data: { requires_confirmation: true, existing_count: 11, error: "x" } },
    });
    confirmSpy.mockReturnValueOnce(true);
    await user.click(screen.getByRole("button", { name: /Generate Y0–Y10 Default Plan/i }));
    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/ogmp/implementation-plans", {
        facility_id: 1,
        generate_default: true,
        confirm: true,
      });
    });
    confirmSpy.mockRestore();

    // 5. Clicking + Add OGMP Survey from non-surveys sub-tab mounts and opens the drawer
    await user.click(screen.getByRole("button", { name: /\+ Add OGMP Survey/i }));
    expect(await screen.findByText(/Add OGMP 2\.0 Survey/i)).toBeInTheDocument();
  });

  it("filters CBAM by quarter, validates via modal, renders Gross/CCS/Net, and previews/copies XML", async () => {
    const user = userEvent.setup();
    const copySpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <CbamSection
          products={[
            {
              id: 1,
              facility_id: 3,
              product_name: "Clean Hydrogen (Demo ATR)",
              cn_code: "2804 10 00",
              year: 2025,
              month: 4,
              quarter: "Q2",
              quantity_tonnes: 9800,
              export_destination: "EU - Germany",
              specific_embedded_direct: 3.95,
              specific_embedded_indirect: 0.31,
              captured_co2_tonnes: 2450,
              carbon_price_paid_eur: 22,
            },
          ]}
          facilities={MOCK_FACILITIES}
          selectedYear="2025"
          selectedFacility="3"
        />
      </MemoryRouter>,
    );

    const quarterSelect = screen.getByRole("combobox", { name: /CBAM Reporting Quarter/i });
    await user.selectOptions(quarterSelect, "Q1");

    await user.click(screen.getByRole("button", { name: /Validate CBAM/i }));

    await waitFor(() => {
      expect(apiGetMock).toHaveBeenCalledWith("/reports/cbam-validate", {
        params: { quarter: "Q1", status: "Verified", year: "2025", facility_id: "3" },
      });
    });

    expect(await screen.findByText(/Ready for Submission/i)).toBeInTheDocument();
    expect(screen.getByText(/4\.2000/)).toBeInTheDocument();
    expect(screen.getByText(/-0\.2500/)).toBeInTheDocument();
    expect(screen.getByText(/Pre-Assurance \/ Internal Review/i)).toBeInTheDocument();

    // Switch to XML Preview tab inside modal and copy XML
    await user.click(screen.getByRole("button", { name: /XML Preview/i }));
    expect(await screen.findByText(/<CBAM_Declaration>/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Copy XML/i }));
    await waitFor(() => {
      expect(copySpy).toHaveBeenCalledWith(SAMPLE_XML);
      expect(toastMock.success).toHaveBeenCalledWith("CBAM XML copied to clipboard.");
    });
  });
});
