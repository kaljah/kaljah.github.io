// Role-based access rules. These reproduce the guards that used to live in App.jsx
// (NonITRoute, ITRoute, SuperuserRoute, AuditRoute) exactly.
export const IT_ROLES = ["it_admin", "it_manager", "it"];

export const isIT = (user) => IT_ROLES.includes(user?.role);

export const ACCESS = {
  // everyone except the IT roles (they are redirected to /user-management)
  nonIT: (user) => Boolean(user) && !isIT(user),
  it: (user) => isIT(user),
  superuser: (user) => ["admin", "superuser"].includes(user?.role),
  audit: (user) => ["admin", "superuser", "it_admin", "it_manager"].includes(user?.role),
};

/** Where a signed-in user is sent when the rule denies them. */
export const deniedRedirect = (user, rule) => (rule === "nonIT" && isIT(user) ? "/user-management" : "/");

export const canAccess = (user, rule) => Boolean(user) && ACCESS[rule](user);
