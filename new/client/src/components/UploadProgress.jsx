import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "./Toast";
import "./UploadProgress.css";

/* ── Inline SVG icons (no emoji, no lucide dep needed here) ── */
const Spinner = () => (
  <svg
    className="[width:32px]! [height:32px]! [color:var(--color-link)]! [animation:up-spin_1s_linear_infinite]!"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
    strokeLinecap="round"
  >
    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
  </svg>
);
const IconCheck = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);
const IconWarn = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);
const IconX = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <line x1="15" y1="9" x2="9" y2="15" />
    <line x1="9" y1="9" x2="15" y2="15" />
  </svg>
);
const IconDownload = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);
const IconChevron = ({ open }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{
      width: 16,
      height: 16,
      flexShrink: 0,
      transform: open ? "rotate(90deg)" : "none",
      transition: "transform 0.2s",
    }}
  >
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

/* ── Reason tag colour coding ─────────────────────────────── */
function categoryFromReason(reason = "") {
  const r = reason.toLowerCase();
  if (r.includes("duplicate")) return { label: "Duplicate", cls: "tag-duplicate" };
  if (r.includes("access denied") || r.includes("permission")) return { label: "Access Denied", cls: "tag-access" };
  if (r.includes("facility") || r.includes("region")) return { label: "Region", cls: "tag-facility" };
  if (r.includes("date") || r.includes("year"))
    return { label: "Date", cls: "tag-date" };
  if (r.includes("factor") || r.includes("emission factor"))
    return { label: "Factor", cls: "tag-factor" };
  if (r.includes("quantity")) return { label: "Quantity", cls: "tag-quantity" };
  if (r.includes("process")) return { label: "Process", cls: "tag-process" };
  if (r.includes("calculation"))
    return { label: "Calculation", cls: "tag-calc" };
  return { label: "Other", cls: "tag-other" };
}

