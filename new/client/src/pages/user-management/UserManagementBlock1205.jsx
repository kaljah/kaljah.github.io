import React from "react";
import { Briefcase, KeyRound, Shield, User, UserCheck, UserPlus } from "lucide-react";
import Drawer from "../../components/Drawer";
import { NativeSelect } from "../../ui/NativeSelect";

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock1205 = ({ S, editingUser, focusProps, focusedField, formData, handleSubmit, inputStyle, isModalOpen, regions, setFormData, setIsModalOpen }) => (
<Drawer
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingUser ? "Edit User Information" : "Register New User"}
        subtitle={
          editingUser
            ? `Update profile details for ${editingUser.fullName || editingUser.email}`
            : "Provision a new system identity and configure role access"
        }
        icon={editingUser ? UserCheck : UserPlus}
        iconColor={editingUser ? "#6366f1" : "#ff6600"}
        iconBg={editingUser ? "rgba(99, 102, 241, 0.12)" : "rgba(255, 102, 0, 0.12)"}
        width="560px"
      >
        <form id="um-user-form" onSubmit={handleSubmit}>
          {/* Section 1: Profile & Identity */}
          <div style={S.drawerSection}>
            <div style={S.sectionHeader}>
              <span style={S.sectionIconBadge("#6366f1")}>
                <User size={14} />
              </span>
              <span style={S.sectionTitle}>Profile & Identity</span>
            </div>

            <div className="flex! flex-col! gap-[14px]!">
              <div style={S.formGroup}>
                <label style={S.label}>
                  Full Name <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  id="um-modal-fullname"
                  type="text"
                  value={formData.fullName}
                  onChange={(e) =>
                    setFormData({ ...formData, fullName: e.target.value })
                  }
                  style={inputStyle("fullName")}
                  {...focusProps("fullName")}
                  placeholder="e.g. Jane Smith"
                />
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>
                  Email Address <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  id="um-modal-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  style={inputStyle("email")}
                  {...focusProps("email")}
                  placeholder="e.g. jane.smith@company.com"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Organization & Title */}
          <div style={S.drawerSection}>
            <div style={S.sectionHeader}>
              <span style={S.sectionIconBadge("#0ea5e9")}>
                <Briefcase size={14} />
              </span>
              <span style={S.sectionTitle}>Organization & Title</span>
            </div>

            <div style={S.formRow}>
              <div style={S.formGroup}>
                <label style={S.label}>Department</label>
                <input
                  id="um-modal-department"
                  type="text"
                  value={formData.department}
                  onChange={(e) =>
                    setFormData({ ...formData, department: e.target.value })
                  }
                  style={inputStyle("department")}
                  {...focusProps("department")}
                  placeholder="e.g. Engineering"
                />
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>Job Title</label>
                <input
                  id="um-modal-jobtitle"
                  type="text"
                  value={formData.jobTitle}
                  onChange={(e) =>
                    setFormData({ ...formData, jobTitle: e.target.value })
                  }
                  style={inputStyle("jobTitle")}
                  {...focusProps("jobTitle")}
                  placeholder="e.g. Lead Carbon Analyst"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Access Governance & Scope */}
          <div style={S.drawerSection}>
            <div className="flex! justify-between! items-center! mb-[14px]!">
              <div style={{ ...S.sectionHeader, marginBottom: 0 }}>
                <span style={S.sectionIconBadge("#f59e0b")}>
                  <Shield size={14} />
                </span>
                <span style={S.sectionTitle}>Access Governance & Scope</span>
              </div>
            </div>

            <div style={S.formRow}>
              <div style={S.formGroup}>
                <label style={S.label}>System Role</label>
                <NativeSelect
                  id="um-modal-role"
                  value={formData.role}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      role: e.target.value,
                      location: ["user", "superuser"].includes(e.target.value)
                        ? formData.location || regions[0] || ""
                        : "",
                    })
                  }
                  style={inputStyle("role")}
                  {...focusProps("role")}
                >
                  <option value="user">Standard User</option>
                  <option value="superuser">Super User</option>
                  <option value="admin">Admin (All Data)</option>
                  <option value="it_manager">IT Manager</option>
                  <option value="it">IT</option>
                </NativeSelect>
              </div>

              {(["user", "superuser"].includes(formData.role) || formData.location) && (
                <div style={S.formGroup}>
                  <label style={S.label}>Assigned Region</label>
                  <NativeSelect
                    id="um-modal-region"
                    value={formData.location}
                    onChange={(e) =>
                      setFormData({ ...formData, location: e.target.value })
                    }
                    style={{
                      ...inputStyle("location"),
                      borderColor:
                        !formData.location
                          ? "#ef4444"
                          : focusedField === "location"
                          ? "#ff6600"
                          : "var(--border-color)",
                    }}
                    {...focusProps("location")}
                  >
                    <option value="">— Select a Region —</option>
                    {regions.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </NativeSelect>
                  {!formData.location && (
                    <p style={{ fontSize: "0.72rem", color: "#ef4444", marginTop: "4px" }}>
                      ↑ Required — choose an assigned region
                    </p>
                  )}
                </div>
              )}
            </div>

            {editingUser && (
              <div style={{ ...S.formGroup, marginTop: "14px" }}>
                <label style={S.label}>Account Status</label>
                <NativeSelect
                  id="um-modal-status"
                  value={formData.status || "active"}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value })
                  }
                  style={inputStyle("status")}
                  {...focusProps("status")}
                >
                  <option value="active">Active (Full Access Granted)</option>
                  <option value="disabled">Disabled (Account Suspended)</option>
                </NativeSelect>
              </div>
            )}
          </div>

          {/* Section 4: Initial Password (Register only) */}
          {!editingUser && (
            <div style={S.drawerSection}>
              <div style={S.sectionHeader}>
                <span style={S.sectionIconBadge("#10b981")}>
                  <KeyRound size={14} />
                </span>
                <span style={S.sectionTitle}>Initial Credentials</span>
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>
                  Temporary Password <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  id="um-modal-password"
                  type="text"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  style={{
                    ...inputStyle("password"),
                    borderColor:
                      formData.password && formData.password.length < 10
                        ? "#ef4444"
                        : focusedField === "password"
                        ? "#ff6600"
                        : "var(--border-color)",
                  }}
                  {...focusProps("password")}
                  placeholder="Minimum 10 characters"
                />
                <div className="flex! justify-between! items-center! mt-[6px]!">
                  <span style={{ fontSize: "0.74rem", color: formData.password.length >= 10 ? "#10b981" : "#94a3b8" }}>
                    {formData.password.length >= 10 ? "✓ Meets minimum length requirement" : "Requires at least 10 characters"}
                  </span>
                  <span style={{ fontSize: "0.74rem", fontWeight: 600, color: formData.password.length >= 10 ? "#10b981" : "#ef4444" }}>
                    {formData.password.length}/10 chars
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons Right Under Form Fields */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              gap: "12px",
              marginTop: "24px",
              paddingTop: "16px",
              borderTop: "1px solid var(--border-color)",
            }}
          >
            <button
              id="um-modal-cancel"
              type="button"
              style={S.btnSecondary}
              onClick={() => setIsModalOpen(false)}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              Cancel
            </button>
            <button
              id="um-modal-submit"
              type="submit"
              style={S.btnPrimary}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-1px)";
                e.currentTarget.style.boxShadow =
                  "0 8px 20px rgba(255,102,0,.35)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow =
                  "0 4px 12px rgba(255,102,0,.25)";
              }}
            >
              {editingUser ? (
                <span className="flex! items-center! gap-[6px]!">
                  <UserCheck size={16} />
                  Save Changes
                </span>
              ) : (
                <span className="flex! items-center! gap-[6px]!">
                  <UserPlus size={16} />
                  Create User
                </span>
              )}
            </button>
          </div>
        </form>
      </Drawer>
);

export default UserManagementBlock1205;
