import React from "react";
import { AlertCircle, Check, CheckCircle2, Eye, EyeOff, KeyRound } from "lucide-react";
import Drawer from "../../components/Drawer";
import type { ManagedUser, RoleMeta } from "./UserManagementBlock";

export interface UserManagementBlock1503Props {
  S: Record<string, any>;
  focusedField: string | null;
  getRoleMeta: (role?: string) => RoleMeta;
  handleResetPasswordSubmit: (e: React.FormEvent) => void;
  resetLoading: boolean;
  resetPwd: string;
  resetPwdConfirm: string;
  resetPwdShow: boolean;
  resetTarget: ManagedUser | null;
  setFocusedField: (field: string | null) => void;
  setResetPwd: (pwd: string) => void;
  setResetPwdConfirm: (pwd: string) => void;
  setResetPwdShow: React.Dispatch<React.SetStateAction<boolean>>;
  setResetTarget: (target: ManagedUser | null) => void;
}

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock1503: React.FC<UserManagementBlock1503Props> = ({
  S,
  focusedField,
  getRoleMeta,
  handleResetPasswordSubmit,
  resetLoading,
  resetPwd,
  resetPwdConfirm,
  resetPwdShow,
  resetTarget,
  setFocusedField,
  setResetPwd,
  setResetPwdConfirm,
  setResetPwdShow,
  setResetTarget,
}) => (
  <Drawer
    isOpen={!!resetTarget}
    onClose={() => setResetTarget(null)}
    title="Reset User Password"
    subtitle={resetTarget ? `Administrative credential overwrite for ${resetTarget.email}` : ""}
    icon={KeyRound}
    iconColor="var(--color-amber-500)"
    iconBg="rgba(245, 158, 11, 0.12)"
    width="540px"
  >
    {resetTarget && (
      <form id="um-reset-pwd-form" onSubmit={handleResetPasswordSubmit}>
        {/* Target user info card */}
        <div
          className="flex! items-center! gap-[14px]! p-[14px_16px]! rounded-[14px]! bg-[color:var(--bg-body)]! [border:1px_solid_var(--border-color)]! mb-[20px]!"
        >
          <div
            className="w-[44px]! h-[44px]! rounded-[12px]! bg-[color:rgba(245,_158,_11,_0.15)]! [border:1px_solid_rgba(245,_158,_11,_0.3)]! text-[color:var(--color-amber-700)]! flex! items-center! justify-center! [font-weight:800]! text-[length:1.1rem]! shrink-0!"
          >
            {resetTarget.fullName?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div className="flex-1! min-w-0!">
            <div
              className="font-bold! text-[color:var(--text-primary)]! text-[length:0.98rem]! whitespace-nowrap! overflow-hidden! [text-overflow:ellipsis]!"
            >
              {resetTarget.fullName}
            </div>
            <div
              className="text-[length:0.8rem]! text-[color:var(--text-secondary)]! font-mono! whitespace-nowrap! overflow-hidden! [text-overflow:ellipsis]!"
            >
              {resetTarget.email}
            </div>
          </div>
          {resetTarget.role && (
            <span
              style={S.roleBadge(
                getRoleMeta(resetTarget.role).color,
                getRoleMeta(resetTarget.role).bg,
                getRoleMeta(resetTarget.role).border,
              )}
            >
              {getRoleMeta(resetTarget.role).label}
            </span>
          )}
        </div>

        {/* Security Notice */}
        <div
          className="flex! items-start! gap-[10px]! p-[12px_14px]! rounded-[10px]! bg-[color:rgba(239,_68,_68,_0.06)]! [border:1px_solid_rgba(239,_68,_68,_0.2)]! mb-[22px]! text-[length:0.8rem]! text-[color:var(--color-red-600)]! leading-[1.45]!"
        >
          <AlertCircle size={17} className="shrink-0! mt-[2px]!" />
          <div>
            <strong>Security Impact:</strong> This will overwrite the user's password immediately. Active sessions will be terminated and the user must sign in with the new credentials.
          </div>
        </div>

        {/* New Password input */}
        <div style={{ ...S.formGroup, marginBottom: "20px" }}>
          <label style={S.label}>New Password</label>
          <div className="relative!">
            <input
              id="um-reset-pwd-input"
              type={resetPwdShow ? "text" : "password"}
              value={resetPwd}
              onChange={(e) => setResetPwd(e.target.value)}
              style={{
                ...S.input,
                paddingRight: "44px",
                borderColor:
                  resetPwd && resetPwd.length < 10
                    ? "var(--color-red-500)"
                    : focusedField === "resetPwd"
                    ? "var(--color-amber-500)"
                    : "var(--border-color)",
                boxShadow:
                  focusedField === "resetPwd"
                    ? "0 0 0 3px rgba(245,158,11,.15)"
                    : "none",
              }}
              onFocus={() => setFocusedField("resetPwd")}
              onBlur={() => setFocusedField(null)}
              placeholder="Min 10 chars · Aa1!..."
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setResetPwdShow((s) => !s)}
              style={{
                position: "absolute",
                right: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "4px",
              }}
              title={resetPwdShow ? "Hide password" : "Show password"}
            >
              {resetPwdShow ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {/* Password strength visual meter */}
          {resetPwd && (
            <div className="mt-[10px]!">
              <div className="flex! gap-[4px]! mb-[8px]!">
                {[
                  resetPwd.length >= 10,
                  /[A-Z]/.test(resetPwd),
                  /[a-z]/.test(resetPwd),
                  /[0-9]/.test(resetPwd),
                  /[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd),
                ].map((ok, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: "4px",
                      borderRadius: "2px",
                      background: ok ? "var(--color-green-500)" : "var(--border-color)",
                      transition: "background .2s",
                    }}
                  />
                ))}
              </div>

              {/* Requirements breakdown tags */}
              <div className="flex! flex-wrap! gap-[6px]!">
                {[
                  { label: "10+ Chars", ok: resetPwd.length >= 10 },
                  { label: "Uppercase (A-Z)", ok: /[A-Z]/.test(resetPwd) },
                  { label: "Lowercase (a-z)", ok: /[a-z]/.test(resetPwd) },
                  { label: "Number (0-9)", ok: /[0-9]/.test(resetPwd) },
                  { label: "Special symbol", ok: /[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd) },
                ].map((req, idx) => (
                  <span
                    key={idx}
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
                    {req.ok ? <Check size={10} /> : "·"} {req.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Confirm Password input */}
        <div style={S.formGroup}>
          <label style={S.label}>Confirm New Password</label>
          <input
            id="um-reset-pwd-confirm"
            type={resetPwdShow ? "text" : "password"}
            value={resetPwdConfirm}
            onChange={(e) => setResetPwdConfirm(e.target.value)}
            style={{
              ...S.input,
              borderColor:
                resetPwdConfirm && resetPwdConfirm !== resetPwd
                  ? "var(--color-red-500)"
                  : resetPwdConfirm && resetPwdConfirm === resetPwd
                  ? "var(--color-green-500)"
                  : focusedField === "resetPwdConfirm"
                  ? "var(--color-amber-500)"
                  : "var(--border-color)",
            }}
            onFocus={() => setFocusedField("resetPwdConfirm")}
            onBlur={() => setFocusedField(null)}
            placeholder="Re-enter the new password"
            autoComplete="new-password"
          />
          {resetPwdConfirm && resetPwdConfirm !== resetPwd && (
            <p className="text-[length:0.75rem]! text-[color:var(--color-red-700)]! mt-[6px]! flex! items-center! gap-[4px]!">
              <AlertCircle size={13} /> Passwords do not match
            </p>
          )}
          {resetPwdConfirm && resetPwdConfirm === resetPwd && resetPwd.length >= 10 && (
            <p className="text-[length:0.75rem]! text-[color:var(--color-green-700)]! mt-[6px]! flex! items-center! gap-[4px]!">
              <CheckCircle2 size={13} /> Passwords match
            </p>
          )}
        </div>

        {/* Action Buttons Right Under Form Fields */}
        <div
          className="flex! justify-end! items-center! gap-[12px]! mt-[24px]! pt-[16px]! [border-top:1px_solid_var(--border-color)]!"
        >
          <button
            id="um-reset-pwd-cancel"
            type="button"
            style={S.btnSecondary}
            onClick={() => setResetTarget(null)}
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
            id="um-reset-pwd-submit"
            type="submit"
            disabled={resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10}
            style={{
              ...S.btnPrimary,
              background: "linear-gradient(135deg, var(--color-amber-500) 0%, var(--color-legacy-fbbf24) 100%)",
              boxShadow: "0 4px 12px rgba(245,158,11,.3)",
              opacity:
                resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10
                  ? 0.6
                  : 1,
              cursor:
                resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10
                  ? "not-allowed"
                  : "pointer",
            }}
          >
            {resetLoading ? (
              "Resetting…"
            ) : (
              <span className="flex! items-center! gap-[6px]!">
                <KeyRound size={16} />
                Reset Password
              </span>
            )}
          </button>
        </div>
      </form>
    )}
  </Drawer>
);

export default UserManagementBlock1503;
