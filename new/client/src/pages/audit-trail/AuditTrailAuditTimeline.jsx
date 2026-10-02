import React from "react";
import { ArrowRight, Calendar, ChevronDown, ChevronUp, Clock, Code, Database, Globe, History, User as UserIcon } from "lucide-react";

// Extracted from AuditTrail.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const AuditTrailAuditTimeline = ({ auditLogs, expandedRows, formatDiffVal, formatFullDateTime, formatTimestamp, getActionConfig, toggleRawData }) => (
<div className="audit-timeline">
            {auditLogs.map((log) => {
              const actConfig = getActionConfig(log.action);
              const isRawExpanded = expandedRows.has(log.id);
              const hasDiff = Boolean(log.old_values || log.new_values);

              return (
                <div key={log.id} className="audit-entry-item">
                  {/* Timeline Visual Node */}
                  <div
                    className="timeline-node"
                    style={{
                      backgroundColor: actConfig.color,
                      boxShadow: `0 0 0 4px ${actConfig.bg}`,
                    }}
                  >
                    {actConfig.icon}
                  </div>
                  <div className="timeline-connector" />

                  {/* Card Content */}
                  <div className="audit-card">
                    {/* Header Row */}
                    <div className="card-top-row">
                      <div className="event-primary-info">
                        <div className="user-badge">
                          <UserIcon size={12} className="badge-user-icon" />
                          <span className="user-name-text">{log.user}</span>
                        </div>

                        <ArrowRight size={12} className="flow-arrow" />

                        <span
                          className="action-pill"
                          style={{
                            backgroundColor: actConfig.bg,
                            color: actConfig.color,
                            borderColor: actConfig.border,
                          }}
                        >
                          {log.action}
                        </span>

                        <span className="entity-tag">{log.entity}</span>
                      </div>

                      <div className="event-timestamp" title={formatFullDateTime(log.timestamp)}>
                        <Clock size={12} style={{ opacity: 0.6 }} />
                        <span>{formatTimestamp(log.timestamp)}</span>
                      </div>
                    </div>

                    {/* Main Description */}
                    <p className="card-description">{log.description || log.details || "No details recorded"}</p>

                    {/* Field-level Before/After Diff Block */}
                    {hasDiff && (
                      <div className="field-diff-container">
                        <div className="field-diff-header">
                          <History size={12} />
                          <span>Field-Level Changes:</span>
                        </div>

                        {typeof log.old_values === "object" &&
                        typeof log.new_values === "object" &&
                        (log.old_values !== null || log.new_values !== null) ? (
                          <div className="diff-fields-grid">
                            {Array.from(
                              new Set([
                                ...Object.keys(log.old_values || {}),
                                ...Object.keys(log.new_values || {}),
                              ]),
                            ).map((key) => {
                              const before = log.old_values?.[key];
                              const after = log.new_values?.[key];
                              return (
                                <div key={key} className="diff-field-row">
                                  <span className="diff-key">{key}:</span>
                                  <span className="diff-before" title={formatDiffVal(before)}>
                                    {formatDiffVal(before)}
                                  </span>
                                  <ArrowRight size={11} className="diff-arrow" />
                                  <span className="diff-after" title={formatDiffVal(after)}>
                                    {formatDiffVal(after)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="diff-text-view">
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
                      <div className="raw-json-viewer">
                        <pre>{JSON.stringify(log, null, 2)}</pre>
                      </div>
                    )}

                    {/* Card Footer Meta */}
                    <div className="card-meta-row">
                      <div className="meta-left-group">
                        <span className="meta-item">
                          <Database size={12} />
                          <span>Ref: #{log.entityId || log.recordId || "N/A"}</span>
                        </span>

                        <span className="meta-item">
                          <Globe size={12} />
                          <span>IP: {log.ipAddress || "Local / System"}</span>
                        </span>

                        <span className="meta-item timestamp-full">
                          <Calendar size={12} />
                          <span>{formatFullDateTime(log.timestamp)}</span>
                        </span>
                      </div>

                      <button
                        className="btn-toggle-raw"
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
