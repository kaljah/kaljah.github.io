import React from "react";
import { Globe, Key as KeyIcon, Loader, MapPin as MapPinIcon, Search as SearchIcon, SquarePen as SquarePenIcon, Trash2 as Trash2Icon } from "lucide-react";
import { Lock } from "lucide-react";

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock = ({ S, filteredUsers, getRoleMeta, handleDelete, handleOpenModal, handleOpenResetPassword, hoveredRow, isITOnly, loading, setHoveredRow, totalUsers }) => (
<div style={S.tableCard}>
        <div style={S.tableToolbar}>
          <div>
            <p style={S.tableCardTitle}>Registered Users</p>
            <p style={S.tableCardSub}>
              {loading
                ? "Loading…"
                : `${filteredUsers.length} of ${totalUsers} users shown`}
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
                  "Region Access",
                  "Joined",
                  "Actions",
                ].map((h) => (
                  <th key={h} style={S.th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" style={S.emptyCell}>
                    <div
                      className="flex! flex-col! items-center! gap-[10px]!"
                    >
                      <Loader size={32} color="#ff6600" style={{ animation: "spin 1s linear infinite" }} aria-hidden="true" />
                      Loading users…
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="7" style={S.emptyCell}>
                    <div
                      className="flex! flex-col! items-center! gap-[8px]!"
                    >
                      <span className="text-[color:var(--text-secondary)]!"><SearchIcon size={32} strokeWidth={1.5} aria-hidden="true" /></span>
                      No users match the current filters.
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

                  return (
                    <tr
                      key={u.id}
                      onMouseEnter={() => setHoveredRow(u.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        background: isHovered
                          ? "var(--bg-hover)"
                          : "transparent",
                        transition: "background .15s",
                        animation: `um-slide-in .3s ease ${idx * 40}ms both`,
                      }}
                    >
                      {/* User */}
                      <td style={S.td}>
                        <div
                          className="flex! items-center! gap-[10px]!"
                        >
                          <div style={S.avatar(meta.color)}>{initials}</div>
                          <div>
                            <div
                              className="font-bold! text-[color:var(--text-primary)]! leading-[1.2]!"
                            >
                              {u.fullName}
                            </div>
                            <div
                              className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! mt-[2px]!"
                            >
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
                              <div
                                className="font-semibold! text-[color:var(--text-primary)]! text-[length:0.85rem]!"
                              >
                                {u.department}
                              </div>
                            )}
                            {u.jobTitle && (
                              <div
                                className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! mt-[2px]!"
                              >
                                {u.jobTitle}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span
                            className="text-[color:var(--text-secondary)]! [font-style:italic]! text-[length:0.8rem]!"
                          >
                            Not set
                          </span>
                        )}
                      </td>

                      {/* Role */}
                      <td style={S.td}>
                        <span
                          style={S.regionPill(meta.color, meta.bg, meta.border)}
                        >
                          {meta.label}
                        </span>
                      </td>

                      {/* Region Access */}
                      <td style={S.td}>
                        {u.role === "admin" ? (
                          <span
                            style={S.regionPill(
                              "#10b981",
                              "#ecfdf5",
                              "rgba(16,185,129,.25)",
                            )}
                          >
                            <Globe size={12} aria-hidden="true" />
                            All Regions
                          </span>
                        ) : u.role === "it_admin" || u.role === "it_manager" || u.role === "it" ? (
                          <span
                            style={S.regionPill(
                              "#ef4444",
                              "#fef2f2",
                              "rgba(239,68,68,.25)",
                            )}
                          >
                            <Lock size="12" strokeWidth="2" aria-hidden="true" />
                            No Data Access
                          </span>
                        ) : u.location ? (
                          <span
                            style={S.regionPill(
                              "#ff6600",
                              "#fff7ed",
                              "rgba(255,102,0,.25)",
                            )}
                          >
                            <MapPinIcon size={11} strokeWidth={2} aria-hidden="true" />
                            {u.location}
                          </span>
                        ) : (
                          <span
                            className="text-[color:var(--text-secondary)]! [font-style:italic]! text-[length:0.8rem]!"
                          >
                            None
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
                      <td style={{ ...S.td, whiteSpace: "nowrap" }}>
                        {!isITOnly && (
                          <button
                            id={`um-edit-btn-${u.id}`}
                            style={S.iconBtn("#6366f1")}
                            onClick={() => handleOpenModal(u)}
                            title="Edit User Information"
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.background = "#eef2ff")
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.background = "none")
                            }
                          >
                            <SquarePenIcon size={15} strokeWidth={2} aria-hidden="true" />
                          </button>
                        )}
                        <button
                          id={`um-reset-pwd-btn-${u.id}`}
                          style={S.iconBtn("#f59e0b")}
                          onClick={() => handleOpenResetPassword(u)}
                          title="Modify / Reset Password"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#fffbeb")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "none")
                          }
                        >
                          <KeyIcon size={15} strokeWidth={2} aria-hidden="true" />
                        </button>
                        {!isITOnly && (
                          <button
                            id={`um-delete-btn-${u.id}`}
                            style={S.iconBtn("#ef4444")}
                            onClick={() => handleDelete(u.id)}
                            title="Revoke Access"
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.background = "#fef2f2")
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.background = "none")
                            }
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
