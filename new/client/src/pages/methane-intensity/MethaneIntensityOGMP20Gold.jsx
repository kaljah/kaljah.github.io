import React from "react";
import { AlertTriangle, Award, Calendar, Check, ChevronDown, ChevronUp } from "lucide-react";

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityOGMP20Gold = ({ facilities, globalThreshold, ogmpRoadmapData, ogmpSurveys, roadmapCollapsed, selectedBaselineYear, selectedYear, setRoadmapCollapsed, setSelectedBaselineYear }) => (
<div
          className={`ogmp-roadmap-card ${roadmapCollapsed ? "collapsed-card" : ""}`}
        >
          <div
            className="roadmap-header-row"
            onClick={() => setRoadmapCollapsed(!roadmapCollapsed)}
            style={{ cursor: "pointer", userSelect: "none" }}
          >
            <div className="roadmap-title-area">
              <h3>
                <Award size={22} color="#ff6600" />
                OGMP 2.0 Gold Standard Pathway & Milestone Roadmap
              </h3>
              <p>
                Multi-year reporting level progression towards Level 4/5
                site-level measurement reconciliation.
              </p>
            </div>

            <div className="flex! items-center! gap-[16px]!">
              {/* Interactive Baseline Selector UI button/pill matching theme */}
              <div
                className="baseline-selector-wrapper"
                onClick={(e) => e.stopPropagation()}
              >
                <span className="baseline-selector-label">
                  <Calendar
                    size={14}
                    style={{
                      display: "inline",
                      verticalAlign: "middle",
                      marginRight: "4px",
                    }}
                  />
                  Base Year:
                </span>
                <div className="baseline-pills">
                  {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((yr) => (
                    <button
                      key={yr}
                      type="button"
                      className={`btn-baseline-pill ${selectedBaselineYear === yr ? "active" : ""}`}
                      onClick={() => setSelectedBaselineYear(yr)}
                    >
                      {yr}
                    </button>
                  ))}
                </div>
              </div>
              {roadmapCollapsed ? (
                <ChevronDown size={18} color="var(--text-secondary)" />
              ) : (
                <ChevronUp size={18} color="var(--text-secondary)" />
              )}
            </div>
          </div>

          <div
            className={`ogmp-roadmap-body-wrapper ${roadmapCollapsed ? "collapsed" : ""}`}
          >
            {/* Facility Roadmap Cards Grid */}
            <div className="facility-roadmap-grid">
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

                  const matchedSurvey = ogmpSurveys.find(
                    (s) =>
                      String(s.facilityId || s.facility_id) ===
                        String(fac.facility_id || fac.id) ||
                      (s.facility_name || s.facilityName) === facName,
                  );
                  const threshold = Number(
                    fac.reconciliation_threshold ?? globalThreshold ?? 20.0,
                  );
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

                  const highestLevel =
                    fac.highest_ogmp_level ||
                    fac.current_ogmp_level ||
                    (matchedSurvey && passThreshold ? 5 : matchedSurvey ? 4 : 3);
                  const isReconciled =
                    fac.is_reconciled !== undefined
                      ? fac.is_reconciled
                      : (highestLevel >= 5 && passThreshold);

                  let statusBadgeClass = "ontrack";
                  let statusText = `On Track (${yearsLeft > 0 ? `${yearsLeft} yrs to Level 5` : "Target Year"})`;
                  if (isReconciled && highestLevel >= 5) {
                    statusBadgeClass = "achieved";
                    statusText = "Gold Standard Achieved (Level 5)";
                  } else if (yearsLeft < 0) {
                    statusBadgeClass = "action";
                    statusText = "Action Plan Required (Overdue)";
                  } else if (yearsLeft === 0) {
                    statusBadgeClass = "ontrack";
                    statusText = "Target Milestone Year (Level 5 Due)";
                  }

                  return (
                    <div
                      key={fac.facility_id || fac.id}
                      className="fac-roadmap-card"
                    >
                      <div className="fac-roadmap-top">
                        <div className="fac-roadmap-info">
                          <span className="fac-roadmap-name">{facName}</span>
                          <span className="fac-roadmap-meta">
                            {opStatus === "operated"
                              ? "Operated Asset (3-Yr Target)"
                              : "Non-Operated Asset (5-Yr Target)"}{" "}
                            • Base: {baseYear} • Target: {targetYear}
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
                      <div className="ogmp-stepper-container">
                        {[1, 2, 3, 4, 5].map((lvl) => {
                          const isDone = highestLevel >= lvl;
                          const isCurrent = highestLevel === lvl;
                          const levelNames = [
                            "L1: Venture",
                            "L2: Segment",
                            "L3: Generic",
                            "L4: Specific",
                            "L5: Reconciled",
                          ];
                          return (
                            <div
                              key={lvl}
                              className={`ogmp-step ${isDone ? "completed" : ""} ${isCurrent ? "current" : ""}`}
                            >
                              <div className="step-circle">
                                {isDone ? "✓" : lvl}
                              </div>
                              <span className="step-name">
                                {levelNames[lvl - 1]}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Footer stats */}
                      <div className="fac-roadmap-stats">
                        <div className="roadmap-stat-item">
                          <span className="roadmap-stat-label">
                            Current Milestone
                          </span>
                          <span className="roadmap-stat-val">
                            OGMP Level {highestLevel}
                          </span>
                        </div>
                        <div className="roadmap-stat-item">
                          <span className="roadmap-stat-label">
                            Reconciliation Var.
                          </span>
                          <span
                            className={`roadmap-stat-val ${variancePct !== null ? (passThreshold ? "variance-pass" : "variance-fail") : ""}`}
                          >
                            {variancePct !== null
                              ? variancePct >= 0
                                ? `+${Number(variancePct).toFixed(1)}%`
                                : `${Number(variancePct).toFixed(1)}%`
                              : "Pending Survey"}
                          </span>
                        </div>
                        <div className="roadmap-stat-item">
                          <span className="roadmap-stat-label">
                            Tolerance Limit
                          </span>
                          <span className="roadmap-stat-val">
                            ±{threshold.toFixed(1)}%{" "}
                            {variancePct !== null
                              ? passThreshold
                                ? "(PASS)"
                                : "(FLAGGED)"
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
