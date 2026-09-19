import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import Papa from "papaparse";
import api from "../api";
import { useToast } from "./Toast";
import UploadProgress from "./UploadProgress";
import "./Scope1ImportWizard.css"; // Reuse the same CSS for identical aesthetic

// ─── SVG Icon Library ────────────────────────────────────────────────────────
const Icon = {
  Close: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  ChevronRight: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  ChevronDown: ({ open }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  ArrowLeft: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  Upload: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  ),
  File: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  FileExcel: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="10" y2="13" /><line x1="14" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="16" y2="17" />
    </svg>
  ),
  Wand: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 4V2m0 14v-2M8 9H2m14 0h-2M3.5 3.5l1.5 1.5M16.5 16.5l1.5 1.5M16.5 3.5 15 5M3.5 20.5 5 19" />
      <path d="m3 9 9 9 9-9-9-9Z" />
    </svg>
  ),
  Search: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  Warning: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  Zap: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  Columns: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" /><line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  ),
  Processing: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  Layers: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  ),
  Activity: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
};

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
    ],
  },
  {
    id: "measurement",
    label: "Measurement & Type",
    IconComp: Icon.Activity,
    fields: [
      { key: "source_type",   label: "Source Type",   required: false, hint: "electricity, indirect_steam, or cogen_allocation" },
      { key: "grid_region",   label: "Grid Region",   required: true,  hint: "E.g. SONELGAZ, REB_GRID. Required for electricity." },
      { key: "consumption",   label: "Consumption",   required: true,  hint: "Amount of electricity/steam purchased" },
      { key: "unit",          label: "Unit",          required: true,  hint: "e.g. kWh, MWh, MMBtu" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  }
];

// ─── Step definitions ────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Select File",    IconComp: Icon.Upload    },
  { id: 2, label: "Map Columns",    IconComp: Icon.Columns   },
  { id: 3, label: "Import",         IconComp: Icon.Processing },
];

