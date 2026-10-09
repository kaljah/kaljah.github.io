import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ImportWizard } from "../components/import-wizard/ImportWizard";
import api from "../api";

vi.mock("../api", () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

vi.mock("../components/Toast", () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn(), show: vi.fn() }),
}));

// Pilot check 2026-10-09 (F6): the decimal format is chosen per file and sent with the check and the import.
describe("ImportWizard decimal format", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockResolvedValue({ data: [] });
    // a complete "Check file" answer (the panel shows these figures)
    (api.post as any).mockResolvedValue({
      data: {
        preview: {
          rows: 1, checked: 1, checked_ok: 1, checked_skipped: 0, estimated_ok: 1, estimated_skipped: 0, is_estimate: false,
          example_rows: 0, period: { from: "2025-05", to: "2025-05", months: 1, unreadable_rows: 0 },
          facilities: [], unknown_facility_rows: 0, processes: [], unknown_process_rows: 0, scope2_rows: 0,
          columns: { total: 0, headers: [], matched: [], by_name: [] },
        },
        skipped_groups: [],
      },
    });
  });

  const renderWizard = () =>
    render(
      <ImportWizard
        title="Import"
        fieldGroupsFor={() => []}
        scopeFor={() => "1"}
        regionAccess={false}
        checkBeforeImport
        onClose={() => {}}
      />,
    );

  // the wizard is a dialog (rendered in a portal), so the input is looked up in the document
  const pickFile = () => {
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["x"], "data.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    fireEvent.change(input, { target: { files: [file] } });
  };

  it("refuses a file until the decimal format is chosen", () => {
    renderWizard();
    pickFile();
    expect(screen.getByText("Choose how decimals are written in the file first.")).toBeTruthy();
    expect(api.post).not.toHaveBeenCalled();
  });

  it("sends the chosen decimal format with the file check", async () => {
    renderWizard();
    fireEvent.click(screen.getByRole("radio", { name: /Decimal comma/ }));
    pickFile();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [url, form] = (api.post as any).mock.calls[0];
    expect(url).toBe("/emissions/upload/check");
    expect((form as FormData).get("decimal_mark")).toBe("comma");
  });
});
