import React from "react";
import { AlertTriangle, Award, Calendar, Check, ChevronDown, ChevronUp } from "lucide-react";

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityOGMP20Gold = ({ facilities, globalThreshold, ogmpRoadmapData, ogmpSurveys, roadmapCollapsed, selectedBaselineYear, selectedYear, setRoadmapCollapsed, setSelectedBaselineYear }) => (
<div
          className={`[background:var(--bg-card)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:28px] [box-shadow:var(--card-shadow)] [display:flex] [flex-direction:column] [gap:22px] [transition:gap_0.3s_ease] [&.collapsed-card]:[gap:0] ${roadmapCollapsed ? "collapsed-card" : ""}`}
        >
          <div role="presentation"
            className="[display:flex] [justify-content:space-between] [align-items:center] [flex-wrap:wrap] [gap:16px] [padding-bottom:18px] [border-bottom:1px_solid_var(--border-color)]"
            onClick={() => setRoadmapCollapsed(!roadmapCollapsed)}
            style={{ cursor: "pointer", userSelect: "none" }}
          >
            <div className="[display:flex] [flex-direction:column] [gap:4px] [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:700]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]! [&_h3]:[display:flex] [&_h3]:[align-items:center] [&_h3]:[gap:10px] [&&]:[&&]:[&_p]:[font-size:var(--text-base)]! [&&]:[&_p]:[color:var(--text-secondary)]! [&&]:[&_p]:[margin:0]!">
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
              <div role="presentation"
                className="[display:flex] [align-items:center] [gap:10px] [background:var(--bg-app)] [padding:6px_12px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color)]"
                onClick={(e) => e.stopPropagation()}
              >
                <span className="[font-size:var(--text-sm)] [font-weight:600] [color:var(--text-secondary)]">
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
                <div className="[display:flex] [gap:6px]">
                  {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((yr) => (
                    <button
                      key={yr}
                      type="button"
                      className={`[background:var(--bg-card)]! [border:1px_solid_var(--border-color)]! [color:var(--text-primary)]! [font-size:var(--text-sm)] [font-weight:600] [padding:4px_10px] [&&]:[border-radius:var(--radius-sm)]! [cursor:pointer] [transition:all_0.2s_ease] hover:[border-color:var(--accent-secondary)]! hover:[color:var(--accent-secondary)]! [&.active]:[background:var(--accent-secondary)]! [&.active]:[color:var(--color-white)]! [&.active]:[border-color:var(--accent-secondary)]! [&.active]:[box-shadow:0_2px_8px_rgba(37,_99,_235,_0.3)]! ${selectedBaselineYear === yr ? "active" : ""}`}
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
            className={`[max-height:2500px] [opacity:1] [overflow:hidden] [transition:max-height_0.45s_cubic-bezier(0.4,_0,_0.2,_1),_opacity_0.3s_ease,_margin-top_0.3s_ease] [&.collapsed]:[max-height:0] [&.collapsed]:[opacity:0] [&.collapsed]:[margin-top:0] [&.collapsed]:[pointer-events:none] ${roadmapCollapsed ? "collapsed" : ""}`}
          >
            {/* Facility Roadmap Cards Grid */}
            <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(480px,_1fr))] [gap:20px]">
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
                      className="[background:var(--bg-app)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-md)] [padding:20px] [display:flex] [flex-direction:column] [gap:16px] [transition:transform_0.2s,_box-shadow_0.2s] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--card-shadow-hover)]"
                    >
                      <div className="[display:flex] [justify-content:space-between] [align-items:flex-start] [gap:12px]">
                        <div className="[display:flex] [flex-direction:column] [gap:2px]">
                          <span className="[font-size:var(--text-md)] [font-weight:700] [color:var(--text-primary)]">{facName}</span>
                          <span className="[font-size:var(--text-sm)] [color:var(--text-secondary)]">
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
                      <div className="[display:flex] [justify-content:space-between] [position:relative] [padding:10px_0] before:[content:''] before:[position:absolute] before:[top:24px] before:[left:20px] before:[right:20px] before:[height:3px] before:[background:var(--border-color)] before:[z-index:1]">
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
                              className={`[position:relative] [z-index:2] [display:flex] [flex-direction:column] [align-items:center] [gap:6px] [text-align:center] [width:70px] [&.completed_.step-circle]:[background:var(--color-green-700)] [&.completed_.step-circle]:[border-color:var(--color-green-500)] [&.completed_.step-circle]:[color:var(--color-white)] [&.completed_.step-circle]:[box-shadow:0_0_10px_rgba(16,_185,_129,_0.4)] [&&]:[&.current_.step-circle]:[background:var(--accent-secondary)] [&&]:[&.current_.step-circle]:[border-color:var(--accent-secondary)] [&&]:[&.current_.step-circle]:[color:var(--color-white)] [&&]:[&.current_.step-circle]:[box-shadow:0_0_10px_rgba(37,_99,_235,_0.4)] [&.current_.step-circle]:[transform:scale(1.15)] [&&]:[&&]:[&.current_.step-name]:[color:var(--accent-secondary)] [&.current_.step-name]:[font-weight:700] [&&]:[&&]:[&&]:[&.completed_.step-name]:[color:var(--color-green-700)] ${isDone ? "completed" : ""} ${isCurrent ? "current" : ""}`}
                            >
                              <div className="step-circle [width:28px] [height:28px] [border-radius:50%] [background:var(--bg-card)] [border:2px_solid_var(--border-color)] [display:flex] [align-items:center] [justify-content:center] [font-size:var(--text-sm)] [font-weight:700] [color:var(--text-secondary)] [transition:all_0.25s_ease]">
                                {isDone ? "✓" : lvl}
                              </div>
                              <span className="step-name [font-size:var(--text-xs)] [font-weight:600] [color:var(--text-secondary)] [line-height:1.2]">
                                {levelNames[lvl - 1]}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Footer stats */}
                      <div className="[display:grid] [grid-template-columns:repeat(3,_1fr)] [gap:10px] [background:var(--bg-card)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-md)] [padding:10px_12px]">
                        <div className="[display:flex] [flex-direction:column] [gap:2px]">
                          <span className="[font-size:var(--text-xs)] [color:var(--text-secondary)] [font-weight:500]">
                            Current Milestone
                          </span>
                          <span className="[font-size:var(--text-base)] [font-weight:700] [color:var(--text-primary)] [&.variance-pass]:[color:var(--color-green-700)] [&&]:[&.variance-fail]:[color:var(--color-red-700)]">
                            OGMP Level {highestLevel}
                          </span>
                        </div>
                        <div className="[display:flex] [flex-direction:column] [gap:2px]">
                          <span className="[font-size:var(--text-xs)] [color:var(--text-secondary)] [font-weight:500]">
                            Reconciliation Var.
                          </span>
                          <span
                            className={`[font-size:var(--text-base)] [font-weight:700] [color:var(--text-primary)] [&.variance-pass]:[color:var(--color-green-700)] [&&]:[&.variance-fail]:[color:var(--color-red-700)] ${variancePct !== null ? (passThreshold ? "variance-pass" : "variance-fail") : ""}`}
                          >
                            {variancePct !== null
                              ? variancePct >= 0
                                ? `+${Number(variancePct).toFixed(1)}%`
                                : `${Number(variancePct).toFixed(1)}%`
                              : "Pending Survey"}
                          </span>
                        </div>
                        <div className="[display:flex] [flex-direction:column] [gap:2px]">
                          <span className="[font-size:var(--text-xs)] [color:var(--text-secondary)] [font-weight:500]">
                            Tolerance Limit
                          </span>
                          <span className="[font-size:var(--text-base)] [font-weight:700] [color:var(--text-primary)] [&.variance-pass]:[color:var(--color-green-700)] [&&]:[&.variance-fail]:[color:var(--color-red-700)]">
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
