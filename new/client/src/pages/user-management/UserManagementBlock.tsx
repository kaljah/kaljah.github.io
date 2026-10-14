import React from "react";
import { Globe, Key as KeyIcon, Loader, Lock, MapPin as MapPinIcon, Search as SearchIcon, SquarePen as SquarePenIcon, Trash2 as Trash2Icon } from "lucide-react";
import { t } from "../../i18n";

export interface ManagedUser {
  id: number | string;
  fullName?: string;
  email: string;
  department?: string;
  jobTitle?: string;
  role?: string;
  location?: string;
  created_at?: string;
  orgName?: string;
  status?: string;
  [key: string]: any;
}

export interface RoleMeta {
  label: string;
  color: string;
  bg: string;
  border: string;
}

export interface UserManagementBlockProps {
  S: Record<string, any>;
  filteredUsers: ManagedUser[];
  getRoleMeta: (role?: string) => RoleMeta;
  handleDelete: (id: number | string) => void;
  handleOpenModal: (user: ManagedUser) => void;
  handleOpenResetPassword: (user: ManagedUser) => void;
  hoveredRow: number | string | null;
  isITOnly: boolean;
  loading: boolean;
  setHoveredRow: (id: number | string | null) => void;
  totalUsers: number;
  currentUserRole?: string;
}

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock: React.FC<UserManagementBlockProps> = ({
  S,
  filteredUsers,
  getRoleMeta,
  handleDelete,
  handleOpenModal,
  handleOpenResetPassword,
  hoveredRow,
  isITOnly,
  loading,
  setHoveredRow,
  totalUsers,
  currentUserRole,
}) => (
  <div style={S.tableCard}>
    <div style={S.tableToolbar}>
      <div>
        <p style={S.tableCardTitle}>{t("Registered Users")}</p>
        <p style={S.tableCardSub}>
          {loading ? t("Loading…") : `${filteredUsers.length} of ${totalUsers} users shown`}
        </p>
      </div>
    </div>

    <div style={S.tableWrap}>
      <table style={S.table}>
        <thead>
          <tr>
            {[
              "User",
              "Email",
              "Department / Job Title",
              "Role",
              "Status",
              "Region Access",
              "Joined",
              "Actions",
            ].map((h) => (
              <th key={h} style={h === "Actions" ? { ...S.th, minWidth: "130px", textAlign: "right" } : S.th}>
                {t(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={8} style={S.emptyCell}>
                <div className="flex! flex-col! items-center! gap-[10px]!">
                  <Loader size={32} color="var(--color-brand-500)" className="animate-spin!" aria-hidden="true" />
                  {t("Loading users…")}
                </div>
              </td>
            </tr>
          ) : filteredUsers.length === 0 ? (
            <tr>
              <td colSpan={8} style={S.emptyCell}>
                <div className="flex! flex-col! items-center! gap-[8px]!">
                  <span className="text-[color:var(--text-secondary)]!">
                    <SearchIcon size={32} strokeWidth={1.5} aria-hidden="true" />
                  </span>
                  {t("No users match the current filters.")}
                </div>
              </td>
            </tr>
          ) : (
            filteredUsers.map((u, idx) => {
              const meta = getRoleMeta(u.role);
              const initials = (u.fullName || "?")
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();
              const isHovered = hoveredRow === u.id;
              const isProtected =
                Boolean(currentUserRole && ["it_admin", "it"].includes(currentUserRole)) &&
                Boolean(u.role && ["admin", "superuser", "it_manager"].includes(u.role));

              return (
                <tr
                  key={u.id}
                  onMouseEnter={() => setHoveredRow(u.id)}
                  onMouseLeave={() => setHoveredRow(null)}
                  style={{
                    background: isHovered ? "var(--bg-hover)" : "transparent",
                    transition: "background .15s",
                    animation: `um-slide-in .3s ease ${idx * 40}ms both`,
                  }}
                >
                  {/* User */}
                  <td style={S.td}>
                    <div className="flex! items-center! gap-[10px]!">
                      <div style={S.avatar(meta.color)}>{initials}</div>
                      <div>
                        <div className="font-bold! text-[color:var(--text-primary)]! leading-[1.2]!">
                          {u.fullName}
                        </div>
                        <div className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! mt-[2px]!">
                          {u.orgName || "—"}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Email */}
                  <td
                    style={{
                      ...S.td,
                      color: "var(--text-secondary)",
                      fontFamily: "monospace",
                      fontSize: "0.82rem",
                    }}
                  >
                    {u.email}
                  </td>

                  {/* Department / Job Title */}
                  <td style={S.td}>
                    {u.department || u.jobTitle ? (
                      <div>
                        {u.department && (
                          <div className="font-semibold! text-[color:var(--text-primary)]! text-[length:0.85rem]!">
                            {u.department}
                          </div>
                        )}
                        {u.jobTitle && (
                          <div className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! mt-[2px]!">
                            {u.jobTitle}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-[color:var(--text-secondary)]! [font-style:italic]! text-[length:0.8rem]!">
                        {t("Not set")}
                      </span>
                    )}
                  </td>

                  {/* Role */}
                  <td style={S.td}>
                    <span style={S.regionPill(meta.color, meta.bg, meta.border)}>
                      {meta.label}
                    </span>
                  </td>

                  {/* Status */}
                  <td style={S.td}>
                    {u.status === "disabled" || u.status === "suspended" || u.status === "inactive" ? (
                      <span
                        style={S.regionPill("var(--color-red-700)", "var(--color-red-50)", "rgba(239,68,68,.25)")}
                        data-testid={`user-status-${u.id}`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 inline-block" />
                        {t("Disabled")}
                      </span>
                    ) : (
                      <span
                        style={S.regionPill("var(--color-green-700)", "var(--color-green-50)", "rgba(16,185,129,.25)")}
                        data-testid={`user-status-${u.id}`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5 inline-block" />
                        {t("Active")}
                      </span>
                    )}
                  </td>

                  {/* Region Access */}
                  <td style={S.td}>
                    {u.role === "admin" ? (
                      <span style={S.regionPill("var(--color-green-500)", "var(--color-green-50)", "rgba(16,185,129,.25)")}>
                        <Globe size={12} aria-hidden="true" />
                        {t("All Regions")}
                      </span>
                    ) : u.role === "it_admin" || u.role === "it_manager" || u.role === "it" ? (
                      <span style={S.regionPill("var(--color-red-500)", "var(--color-red-50)", "rgba(239,68,68,.25)")}>
                        <Lock size={12} strokeWidth={2} aria-hidden="true" />
                        {t("No Data Access")}
                      </span>
                    ) : u.location ? (
                      <span style={S.regionPill("var(--color-brand-500)", "var(--color-brand-50)", "rgba(255,102,0,.25)")}>
                        <MapPinIcon size={11} strokeWidth={2} aria-hidden="true" />
                        {u.location}
                      </span>
                    ) : (
                      <span className="text-[color:var(--text-secondary)]! [font-style:italic]! text-[length:0.8rem]!">
                        {t("None")}
                      </span>
                    )}
                  </td>

                  {/* Joined */}
                  <td
                    style={{
                      ...S.td,
                      color: "var(--text-secondary)",
                      fontSize: "0.8rem",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {u.created_at
                      ? new Date(u.created_at).toLocaleDateString("en-GB", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })
                      : "—"}
                  </td>

                  {/* Actions */}
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
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  </div>
);

export default UserManagementBlock;
