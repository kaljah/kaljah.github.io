import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ACCESS, canAccess, deniedRedirect } from "../access";
import { NAV_GROUPS, ROUTES, findRoute } from "../routes.config";
import RequireRole from "../RequireRole";

let mockUser = null;
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ user: mockUser, loading: false }),
}));

const ROLES = ["user", "superuser", "admin", "it", "it_admin", "it_manager"];

// What each role may open. This mirrors the guards that existed in App.jsx before the route config
// (NonITRoute, ITRoute, SuperuserRoute, AuditRoute); any change here is a permission change.
const EXPECTED = {
  nonIT: { user: true, superuser: true, admin: true, it: false, it_admin: false, it_manager: false },
  it: { user: false, superuser: false, admin: false, it: true, it_admin: true, it_manager: true },
  superuser: { user: false, superuser: true, admin: true, it: false, it_admin: false, it_manager: false },
  audit: { user: false, superuser: true, admin: true, it: false, it_admin: true, it_manager: true },
};

describe("access rules", () => {
  for (const [rule, byRole] of Object.entries(EXPECTED)) {
    for (const role of ROLES) {
      it(`${rule}: ${role} ${byRole[role] ? "may" : "may not"} access`, () => {
        expect(ACCESS[rule]({ role })).toBe(byRole[role]);
      });
    }
  }

  it("denies everything when signed out", () => {
    for (const rule of Object.keys(ACCESS)) expect(canAccess(null, rule)).toBe(false);
  });

  it("sends IT roles to user management and everyone else home", () => {
    expect(deniedRedirect({ role: "it_admin" }, "nonIT")).toBe("/user-management");
    expect(deniedRedirect({ role: "user" }, "it")).toBe("/");
    expect(deniedRedirect({ role: "user" }, "superuser")).toBe("/");
    expect(deniedRedirect({ role: "it" }, "audit")).toBe("/");
  });
});

describe("route config", () => {
  it("keeps every public path unchanged", () => {
    expect(ROUTES.map((r) => r.path).sort()).toEqual(
      [
        "/",
        "/audit-trail",
        "/carbon-intensity",
        "/emissions",
        "/manage-data",
        "/methane-explorer",
        "/methane-intensity",
        "/qa-dashboard",
        "/reference-data",
        "/reports",
        "/sbti",
        "/settings",
        "/uncertainty",
        "/user-management",
      ].sort(),
    );
  });

  it("assigns the old guard to each page", () => {
    const rule = (path) => findRoute(path).access;
    expect(rule("/qa-dashboard")).toBe("superuser");
    expect(rule("/audit-trail")).toBe("audit");
    expect(rule("/user-management")).toBe("it");
    for (const p of ["/", "/emissions", "/manage-data", "/reports", "/settings", "/sbti", "/uncertainty"]) {
      expect(rule(p)).toBe("nonIT");
    }
  });

  it("puts every grouped route in a known nav group, and only Settings is pinned", () => {
    for (const r of ROUTES) {
      if (r.group !== null) expect(NAV_GROUPS).toContain(r.group);
    }
    expect(ROUTES.filter((r) => r.group === null).map((r) => r.path)).toEqual(["/settings"]);
  });

  it("resolves the /dashboard alias and trailing slashes", () => {
    expect(findRoute("/dashboard").path).toBe("/");
    expect(findRoute("/reports/").path).toBe("/reports");
    expect(findRoute("/nope")).toBeUndefined();
  });
});

describe("RequireRole", () => {
  const renderAt = (rule, role) => {
    mockUser = role ? { role } : null;
    return render(
      <MemoryRouter initialEntries={["/target"]}>
        <Routes>
          <Route
            path="/target"
            element={
              <RequireRole rule={rule}>
                <p>secret</p>
              </RequireRole>
            }
          />
          <Route path="/" element={<p>home</p>} />
          <Route path="/login" element={<p>login page</p>} />
          <Route path="/user-management" element={<p>user mgmt</p>} />
        </Routes>
      </MemoryRouter>,
    );
  };

  it("sends signed-out visitors to /login", () => {
    renderAt("nonIT", null);
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("renders the page for an allowed role", () => {
    renderAt("superuser", "admin");
    expect(screen.getByText("secret")).toBeInTheDocument();
  });

  it("redirects IT roles away from nonIT pages to user management", () => {
    renderAt("nonIT", "it_manager");
    expect(screen.getByText("user mgmt")).toBeInTheDocument();
  });

  it("redirects a plain user away from admin pages to home", () => {
    renderAt("superuser", "user");
    expect(screen.getByText("home")).toBeInTheDocument();
  });
});
