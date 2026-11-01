import React from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Clock, ShieldCheck, Users } from "lucide-react";
import { Button, Card } from "../ui";
import { useAuth } from "../context/AuthContext";
import { t } from "../i18n";

export interface RoleHomeBannerProps {
  pendingCount?: number;
  className?: string;
}

export const RoleHomeBanner: React.FC<RoleHomeBannerProps> = ({ pendingCount = 0, className }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const role = user?.role || "user";

  // Operator / standard user
  if (role === "user") {
    return (
      <Card className={className}>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700 border border-brand-200">
              <Plus className="size-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text m-0">{t("Operator Data Entry Console")}</h2>
              <p className="text-sm text-text-secondary m-0 mt-0.5">
                {t("Log monthly activity data across Scope 1, Scope 2, and Scope 3 with real-time emissions preview.")}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <Button size="sm" onClick={() => navigate("/emissions")}>
              <Plus className="size-4" />
              {t("Enter Emissions Data")}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => navigate("/manage-data?tab=pending")}>
              {t("My Drafts & Submissions")}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // Admin / superuser / reviewer
  if (["admin", "superuser"].includes(role)) {
    return (
      <Card className={className}>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
              <Clock className="size-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text m-0">
                {t("Compliance Review Desk")}
                {pendingCount > 0 && (
                  <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
                    {t("{{count}} pending", { count: pendingCount })}
                  </span>
                )}
              </h2>
              <p className="text-sm text-text-secondary m-0 mt-0.5">
                {pendingCount > 0
                  ? t("Unreviewed records await dual-control maker-checker validation before inclusion in the inventory.")
                  : t("All submitted records have been verified. Inventory totals are synchronized.")}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <Button size="sm" onClick={() => navigate("/manage-data?tab=pending")}>
              <Clock className="size-4" />
              {t("Open Approval Queue")}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => navigate("/qa-dashboard")}>
              {t("QA/QC Diagnostics")}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // Auditor
  if (role === "auditor") {
    return (
      <Card className={className}>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-green-50 text-green-700 border border-green-200">
            <ShieldCheck className="size-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-text m-0">{t("Independent Assurance & Audit Portal")}</h2>
            <p className="text-sm text-text-secondary m-0 mt-0.5">
              {t("Inspect ISO 14064-1 compliance, immutable cryptographic audit logs, and Monte Carlo uncertainty assessments.")}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Button size="sm" onClick={() => navigate("/qa-dashboard")}>
            <ShieldCheck className="size-4" />
            {t("QA/QC Diagnostics")}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => navigate("/audit-trail")}>
            {t("Audit Trail & Integrity")}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => navigate("/uncertainty")}>
            {t("Uncertainty Assessment")}
          </Button>
        </div>
      </Card>
    );
  }

  // IT Administrator / IT Manager
  if (["it", "it_admin", "it_manager"].includes(role)) {
    return (
      <Card className={className}>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
              <Users className="size-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text m-0">{t("IT Administration & Security Console")}</h2>
              <p className="text-sm text-text-secondary m-0 mt-0.5">
                {t("Manage user accounts, credential security, role-based access control, and IPCC standard configurations.")}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <Button size="sm" onClick={() => navigate("/user-management")}>
              <Users className="size-4" />
              {t("User Management")}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => navigate("/audit-trail")}>
              {t("Audit Log & Security Trail")}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  return null;
};

export default RoleHomeBanner;
