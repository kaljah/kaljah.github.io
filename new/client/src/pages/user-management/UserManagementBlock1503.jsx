import React from "react";
import { AlertCircle, Check, CheckCircle2, Eye, EyeOff, KeyRound } from "lucide-react";
import Drawer from "../../components/Drawer";

// Extracted from UserManagement.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const UserManagementBlock1503 = ({ S, focusedField, getRoleMeta, handleResetPasswordSubmit, resetLoading, resetPwd, resetPwdConfirm, resetPwdShow, resetTarget, setFocusedField, setResetPwd, setResetPwdConfirm, setResetPwdShow, setResetTarget }) => (
<Drawer
        isOpen={!!resetTarget}
        onClose={() => setResetTarget(null)}
        title="Reset User Password"
        subtitle={resetTarget ? `Administrative credential overwrite for ${resetTarget.email}` : ""}
        icon={KeyRound}
        iconColor="#f59e0b"
        iconBg="rgba(245, 158, 11, 0.12)"
        width="540px"
      >
        {resetTarget && (
          <form id="um-reset-pwd-form" onSubmit={handleResetPasswordSubmit}>
            {/* Target user info card */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "14px 16px",
                borderRadius: "14px",
                background: "var(--bg-body)",
                border: "1px solid var(--border-color)",
                marginBottom: "20px",
              }}
            >
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "12px",
                  background: "rgba(245, 158, 11, 0.15)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  color: "#f59e0b",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "1.1rem",
                  flexShrink: 0,
                }}
              >
                {resetTarget.fullName?.charAt(0)?.toUpperCase() || "U"}
              </div>
              <div className="flex-1! min-w-0!">
                <div
                  style={{
                    fontWeight: 700,
                    color: "var(--text-primary)",
                    fontSize: "0.98rem",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {resetTarget.fullName}
                </div>
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                    fontFamily: "monospace",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
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
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "12px 14px",
                borderRadius: "10px",
                background: "rgba(239, 68, 68, 0.06)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                marginBottom: "22px",
                fontSize: "0.8rem",
                color: "#dc2626",
                lineHeight: 1.45,
              }}
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
                        ? "#ef4444"
                        : focusedField === "resetPwd"
                        ? "#f59e0b"
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
                          background: ok ? "#10b981" : "var(--border-color)",
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
                          color: req.ok ? "#10b981" : "var(--text-secondary)",
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
                      ? "#ef4444"
                      : resetPwdConfirm && resetPwdConfirm === resetPwd
                      ? "#10b981"
                      : focusedField === "resetPwdConfirm"
                      ? "#f59e0b"
                      : "var(--border-color)",
                }}
                onFocus={() => setFocusedField("resetPwdConfirm")}
                onBlur={() => setFocusedField(null)}
                placeholder="Re-enter the new password"
                autoComplete="new-password"
              />
              {resetPwdConfirm && resetPwdConfirm !== resetPwd && (
                <p style={{ fontSize: "0.75rem", color: "#ef4444", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                  <AlertCircle size={13} /> Passwords do not match
                </p>
              )}
              {resetPwdConfirm && resetPwdConfirm === resetPwd && resetPwd.length >= 10 && (
                <p style={{ fontSize: "0.75rem", color: "#10b981", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                  <CheckCircle2 size={13} /> Passwords match
                </p>
              )}
            </div>

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
                  background: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)",
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
