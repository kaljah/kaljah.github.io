import React from "react";
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
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#ff6600"
                        strokeWidth="2"
                        style={{ animation: "spin 1s linear infinite" }}
                      >
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                      </svg>
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
                      <span className="text-[color:var(--text-secondary)]!"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
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
                            style={{
                              color: "var(--text-secondary)",
                              fontStyle: "italic",
                              fontSize: "0.8rem",
                            }}
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
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
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
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                            {u.location}
                          </span>
                        ) : (
                          <span
                            style={{
                              color: "var(--text-secondary)",
                              fontStyle: "italic",
                              fontSize: "0.8rem",
                            }}
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
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
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
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
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
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
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
