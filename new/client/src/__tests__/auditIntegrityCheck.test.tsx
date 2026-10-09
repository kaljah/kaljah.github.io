import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuditIntegrityCheck } from "../pages/audit-trail/AuditTrailChrome";
import api from "../api";

vi.mock("../api", () => ({ default: { get: vi.fn() } }));

const base = { chain_head_hash: "a".repeat(64), checkpoint_hmac: "b".repeat(64), verified_at: "2026-10-09T00:00:00Z" };

// Pilot check 2026-10-09 (F12): the verdict comes from the server's hash-chain check, never assumed.
describe("AuditIntegrityCheck", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows an intact log with the checkpoint to keep", async () => {
    (api.get as any).mockResolvedValue({ data: { ...base, status: "verified", total_records: 1200, issue_count: 0, issues: [] } });
    render(<AuditIntegrityCheck />);
    fireEvent.click(screen.getByRole("button", { name: /Verify integrity/ }));
    expect(await screen.findByText(/Log intact: 1,200 entries verified/)).toBeTruthy();
    expect(screen.getByText(new RegExp(base.chain_head_hash))).toBeTruthy();
  });

  it("lists the altered entries", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        ...base, status: "tampered", total_records: 50, issue_count: 1,
        issues: [{ id: 17, problem: "content_changed", detail: "This entry was changed after it was written." }],
      },
    });
    render(<AuditIntegrityCheck />);
    fireEvent.click(screen.getByRole("button", { name: /Verify integrity/ }));
    expect(await screen.findByText(/Log altered: 1 problem in 50 entries/)).toBeTruthy();
    expect(screen.getByText(/Entry #17: This entry was changed after it was written./)).toBeTruthy();
  });
});
