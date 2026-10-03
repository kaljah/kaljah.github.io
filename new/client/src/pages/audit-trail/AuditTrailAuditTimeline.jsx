import React from "react";
import { ArrowRight, Calendar, ChevronDown, ChevronUp, Clock, Code, Database, Globe, History, User as UserIcon } from "lucide-react";

// Extracted from AuditTrail.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const AuditTrailAuditTimeline = ({ auditLogs, expandedRows, formatDiffVal, formatFullDateTime, formatTimestamp, getActionConfig, toggleRawData }) => (
<div className="[position:relative] [display:flex]! [flex-direction:column] [gap:20px]">
            {auditLogs.map((log) => {
              const actConfig = getActionConfig(log.action);
              const isRawExpanded = expandedRows.has(log.id);
              const hasDiff = Boolean(log.old_values || log.new_values);

              return (
                <div key={log.id} className="[display:flex]! [gap:24px] [position:relative] [&:hover_.timeline-node]:[transform:scale(1.06)]! [&:last-child_.timeline-connector]:[display:none]! [@media(max-width:768px)]:[gap:14px]!">
                  {/* Timeline Visual Node */}
                  <div
                    className="timeline-node [width:40px]! [height:40px]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-white)]! [flex-shrink:0] [z-index:2] [transition:transform_0.2s_ease]! [@media(max-width:768px)]:[width:34px]! [@media(max-width:768px)]:[height:34px]!"
                    style={{
                      backgroundColor: actConfig.color,
                      boxShadow: `0 0 0 4px ${actConfig.bg}`,
                    }}
                  >
                    {actConfig.icon}
                  </div>
                  <div className="timeline-connector [position:absolute] [left:19px] [top:40px] [bottom:-20px] [width:2px]! [background:var(--color-ink-200)]! [z-index:1] [@media(max-width:768px)]:[left:16px]!" />

                  {/* Card Content */}
                  <div className="[flex:1] [background:var(--bg-card,_var(--color-white))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [border-radius:var(--radius-lg)]! [padding:18px_22px]! [box-shadow:var(--shadow-xs)]! [transition:all_0.2s_ease]! hover:[border-color:rgba(99,_102,_241,_0.4)]! hover:[box-shadow:var(--shadow-card)]! hover:[transform:translateX(3px)]">
                    {/* Header Row */}
                    <div className="[display:flex]! [justify-content:space-between] [align-items:center] [margin-bottom:10px]! [flex-wrap:wrap] [gap:8px] [@media(max-width:768px)]:[flex-direction:column]! [@media(max-width:768px)]:[align-items:flex-start]!">
                      <div className="[display:flex]! [align-items:center] [gap:10px] [flex-wrap:wrap]">
                        <div className="[display:inline-flex]! [align-items:center] [gap:6px] [background:rgba(241,_245,_249,_0.9)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:3px_8px]!">
                          <UserIcon size={12} className="[color:var(--color-ink-500)]!" />
                          <span className="[font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-ink-800)]!">{log.user}</span>
                        </div>

                        <ArrowRight size={12} className="[color:var(--color-ink-300)]!" />

                        <span
                          className="[font-size:var(--text-xs)]! [font-weight:800]! [text-transform:uppercase]! [letter-spacing:0.06em] [padding:3px_8px]! [border-radius:var(--radius-sm)]! [border:1px_solid]!"
                          style={{
                            backgroundColor: actConfig.bg,
                            color: actConfig.color,
                            borderColor: actConfig.border,
                          }}
                        >
                          {log.action}
                        </span>

                        <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-500)]! [background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [padding:2px_8px]! [border-radius:var(--radius-sm)]!">{log.entity}</span>
                      </div>

                      <div className="[display:flex]! [align-items:center] [gap:6px] [font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [font-weight:500]!" title={formatFullDateTime(log.timestamp)}>
                        <Clock size={12} className="opacity-[0.6]!" />
                        <span>{formatTimestamp(log.timestamp)}</span>
                      </div>
                    </div>

                    {/* Main Description */}
                    <p className="[margin:0_0_12px_0]! [color:var(--color-ink-700)]! [font-size:var(--text-md)]! [line-height:1.55]">{log.description || log.details || "No details recorded"}</p>

                    {/* Field-level Before/After Diff Block */}
                    {hasDiff && (
                      <div className="[background:rgba(248,_250,_252,_0.95)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:10px_14px]! [margin-bottom:12px]!">
                        <div className="[display:flex]! [align-items:center] [gap:6px] [font-size:var(--text-sm)]! [font-weight:700]! [text-transform:uppercase]! [letter-spacing:0.04em] [color:var(--color-ink-600)]! [margin-bottom:8px]!">
                          <History size={12} />
                          <span>Field-Level Changes:</span>
                        </div>

                        {typeof log.old_values === "object" &&
                        typeof log.new_values === "object" &&
                        (log.old_values !== null || log.new_values !== null) ? (
                          <div className="[display:flex]! [flex-direction:column] [gap:6px]">
                            {Array.from(
                              new Set([
                                ...Object.keys(log.old_values || {}),
                                ...Object.keys(log.new_values || {}),
                              ]),
                            ).map((key) => {
                              const before = log.old_values?.[key];
                              const after = log.new_values?.[key];
                              return (
                                <div key={key} className="[display:flex]! [align-items:center] [gap:8px] [font-size:var(--text-sm)]! [font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]!">
                                  <span className="[font-weight:700]! [color:var(--color-ink-700)]! [min-width:90px]">{key}:</span>
                                  <span className="[color:var(--color-red-700)]! [background:#fee2e2]! [padding:2px_6px]! [border-radius:var(--radius-sm)]! [text-decoration:line-through]! [max-width:280px]! [overflow:hidden]! [text-overflow:ellipsis]! [white-space:nowrap]" title={formatDiffVal(before)}>
                                    {formatDiffVal(before)}
                                  </span>
                                  <ArrowRight size={11} className="[color:var(--color-ink-600)]! [flex-shrink:0]" />
                                  <span className="[color:var(--color-green-700)]! [background:#dcfce7]! [padding:2px_6px]! [border-radius:var(--radius-sm)]! [font-weight:600]! [max-width:280px]! [overflow:hidden]! [text-overflow:ellipsis]! [white-space:nowrap]" title={formatDiffVal(after)}>
                                    {formatDiffVal(after)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [display:flex]! [flex-direction:column] [gap:4px]">
                            {log.old_values && (
                              <div>
                                <strong>Before:</strong> {formatDiffVal(log.old_values)}
                              </div>
                            )}
                            {log.new_values && (
                              <div>
                                <strong>After:</strong> {formatDiffVal(log.new_values)}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Expandable Technical Raw JSON */}
                    {isRawExpanded && (
                      <div className="[background:var(--color-ink-900)]! [color:var(--color-ink-50)]! [padding:12px_16px]! [border-radius:var(--radius-md)]! [margin-bottom:12px]! [overflow-x:auto]! [&_pre]:[margin:0]! [&_pre]:[font-size:var(--text-sm)]! [&_pre]:[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [&_pre]:[line-height:1.4]!">
                        <pre>{JSON.stringify(log, null, 2)}</pre>
                      </div>
                    )}

                    {/* Card Footer Meta */}
                    <div className="[display:flex]! [justify-content:space-between] [align-items:center] [padding-top:10px]! [border-top:1px_solid_var(--color-ink-100)]! [font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [flex-wrap:wrap] [gap:8px] [@media(max-width:768px)]:[flex-direction:column]! [@media(max-width:768px)]:[align-items:flex-start]!">
                      <div className="[display:flex]! [align-items:center] [gap:16px] [flex-wrap:wrap]">
                        <span className="[display:flex]! [align-items:center] [gap:5px] [color:var(--color-ink-500)]! [font-weight:500]!">
                          <Database size={12} />
                          <span>Ref: #{log.entityId || log.recordId || "N/A"}</span>
                        </span>

                        <span className="[display:flex]! [align-items:center] [gap:5px] [color:var(--color-ink-500)]! [font-weight:500]!">
                          <Globe size={12} />
                          <span>IP: {log.ipAddress || "Local / System"}</span>
                        </span>

                        <span className="[display:flex]! [align-items:center] [gap:5px] [color:var(--color-ink-500)]! [font-weight:500]! [color:var(--color-ink-600)]!">
                          <Calendar size={12} />
                          <span>{formatFullDateTime(log.timestamp)}</span>
                        </span>
                      </div>

                      <button
                        className="[display:inline-flex]! [align-items:center] [gap:4px] [padding:4px_8px]! [background:transparent]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-sm)]! [color:var(--color-ink-500)]! [font-size:var(--text-xs)]! [font-weight:600]! [cursor:pointer] [transition:all_0.15s_ease]! hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-800)]!"
                        onClick={() => toggleRawData(log.id)}
                        title="Toggle Technical Audit JSON"
                      >
                        <Code size={12} />
                        <span>{isRawExpanded ? "Hide Raw" : "Raw JSON"}</span>
                        {isRawExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
);

export default AuditTrailAuditTimeline;
