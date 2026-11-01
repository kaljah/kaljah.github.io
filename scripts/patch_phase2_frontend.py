import os

# 1. Patch UserManagement.tsx
um_path = 'new/client/src/pages/UserManagement.tsx'
with open(um_path, 'r', encoding='utf-8') as f:
    um_content = f.read()

# Add AlertTriangle to lucide-react imports if not there
if 'AlertTriangle' not in um_content:
    um_content = um_content.replace('from "lucide-react";', ', AlertTriangle } from "lucide-react";')
    # also handle any other style import
    if 'AlertTriangle } from "lucide-react";' not in um_content:
        um_content = um_content.replace('import { Globe, Plus,', 'import { AlertTriangle, Globe, Plus,')

# Add high admin ratio logic and warning banner
old_stats_block = '''          {/* ── Stats Row ── */}
          <div style={S.statsRow}>'''

new_stats_block = '''          {/* High Administrative Ratio Warning (2.2 Audit Remediation) */}
          {(adminCount > 5 || (totalUsers > 0 && adminCount / totalUsers > 0.2)) && (
            <div
              id="um-high-admin-warning"
              className="mb-4 rounded-xl border border-amber-300 bg-amber-50/90 p-4 text-amber-900 flex items-start gap-3 shadow-xs"
            >
              <AlertTriangle className="size-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1 text-xs">
                <span className="font-bold text-sm text-amber-950">
                  {t("High Administrative Privileges Concentration ({{count}} of {{total}} accounts)", {
                    count: adminCount,
                    total: totalUsers,
                  })}
                </span>
                <p className="m-0 leading-relaxed text-amber-800">
                  {t(
                    "{{pct}}% of user accounts hold Administrator or Superuser roles. In accordance with the Principle of Least Privilege and ISO 27001 access control guidelines, review whether test or non-essential accounts can be de-escalated to standard operator roles.",
                    { pct: Math.round((adminCount / Math.max(1, totalUsers)) * 100) }
                  )}
                </p>
              </div>
            </div>
          )}

          {/* ── Stats Row ── */}
          <div style={S.statsRow}>'''

assert old_stats_block in um_content, "old_stats_block not found in UserManagement.tsx"
um_content = um_content.replace(old_stats_block, new_stats_block)

# Pass currentUserEmail & currentUserId to UserManagementBlock
old_block_props = '''            currentUserRole={user?.role}
          />'''
new_block_props = '''            currentUserRole={user?.role}
            currentUserEmail={user?.email}
            currentUserId={user?.id}
          />'''

assert old_block_props in um_content, "old_block_props not found in UserManagement.tsx"
um_content = um_content.replace(old_block_props, new_block_props)

