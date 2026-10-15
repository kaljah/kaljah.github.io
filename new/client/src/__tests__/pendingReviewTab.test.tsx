import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PendingReviewTab, { type PendingReviewTabProps } from "../pages/manage-data/PendingReviewTab";

vi.mock("../components/BatchReviewWizard", () => ({ default: () => null }));
vi.mock("../components/modals/EditEmissionModal", () => ({ default: () => null }));

const record = { id: 129, key: "1-129", scope: 1, date: "2025-01", facility_id: 1, desc: "Flaring", tco2e: 12.5 };

const props = (over: Partial<PendingReviewTabProps> = {}): PendingReviewTabProps => ({
  QUICK_REJECTION_REASONS: ["Wrong meter reading"],
  facilities: [{ id: 1, name: "Hassi Plant" }],
  fetchPendingEmissions: vi.fn(),
  filteredPendingRecords: [record],
  handleApproveAllInScope: vi.fn(),
  handleApproveSingle: vi.fn(),
  handleBatchApproveSelected: vi.fn(),
  handleConfirmReject: vi.fn(),
  handleOpenBatchRejectModal: vi.fn(),
  handleOpenRejectModal: vi.fn(),
  handleSelectAllPendingToggle: vi.fn(),
  handleToggleSelectPending: vi.fn(),
  isBatchWizardOpen: false,
  isProcessingBatch: false,
  isRefreshingPending: false,
  pendingMetrics: { totalCount: 1, count1: 1, count2: 0, count3: 0, totalTco2e: 12.5, flaggedCount: 0, cleanCount: 1, loadedCount: 1 },
  pendingQaFilter: "all",
  pendingScopeFilter: "all",
  pendingSearch: "",
  rejectionModal: { isOpen: false, isBatch: false, recordIds: [], reason: "" },
  selectedPendingImpactTco2e: 0,
  selectedPendingKeys: new Set<string>(),
  setIsBatchWizardOpen: vi.fn(),
  setPendingQaFilter: vi.fn(),
  setPendingScopeFilter: vi.fn(),
  setPendingSearch: vi.fn(),
  setRejectionModal: vi.fn(),
  setSelectedPendingKeys: vi.fn(),
  user: { id: 99, role: "admin" },
  ...over,
});

describe("PendingReviewTab (audit 2026-10-14)", () => {
  it("BUG-0055: a double click on Approve sends one approval", async () => {
    let resolve: () => void = () => {};
    const approve = vi.fn(() => new Promise<void>((r) => { resolve = r; }));
    render(<PendingReviewTab {...props({ handleApproveSingle: approve })} />);
    const button = screen.getByRole("button", { name: "Approve Record" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(approve).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(button).toBeDisabled());
    resolve();
    await waitFor(() => expect(button).not.toBeDisabled());
  });

  it("BUG-0029: the rejection form is a labelled modal dialog that Escape closes", () => {
    const setRejectionModal = vi.fn();
    render(<PendingReviewTab {...props({
      setRejectionModal,
      rejectionModal: { isOpen: true, isBatch: false, recordIds: ["1-129"], reason: "" },
    })} />);
    const dialog = screen.getByRole("dialog", { name: "Reject Emission Record" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog.contains(document.activeElement)).toBe(true);
    expect(screen.getByLabelText(/Audit Reason/)).toBeInTheDocument();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(setRejectionModal).toHaveBeenCalled();
  });
});
