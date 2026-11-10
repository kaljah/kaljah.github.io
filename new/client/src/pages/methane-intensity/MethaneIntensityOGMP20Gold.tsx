import React from "react";
import { AlertTriangle, Award, Calendar, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "../../ui";
import { t } from "../../i18n";

export interface MethaneIntensityOGMP20GoldProps {
  facilities: any[];
  globalThreshold?: number;
  ogmpRoadmapData: any[];
  ogmpSurveys: any[];
  roadmapCollapsed: boolean;
  selectedBaselineYear?: number;
  selectedYear: string | number;
  setRoadmapCollapsed: (collapsed: boolean) => void;
  setSelectedBaselineYear: (year: number) => void;
}

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityOGMP20Gold: React.FC<MethaneIntensityOGMP20GoldProps> = ({
  facilities,
  globalThreshold,
  ogmpRoadmapData,
  ogmpSurveys,
  roadmapCollapsed,
  selectedBaselineYear,
  selectedYear,
  setRoadmapCollapsed,
  setSelectedBaselineYear,
}) => (
  <div
    className={`bg-surface border border-border rounded-lg p-7 shadow-card flex flex-col gap-5 transition-[gap] duration-200 ${roadmapCollapsed ? "gap-0" : ""}`}
  >
    <div
      role="presentation"
      className={`flex justify-between items-center flex-wrap gap-4 cursor-pointer select-none ${roadmapCollapsed ? "" : "pb-4 border-b border-border"}`}
      onClick={() => setRoadmapCollapsed(!roadmapCollapsed)}
    >
      <div className="flex flex-col gap-1">
        <h3 className="text-lg font-bold text-text m-0 flex flex-wrap items-center gap-2.5">
          <Award size={22} className="text-brand-500" />
          <span>{t("OGMP 2.0 Gold Standard Pathway & Milestone Roadmap")}</span>
          <Badge tone="warning">{t("Preview / Roadmap")}</Badge>
        </h3>
        <p className="text-sm text-text-secondary m-0">
          {t("Multi-year reporting level tracking towards Level 4/5 site-level measurement reconciliation (preview, reconciliation logic in development).")}
        </p>
      </div>

      <div className="flex min-w-0 items-center gap-4">
        {/* Interactive Baseline Selector UI button/pill matching theme */}
        <div
          role="presentation"
          className="min-w-0 flex flex-wrap items-center gap-2.5 bg-ink-50 px-3 py-1.5 rounded-md border border-border"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="text-xs font-medium text-text-secondary inline-flex items-center gap-1">
            <Calendar size={13} />
            {t("Base Year:")}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((yr) => (
              <button
                key={yr}
                type="button"
                className={`bg-surface border border-border text-text text-xs font-semibold px-2 py-0.5 rounded cursor-pointer transition-colors hover:border-ink-300 [&.active]:bg-brand-600 [&.active]:text-white [&.active]:border-brand-600 ${selectedBaselineYear === yr ? "active" : ""}`}
                onClick={() => setSelectedBaselineYear(yr)}
              >
                {yr}
              </button>
            ))}
          </div>
        </div>
        {roadmapCollapsed ? (
          <ChevronDown size={18} className="text-text-secondary" />
        ) : (
          <ChevronUp size={18} className="text-text-secondary" />
        )}
      </div>
    </div>

    <div
      className={roadmapCollapsed ? "hidden" : "overflow-hidden"}
    >
      {/* Facility Roadmap Cards Grid */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(480px,100%),1fr))] gap-5 pt-5">
        {(ogmpRoadmapData.length > 0 ? ogmpRoadmapData : facilities).map(
          (fac) => {
            const facName = fac.facility_name || fac.name;
            const opStatus = fac.operator_status || "operated";
            const baseYear =
              selectedBaselineYear ||
              Number(fac.ogmp_membership_year || 2023);
            const targetYear =
              baseYear + (opStatus === "operated" ? 3 : 5);
            const currentYear = Number(
              selectedYear !== "all"
                ? selectedYear
                : new Date().getFullYear(),
            );
            const yearsLeft = targetYear - currentYear;

            const matchedSurveys = ogmpSurveys.filter(
              (s) =>
                String(s.facilityId || s.facility_id) ===
                  String(fac.facility_id || fac.id) ||
                (s.facility_name || s.facilityName) === facName,
            );
            const threshold = Number(
              fac.reconciliation_threshold ?? globalThreshold ?? 10.0,
            );
            const matchedSurvey = matchedSurveys[0];
            const variancePct =
              fac.reconciliation_variance_pct ??
              fac.variance_pct ??
              (matchedSurvey
                ? (matchedSurvey.reconciliation_variance_pct ?? matchedSurvey.variance_pct ?? null)
                : null);
            const passThreshold =
              variancePct !== null
                ? Math.abs(variancePct) <= threshold
                : false;
            const hasSurveyDiscrepancy = (fac.reconciliation_status || "").toLowerCase().includes("discrepancy") ||
              fac.variance_flag === true ||
              matchedSurveys.some((s) => {
                const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
                const variance = s.variance_pct ?? s.reconciliation_variance_pct;
                const bu = Number(s.bottom_up_tch4 ?? s.bottomUpTch4 ?? 0);
                return status.includes("discrepancy") || s.variance_flag === true || (variance !== null && Math.abs(variance) > threshold) || bu === 0;
              });

            const hasSurveyReconciled = !hasSurveyDiscrepancy && (
              (fac.reconciliation_status || "").toLowerCase() === "reconciled" ||
              (matchedSurveys.length > 0 && matchedSurveys.some((s) => (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase().includes("reconciled")))
            );

            const highestLevel = hasSurveyDiscrepancy
              ? Math.min(4, Number(fac.highest_ogmp_level || fac.current_ogmp_level || 4))
              : hasSurveyReconciled
                ? 5
                : Number(fac.highest_ogmp_level || fac.current_ogmp_level || 3);

            const isReconciled = hasSurveyReconciled && highestLevel >= 5;

            let statusBadgeClass = "ontrack";
            let statusText = yearsLeft > 0
              ? t("On Track ({{years}} yrs to Level 5)", { years: yearsLeft })
              : t("On Track (Target Year)");

            if (hasSurveyDiscrepancy) {
              statusBadgeClass = "action";
              statusText = t("Discrepancy Detected (Level 4 - Action Required)");
            } else if (isReconciled && highestLevel >= 5) {
              statusBadgeClass = "achieved";
              statusText = t("Gold Standard Achieved (Level 5)");
            } else if (yearsLeft < 0) {
              statusBadgeClass = "action";
              statusText = t("Action Plan Required (Overdue)");
            } else if (yearsLeft === 0) {
              statusBadgeClass = "ontrack";
              statusText = t("Target Milestone Year (Level 5 Due)");
            }

            return (
              <div
                key={fac.facility_id || fac.id}
                className="bg-ink-50/50 border border-border rounded-md p-5 flex flex-col gap-4 transition-colors hover:border-ink-300"
              >
                <div className="flex justify-between items-start gap-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-base font-bold text-text">{facName}</span>
                    <span className="text-xs text-text-secondary">
                      {opStatus === "operated"
                        ? t("Operated Asset (3-Yr Target)")
                        : t("Non-Operated Asset (5-Yr Target)")}{" "}
                      {t("• Base:")}{" "}{baseYear}{" "}{t("• Target:")}{" "}{targetYear}
                    </span>
                  </div>
                  <span
                    className={`badge-roadmap-status ${statusBadgeClass}`}
                  >
                    {statusBadgeClass === "achieved" && (
                      <Check size={13} />
                    )}
                    {statusBadgeClass === "action" && (
                      <AlertTriangle size={13} />
                    )}
                    {statusText}
                  </span>
                </div>

                {/* 5-Level Stepper */}
                <div className="flex justify-between relative py-2.5 before:content-[''] before:absolute before:top-6 before:left-5 before:right-5 before:h-[2px] before:bg-border before:z-1">
                  {[1, 2, 3, 4, 5].map((lvl) => {
                    const isDone = highestLevel >= lvl;
                    const isCurrent = highestLevel === lvl;
                    const levelNames = [
                      t("L1: Venture"),
                      t("L2: Segment"),
                      t("L3: Generic"),
                      t("L4: Specific"),
                      t("L5: Reconciled"),
                    ];
                    return (
                      <div
                        key={lvl}
                        className={`relative z-2 flex flex-col items-center gap-1.5 text-center w-[70px] ${isDone ? "completed" : ""} ${isCurrent ? "current" : ""}`}
                      >
                        <div className={`size-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                          isDone
                            ? "bg-emerald-600 text-white border border-emerald-700"
                            : isCurrent
                            ? "bg-white text-blue-700 border-2 border-blue-600 ring-2 ring-blue-500/20"
                            : "bg-surface text-text-secondary border border-border"
                        }`}>
                          {isDone ? "✓" : lvl}
                        </div>
                        <span className={`text-[11px] leading-tight ${isCurrent ? "font-bold text-blue-700" : isDone ? "font-semibold text-emerald-700" : "font-medium text-text-secondary"}`}>
                          {levelNames[lvl - 1]}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Footer stats */}
                <div className="grid grid-cols-3 gap-2.5 bg-surface border border-border rounded-md px-3 py-2.5">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[11px] text-text-secondary font-medium">
                      {t("Current Milestone")}
                    </span>
                    <span className="text-sm font-bold text-text tabular-nums">
                      {t("OGMP Level")}{" "}{highestLevel}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[11px] text-text-secondary font-medium">
                      {t("Reconciliation Var.")}
                    </span>
                    <span
                      className={`text-sm font-bold tabular-nums ${variancePct !== null ? (passThreshold ? "text-emerald-700" : "text-danger-fg") : "text-text"}`}
                    >
                      {variancePct !== null
                        ? variancePct >= 0
                          ? `+${Number(variancePct).toFixed(1)}%`
                          : `${Number(variancePct).toFixed(1)}%`
                        : t("Pending Survey")}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[11px] text-text-secondary font-medium">
                      {t("Tolerance Limit")}
                    </span>
                    <span className={`text-sm font-bold tabular-nums ${variancePct !== null ? (passThreshold ? "text-emerald-700" : "text-danger-fg") : "text-text"}`}>
                      ±{threshold.toFixed(1)}%{" "}
                      {variancePct !== null
                        ? passThreshold
                          ? t("(PASS)")
                          : t("(FLAGGED)")
                        : ""}
                    </span>
                  </div>
                </div>
              </div>
            );
          },
        )}
      </div>
    </div>
  </div>
);

export default MethaneIntensityOGMP20Gold;
