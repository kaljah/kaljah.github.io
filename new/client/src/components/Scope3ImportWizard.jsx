import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import { Activity as ActivityIcon, ArrowLeft as ArrowLeftIcon, Check as CheckIcon, ChevronDown as ChevronDownIcon, ChevronRight as ChevronRightIcon, CloudUpload as CloudUploadIcon, Columns3 as Columns3Icon, File as FileIcon, Globe as GlobeIcon, Info as InfoIcon, Layers as LayersIcon, Search as SearchIcon, Settings as SettingsIcon, TriangleAlert as TriangleAlertIcon, Wand2 as Wand2Icon, X as XIcon } from "lucide-react";
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
  Close: () => <XIcon strokeWidth={2} aria-hidden="true" />,
  Check: () => <CheckIcon strokeWidth={2.5} aria-hidden="true" />,
  ChevronRight: () => <ChevronRightIcon strokeWidth={2} aria-hidden="true" />,
  ChevronDown: ({ open }) => <ChevronDownIcon strokeWidth={2} aria-hidden="true" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }} />,
  ArrowLeft: () => <ArrowLeftIcon strokeWidth={2} aria-hidden="true" />,
  Upload: () => <CloudUploadIcon strokeWidth={1.75} aria-hidden="true" />,
  File: () => <FileIcon strokeWidth={1.75} aria-hidden="true" />,
  Wand: () => <Wand2Icon strokeWidth={1.75} aria-hidden="true" />,
  Search: () => <SearchIcon strokeWidth={2} aria-hidden="true" />,
  Warning: () => <TriangleAlertIcon strokeWidth={1.75} aria-hidden="true" />,
  Info: () => <InfoIcon strokeWidth={1.75} aria-hidden="true" />,
  Columns: () => <Columns3Icon strokeWidth={1.75} aria-hidden="true" />,
  Processing: () => <ActivityIcon strokeWidth={1.75} aria-hidden="true" />,
  Layers: () => <LayersIcon strokeWidth={1.75} aria-hidden="true" />,
  Globe: () => <GlobeIcon strokeWidth={1.75} aria-hidden="true" />,
  Settings: () => <SettingsIcon strokeWidth={1.75} aria-hidden="true" />,
};

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS_ACTIVITY = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  },
  {
    id: "classification",
    label: "GHG Protocol Classification",
    IconComp: Icon.Globe,
    fields: [
      { key: "category",      label: "Category",      required: true,  hint: "e.g. 1, 2, 3... or 'Category 11'" },
      { key: "sub_category",  label: "Sub Category",  required: false, hint: "Activity name as in the Scope 3 form (e.g. Truck Transport) to use its factor" },
      { key: "notes",         label: "Description / Notes", required: false, hint: "Description of the emission source" },
    ],
  },
  {
    id: "measurement",
    label: "Activity & Emissions",
    IconComp: Icon.Settings,
    fields: [
      { key: "amount",          label: "Activity Data Amount", required: true, hint: "Quantity of the activity" },
      { key: "unit",            label: "Activity Unit",        required: true, hint: "e.g. kg, USD, miles" },
      { key: "emission_factor", label: "Emission Factor",      required: false, hint: "kg CO2e per activity unit. If empty, the factor of the Sub Category activity in the Scope 3 form is used (unit must match)." },
      { key: "ef_unit",         label: "EF Unit",              required: false, hint: "kg CO2e per unit (default), t CO2e per unit, or kg CO2e per $1,000" },
      { key: "co2e",            label: "Total CO2e",           required: false, hint: "Provide direct CO2e to skip calculations" },
    ],
  }
];

