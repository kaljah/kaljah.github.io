import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserManagementSessionTab } from "../pages/user-management/UserManagementSessionTab";
import UserManagementBlock from "../pages/user-management/UserManagementBlock";
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
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

describe("Phase 2 User Management & Session Governance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Enterprise Complexity Standard in SessionTab", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        idle_timeout_minutes: 30,
        max_failed_logins: 5,
        nist_password_policy: "Enterprise Complexity Standard (min 10 chars, uppercase, lowercase, digits, symbols)",
        session_invalidation: "Cryptographic",
        total_users: 25,
        active_users: 24,
      },
    });

    render(<UserManagementSessionTab currentUserRole="it_admin" />);
    expect(await screen.findByText(/Enterprise Complexity/i)).toBeTruthy();
    expect(screen.getByText(/10\+ characters, 5 composition rules strictly enforced/i)).toBeTruthy();
  });

  it("requires typing REVOKE to confirm global session invalidation", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        idle_timeout_minutes: 30,
        max_failed_logins: 5,
        nist_password_policy: "Enterprise Complexity Standard",
        session_invalidation: "Cryptographic",
        total_users: 25,
        active_users: 24,
      },
    });

    render(<UserManagementSessionTab currentUserRole="it_admin" />);
    const revokeBtn = await screen.findByRole("button", { name: /Revoke All Active Sessions/i });
    fireEvent.click(revokeBtn);

    // Modal appears
    expect(screen.getByText(/Are you sure you want to invalidate all active sessions/i)).toBeTruthy();
    const confirmBtn = screen.getByRole("button", { name: /Confirm Global Revocation/i }) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);

    // Type incorrect text
    const input = screen.getByPlaceholderText("REVOKE");
    fireEvent.change(input, { target: { value: "NOPE" } });
    expect(confirmBtn.disabled).toBe(true);

    // Type REVOKE
    fireEvent.change(input, { target: { value: "REVOKE" } });
    expect(confirmBtn.disabled).toBe(false);

    (api.post as any).mockResolvedValue({ data: { success: true, revoked_count: 24 } });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/sessions/revoke-all");
    });
  });

  it("displays Test Account badge and Protected Account tooltips in UserManagementBlock", () => {
    const mockUsers = [
      {
        id: 1,
        fullName: "Root Administrator",
        email: "admin@ghg.com",
        role: "admin",
        status: "active",
        is_test: false,
      },
      {
        id: 20,
        fullName: "Test QA User",
        email: "test_qa@audit.test",
        role: "user",
        status: "active",
        is_test: true,
      },
    ];

    const mockS = {
      tableCard: {},
      tableToolbar: {},
      tableCardTitle: {},
      tableCardSub: {},
      tableWrap: {},
      table: {},
      th: {},
      td: {},
      emptyCell: {},
      avatar: () => ({}),
      regionPill: () => ({}),
      iconBtn: () => ({}),
    };

    render(
      <UserManagementBlock
        S={mockS}
        filteredUsers={mockUsers as any}
        getRoleMeta={() => ({ label: "Admin", color: "#000", bg: "#fff", border: "#ccc" })}
        handleDelete={vi.fn()}
        handleOpenModal={vi.fn()}
        handleOpenResetPassword={vi.fn()}
        hoveredRow={null}
        isITOnly={false}
        loading={false}
        setHoveredRow={vi.fn()}
        totalUsers={2}
        currentUserRole="it_admin"
        currentUserEmail="itadmin@sonatrach.dz"
        currentUserId={3}
      />
    );

    // Verify Test Account badge renders
    expect(screen.getByText("Test Account")).toBeTruthy();

    // Verify protected account title exists
    const protectedSpan = screen.getAllByTitle(/Protected account/i);
    expect(protectedSpan.length).toBeGreaterThan(0);
  });
});
