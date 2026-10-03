import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import { activateOnKey } from "../utils/a11yKeys";
import Papa from "papaparse";
import api from "../api";
import { autoDetectMapping, missingRequiredFields } from "../utils/importMapping";
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
      { key: "grid_region",   label: "Grid Region",   required: false, hint: "Grid name as listed on the Scope 2 form (e.g. Algerian National Grid). Required for electricity unless a supplier factor is given." },
      { key: "factor",        label: "Supplier Factor", required: false, hint: "Electricity: supplier / contract factor in kg CO2e/kWh (used when the grid is not listed). Steam: boiler factor in kg CO2/MMBtu" },
      { key: "consumption",   label: "Consumption",   required: true,  hint: "Amount of electricity/steam purchased" },
      { key: "unit",          label: "Unit",          required: true,  hint: "Electricity: kWh, MWh, GWh. Steam: MMBtu, GJ, tonne, klb" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  },
  {
    id: "steam",
    label: "Steam & CHP (optional)",
    IconComp: Icon.Activity,
    fields: [
      { key: "boiler_eff",        label: "Boiler Efficiency", required: false, hint: "Steam: % (85) or fraction (0.85). Default 80 %" },
      { key: "trans_loss",        label: "Transmission Loss", required: false, hint: "Steam: percentage, e.g. 5 = 5 %, 0.9 = 0.9 %. Default 0" },
      { key: "total_emissions",   label: "CHP Total Emissions", required: false, hint: "CHP: plant emissions, t CO2e" },
      { key: "heat_output_mmbtu", label: "CHP Heat Output", required: false, hint: "CHP: heat bought, MMBtu" },
      { key: "power_output_mwh",  label: "CHP Power Output", required: false, hint: "CHP: power bought, MWh" },
      { key: "heat_efficiency",   label: "CHP Heat Efficiency", required: false, hint: "CHP: % or fraction. Default 80 %" },
      { key: "power_efficiency",  label: "CHP Power Efficiency", required: false, hint: "CHP: % or fraction. Default 35 %" },
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
    <div className="[display:flex]! [align-items:center] [padding:16px_24px]! [gap:0] [flex-shrink:0] [border-bottom:1px_solid_var(--color-ink-200)]! [overflow-x:auto]!">
      {STEPS.map((s, i) => {
        const done   = s.id < current;
        const active = s.id === current;
        const SIcon  = s.IconComp;
        return (
          <React.Fragment key={s.id}>
            <div className={`[display:flex]! [flex-direction:column] [align-items:center] [gap:5px] [flex-shrink:0] [&.active_.s1w-step-circle]:[border-color:var(--color-brand-500)]! [&.active_.s1w-step-circle]:[background:#fff7f0]! [&.active_.s1w-step-circle]:[color:var(--color-link)]! [&&]:[&.done_.s1w-step-circle]:[border-color:var(--color-green-500)]! [&&]:[&.done_.s1w-step-circle]:[background:var(--color-green-50)]! [&&]:[&.done_.s1w-step-circle]:[color:var(--color-green-700)]! [&&]:[&&]:[&.active_.s1w-step-label]:[color:var(--color-link)]! [&&]:[&&]:[&&]:[&.done_.s1w-step-label]:[color:var(--color-green-700)]! ${active ? "active" : ""} ${done ? "done" : ""}`}>
              <div className="s1w-step-circle">
                {done ? <Icon.Check /> : <SIcon />}
              </div>
              <span className="s1w-step-label [font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-600)]! [white-space:nowrap] [text-transform:uppercase]! [letter-spacing:0.5px]">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`[height:2px]! [flex:1] [background:var(--color-ink-200)]! [margin:0_4px]! [&&]:[margin-bottom:20px]! [min-width:20px] [transition:background_0.25s]! [&.done]:[background:var(--color-green-500)]! ${done ? "done" : ""}`} />
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
    <div className={`[display:grid]! [grid-template-columns:1fr_1fr_36px]! [align-items:center] [padding:10px_16px]! [border-bottom:1px_solid_var(--color-ink-100)]! [transition:background_0.12s]! [gap:12px] last:[border-bottom:none]! hover:[background:#fafaf9]! [@media(max-width:600px)]:[grid-template-columns:1fr]! ${!mapped && field.required ? "[background:#fff9f5]!" : ""} ${mapped ? "[&&]:[background:#f0fdf4]!" : ""}`}>
      <div className="[display:flex]! [flex-direction:column] [gap:2px] [min-width:0]">
        <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-900)]! [display:flex]! [align-items:center] [gap:4px]">
          {field.label}
          {field.required && <span className="[width:6px]! [height:6px]! [border-radius:50%]! [background:var(--color-red-500)]! [flex-shrink:0] [display:inline-block]!" />}
        </span>
        {field.hint && <span className="[font-size:var(--text-xs)]! [color:var(--color-ink-600)]! [line-height:1.3]">{field.hint}</span>}
      </div>
      <div className="s1w-map-select-wrap">
        {headers.length > 0 ? (
          <NativeSelect className={`[width:100%]! [padding:7px_10px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-sm)]! [background:var(--color-white)]! [font-size:var(--text-sm)]! [color:var(--color-ink-900)]! [outline:none]! [transition:border-color_0.15s]! [font-family:inherit]! focus:[border-color:var(--color-brand-500)]! focus:[box-shadow:0_0_0_2px_rgba(255,102,0,0.08)]! [&.matched]:[border-color:var(--color-green-500)]! [&.matched]:[background:#f0fdf4]! ${mapped ? "matched" : ""}`} value={value} onChange={e => onChange(e.target.value)}>
            <option value="">— Not mapped —</option>
            {headers.map(h => <option key={h} value={h}>{h}</option>)}
          </NativeSelect>
        ) : (
          <input className={`[width:100%]! [padding:7px_10px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-sm)]! [background:var(--color-white)]! [font-size:var(--text-sm)]! [color:var(--color-ink-900)]! [outline:none]! [transition:border-color_0.15s]! [font-family:inherit]! focus:[border-color:var(--color-brand-500)]! focus:[box-shadow:0_0_0_2px_rgba(255,102,0,0.08)]! [&.matched]:[border-color:var(--color-green-500)]! [&.matched]:[background:#f0fdf4]! ${mapped ? "matched" : ""}`} placeholder="Column name in your file" value={value} onChange={e => onChange(e.target.value)} />
        )}
      </div>
      <div className="[display:flex]! [justify-content:center]">
        {mapped
          ? <span className="s1w-status-ok"><Icon.Check /></span>
          : <span className="[width:22px]! [height:22px]! [border-radius:50%]! [border:2px_solid_var(--color-ink-200)]! [display:block]!" />}
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
    <div className="[border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [overflow:hidden]! [transition:border-color_0.15s]! [&:has(.s1w-group-body)]:[border-color:var(--color-ink-200)]!">
      <button className="s1w-group-header" onClick={() => setOpen(v => !v)}>
        <div className="[display:flex]! [align-items:center] [gap:10px]">
          <div className="s1w-group-icon"><GroupIcon /></div>
          <span className="[font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-ink-900)]!">{group.label}</span>
        </div>
        <div className="[display:flex]! [align-items:center] [gap:10px]">
          <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]!">{mappedCount}/{visibleFields.length} mapped</span>
          <Icon.ChevronDown open={open} />
        </div>
      </button>
      {open && (
        <div className="s1w-group-body [border-top:1px_solid_var(--color-ink-200)]!">
          <div className="[display:grid]! [grid-template-columns:1fr_1fr_36px] [padding:8px_16px]! [background:var(--color-ink-50)]! [border-bottom:1px_solid_var(--color-ink-100)]! [font-size:var(--text-xs)]! [font-weight:700]! [color:var(--color-ink-600)]! [text-transform:uppercase]! [letter-spacing:0.5px] [@media(max-width:600px)]:[display:none]!">
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
  const [overwrite, setOverwrite] = useState(false);  // replace records that already exist

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
  const missingRequired = missingRequiredFields(FIELD_GROUPS.flatMap(g => g.fields), mapping);
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
        setMapping(autoDetectMapping(hdrs, allFields));
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
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
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
    <div className="[position:fixed] [inset:0] [background:rgba(10,_15,_30,_0.68)]! [backdrop-filter:blur(6px)] [-webkit-backdrop-filter:blur(6px)]! [display:flex]! [align-items:center] [justify-content:center] [z-index:1000] [padding:16px]! [animation:s1w-fade_0.2s_ease]!" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="[background:var(--color-white)]! [border-radius:var(--radius-lg)]! [width:100%]! [max-width:820px]! [max-height:94vh]! [display:flex]! [flex-direction:column] [box-shadow:var(--shadow-overlay)]! [animation:s1w-slide_0.28s_cubic-bezier(0.34,_1.56,_0.64,_1)]! [overflow:hidden]! [@media(max-width:600px)]:[border-radius:var(--radius-md)]!">
        {/* Header */}
        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [padding:20px_24px_0]! [flex-shrink:0]">
          <div className="[display:flex]! [align-items:center] [gap:12px]">
            <div className="s1w-header-icon"><Icon.Zap /></div>
            <div>
              <h2 className="[font-size:var(--text-lg)]! [font-weight:700]! [color:var(--color-ink-900)]! [margin:0_0_2px]! [letter-spacing:-0.3px] [font-family:inherit]!">Scope 2 Bulk Import</h2>
              <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [margin:0]!">Upload electricity and indirect steam data from CSV or Excel</p>
            </div>
          </div>
          <button className="s1w-close" aria-label="Close" onClick={onClose}><Icon.Close /></button>
        </div>

        {/* Step bar */}
        <StepBar current={step} />

        {/* ── STEP 1: File Upload ── */}
        {step === 1 && (
          <div className="s1w-body">
            <div className="s1w-section-title"><Icon.Upload /><span>Select File</span></div>

            {!isAdmin && allowedRegions !== null && (
              <div className="[padding:14px_16px]! [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)]! [border:1.5px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [display:flex]! [flex-direction:column] [gap:10px]">
                <div className="s1w-access-banner-header">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="[display:flex]! [flex-wrap:wrap] [gap:6px]">
                    {allowedRegions.map(r => (
                      <span key={r} className="[padding:4px_12px]! [background:var(--color-white)]! [border:1.5px_solid_var(--color-brand-400)]! [&&]:[border-radius:var(--radius-lg)]! [font-size:var(--text-sm)]! [font-weight:700]! [color:var(--color-brand-700)]! [white-space:nowrap]">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="[font-size:var(--text-base)]! [color:var(--color-red-700)]! [margin:0]! [font-weight:500]!">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className={`[border:2px_dashed_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-lg)]! [padding:40px_24px]! [display:flex]! [flex-direction:column] [align-items:center] [gap:10px] [cursor:pointer] [transition:all_0.2s]! [background:var(--color-ink-50)]! [text-align:center]! hover:[border-color:var(--color-brand-500)]! hover:[background:#fff7f0]! hover:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)]! [&.dragging]:[border-color:var(--color-brand-500)]! [&.dragging]:[background:#fff7f0]! [&.dragging]:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)]! ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden!" onChange={onFileChange} />
              <div className="s1w-dropzone-icon"><Icon.Upload /></div>
              <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-700)]! [margin:0]! [&_span]:[color:var(--color-link)]! [&_span]:[text-decoration:underline]!">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [margin:0]!">Supports .xlsx and .csv</p>
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
              <div className="[padding:14px_16px]! [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)]! [border:1.5px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [display:flex]! [flex-direction:column]! [gap:10px]! s1w-access-banner--compact">
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
              <div className="[display:flex]! [align-items:center] [gap:12px] [padding:12px_16px]! [background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]!">
                <div className="s1w-file-badge-icon"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-900)]! [margin:0_0_2px]!">{file.name}</p>
                  <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [margin:0]!">{(file.size / 1024).toFixed(1)} KB</p>
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

            <div className="[position:relative] [display:flex]! [align-items:center]">
              <div className="s1w-search-icon"><Icon.Search /></div>
              <input
                className="[width:100%]! [padding:10px_12px_10px_38px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [background:var(--color-ink-50)]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [outline:none]! [transition:border-color_0.15s]! [font-family:inherit]! focus:[border-color:var(--color-brand-500)]! focus:[background:var(--color-white)]! focus:[box-shadow:0_0_0_3px_rgba(255,102,0,0.08)]! placeholder:[color:var(--color-ink-400)]!"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="s1w-search-clear" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            <label className="[display:flex]! [align-items:center] [flex-wrap:wrap] gap-[8px]! cursor-pointer!">
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              <span className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [font-weight:500]! [flex-shrink:0]">
                Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.
              </span>
            </label>

            <div className="[display:flex]! [flex-direction:column] [gap:10px]">
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
          <div className="s1w-body [padding:0]!">
            <UploadProgress
              jobId={jobId}
              onComplete={() => { if (onUploadSuccess) onUploadSuccess(); onClose(); }}
              onCancel={onClose}
            />
          </div>
        )}

        {/* ── Footer ── */}
        {step !== 3 && (
          <div className="[display:flex]! [align-items:center] [justify-content:space-between] [padding:14px_24px]! [border-top:1px_solid_var(--color-ink-200)]! [background:var(--color-ink-50)]! [flex-shrink:0]">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="[display:flex]! [align-items:center] [gap:10px]">
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
                  {isSubmitting ? <span className="[width:15px]! [height:15px]! [border-radius:50%]! [border:2px_solid_rgba(255,255,255,0.4)]! [&&]:[border-top-color:var(--color-white)]! [animation:s1w-spin_0.7s_linear_infinite]! [display:inline-block]!" /> : <Icon.Processing />}
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