const FIELD_GROUPS_EEIO = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12" },
    ],
  },
  {
    id: "measurement",
    label: "Spend & NAICS",
    IconComp: Icon.Settings,
    fields: [
      { key: "naics_code",      label: "NAICS Code",      required: true,  hint: "6-digit 2017 NAICS code (EPA supply chain factors)" },
      { key: "spend_usd",       label: "Spend (USD)",     required: true,  hint: "Amount spent in USD" },
      { key: "notes",           label: "Description / Notes", required: false, hint: "Optional supplier or purchase description" },
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
    <div className="[display:flex] [align-items:center] [padding:16px_24px] [gap:0] [flex-shrink:0] [border-bottom:1px_solid_var(--color-ink-200)] [overflow-x:auto]">
      {STEPS.map((s, i) => {
        const done   = s.id < current;
        const active = s.id === current;
        const SIcon  = s.IconComp;
        return (
          <React.Fragment key={s.id}>
            <div className={`[display:flex] [flex-direction:column] [align-items:center] [gap:5px] [flex-shrink:0] [&.active_.s1w-step-circle]:[border-color:var(--color-brand-500)] [&.active_.s1w-step-circle]:[background:#fff7f0] [&.active_.s1w-step-circle]:[color:var(--color-link)]! [&&]:[&.done_.s1w-step-circle]:[border-color:var(--color-green-500)] [&&]:[&.done_.s1w-step-circle]:[background:var(--color-green-50)] [&&]:[&.done_.s1w-step-circle]:[color:var(--color-green-700)]! [&&]:[&&]:[&.active_.s1w-step-label]:[color:var(--color-link)]! [&&]:[&&]:[&&]:[&.done_.s1w-step-label]:[color:var(--color-green-700)]! ${active ? "active" : ""} ${done ? "done" : ""}`}>
              <div className="s1w-step-circle">
                {done ? <Icon.Check /> : <SIcon />}
              </div>
              <span className="s1w-step-label [font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-600)] [white-space:nowrap] [text-transform:uppercase] [letter-spacing:0.5px]">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`[height:2px] [flex:1] [background:var(--color-ink-200)] [margin:0_4px] [&&]:[margin-bottom:20px] [min-width:20px] [transition:background_0.25s] [&.done]:[background:var(--color-green-500)] ${done ? "done" : ""}`} />
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
    <div className={`s1w-map-row ${!mapped && field.required ? "[background:#fff9f5]" : ""} ${mapped ? "[&&]:[background:#f0fdf4]" : ""}`}>
      <div className="[display:flex] [flex-direction:column] [gap:2px] [min-width:0]">
        <span className="[font-size:var(--text-sm)] [font-weight:600] [color:var(--color-ink-900)] [display:flex] [align-items:center] [gap:4px]">
          {field.label}
          {field.required && <span className="[width:6px] [height:6px] [border-radius:50%] [background:var(--color-red-500)] [flex-shrink:0] [display:inline-block]" />}
        </span>
        {field.hint && <span className="[font-size:var(--text-xs)] [color:var(--color-ink-600)] [line-height:1.3]">{field.hint}</span>}
      </div>
      <div className="s1w-map-select-wrap">
        {headers.length > 0 ? (
          <NativeSelect className={`s1w-map-select ${mapped ? "matched" : ""}`} value={value} onChange={e => onChange(e.target.value)}>
            <option value="">— Not mapped —</option>
            {headers.map(h => <option key={h} value={h}>{h}</option>)}
          </NativeSelect>
        ) : (
          <input className={`s1w-map-input ${mapped ? "matched" : ""}`} placeholder="Column name in your file" value={value} onChange={e => onChange(e.target.value)} />
        )}
      </div>
      <div className="[display:flex] [justify-content:center]">
        {mapped
          ? <span className="s1w-status-ok"><Icon.Check /></span>
          : <span className="[width:22px] [height:22px] [border-radius:50%] [border:2px_solid_var(--color-ink-200)] [display:block]" />}
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
    <div className="[border:1.5px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [overflow:hidden] [transition:border-color_0.15s] [&:has(.s1w-group-body)]:[border-color:var(--color-ink-200)]">
      <button className="s1w-group-header" onClick={() => setOpen(v => !v)}>
        <div className="[display:flex] [align-items:center] [gap:10px]">
          <div className="s1w-group-icon"><GroupIcon /></div>
          <span className="[font-size:var(--text-base)] [font-weight:700] [color:var(--color-ink-900)]">{group.label}</span>
        </div>
        <div className="[display:flex] [align-items:center] [gap:10px]">
          <span className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:600]">{mappedCount}/{visibleFields.length} mapped</span>
          <Icon.ChevronDown open={open} />
        </div>
      </button>
      {open && (
        <div className="s1w-group-body [border-top:1px_solid_var(--color-ink-200)]">
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
// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function Scope3ImportWizard({ onClose, onUploadSuccess }) {
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

  // Activity-based or spend-based (EEIO / NAICS) import: each has its own columns and server scope
  const [importMode, setImportMode] = useState("activity");
  const FIELD_GROUPS = importMode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY;

  // All fields flattened
  const allFields = useMemo(() =>
    (importMode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY).flatMap(g => g.fields),
  [importMode]);

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
    form.append("scope", importMode === "eeio" ? "3_eeio" : "3");
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
    <div role="presentation" className="[position:fixed] [inset:0] [background:rgba(10,_15,_30,_0.68)] [backdrop-filter:blur(6px)] [-webkit-backdrop-filter:blur(6px)] [display:flex] [align-items:center] [justify-content:center] [z-index:1000] [padding:16px] [animation:s1w-fade_0.2s_ease]" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="s1w-modal">
        {/* Header */}
        <div className="[display:flex] [align-items:center] [justify-content:space-between] [padding:20px_24px_0] [flex-shrink:0]">
          <div className="[display:flex] [align-items:center] [gap:12px]">
            <div className="s1w-header-icon"><Icon.Globe /></div>
            <div>
              <h2 className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--color-ink-900)] [margin:0_0_2px] [letter-spacing:-0.3px] [font-family:inherit]">Scope 3 Bulk Import</h2>
              <p className="[font-size:var(--text-sm)] [color:var(--color-ink-500)] [margin:0]">Upload value chain emissions data from CSV or Excel</p>
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
              <div className="[padding:14px_16px] [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)] [border:1.5px_solid_#fed7aa] [&&]:[border-radius:var(--radius-md)] [display:flex] [flex-direction:column] [gap:10px]">
                <div className="s1w-access-banner-header">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="[display:flex] [flex-wrap:wrap] [gap:6px]">
                    {allowedRegions.map(r => (
                      <span key={r} className="[padding:4px_12px] [background:var(--color-white)] [border:1.5px_solid_var(--color-brand-400)] [&&]:[border-radius:var(--radius-lg)] [font-size:var(--text-sm)] [font-weight:700] [color:var(--color-brand-700)] [white-space:nowrap]">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="[font-size:var(--text-base)] [color:var(--color-red-700)] [margin:0] [font-weight:500]">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div className="s1w-mode-switch flex! gap-[8px]! mb-[12px]!" role="radiogroup" aria-label="Import type">
              {[["activity", "Activity data"], ["eeio", "Spend (EEIO / NAICS)"]].map(([v, l]) => (
                <button
                  key={v}
                  type="button"
                  role="radio"
                  aria-checked={importMode === v}
                  className={importMode === v ? "s1w-btn-primary" : "s1w-btn-ghost"}
                  onClick={() => setImportMode(v)}
                >
                  {l}
                </button>
              ))}
            </div>
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className={`[border:2px_dashed_var(--color-ink-200)] [&&]:[border-radius:var(--radius-lg)] [padding:40px_24px] [display:flex] [flex-direction:column] [align-items:center] [gap:10px] [cursor:pointer] [transition:all_0.2s] [background:var(--color-ink-50)] [text-align:center] hover:[border-color:var(--color-brand-500)] hover:[background:#fff7f0] hover:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)] [&.dragging]:[border-color:var(--color-brand-500)] [&.dragging]:[background:#fff7f0] [&.dragging]:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)] ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden!" onChange={onFileChange} />
              <div className="s1w-dropzone-icon"><Icon.Upload /></div>
              <p className="s1w-dropzone-text">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="[font-size:var(--text-sm)] [color:var(--color-ink-600)] [margin:0]">Supports .xlsx and .csv</p>
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
              <div className="[padding:14px_16px] [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)] [border:1.5px_solid_#fed7aa] [&&]:[border-radius:var(--radius-md)] [display:flex] [flex-direction:column] [gap:10px] s1w-access-banner--compact">
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
              <div className="[display:flex] [align-items:center] [gap:12px] [padding:12px_16px] [background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)]">
                <div className="s1w-file-badge-icon"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="[font-size:var(--text-base)] [font-weight:600] [color:var(--color-ink-900)] [margin:0_0_2px]">{file.name}</p>
                  <p className="[font-size:var(--text-sm)] [color:var(--color-ink-600)] [margin:0]">{(file.size / 1024).toFixed(1)} KB</p>
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

            <div className="[position:relative] [display:flex] [align-items:center]">
              <div className="s1w-search-icon"><Icon.Search /></div>
              <input
                className="[width:100%] [padding:10px_12px_10px_38px] [border:1.5px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [background:var(--color-ink-50)] [font-size:var(--text-base)] [color:var(--color-ink-900)] [outline:none] [transition:border-color_0.15s] [font-family:inherit] focus:[border-color:var(--color-brand-500)] focus:[background:var(--color-white)] focus:[box-shadow:0_0_0_3px_rgba(255,102,0,0.08)] placeholder:[color:var(--color-ink-400)]"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="s1w-search-clear" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            <label className="[display:flex] [align-items:center] [flex-wrap:wrap] gap-[8px]! cursor-pointer!">
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              <span className="[font-size:var(--text-sm)] [color:var(--color-ink-600)] [font-weight:500] [flex-shrink:0]">
                Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.
              </span>
            </label>

            <div className="[display:flex] [flex-direction:column] [gap:10px]">
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
          <div className="[display:flex] [align-items:center] [justify-content:space-between] [padding:14px_24px] [border-top:1px_solid_var(--color-ink-200)] [background:var(--color-ink-50)] [flex-shrink:0]">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="[display:flex] [align-items:center] [gap:10px]">
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
                  {isSubmitting ? <span className="[width:15px] [height:15px] [border-radius:50%] [border:2px_solid_rgba(255,255,255,0.4)] [&&]:[border-top-color:var(--color-white)] [animation:s1w-spin_0.7s_linear_infinite] [display:inline-block]" /> : <Icon.Processing />}
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