with open(um_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(um_content)
print("Patched UserManagement.tsx successfully")


# 2. Patch UserManagementBlock.tsx
umb_path = 'new/client/src/pages/user-management/UserManagementBlock.tsx'
with open(umb_path, 'r', encoding='utf-8') as f:
    umb_content = f.read()

# Update props interface
old_interface = '''  totalUsers: number;
  currentUserRole?: string;
}'''

new_interface = '''  totalUsers: number;
  currentUserRole?: string;
  currentUserEmail?: string;
  currentUserId?: number | string;
}'''

assert old_interface in umb_content, "old_interface not found in UserManagementBlock.tsx"
umb_content = umb_content.replace(old_interface, new_interface)

# Update component destructuring
old_destruct = '''  totalUsers,
  currentUserRole,
}) => ('''

new_destruct = '''  totalUsers,
  currentUserRole,
  currentUserEmail,
  currentUserId,
}) => ('''

assert old_destruct in umb_content, "old_destruct not found in UserManagementBlock.tsx"
umb_content = umb_content.replace(old_destruct, new_destruct)

# Update row variables (isProtected, isTestAccount, isSelf, isRootAdmin)
old_protected = '''              const isHovered = hoveredRow === u.id;
              const isProtected =
                Boolean(currentUserRole && ["it_admin", "it"].includes(currentUserRole)) &&
                Boolean(u.role && ["admin", "superuser", "it_manager"].includes(u.role));'''

new_protected = '''              const isHovered = hoveredRow === u.id;
              const isSelf = Boolean(
                (currentUserId && String(u.id) === String(currentUserId)) ||
                (currentUserEmail && u.email?.toLowerCase() === currentUserEmail.toLowerCase())
              );
              const isRootAdmin = u.id === 1 || u.email === "admin@ghg.com";
              const isProtected =
                Boolean(currentUserRole && ["it_admin", "it"].includes(currentUserRole)) &&
                Boolean(u.role && ["admin", "superuser", "it_manager"].includes(u.role));
              const isTestAccount = Boolean(
                u.is_test ||
                u.email?.endsWith("@audit.test") ||
                u.email === "a@a" ||
                u.email === "a" ||
                u.email?.endsWith("@example.test") ||
                u.fullName?.toLowerCase().includes("test")
              );'''

assert old_protected in umb_content, "old_protected not found in UserManagementBlock.tsx"
umb_content = umb_content.replace(old_protected, new_protected)

# Add Test Account badge next to name
old_name_div = '''                        <div className="font-bold! text-[color:var(--text-primary)]! leading-[1.2]!">
                          {u.fullName}
                        </div>'''

new_name_div = '''                        <div className="flex! items-center! gap-1.5! font-bold! text-[color:var(--text-primary)]! leading-[1.2]!">
                          <span>{u.fullName}</span>
                          {isTestAccount && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-900 border border-amber-300">
                              {t("Test Account")}
                            </span>
                          )}
                        </div>'''

assert old_name_div in umb_content, "old_name_div not found in UserManagementBlock.tsx"
umb_content = umb_content.replace(old_name_div, new_name_div)

# Fix action buttons tooltips and remove pointerEvents: "none"
old_actions = '''                  {/* Actions */}
                  <td style={{ ...S.td, whiteSpace: "nowrap", minWidth: "130px", textAlign: "right" }}>
                    {!isITOnly && (
                      <button
                        id={`um-edit-btn-${u.id}`}
                        disabled={isProtected}
                        data-protected={isProtected ? "true" : undefined}
                        style={{
                          ...S.iconBtn("var(--color-legacy-6366f1)"),
                          ...(isProtected
                            ? { opacity: 0.35, cursor: "not-allowed", pointerEvents: "none" }
                            : {}),
                        }}
                        onClick={() => !isProtected && handleOpenModal(u)}
                        title={
                          isProtected
                            ? t("Protected account — requires platform manager authority")
                            : t("Edit User Information")
                        }
                        onMouseEnter={(e) => {
                          if (!isProtected)
                            e.currentTarget.style.background = "var(--color-legacy-eef2ff)";
                        }}
                        onMouseLeave={(e) => {
                          if (!isProtected) e.currentTarget.style.background = "none";
                        }}
                      >
                        <SquarePenIcon size={15} strokeWidth={2} aria-hidden="true" />
                      </button>
                    )}
                    <button
                      id={`um-reset-pwd-btn-${u.id}`}
                      disabled={isProtected}
                      data-protected={isProtected ? "true" : undefined}
                      style={{
                        ...S.iconBtn("var(--color-amber-500)"),
                        ...(isProtected
                          ? { opacity: 0.35, cursor: "not-allowed", pointerEvents: "none" }
                          : {}),
                      }}
                      onClick={() => !isProtected && handleOpenResetPassword(u)}
                      title={
                        isProtected
                          ? t("Protected account — client IT staff cannot reset credentials")
                          : t("Modify / Reset Password")
                      }
                      onMouseEnter={(e) => {
                        if (!isProtected)
                          e.currentTarget.style.background = "var(--color-amber-50)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isProtected) e.currentTarget.style.background = "none";
                      }}
                    >
                      <KeyIcon size={15} strokeWidth={2} aria-hidden="true" />
                    </button>
                    {!isITOnly && (
                      <button
                        id={`um-delete-btn-${u.id}`}
                        disabled={isProtected}
                        data-protected={isProtected ? "true" : undefined}
                        style={{
                          ...S.iconBtn("var(--color-red-500)"),
                          ...(isProtected
                            ? { opacity: 0.35, cursor: "not-allowed", pointerEvents: "none" }
                            : {}),
                        }}
                        onClick={() => !isProtected && handleDelete(u.id)}
                        title={
                          isProtected
                            ? t("Protected account — client IT staff cannot delete compliance accounts")
                            : t("Revoke Access")
                        }
                        onMouseEnter={(e) => {
                          if (!isProtected)
                            e.currentTarget.style.background = "var(--color-red-50)";
                        }}
                        onMouseLeave={(e) => {
                          if (!isProtected) e.currentTarget.style.background = "none";
                        }}
                      >
                        <Trash2Icon size={15} strokeWidth={2} aria-hidden="true" />
                      </button>
                    )}
                  </td>'''

new_actions = '''                  {/* Actions */}
                  <td style={{ ...S.td, whiteSpace: "nowrap", minWidth: "130px", textAlign: "right" }}>
                    {!isITOnly && (
                      <span
                        title={
                          isSelf
                            ? t("Protected account — you cannot modify your own active account")
                            : isRootAdmin
                            ? t("Protected account — Root administrator cannot be modified")
                            : isProtected
                            ? t("Protected account — requires platform manager authority")
                            : t("Edit User Information")
                        }
                        className="inline-block"
                      >
                        <button
                          id={`um-edit-btn-${u.id}`}
                          disabled={isProtected || isSelf}
                          data-protected={isProtected || isSelf ? "true" : undefined}
                          style={{
                            ...S.iconBtn("var(--color-legacy-6366f1)"),
                            ...(isProtected || isSelf
                              ? { opacity: 0.35, cursor: "not-allowed" }
                              : {}),
                          }}
                          onClick={() => !isProtected && !isSelf && handleOpenModal(u)}
                          onMouseEnter={(e) => {
                            if (!isProtected && !isSelf)
                              e.currentTarget.style.background = "var(--color-legacy-eef2ff)";
                          }}
                          onMouseLeave={(e) => {
                            if (!isProtected && !isSelf) e.currentTarget.style.background = "none";
                          }}
                        >
                          <SquarePenIcon size={15} strokeWidth={2} aria-hidden="true" />
                        </button>
                      </span>
                    )}
                    <span
                      title={
                        isProtected
                          ? t("Protected account — client IT staff cannot reset credentials for compliance accounts")
                          : t("Modify / Reset Password")
                      }
                      className="inline-block ml-1"
                    >
                      <button
                        id={`um-reset-pwd-btn-${u.id}`}
                        disabled={isProtected}
                        data-protected={isProtected ? "true" : undefined}
                        style={{
                          ...S.iconBtn("var(--color-amber-500)"),
                          ...(isProtected
                            ? { opacity: 0.35, cursor: "not-allowed" }
                            : {}),
                        }}
                        onClick={() => !isProtected && handleOpenResetPassword(u)}
                        onMouseEnter={(e) => {
                          if (!isProtected)
                            e.currentTarget.style.background = "var(--color-amber-50)";
                        }}
                        onMouseLeave={(e) => {
                          if (!isProtected) e.currentTarget.style.background = "none";
                        }}
                      >
                        <KeyIcon size={15} strokeWidth={2} aria-hidden="true" />
                      </button>
                    </span>
                    {!isITOnly && (
                      <span
                        title={
                          isSelf
                            ? t("Protected account — you cannot delete your own active account")
                            : isRootAdmin
                            ? t("Protected account — Root administrator cannot be deleted")
                            : isProtected
                            ? t("Protected account — client IT staff cannot delete compliance accounts")
                            : t("Revoke Access")
                        }
                        className="inline-block ml-1"
                      >
                        <button
                          id={`um-delete-btn-${u.id}`}
                          disabled={isProtected || isSelf}
                          data-protected={isProtected || isSelf ? "true" : undefined}
                          style={{
                            ...S.iconBtn("var(--color-red-500)"),
                            ...(isProtected || isSelf
                              ? { opacity: 0.35, cursor: "not-allowed" }
                              : {}),
                          }}
                          onClick={() => !isProtected && !isSelf && handleDelete(u.id)}
                          onMouseEnter={(e) => {
                            if (!isProtected && !isSelf)
                              e.currentTarget.style.background = "var(--color-red-50)";
                          }}
                          onMouseLeave={(e) => {
                            if (!isProtected && !isSelf) e.currentTarget.style.background = "none";
                          }}
                        >
                          <Trash2Icon size={15} strokeWidth={2} aria-hidden="true" />
                        </button>
                      </span>
                    )}
                  </td>'''

assert old_actions in umb_content, "old_actions not found in UserManagementBlock.tsx"
umb_content = umb_content.replace(old_actions, new_actions)

with open(umb_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(umb_content)
print("Patched UserManagementBlock.tsx successfully")
