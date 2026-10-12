import React, { useState, useEffect } from "react";
import { Shield, Clock, AlertTriangle, KeyRound, CheckCircle2, RefreshCw, Lock } from "lucide-react";
import api from "../../api";
import { useToast } from "../../components/Toast";
import ConfirmModal from "../../components/ConfirmModal";
import { t } from "../../i18n";

interface SessionPolicy {
  idle_timeout_minutes: number;
  max_failed_logins: number;
  nist_password_policy: string;
  session_invalidation: string;
  total_users: number;
  active_users: number;
}

interface UserManagementSessionTabProps {
  currentUserRole?: string;
}

export const UserManagementSessionTab: React.FC<UserManagementSessionTabProps> = ({
  currentUserRole = "it_admin",
}) => {
  const toast = useToast();
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [policy, setPolicy] = useState<SessionPolicy>({
    idle_timeout_minutes: 30,
    max_failed_logins: 5,
    nist_password_policy: "NIST SP 800-63B Enforced (min 10 chars, uppercase, lowercase, digits, symbols)",
    session_invalidation: "Cryptographic Session Versioning (sv)",
    total_users: 0,
    active_users: 0,
  });
  const [selectedTimeout, setSelectedTimeout] = useState<number>(30);
  const [confirmRevokeOpen, setConfirmRevokeOpen] = useState<boolean>(false);
  const [revoking, setRevoking] = useState<boolean>(false);

  useEffect(() => {
    fetchPolicy();
  }, []);

  const fetchPolicy = async () => {
    try {
      setLoading(true);
      const res = await api.get("/auth/sessions/policy");
      if (res.data) {
        setPolicy(res.data);
        setSelectedTimeout(res.data.idle_timeout_minutes || 30);
      }
    } catch (err: any) {
      console.error("Failed to load session policy:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTimeout = async () => {
    try {
      setSaving(true);
      await api.put("/auth/sessions/policy", {
        idle_timeout_minutes: Number(selectedTimeout),
      });
      toast.success(t("Idle session timeout updated successfully."));
      fetchPolicy();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to update session timeout."));
    } finally {
      setSaving(false);
    }
  };

  const handleRevokeAllSessions = async () => {
    try {
      setRevoking(true);
      const res = await api.post("/auth/sessions/revoke-all");
      toast.success(
        t("Successfully revoked {{count}} active sessions across the platform.", {
          count: res.data?.revoked_count || 0,
        })
      );
      setConfirmRevokeOpen(false);
      fetchPolicy();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to revoke active sessions."));
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="flex flex-col gap-6" id="it-session-governance-panel">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {t("Idle Session Timeout")}
            </span>
            <Clock className="size-4 text-brand-600" />
          </div>
          <div className="text-2xl font-bold text-text">
            {policy.idle_timeout_minutes} {t("Minutes")}
          </div>
          <p className="text-xs text-text-secondary">
            {t("Automatic token invalidation upon user inactivity")}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {t("Session Invalidation")}
            </span>
            <Shield className="size-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700">
            {t("Cryptographic")}
          </div>
          <p className="text-xs text-text-secondary">
            {t("RFC 6265 cookie epoch verification (sv) on every request")}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {t("Password Standard")}
            </span>
            <KeyRound className="size-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-amber-700">
            NIST SP 800-63B
          </div>
          <p className="text-xs text-text-secondary">
            {t("10+ characters, 5 complexity rules strictly enforced")}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {t("Monitored Accounts")}
            </span>
            <Lock className="size-4 text-brand-600" />
          </div>
          <div className="text-2xl font-bold text-text">
            {policy.active_users} / {policy.total_users}
          </div>
          <p className="text-xs text-text-secondary">
            {t("Active accounts under active governance")}
          </p>
        </div>
      </div>

      {/* Configuration & Action Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Policy Configuration Card */}
        <div className="rounded-xl border border-border bg-surface p-6 shadow-xs flex flex-col justify-between gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Shield className="size-5 text-brand-600" />
              <h2 className="text-lg font-bold text-text m-0">
                {t("Operational Session Governance Policy")}
              </h2>
            </div>
            <p className="text-sm text-text-secondary m-0">
              {t(
                "Configure enterprise session duration and idle timeouts. When sessions expire, cookies are cryptographically invalidated, requiring re-authentication."
              )}
            </p>
          </div>

          <div className="flex flex-col gap-4">
            <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {t("Inactivity Timeout Window")}
            </label>
            <div className="flex flex-wrap items-center gap-3">
              {[15, 30, 60, 120, 240].map((mins) => (
                <button
                  key={mins}
                  type="button"
                  id={`timeout-btn-${mins}`}
                  onClick={() => setSelectedTimeout(mins)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-all cursor-pointer ${
                    selectedTimeout === mins
                      ? "bg-brand-50 border-brand-500 text-brand-700 shadow-xs"
                      : "bg-surface border-border text-text hover:bg-ink-50"
                  }`}
                >
                  {mins} {t("mins")}
                </button>
              ))}
            </div>

            <div className="rounded-lg bg-ink-50/70 border border-border/80 p-3.5 flex items-start gap-2.5 text-xs text-text-secondary">
              <CheckCircle2 className="size-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>
                {t(
                  "Session fixation defenses enabled: Session IDs are regenerated upon login, role elevation, and password change."
                )}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-border flex justify-end">
            <button
              type="button"
              id="save-session-policy-btn"
              disabled={saving || loading}
              onClick={handleUpdateTimeout}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`size-4 ${saving ? "animate-spin" : ""}`} />
              {saving ? t("Saving Policy...") : t("Save Session Policy")}
            </button>
          </div>
        </div>

        {/* Global Invalidation / Emergency Revocation Card */}
        <div className="rounded-xl border border-red-200 bg-red-50/20 p-6 shadow-xs flex flex-col justify-between gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-red-600" />
              <h2 className="text-lg font-bold text-red-950 m-0">
                {t("Emergency Session Invalidation")}
              </h2>
            </div>
            <p className="text-sm text-text-secondary m-0">
              {t(
                "Immediately revoke all active authentication tokens and browser cookies across client workstations. Forces immediate re-authentication for all governed accounts."
              )}
            </p>
          </div>

          <div className="rounded-lg bg-white/80 border border-red-200 p-4 flex flex-col gap-2 text-xs text-red-900">
            <span className="font-semibold">{t("Separation of Duties Notice:")}</span>
            <p className="m-0 leading-relaxed">
              {currentUserRole === "it_manager"
                ? t(
                    "As IT Manager, executing this command revokes active sessions across all platform user accounts, logging the event into the tamper-evident audit ledger."
                  )
                : t(
                    "Client IT Administrators may revoke sessions across operational and support accounts. Protected business compliance admin accounts remain shielded."
                  )}
            </p>
          </div>

          <div className="pt-2 border-t border-red-200 flex justify-end">
            <button
              type="button"
              id="revoke-all-sessions-btn"
              disabled={revoking}
              onClick={() => setConfirmRevokeOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium text-sm transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            >
              <AlertTriangle className="size-4" />
              {t("Revoke All Active Sessions")}
            </button>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={confirmRevokeOpen}
        title={t("Revoke All Active Platform Sessions?")}
        description={t(
          "Are you sure you want to invalidate all active sessions? Users across all facilities and workstations will be required to sign back in immediately. Your current active session will be preserved."
        )}
        confirmLabel={revoking ? t("Revoking...") : t("Confirm Global Revocation")}
        onConfirm={handleRevokeAllSessions}
        onCancel={() => setConfirmRevokeOpen(false)}
        variant="danger"
      />
    </div>
  );
};
