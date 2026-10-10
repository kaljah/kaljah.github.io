import React from "react";
import { Briefcase, KeyRound, Shield, User, UserCheck, UserPlus } from "lucide-react";
import Drawer from "../../components/Drawer";
import { NativeSelect } from "../../ui/NativeSelect";
import type { ManagedUser } from "./UserManagementBlock";
import { t } from "../../i18n";

export interface UserFormData {
  fullName: string;
  email: string;
  department: string;
  jobTitle: string;
  role: string;
  location: string;
  status?: string;
  password?: string;
  [key: string]: any;
}

export interface UserManagementBlock1205Props {
  S: Record<string, any>;
  editingUser: ManagedUser | null;
  focusProps: (field: string) => { onFocus: () => void; onBlur: () => void };
  focusedField: string | null;
  formData: UserFormData;
  handleSubmit: (e: React.FormEvent) => void;
  inputStyle: (field: string) => React.CSSProperties;
  isModalOpen: boolean;
  regions: string[];
  setFormData: React.Dispatch<React.SetStateAction<any>>;
  setIsModalOpen: (open: boolean) => void;
}

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock1205: React.FC<UserManagementBlock1205Props> = ({
  S,
  editingUser,
  focusProps,
  focusedField,
  formData,
  handleSubmit,
  inputStyle,
  isModalOpen,
  regions,
  setFormData,
  setIsModalOpen,
}) => (
  <Drawer
    isOpen={isModalOpen}
    onClose={() => setIsModalOpen(false)}
    title={editingUser ? t("Edit User Information") : t("Register New User")}
    subtitle={
      editingUser
        ? `Update profile details for ${editingUser.fullName || editingUser.email}`
        : t("Provision a new system identity and configure role access")
    }
    icon={editingUser ? UserCheck : UserPlus}
    iconColor={editingUser ? "var(--color-legacy-6366f1)" : "var(--color-brand-500)"}
    iconBg={editingUser ? "rgba(99, 102, 241, 0.12)" : "rgba(255, 102, 0, 0.12)"}
    width="560px"
  >
    <form id="um-user-form" onSubmit={handleSubmit}>
      {/* Section 1: Profile & Identity */}
      <div style={S.drawerSection}>
        <div style={S.sectionHeader}>
          <span style={S.sectionIconBadge("var(--color-legacy-6366f1)")}>
            <User size={14} />
          </span>
          <span style={S.sectionTitle}>{t("Profile & Identity")}</span>
        </div>

        <div className="flex! flex-col! gap-[14px]!">
          <div style={S.formGroup}>
            <label style={S.label}>
              {t("Full Name")}{" "}<span className="text-[color:var(--color-red-700)]!">*</span>
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
              placeholder={t("e.g. Jane Smith")}
            />
          </div>

          <div style={S.formGroup}>
            <label style={S.label}>
              {t("Email Address")}{" "}<span className="text-[color:var(--color-red-700)]!">*</span>
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
              placeholder={t("e.g. jane.smith@company.com")}
            />
          </div>
        </div>
      </div>

      {/* Section 2: Organization & Title */}
      <div style={S.drawerSection}>
        <div style={S.sectionHeader}>
          <span style={S.sectionIconBadge("var(--color-legacy-0ea5e9)")}>
            <Briefcase size={14} />
          </span>
          <span style={S.sectionTitle}>{t("Organization & Title")}</span>
        </div>

        <div style={S.formRow}>
          <div style={S.formGroup}>
            <label style={S.label}>{t("Department")}</label>
            <input
              id="um-modal-department"
              type="text"
              value={formData.department}
              onChange={(e) =>
                setFormData({ ...formData, department: e.target.value })
              }
              style={inputStyle("department")}
              {...focusProps("department")}
              placeholder={t("e.g. Engineering")}
            />
          </div>

          <div style={S.formGroup}>
            <label style={S.label}>{t("Job Title")}</label>
            <input
              id="um-modal-jobtitle"
              type="text"
              value={formData.jobTitle}
              onChange={(e) =>
                setFormData({ ...formData, jobTitle: e.target.value })
              }
              style={inputStyle("jobTitle")}
              {...focusProps("jobTitle")}
              placeholder={t("e.g. Lead Carbon Analyst")}
            />
          </div>
        </div>
      </div>

      {/* Section 3: Access Governance & Scope */}
      <div style={S.drawerSection}>
        <div className="flex! justify-between! items-center! mb-[14px]!">
          <div style={{ ...S.sectionHeader, marginBottom: 0 }}>
            <span style={S.sectionIconBadge("var(--color-amber-500)")}>
              <Shield size={14} />
            </span>
            <span style={S.sectionTitle}>{t("Access Governance & Scope")}</span>
          </div>
        </div>

        <div style={S.formRow}>
          <div style={S.formGroup}>
            <label style={S.label}>{t("System Role")}</label>
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
              <option value="user">{t("Standard User")}</option>
              <option value="superuser">{t("Super User")}</option>
              <option value="admin">{t("Admin (All Data)")}</option>
              <option value="it_manager">{t("IT Manager")}</option>
              <option value="it">IT</option>
            </NativeSelect>
          </div>

          {(["user", "superuser"].includes(formData.role) || formData.location) && (
            <div style={S.formGroup}>
              <label style={S.label}>{t("Assigned Region")}</label>
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
                      ? "var(--color-red-500)"
                      : focusedField === "location"
                      ? "var(--color-brand-500)"
                      : "var(--border-color)",
                }}
                {...focusProps("location")}
              >
                <option value="">{t("— Select a Region —")}</option>
                {regions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </NativeSelect>
              {!formData.location && (
                <p className="text-[length:0.72rem]! text-[color:var(--color-red-700)]! mt-[4px]!">
                  {t("↑ Required — choose an assigned region")}
                </p>
              )}
            </div>
          )}
        </div>

        {editingUser && (
          <div style={{ ...S.formGroup, marginTop: "14px" }}>
            <label style={S.label}>{t("Account Status")}</label>
            <NativeSelect
              id="um-modal-status"
              value={formData.status || "active"}
              onChange={(e) =>
                setFormData({ ...formData, status: e.target.value })
              }
              style={inputStyle("status")}
              {...focusProps("status")}
            >
              <option value="active">{t("Active (Full Access Granted)")}</option>
              <option value="disabled">{t("Disabled (Account Suspended)")}</option>
            </NativeSelect>
          </div>
        )}
      </div>

      {/* Section 4: Initial Password (Register only) */}
      {!editingUser && (
        <div style={S.drawerSection}>
          <div style={S.sectionHeader}>
            <span style={S.sectionIconBadge("var(--color-green-500)")}>
              <KeyRound size={14} />
            </span>
            <span style={S.sectionTitle}>{t("Initial Credentials")}</span>
          </div>

          <div style={S.formGroup}>
            <label style={S.label}>
              {t("Temporary Password")}{" "}<span className="text-[color:var(--color-red-700)]!">*</span>
            </label>
            <input
              id="um-modal-password"
              type="text"
              value={formData.password || ""}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              style={{
                ...inputStyle("password"),
                borderColor:
                  formData.password && formData.password.length < 10
                    ? "var(--color-red-500)"
                    : focusedField === "password"
                    ? "var(--color-brand-500)"
                    : "var(--border-color)",
              }}
              {...focusProps("password")}
              placeholder={t("Minimum 10 characters")}
            />
            <div className="flex! justify-between! items-center! mt-[6px]!">
              <span className={`[font-size:0.74rem]! ${(formData.password?.length ?? 0) >= 10 ? "[color:var(--color-green-700)]!" : "[color:var(--color-ink-600)]!"}`}>
                {(formData.password?.length ?? 0) >= 10 ? t("✓ Meets minimum length requirement") : t("Requires at least 10 characters")}
              </span>
              <span className={`[font-size:0.74rem]! [font-weight:600]! ${(formData.password?.length ?? 0) >= 10 ? "[color:var(--color-green-700)]!" : "[color:var(--color-red-700)]!"}`}>
                {formData.password?.length || 0}/10 chars
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons Right Under Form Fields */}
      <div
        className="flex! justify-end! items-center! gap-[12px]! mt-[24px]! pt-[16px]! [border-top:1px_solid_var(--border-color)]!"
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
          {t("Cancel")}
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
              {t("Save Changes")}
            </span>
          ) : (
            <span className="flex! items-center! gap-[6px]!">
              <UserPlus size={16} />
              {t("Create User")}
            </span>
          )}
        </button>
      </div>
    </form>
  </Drawer>
);

export default UserManagementBlock1205;
