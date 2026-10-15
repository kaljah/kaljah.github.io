import React from "react";
import { Briefcase, Check, KeyRound, Shield, User, UserCheck, UserPlus } from "lucide-react";
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
  currentUserRole?: string;
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
  currentUserRole,
}) => {
  const pwd = formData.password || "";
  const pwdChecks = [
    { label: t("10+ Chars"), ok: pwd.length >= 10 },
    { label: t("Uppercase (A-Z)"), ok: /[A-Z]/.test(pwd) },
    { label: t("Lowercase (a-z)"), ok: /[a-z]/.test(pwd) },
    { label: t("Number (0-9)"), ok: /[0-9]/.test(pwd) },
    { label: t("Special symbol"), ok: /[!@#$%^&*(),.?":{}|<>\-_+=[\]\\/~`]/.test(pwd) },
  ];
  const allPwdChecksPassed = pwdChecks.every((c) => c.ok);

  const roleOptions: { value: string; label: string; disabled?: boolean }[] =
    currentUserRole === "it"
      ? [
          { value: "user", label: t("Standard User") },
          { value: "auditor", label: t("Assurance Auditor") },
          { value: "it", label: t("IT Support") },
          { value: "it_admin", label: t("IT Administrator") },
        ]
      : currentUserRole === "it_admin"
      ? [
          // Client IT cannot assign the compliance roles (admin, superuser): audit 2026-10-14 BUG-0001
          { value: "user", label: t("Standard User") },
          { value: "auditor", label: t("Assurance Auditor") },
          { value: "it", label: t("IT Support") },
          { value: "it_admin", label: t("IT Administrator") },
        ]
      : [
          { value: "user", label: t("Standard User") },
          { value: "auditor", label: t("Assurance Auditor") },
          { value: "superuser", label: t("Super User") },
          { value: "admin", label: t("Admin (All Data)") },
          { value: "it", label: t("IT Support") },
          { value: "it_admin", label: t("IT Administrator") },
          { value: "it_manager", label: t("IT Manager") },
        ];

  if (editingUser && formData.role && !roleOptions.some((r) => r.value === formData.role)) {
    roleOptions.unshift({
      value: formData.role,
      label: `${formData.role.charAt(0).toUpperCase() + formData.role.slice(1)} (Protected)`,
      disabled: true,
    });
  }

  return (
  <Drawer
    isOpen={isModalOpen}
    onClose={() => setIsModalOpen(false)}
    title={editingUser ? t("Edit User Information") : t("Register New User")}
    subtitle={
      editingUser
        ? t("Update profile details for {{name}}", { name: editingUser.fullName || editingUser.email })
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
              {roleOptions.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                  {opt.label}
                </option>
              ))}
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
                  formData.password && !allPwdChecksPassed
                    ? "var(--color-red-500)"
                    : focusedField === "password"
                    ? "var(--color-brand-500)"
                    : "var(--border-color)",
              }}
              {...focusProps("password")}
              placeholder={t("Min 10 chars · Aa1!...")}
            />

            {/* Password strength visual meter */}
            {formData.password ? (
              <div className="mt-[10px]!" data-testid="password-strength-meter">
                <div className="flex! gap-[4px]! mb-[8px]!">
                  {pwdChecks.map((req, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        height: "4px",
                        borderRadius: "2px",
                        background: req.ok ? "var(--color-green-500)" : "var(--border-color)",
                        transition: "background .2s",
                      }}
                    />
                  ))}
                </div>

                {/* Requirements breakdown tags */}
                <div className="flex! flex-wrap! gap-[6px]!">
                  {pwdChecks.map((req, idx) => (
                    <span
                      key={idx}
                      data-testid={`um-pwd-req-${idx}`}
                      style={{
                        fontSize: "0.7rem",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        background: req.ok ? "rgba(16, 185, 129, 0.1)" : "rgba(100, 116, 139, 0.08)",
                        color: req.ok ? "var(--color-green-700)" : "var(--text-secondary)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "3px",
                        fontWeight: req.ok ? 600 : 400,
                      }}
                    >
                      {req.ok ? <Check size={11} /> : <span className="opacity-50!">•</span>}
                      {req.label}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="flex! justify-between! items-center! mt-[6px]!">
              <span
                id="um-pwd-status-msg"
                className={`[font-size:0.74rem]! ${allPwdChecksPassed ? "[color:var(--color-green-700)]!" : "[color:var(--color-ink-600)]!"}`}
              >
                {allPwdChecksPassed
                  ? t("✓ Meets all password security requirements")
                  : t("Requires 10+ characters with uppercase, lowercase, number & symbol")}
              </span>
              <span
                id="um-pwd-char-counter"
                className={`[font-size:0.74rem]! [font-weight:600]! ${allPwdChecksPassed ? "[color:var(--color-green-700)]!" : "[color:var(--color-red-700)]!"}`}
              >
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
};

export default UserManagementBlock1205;
