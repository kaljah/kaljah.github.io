import type { User } from "../types/auth";

// Role-based access rules. These reproduce the guards that used to live in App.jsx
// (NonITRoute, ITRoute, SuperuserRoute, AuditRoute) exactly.
export const IT_ROLES = ["it_admin", "it_manager", "it"] as const;

export type AccessRule = "nonIT" | "it" | "superuser" | "audit";

export const isIT = (user?: User | null): boolean =>
  Boolean(user?.role && (IT_ROLES as readonly string[]).includes(user.role));

export const ACCESS: Record<AccessRule, (user?: User | null) => boolean> = {
  // everyone except the IT roles (they are redirected to /user-management)
  nonIT: (user) => Boolean(user) && !isIT(user),
  it: (user) => isIT(user),
  superuser: (user) => Boolean(user?.role && ["admin", "superuser"].includes(user.role)),
  audit: (user) => Boolean(user?.role && ["admin", "superuser", "it_admin", "it_manager"].includes(user.role)),
};

/** Where a signed-in user is sent when the rule denies them. */
export const deniedRedirect = (user?: User | null, rule?: AccessRule): string =>
  rule === "nonIT" && isIT(user) ? "/user-management" : "/";

export const canAccess = (user?: User | null, rule?: AccessRule): boolean =>
  Boolean(user && rule && ACCESS[rule]?.(user));