// ─── Step Indicator ───────────────────────────────────────────────────────────
function StepBar({ current }) {
  return (
    <div className="s1w-stepbar">
      {STEPS.map((s, i) => {
        const done   = s.id < current;
        const active = s.id === current;
        const SIcon  = s.IconComp;
        return (
          <React.Fragment key={s.id}>
            <div className={`s1w-step ${active ? "active" : ""} ${done ? "done" : ""}`}>
              <div className="s1w-step-circle">
                {done ? <Icon.Check /> : <SIcon />}
              </div>
              <span className="s1w-step-label">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`s1w-step-line ${done ? "done" : ""}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Mapping Row ──────────────────────────────────────────────────────────────
function MappingRow({ field, headers, value, onChange }) {
  const mapped = !!value;
  return (
    <div className={`s1w-map-row ${!mapped && field.required ? "s1w-map-row--missing" : ""} ${mapped ? "s1w-map-row--mapped" : ""}`}>
      <div className="s1w-map-field">
        <span className="s1w-map-field-label">
          {field.label}
          {field.required && <span className="s1w-required-dot" />}
        </span>
        {field.hint && <span className="s1w-map-field-hint">{field.hint}</span>}
      </div>
      <div className="s1w-map-select-wrap">
        {headers.length > 0 ? (
          <select className={`s1w-map-select ${mapped ? "matched" : ""}`} value={value} onChange={e => onChange(e.target.value)}>
            <option value="">— Not mapped —</option>
            {headers.map(h => <option key={h} value={h}>{h}</option>)}
          </select>
        ) : (
          <input className={`s1w-map-input ${mapped ? "matched" : ""}`} placeholder="Column name in your file" value={value} onChange={e => onChange(e.target.value)} />
        )}
      </div>
      <div className="s1w-map-status">
        {mapped
          ? <span className="s1w-status-ok"><Icon.Check /></span>
          : <span className="s1w-status-empty" />}
      </div>
    </div>
  );
}

// ─── Field Group Panel ────────────────────────────────────────────────────────
function FieldGroup({ group, headers, mapping, setMapping, searchQuery }) {
  const [open, setOpen] = useState(true);

  // Filter fields by search
  const visibleFields = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return group.fields.filter(f => {
      if (q && !f.label.toLowerCase().includes(q) && !f.key.toLowerCase().includes(q) && !f.hint.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [group.fields, searchQuery]);

  if (visibleFields.length === 0) return null;

  const GroupIcon = group.IconComp;
  const mappedCount = visibleFields.filter(f => mapping[f.key]).length;

  return (
    <div className="s1w-field-group">
      <button className="s1w-group-header" onClick={() => setOpen(v => !v)}>
        <div className="s1w-group-header-left">
          <div className="s1w-group-icon"><GroupIcon /></div>
          <span className="s1w-group-label">{group.label}</span>
        </div>
        <div className="s1w-group-header-right">
          <span className="s1w-group-count">{mappedCount}/{visibleFields.length} mapped</span>
          <Icon.ChevronDown open={open} />
        </div>
      </button>
      {open && (
        <div className="s1w-group-body">
          <div className="s1w-group-table-header">
            <span>Field</span>
            <span>Your CSV Column</span>
            <span>Status</span>
          </div>
          {visibleFields.map(field => (
            <MappingRow
              key={field.key}
              field={field}
              headers={headers}
              value={mapping[field.key] || ""}
              onChange={val => setMapping(m => ({ ...m, [field.key]: val }))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Auto-detect mapping ───────────────────────────────────────────────────────
function autoDetect(headers, allFields) {
  const mapping = {};
  allFields.forEach(f => {
    const match = headers.find(h => {
      const hl = h.toLowerCase();
      return hl === f.key || hl.includes(f.key.replace(/_/g, " ")) || hl.includes(f.label.toLowerCase()) || f.label.toLowerCase().includes(hl);
    });
    if (match && !mapping[f.key]) mapping[f.key] = match;
  });
  return mapping;
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function Scope2ImportWizard({ onClose, onUploadSuccess }) {
  const toast = useToast();
  const fileInputRef = useRef(null);

  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState("");
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({});
  const [searchQuery, setSearchQuery] = useState("");
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ── Access Control: fetch allowed regions on mount ─────────────────────────
  const [allowedRegions, setAllowedRegions] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    api.get("/facilities/").then(res => {
      const regions = res.data.map(f => f.name);
      setAllowedRegions(regions);
    }).catch(() => setAllowedRegions([]));

    api.get("/auth/me").then(res => {
      const role = res.data?.role;
      setIsAdmin(role === "admin" ||
        (role === "superuser" && res.data?.location === "all"));
    }).catch(() => {});
  }, []);

  // All fields flattened
  const allFields = useMemo(() =>
    FIELD_GROUPS.flatMap(g => g.fields),
  []);

  // Required fields check
  const requiredFields = FIELD_GROUPS.flatMap(g => g.fields).filter(f => f.required);
  const missingRequired = requiredFields.filter(f => !mapping[f.key]);
  const canSubmit = missingRequired.length === 0 || headers.length === 0;

  // File processing
  const processFile = useCallback((f) => {
    if (!f) return;
    setParseError("");
    const isExcel = f.name.toLowerCase().endsWith(".xlsx");
    if (isExcel) {
      setFile(f); setHeaders([]); setMapping({}); setStep(2);
      return;
    }
    Papa.parse(f, {
      preview: 5, header: true, skipEmptyLines: true,
      complete: (results) => {
        if (!results.meta.fields?.length) {
          setParseError("Could not read column headers. Make sure the file has a header row.");
          return;
        }
        const hdrs = results.meta.fields;
        setHeaders(hdrs);
        setMapping(autoDetect(hdrs, allFields));
        setFile(f);
        setStep(2);
      },
      error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV."),
    });
  }, [allFields]);

  const onDrop = (e) => { e.preventDefault(); setIsDragging(false); processFile(e.dataTransfer.files[0]); };
  const onFileChange = (e) => { processFile(e.target.files[0]); e.target.value = ""; };

  // Submit
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("scope", "2");
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJobId(res.data.job_id);
      setStep(3);
    } catch (err) {
      toast.error("Upload error: " + (err.response?.data?.error || err.message));
    } finally { setIsSubmitting(false); }
  };

  return (
    <div className="s1w-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="s1w-modal">
        {/* Header */}
        <div className="s1w-header">
          <div className="s1w-header-left">
            <div className="s1w-header-icon"><Icon.Zap /></div>
            <div>
              <h2 className="s1w-title">Scope 2 Bulk Import</h2>
              <p className="s1w-subtitle">Upload electricity and indirect steam data from CSV or Excel</p>
            </div>
          </div>
          <button className="s1w-close" onClick={onClose}><Icon.Close /></button>
        </div>

        {/* Step bar */}
        <StepBar current={step} />

        {/* ── STEP 1: File Upload ── */}
        {step === 1 && (
          <div className="s1w-body">
            <div className="s1w-section-title"><Icon.Upload /><span>Select File</span></div>

            {!isAdmin && allowedRegions !== null && (
              <div className="s1w-access-banner">
                <div className="s1w-access-banner-header">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="s1w-access-region-list">
                    {allowedRegions.map(r => (
                      <span key={r} className="s1w-access-region-pill">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="s1w-access-no-regions">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div
              className={`s1w-dropzone ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" style={{ display: "none" }} onChange={onFileChange} />
              <div className="s1w-dropzone-icon"><Icon.Upload /></div>
              <p className="s1w-dropzone-text">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="s1w-dropzone-sub">Supports .xlsx and .csv</p>
              {parseError && (
                <div className="s1w-inline-error"><Icon.Warning />{parseError}</div>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 2: Column Mapping ── */}
        {step === 2 && (
          <div className="s1w-body">
            {!isAdmin && allowedRegions !== null && allowedRegions.length > 0 && (
              <div className="s1w-access-banner s1w-access-banner--compact">
                <Icon.Info />
                <span>
                  <strong>Allowed regions:</strong>{" "}
                  {allowedRegions.join(" · ")}
                </span>
              </div>
            )}
            {!isAdmin && allowedRegions !== null && allowedRegions.length === 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>No accessible regions.</strong> Your account has no assigned regions. All rows will be rejected. Contact an administrator.</span>
              </div>
            )}
            {file && (
              <div className="s1w-file-badge">
                <div className="s1w-file-badge-icon"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="s1w-file-name">{file.name}</p>
                  <p className="s1w-file-size">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                {headers.length > 0 && (
                  <div className="s1w-auto-badge"><Icon.Wand /><span>{Object.keys(mapping).length} auto-detected</span></div>
                )}
              </div>
            )}

            {headers.length === 0 && (
              <div className="s1w-info-banner">
                <Icon.Info />
                <span>Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.</span>
              </div>
            )}

            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>{missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:</strong> {missingRequired.map(f => f.label).join(", ")}</span>
              </div>
            )}

            <div className="s1w-search-bar">
              <div className="s1w-search-icon"><Icon.Search /></div>
              <input
                className="s1w-search-input"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="s1w-search-clear" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            <div className="s1w-field-groups">
              {FIELD_GROUPS.map(group => (
                <FieldGroup
                  key={group.id}
                  group={group}
                  headers={headers}
                  mapping={mapping}
                  setMapping={setMapping}
                  searchQuery={searchQuery}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── STEP 3: Processing ── */}
        {step === 3 && jobId && (
          <div className="s1w-body s1w-body--progress">
            <UploadProgress
              jobId={jobId}
              onComplete={() => { if (onUploadSuccess) onUploadSuccess(); onClose(); }}
              onCancel={onClose}
            />
          </div>
        )}

        {/* ── Footer ── */}
        {step !== 3 && (
          <div className="s1w-footer">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="s1w-footer-right">
              {step === 1 && (
                <button
                  className="s1w-btn-primary"
                  onClick={() => setStep(s => s + 1)}
                  disabled={!file}
                >
                  Next <Icon.ChevronRight />
                </button>
              )}
              {step === 2 && (
                <button
                  className="s1w-btn-primary"
                  onClick={handleSubmit}
                  disabled={isSubmitting || (!canSubmit && headers.length > 0) || (!isAdmin && allowedRegions !== null && allowedRegions.length === 0)}
                >
                  {isSubmitting ? <span className="s1w-spinner" /> : <Icon.Processing />}
                  {isSubmitting ? "Starting…" : "Start Import"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
