import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { RoleHomeBanner } from "../components/RoleHomeBanner";

// Mock auth context
let mockUser: { id: number; fullName: string; role: string } | null = null;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: false,
  }),
}));

describe("Part 6: Information Architecture & Decluttering", () => {
  it("6.7 Role-based Home: Operator sees Data Entry console and my drafts", () => {
    mockUser = { id: 1, fullName: "Field Operator", role: "user" };
    render(
      <MemoryRouter>
        <RoleHomeBanner pendingCount={0} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Operator Data Entry Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Enter Emissions Data/i)).toBeInTheDocument();
    expect(screen.getByText(/My Drafts & Submissions/i)).toBeInTheDocument();
  });

  it("6.7 Role-based Home: Reviewer/Admin sees Compliance Review Desk with pending count", () => {
    mockUser = { id: 2, fullName: "Admin Lead", role: "admin" };
    render(
      <MemoryRouter>
        <RoleHomeBanner pendingCount={5} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Compliance Review Desk/i)).toBeInTheDocument();
    expect(screen.getByText(/5 pending/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Approval Queue/i)).toBeInTheDocument();
    expect(screen.getByText(/QA\/QC Diagnostics/i)).toBeInTheDocument();
  });

  it("6.7 Role-based Home: Auditor sees Independent Assurance & Audit Portal", () => {
    mockUser = { id: 3, fullName: "ISO Auditor", role: "auditor" };
    render(
      <MemoryRouter>
        <RoleHomeBanner pendingCount={0} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Independent Assurance & Audit Portal/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Audit Trail & Integrity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Uncertainty Assessment/i })).toBeInTheDocument();
  });

  it("6.7 Role-based Home: IT Manager sees IT Administration & Security Console", () => {
    mockUser = { id: 4, fullName: "IT Administrator", role: "it_admin" };
    render(
      <MemoryRouter>
        <RoleHomeBanner pendingCount={0} />
      </MemoryRouter>
    );

    expect(screen.getByText(/IT Administration & Security Console/i)).toBeInTheDocument();
    expect(screen.getByText(/User Management/i)).toBeInTheDocument();
    expect(screen.getByText(/Audit Log & Security Trail/i)).toBeInTheDocument();
  });
});