/* ── Main component ──────────────────────────────────────── */
// reviewable: the import creates emission records that wait for approval (Scope 1 / 2 / 3)
const UploadProgress = ({ jobId, onComplete, onCancel, reviewable = true }) => {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const isReviewer = ["admin", "superuser"].includes(user?.role);

  const [status, setStatus] = useState("processing");
  const [progress, setProgress] = useState(0);
  const [processed, setProcessed] = useState(0);
  const [total, setTotal] = useState(0);
  const [errors, setErrors] = useState([]);
  const [skippedCount, setSkippedCount] = useState(0);
  const [skippedPreview, setSkippedPreview] = useState([]);
  const [hasErrorCsv, setHasErrorCsv] = useState(false);
  const [showReasons, setShowReasons] = useState(false);
  const [filterCategory, setFilterCategory] = useState("all");
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [anomalies, setAnomalies] = useState([]);
  const [showAnomalies, setShowAnomalies] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/emissions/upload/status/${jobId}`);
        const data = res.data;
        setStatus(data.status);
        setProgress(data.progress || 0);
        setProcessed(data.processed || 0);
        setTotal(data.total || 0);
        setErrors(data.errors || []);
        setSkippedCount(data.skipped_count || 0);
        setSkippedPreview(data.skipped_preview || []);
        setHasErrorCsv(!!(data.has_error_csv ?? data.error_csv_path));
        setAnomalyCount(data.anomaly_count || 0);
        setAnomalies(data.anomalies || []);
        if (data.status === "completed" || data.status === "error") {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Upload status poll failed", err);
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [jobId]);

  const downloadErrors = async () => {
    try {
      const res = await api.get(`/emissions/upload/errors/${jobId}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `skipped_rows_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      toast.error("Failed to download error CSV.");
    }
  };

  /* ── categories present in this batch ── */
  const categories = [
    "all",
    ...new Set(skippedPreview.map((r) => categoryFromReason(r.reason).label)),
  ];

  const filtered =
    filterCategory === "all"
      ? skippedPreview
      : skippedPreview.filter(
          (r) => categoryFromReason(r.reason).label === filterCategory,
        );

  const successCount = processed - skippedCount;

  return (
    <div className="[width:100%]! [max-width:900px]! [margin:0_auto]! [font-family:inherit]! [color:var(--color-ink-800)]! [animation:up-fade-in_0.25s_ease-out]!">
      {/* ── PROCESSING ── */}
      {status === "processing" && (
        <div className="[background:var(--color-white)]! [border-radius:var(--radius-md)]! [padding:24px]! [border:1px_solid_var(--color-ink-200)]! [box-shadow:var(--shadow-xs)]!">
          <div className="[display:flex]! [align-items:center] [gap:16px] [margin-bottom:24px]!">
            <Spinner />
            <div>
              <p className="[font-size:var(--text-md)]! [font-weight:600]! [margin:0_0_4px_0]! [color:var(--color-ink-900)]!">Processing your file…</p>
              <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]!">
                Large files may take several minutes. You can safely leave this
                page.
              </p>
            </div>
          </div>
          <div className="[width:100%]! [height:8px]! [background:var(--color-ink-100)]! [border-radius:var(--radius-sm)]! [overflow:hidden]! [margin-bottom:12px]!">
            <div className="[height:100%]! [background:linear-gradient(90deg,_var(--color-brand-500)_0%,_var(--color-brand-400)_100%)]! [border-radius:var(--radius-sm)]! [transition:width_0.4s_ease-out]! [box-shadow:0_0_8px_rgba(255,_102,_0,_0.35)]!" style={{ width: `${progress}%` }} />
          </div>
          <div className="[display:flex]! [justify-content:space-between] [font-size:var(--text-base)]! [color:var(--color-ink-600)]! [font-weight:500]!">
            <span className="[color:var(--color-link)]! [font-weight:600]!">{progress}%</span>
            <span className="up-rows">
              {processed.toLocaleString()} rows processed
              {total > 0 ? ` of ~${total.toLocaleString()}` : ""}
            </span>
          </div>
          {skippedCount > 0 && (
            <div className="up-live-skip">
              <IconWarn />
              <span>{skippedCount.toLocaleString()} rows skipped so far</span>
            </div>
          )}
        </div>
      )}

      {/* ── COMPLETED ── */}
      {status === "completed" && (
        <div className="[background:var(--color-white)]! [border-radius:var(--radius-md)]! [padding:24px]! [border:1px_solid_var(--color-ink-200)]! [box-shadow:var(--shadow-xs)]!">
          {/* Summary cards */}
          <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))] [gap:16px] [margin-bottom:24px]!">
            <div className="up-card up-card--success">
              <div className="up-card-icon">
                <IconCheck />
              </div>
              <div>
                <p className="[font-size:var(--text-xl)]! [font-weight:700]! [margin:0_0_2px_0]! [color:var(--color-ink-900)]! [line-height:1]">{successCount.toLocaleString()}</p>
                <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [font-weight:500]!">Rows Imported</p>
              </div>
            </div>
            <div
              className={`up-card ${skippedCount > 0 ? "up-card--warn" : "up-card--neutral"}`}
            >
              <div className="up-card-icon">
                <IconWarn />
              </div>
              <div>
                <p className="[font-size:var(--text-xl)]! [font-weight:700]! [margin:0_0_2px_0]! [color:var(--color-ink-900)]! [line-height:1]">{skippedCount.toLocaleString()}</p>
                <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [font-weight:500]!">Rows Skipped</p>
              </div>
            </div>
            <div className="up-card up-card--neutral">
              <div className="up-card-icon">
                <IconCheck />
              </div>
              <div>
                <p className="[font-size:var(--text-xl)]! [font-weight:700]! [margin:0_0_2px_0]! [color:var(--color-ink-900)]! [line-height:1]">{processed.toLocaleString()}</p>
                <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [font-weight:500]!">Total Processed</p>
              </div>
            </div>
          </div>

          {/* Skipped reasons panel */}
          {skippedCount > 0 && (
            <div className="up-skip-panel">
              <div className="[display:flex]! [align-items:center] [width:100%]! [background:var(--color-ink-50)]! [border-bottom:1px_solid_transparent]!">
                <button
                  className="up-skip-toggle"
                  onClick={() => setShowReasons((v) => !v)}
                >
                  <IconChevron open={showReasons} />
                  <span>
                    {skippedCount.toLocaleString()} rows skipped — click to see
                    reasons
                    {skippedCount > 100 && " (showing first 100)"}
                  </span>
                </button>
                {hasErrorCsv && (
                  <button
                    className="up-dl-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      downloadErrors();
                    }}
                  >
                    <IconDownload /> Download full CSV
                  </button>
                )}
              </div>

              {showReasons && (
                <div className="up-reasons-body">
                  {/* Category filter pills */}
                  {categories.length > 2 && (
                    <div className="[display:flex]! [flex-wrap:wrap] [gap:8px] [padding:16px_20px]! [border-bottom:1px_solid_var(--color-ink-200)]! [background:#fafaf9]!">
                      {categories.map((cat) => (
                        <button
                          key={cat}
                          className={`up-pill ${filterCategory === cat ? "active" : ""}`}
                          onClick={() => setFilterCategory(cat)}
                        >
                          {cat === "all"
                            ? `All (${skippedPreview.length})`
                            : cat}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Reasons table */}
                  <div className="[max-height:400px]! [overflow:auto]!">
                    <table className="up-reasons-table">
                      <thead>
                        <tr>
                          <th>Row #</th>
                          <th>Category</th>
                          <th>Reason</th>
                          <th>Year</th>
                          <th>Month</th>
                          <th>Facility</th>
                          <th>Process</th>
                          <th>Fuel</th>
                          <th>Quantity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((row, i) => {
                          const cat = categoryFromReason(row.reason);
                          return (
                            <tr key={i}>
                              <td className="[font-family:monospace]! [color:var(--color-ink-600)]! [font-weight:500]! [width:60px]!">{row.row}</td>
                              <td>
                                <span className={`up-tag ${cat.cls}`}>
                                  {cat.label}
                                </span>
                              </td>
                              <td className="[font-weight:500]! [color:var(--color-red-700)]! [max-width:250px]! [line-height:1.4]">{row.reason}</td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]! [font-family:monospace]! [font-weight:600]! [color:var(--color-ink-700)]! [width:52px]! [text-align:center]!">
                                {row.year || (row.date ? row.date.split("-")[0] : "—")}
                              </td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]! [font-family:monospace]! [font-weight:600]! [color:var(--color-ink-700)]! [width:52px]! [text-align:center]!">
                                {row.month || (row.date ? row.date.split("-")[1] : "—")}
                              </td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">
                                {row.facility || "—"}
                              </td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">
                                {row.process || "—"}
                              </td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">{row.fuel || "—"}</td>
                              <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">
                                {row.quantity || "—"}
                              </td>
                            </tr>
                          );
                        })}
                        {filtered.length === 0 && (
                          <tr>
                            <td colSpan={9} className="[text-align:center]! [padding:32px]! [color:var(--color-ink-600)]!">
                              No rows match this filter.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Anomaly Warnings Panel ── */}
          {anomalyCount > 0 && (
            <div className="[background:#fefce8]! [border:1px_solid_#fef08a]! [border-radius:var(--radius-md)]! [margin-bottom:24px]! [overflow:hidden]!">
              <button
                className="up-anomaly-toggle"
                onClick={() => setShowAnomalies((v) => !v)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[16px]! h-[16px]! shrink-0!">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span>
                  {anomalyCount} statistical anomaly{anomalyCount !== 1 ? "s" : ""} detected — click to review
                </span>
                <IconChevron open={showAnomalies} />
              </button>
              {showAnomalies && (
                <div className="[padding:16px]! [border-top:1px_solid_#fef08a]!">
                  <p className="[font-size:var(--text-base)]! [color:#713f12]! [margin:0_0_12px_0]! [line-height:1.4]">
                    These rows were imported but deviate significantly from historical values for the same facility and process type.
                    Please review them carefully before approving.
                  </p>
                  <div className="[max-height:400px]! [overflow:auto]!">
                    <table className="up-reasons-table">
                      <thead>
                        <tr>
                          <th>Row #</th>
                          <th>Facility</th>
                          <th>Value (tCO2e)</th>
                          <th>Z-Score</th>
                          <th>Expected Range</th>
                          <th>Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {anomalies.map((a, i) => (
                          <tr key={i} className="[background:var(--color-amber-50)]! hover:[background:#fef3c7]!">
                            <td className="[font-family:monospace]! [color:var(--color-ink-600)]! [font-weight:500]! [width:60px]!">{a.row}</td>
                            <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">{a.facility_id || "—"}</td>
                            <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]! text-[color:var(--up-warn)]!">
                              {typeof a.value === "number" ? a.value.toFixed(2) : a.value}
                            </td>
                            <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">
                              {a.z_score != null ? `±${Math.abs(a.z_score).toFixed(1)}σ` : "—"}
                            </td>
                            <td className="[color:var(--color-ink-500)]! [max-width:120px]! [white-space:nowrap] [overflow:hidden]! [text-overflow:ellipsis]!">
                              {a.expected_range
                                ? `${a.expected_range[0].toFixed(1)} – ${a.expected_range[1].toFixed(1)}`
                                : "—"}
                            </td>
                            <td className="[font-weight:500]! [color:var(--color-red-700)]! [max-width:250px]! [line-height:1.4] text-[length:0.75rem]!">
                              {a.message || "Statistical outlier"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="[display:flex]! [align-items:center] [justify-content:flex-end] [gap:12px] [margin-top:24px]!">
            {isReviewer ? (
              <>
                <button
                  type="button"
                  className="[padding:10px_20px]! [background:transparent]! [color:var(--color-ink-500)]! [border:1px_solid_var(--color-ink-300)]! [border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:600]! [cursor:pointer] [transition:all_0.2s]! hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-700)]!"
                  onClick={() => {
                    if (onComplete) onComplete();
                  }}
                >
                  Close
                </button>
                {reviewable && (
                  <button
                    type="button"
                    className="[padding:10px_20px]! [background:var(--primary-gradient)]! [color:var(--color-white)]! [border:none]! [border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:600]! [cursor:pointer] [transition:all_0.18s]! [box-shadow:0_2px_8px_rgba(255,_102,_0,_0.25)]! [font-family:inherit]! hover:[background:var(--primary-gradient)]! hover:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.35)]! hover:[transform:translateY(-1px)]"
                    onClick={() => {
                      if (onComplete) onComplete();
                      navigate("/manage-data", { state: { tab: "pending" } });
                    }}
                  >
                    Review Pending Records →
                  </button>
                )}
              </>
            ) : (
              <button
                type="button"
                className="[padding:10px_20px]! [background:var(--primary-gradient)]! [color:var(--color-white)]! [border:none]! [border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:600]! [cursor:pointer] [transition:all_0.18s]! [box-shadow:0_2px_8px_rgba(255,_102,_0,_0.25)]! [font-family:inherit]! hover:[background:var(--primary-gradient)]! hover:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.35)]! hover:[transform:translateY(-1px)]"
                onClick={() => {
                  if (onComplete) onComplete();
                }}
              >
                Close & View Inventory
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── FATAL ERROR ── */}
      {status === "error" && (
        <div className="[background:var(--color-white)]! [border-radius:var(--radius-md)]! [padding:24px]! [border:1px_solid_var(--color-ink-200)]! [box-shadow:var(--shadow-xs)]!">
          <div className="[display:flex]! [align-items:flex-start] [gap:16px] [margin-bottom:20px]!">
            <div className="up-fatal-icon">
              <IconX />
            </div>
            <div>
              <p className="[font-size:var(--text-md)]! [font-weight:600]! [margin:0_0_4px_0]! [color:var(--color-ink-900)]! [color:var(--color-red-700)]!">Upload Failed</p>
              <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]!">
                A fatal error occurred while processing the file.
              </p>
            </div>
          </div>
          <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:16px]! [margin-bottom:24px]! [max-height:200px]! [overflow-y:auto]! [font-family:monospace]! [font-size:var(--text-sm)]! [color:var(--color-ink-700)]!">
            {errors.map((e, i) => (
              <div key={i} className="[display:flex]! [align-items:flex-start] [gap:8px] [margin-bottom:8px]! [line-height:1.4] last:[margin-bottom:0]!">
                <span className="[width:6px]! [height:6px]! [border-radius:50%]! [background:var(--color-red-600)]! [margin-top:6px]! [flex-shrink:0]" />
                {e}
              </div>
            ))}
          </div>
          <button className="[padding:10px_20px]! [background:transparent]! [color:var(--color-ink-500)]! [border:1px_solid_var(--color-ink-300)]! [border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:600]! [cursor:pointer] [transition:all_0.2s]! hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-700)]!" onClick={onCancel}>
            Go Back
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadProgress;
