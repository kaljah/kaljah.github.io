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

    let pollCount = 0;
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: [] });
      if (url === "/filters/available") return Promise.resolve({ data: { years: [2024], regions: [] } });
      if (url === "/dashboard/base-year") return Promise.resolve({ data: { year: 2020 } });
      if (url === "/emissions") return Promise.resolve({ data: { emissions: [], total: 0, pages: 1 } });
      if (url === "/reports/master-report/regions") {
        return Promise.resolve({
          data: {
            status: "success",
            regions: [
              { key: "basin_alpha", name: "Basin Alpha", segment: "Upstream", facility_count: 1 },
            ],
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
  });

  it("enqueues job via POST, polls status endpoint without blocking, and downloads PDF from download_url", async () => {
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    );

    const downloadBtn = await screen.findByRole("button", {
      name: /Download Regional Master Report/i,
    });
    fireEvent.click(downloadBtn);

    await waitFor(
      () => {
        expect(apiPostMock).toHaveBeenCalledWith(
          "/reports/master-report",
          expect.objectContaining({ mode: "regional" })
        );
      },
      { timeout: 3000 }
    );

    await waitFor(
      () => {
        expect(apiGetMock).toHaveBeenCalledWith("/reports/master-report/jobs/job-step5-123");
        expect(apiGetMock).toHaveBeenCalledWith(
          "/reports/master-report/jobs/job-step5-123/download",
          expect.objectContaining({ responseType: "blob" })
        );
      },
      { timeout: 5000 }
    );

    await waitFor(() => {
      expect(toastMock.success).toHaveBeenCalled();
      expect(anchorClickSpy).toHaveBeenCalled();
      expect(screen.getByRole("link", { name: /Download ready PDF/i })).toHaveAttribute(
        "href",
        "/api/reports/master-report/jobs/job-step5-123/download"
      );
    });
  });
});
