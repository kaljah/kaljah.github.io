import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuditIntegrityCheck } from "../pages/audit-trail/AuditTrailChrome";
import api from "../api";

vi.mock("../api", () => ({ default: { get: vi.fn() } }));

const base = { chain_head_hash: "a".repeat(64), checkpoint_hmac: "b".repeat(64), verified_at: "2026-10-09T00:00:00Z" };

describe("AuditIntegrityCheck", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows an intact log with the checkpoint to keep", async () => {
    (api.get as any).mockResolvedValue({ data: { ...base, status: "verified", total_records: 1200, issue_count: 0, issues: [] } });
    render(<AuditIntegrityCheck />);
    expect(await screen.findByText(/Chain Intact/i)).toBeTruthy();
    expect(await screen.findByText(/1,200/)).toBeTruthy();
    expect(screen.getByText(/Cryptographic Hash Chain Integrity/i)).toBeTruthy();
  });

  it("lists the altered entries", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        ...base, status: "tampered", total_records: 50, issue_count: 1,
        issues: [{ id: 17, problem: "content_changed", detail: "This entry was changed after it was written." }],
      },
    });
    render(<AuditIntegrityCheck />);
    expect(await screen.findByText(/Tampering Detected/i)).toBeTruthy();
    expect(await screen.findByText(/Block #17/i)).toBeTruthy();
  });
});
