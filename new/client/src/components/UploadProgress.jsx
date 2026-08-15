import React, { useState, useEffect } from "react";
import api from "../api";
import "./UploadProgress.css";

/* ── Inline SVG icons (no emoji, no lucide dep needed here) ── */
const Spinner = () => (
  <svg
    className="up-spinner"
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
const UploadProgress = ({ jobId, onComplete, onCancel }) => {
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
        setHasErrorCsv(!!data.error_csv_path);
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
      alert("Failed to download error CSV.");
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
    <div className="up-root">
      {/* ── PROCESSING ── */}
      {status === "processing" && (
        <div className="up-section">
          <div className="up-processing-header">
            <Spinner />
            <div>
              <p className="up-label">Processing your file…</p>
              <p className="up-sub">
                Large files may take several minutes. You can safely leave this
                page.
              </p>
            </div>
          </div>
          <div className="up-bar-track">
            <div className="up-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="up-bar-stats">
            <span className="up-pct">{progress}%</span>
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
        <div className="up-section">
          {/* Summary cards */}
          <div className="up-summary-cards">
            <div className="up-card up-card--success">
              <div className="up-card-icon">
                <IconCheck />
              </div>
              <div>
                <p className="up-card-num">{successCount.toLocaleString()}</p>
                <p className="up-card-lbl">Rows Imported</p>
              </div>
            </div>
            <div
              className={`up-card ${skippedCount > 0 ? "up-card--warn" : "up-card--neutral"}`}
            >
              <div className="up-card-icon">
                <IconWarn />
              </div>
              <div>
                <p className="up-card-num">{skippedCount.toLocaleString()}</p>
                <p className="up-card-lbl">Rows Skipped</p>
              </div>
            </div>
            <div className="up-card up-card--neutral">
              <div className="up-card-icon">
                <IconCheck />
              </div>
              <div>
                <p className="up-card-num">{processed.toLocaleString()}</p>
                <p className="up-card-lbl">Total Processed</p>
              </div>
            </div>
          </div>

          {/* Skipped reasons panel */}
          {skippedCount > 0 && (
            <div className="up-skip-panel">
              <div className="up-skip-toggle-row">
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
                    <div className="up-filter-pills">
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
                  <div className="up-reasons-table-wrap">
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
                              <td className="up-td-row">{row.row}</td>
                              <td>
                                <span className={`up-tag ${cat.cls}`}>
                                  {cat.label}
                                </span>
                              </td>
                              <td className="up-td-reason">{row.reason}</td>
                              <td className="up-td-meta up-td-year">
                                {row.year || (row.date ? row.date.split("-")[0] : "—")}
                              </td>
                              <td className="up-td-meta up-td-month">
                                {row.month || (row.date ? row.date.split("-")[1] : "—")}
                              </td>
                              <td className="up-td-meta">
                                {row.facility || "—"}
                              </td>
                              <td className="up-td-meta">
                                {row.process || "—"}
                              </td>
                              <td className="up-td-meta">{row.fuel || "—"}</td>
                              <td className="up-td-meta">
                                {row.quantity || "—"}
                              </td>
                            </tr>
                          );
                        })}
                        {filtered.length === 0 && (
                          <tr>
                            <td colSpan={9} className="up-empty">
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

          <div className="up-footer-actions">
            <button className="up-btn-primary" onClick={onComplete}>
              View Dashboard
            </button>
          </div>
        </div>
      )}

      {/* ── FATAL ERROR ── */}
      {status === "error" && (
        <div className="up-section">
          <div className="up-fatal-header">
            <div className="up-fatal-icon">
              <IconX />
            </div>
            <div>
              <p className="up-label up-label--error">Upload Failed</p>
              <p className="up-sub">
                A fatal error occurred while processing the file.
              </p>
            </div>
          </div>
          <div className="up-error-log">
            {errors.map((e, i) => (
              <div key={i} className="up-error-line">
                <span className="up-error-bullet" />
                {e}
              </div>
            ))}
          </div>
          <button className="up-btn-ghost" onClick={onCancel}>
            Go Back
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadProgress;
