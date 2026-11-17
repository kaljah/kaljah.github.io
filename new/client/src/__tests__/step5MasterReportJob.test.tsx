import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, fullName: "Demo Admin", role: "admin" },
    loading: false,
  }),
}));

vi.mock("../components/Toast", () => ({
  useToast: () => toastMock,
}));

vi.mock("../hooks/useGwpStandard", () => ({
  useGwpStandard: () => ({ standard: "AR5" }),
}));

let mockRegionsResponse: any[] = [
  { key: "national", name: "Acme Energy Group (Consolidated National)", segment: "Integrated", facility_count: 2 },
  { key: "basin_alpha", name: "Basin Alpha", segment: "Upstream", facility_count: 1 },
];

const apiGetMock = vi.fn();
const apiPostMock = vi.fn();

vi.mock("../api", () => ({
  default: {
    get: (...args: any[]) => apiGetMock(...args),
    post: (...args: any[]) => apiPostMock(...args),
  },
}));

import Reports from "../pages/Reports";

describe("Step 5: Master Report background job polling and download", () => {
  const createObjUrlSpy = vi.fn(() => "blob:mock-pdf-url");
  const revokeObjUrlSpy = vi.fn();
  const anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

  beforeEach(() => {
    vi.clearAllMocks();
    (window.URL as any).createObjectURL = createObjUrlSpy;
    (window.URL as any).revokeObjectURL = revokeObjUrlSpy;

    mockRegionsResponse = [
      { key: "national", name: "Acme Energy Group (Consolidated National)", segment: "Integrated", facility_count: 2 },
      { key: "basin_alpha", name: "Basin Alpha", segment: "Upstream", facility_count: 1 },
    ];
    let pollCount = 0;
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: [] });
      if (url === "/filters/available") return Promise.resolve({ data: { years: [2023, 2024, 2025], regions: [] } });
      if (url === "/dashboard/base-year") return Promise.resolve({ data: { year: 2020 } });
      if (url === "/emissions") return Promise.resolve({ data: { emissions: [], total: 0, pages: 1 } });
      if (url === "/reports/master-report/regions") {
        return Promise.resolve({
          data: {
            status: "success",
            regions: mockRegionsResponse,
          },
        });
      }
      if (url === "/reports/master-report/jobs/job-step5-123") {
        pollCount += 1;
        if (pollCount === 1) {
          return Promise.resolve({
            data: {
              job_id: "job-step5-123",
              status: "running",
              status_url: "/api/reports/master-report/jobs/job-step5-123",
              download_url: null,
              filename: "Demo Operator Co._regional_basin_alpha_Master_Report_2023_2025_EN.pdf",
            },
          });
        }
        return Promise.resolve({
          data: {
            job_id: "job-step5-123",
            status: "completed",
            status_url: "/api/reports/master-report/jobs/job-step5-123",
            download_url: "/api/reports/master-report/jobs/job-step5-123/download",
            filename: "Demo Operator Co._regional_basin_alpha_Master_Report_2023_2025_EN.pdf",
            sha256: "a".repeat(64),
          },
        });
      }
      if (url === "/reports/master-report/jobs/job-step5-123/download") {
        return Promise.resolve({
          data: new Uint8Array([0x25, 0x50, 0x44, 0x46]),
        });
      }
      return Promise.resolve({ data: {} });
    });

    apiPostMock.mockImplementation((url: string) => {
      if (url === "/reports/master-report") {
        return Promise.resolve({
          status: 202,
          data: {
            job_id: "job-step5-123",
            status: "queued",
            status_url: "/api/reports/master-report/jobs/job-step5-123",
            download_url: "/api/reports/master-report/jobs/job-step5-123/download",
            filename: "Demo Operator Co._regional_basin_alpha_Master_Report_2023_2025_EN.pdf",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
  });

  afterEach(() => {
    anchorClickSpy.mockClear();
  }, 15000);

  it("enqueues job via POST, polls status endpoint without blocking, and downloads PDF from download_url", async () => {
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    );

    await screen.findByText(/Basin Alpha/i, {}, { timeout: 10000 });
    const downloadBtn = await screen.findByRole("button", { name: /Download Regional Master Report/i }, { timeout: 10000 });
    await waitFor(() => expect(downloadBtn).not.toBeDisabled(), { timeout: 10000 });
    fireEvent.click(downloadBtn);

    await waitFor(
      () => {
        expect(apiPostMock).toHaveBeenCalledWith(
          "/reports/master-report",
          expect.objectContaining({ mode: "regional" })
        );
      },
      { timeout: 10000 }
    );

    await waitFor(
      () => {
        expect(apiGetMock).toHaveBeenCalledWith("/reports/master-report/jobs/job-step5-123");
        expect(apiGetMock).toHaveBeenCalledWith(
          "/reports/master-report/jobs/job-step5-123/download",
          expect.objectContaining({ responseType: "blob" })
        );
      },
      { timeout: 10000 }
    );

    await waitFor(() => {
      expect(toastMock.success).toHaveBeenCalled();
      expect(anchorClickSpy).toHaveBeenCalled();
      expect(screen.getByRole("link", { name: /Download ready PDF/i })).toHaveAttribute(
        "href",
        "/api/reports/master-report/jobs/job-step5-123/download"
      );
    });
  }, 15000);

  it("clears regions without hardcoded fallback mocks and disables download when API returns empty regions", async () => {
    mockRegionsResponse = [];
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    );

    await screen.findByText(/No reporting facilities available/i);
    const regionSelect = document.getElementById("master-region-select") as HTMLSelectElement;
    expect(regionSelect).toBeDisabled();
    expect(regionSelect.innerHTML).not.toContain("hmd");
    expect(regionSelect.innerHTML).not.toContain("hrm");
    expect(regionSelect.innerHTML).not.toContain("skikda");

    const downloadBtn = screen.getByRole("button", { name: /Download Regional Master Report/i });
    const excelBtn = screen.getByRole("button", { name: /Export Regional Inventory/i });
    expect(downloadBtn).toBeDisabled();
    expect(excelBtn).toBeDisabled();
  }, 15000);

  it("omits unsupported 20yr GWP from Master Report select and switches to national mode when national region selected", async () => {
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    );

    await screen.findByText(/Basin Alpha/i, {}, { timeout: 10000 });
    const gwpSelect = document.getElementById("master-gwp-select") as HTMLSelectElement;
    const optionValues = Array.from(gwpSelect.options).map((opt) => opt.value);
    expect(optionValues).toEqual(["AR5", "AR6", "AR4"]);
    expect(optionValues).not.toContain("20yr");

    const regionSelect = document.getElementById("master-region-select") as HTMLSelectElement;
    fireEvent.change(regionSelect, { target: { value: "national" } });

    const nationalBtn = await screen.findByRole("button", { name: /Download National Master Report/i });
    fireEvent.click(nationalBtn);

    await waitFor(
      () => {
        expect(apiPostMock).toHaveBeenCalledWith(
          "/reports/master-report",
          expect.objectContaining({ mode: "national", region: "national" })
        );
        expect(toastMock.success).toHaveBeenCalled();
      },
      { timeout: 10000 }
    );
  }, 15000);

  it("uses server Content-Disposition filename on benchmark Excel export and surfaces Blob JSON errors", async () => {
    const appendSpy = vi.spyOn(document.body, "appendChild");
    try {
      apiPostMock.mockImplementationOnce(() =>
        Promise.resolve({
          data: new Uint8Array([0x50, 0x4b, 0x03, 0x04]),
          headers: {
            "content-disposition": 'attachment; filename="Acme_Energy_Cross_Basin_Benchmark_2023_2025.xlsx"',
          },
        })
      );

      render(
        <MemoryRouter>
          <Reports />
        </MemoryRouter>
      );

      await screen.findByText(/Basin Alpha/i, {}, { timeout: 10000 });
      const excelBtn = screen.getByRole("button", { name: /Export Regional Inventory/i });
      await waitFor(() => expect(excelBtn).not.toBeDisabled(), { timeout: 10000 });
      fireEvent.click(excelBtn);

      await waitFor(() => {
        expect(toastMock.success).toHaveBeenCalled();
      });
      const createdLinks = appendSpy.mock.calls
        .map((args) => args[0] as HTMLElement)
        .filter((el) => el?.tagName === "A");
      const lastLink = createdLinks[createdLinks.length - 1] as HTMLAnchorElement;
      expect(lastLink.getAttribute("download")).toBe("Acme_Energy_Cross_Basin_Benchmark_2023_2025.xlsx");
      expect(lastLink.getAttribute("download")).not.toContain("Demo Operator Co.");

      const errBlob = new Blob([JSON.stringify({ error: "start_year cannot exceed end_year" })], {
        type: "application/json",
      });
      apiPostMock.mockImplementationOnce(() =>
        Promise.reject({
          response: { status: 400, data: errBlob },
        })
      );
      fireEvent.click(excelBtn);

      await waitFor(() => {
        expect(toastMock.error).toHaveBeenCalledWith("start_year cannot exceed end_year");
      });
    } finally {
      appendSpy.mockRestore();
    }
  }, 15000);

  it("synchronizes Master Report start and end year selectors to available filter years when 2023-2025 are absent", async () => {
    const baseGet = apiGetMock.getMockImplementation()!;
    apiGetMock.mockImplementation((url: string, ...rest: any[]) => {
      if (url === "/filters/available") return Promise.resolve({ data: { years: [2024], regions: [] } });
      return (baseGet as any)(url, ...rest);
    });

    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    );

    await screen.findByText(/Basin Alpha/i, {}, { timeout: 10000 });
    const startSelect = document.getElementById("master-start-year-select") as HTMLSelectElement;
    const endSelect = document.getElementById("master-end-year-select") as HTMLSelectElement;
    await waitFor(() => {
      expect(startSelect.value).toBe("2024");
      expect(endSelect.value).toBe("2024");
    });

    const downloadBtn = screen.getByRole("button", { name: /Download Regional Master Report/i });
    await waitFor(() => expect(downloadBtn).not.toBeDisabled(), { timeout: 10000 });
    fireEvent.click(downloadBtn);

    await waitFor(
      () => {
        expect(apiPostMock).toHaveBeenCalledWith(
          "/reports/master-report",
          expect.objectContaining({ start_year: 2024, end_year: 2024 })
        );
        expect(toastMock.success).toHaveBeenCalled();
      },
      { timeout: 10000 }
    );
  }, 15000);
});
