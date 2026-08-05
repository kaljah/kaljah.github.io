import React, { useState, useRef, useCallback } from 'react';
import Papa from 'papaparse';
import api from '../api';
import UploadProgress from './UploadProgress';
import './ColumnMappingWizard.css';

// ─── System field definitions ─────────────────────────────────────────────────
const REQUIRED_FIELDS = [
    { key: 'date',          label: 'Date',                   hint: 'e.g. YYYY-MM or YYYY-MM-DD',    required: true  },
    { key: 'facility_name', label: 'Region / Facility',      hint: 'Must match a registered facility', required: true  },
    { key: 'process',       label: 'Process Type',            hint: 'Combustion, Flaring, etc.',     required: true  },
    { key: 'fuel',          label: 'Activity / Fuel',         hint: 'Natural Gas, Diesel, etc.',     required: true  },
    { key: 'quantity',      label: 'Quantity',                hint: 'Numeric value',                 required: true  },
    { key: 'unit',          label: 'Unit',                    hint: 'scf, m3, bbl, kg…',             required: true  },
];

const OPTIONAL_FIELDS = [
    { key: 'activity',      label: 'Activity / Segment',      hint: 'Exploration & Production…',     required: false },
    { key: 'division',      label: 'Division',                hint: 'Production, Association…',      required: false },
    { key: 'field',         label: 'Field',                   hint: 'Field or project name',         required: false },
    { key: 'group',         label: 'Emission Source (Group)', hint: 'Functional grouping',           required: false },
    { key: 'equipment',     label: 'Equipment Name',          hint: 'Descriptive equipment name',    required: false },
    { key: 'equipment_id',  label: 'Equipment ID',            hint: 'Asset tag or ID',               required: false },
    { key: 'factor_type',   label: 'Factor Type',             hint: 'default or custom',             required: false },
    { key: 'year',          label: 'Year',                    hint: 'If no Date column',             required: false },
    { key: 'month',         label: 'Month',                   hint: 'If no Date column',             required: false },
];

const ALL_FIELDS = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];

// Auto-detect: tries to match a column header to a system field key/label
function autoDetectMapping(headers) {
    const mapping = {};
    ALL_FIELDS.forEach(field => {
        const match = headers.find(h => {
            const hl = h.toLowerCase();
            return hl === field.key.toLowerCase()
                || hl.includes(field.key.replace(/_/g, ' '))
                || hl.includes(field.label.toLowerCase())
                || field.label.toLowerCase().includes(hl);
        });
        if (match) mapping[field.key] = match;
    });
    return mapping;
}

// ─── SVG Icons ────────────────────────────────────────────────────────────────
const Icons = {
    Upload: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
            <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
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
    FileXlsx: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="16" y2="17" />
            <polyline points="10 9 9 9 8 9" />
        </svg>
    ),
    FileCsv: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="8" y1="13" x2="16" y2="13" />
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
    ArrowLeft: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
        </svg>
    ),
    Warning: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
    ),
    Wand: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 4V2m0 14v-2M8 9H2m14 0h-2M3.5 3.5l1.5 1.5M16.5 16.5l1.5 1.5M16.5 3.5 15 5M3.5 20.5 5 19" />
            <path d="m3 9 9 9 9-9-9-9Z" />
        </svg>
    ),
    X: () => (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
    ),
};

// ─── Step indicator ───────────────────────────────────────────────────────────
const STEPS = [
    { id: 1, label: 'Select File',     Icon: Icons.Upload    },
    { id: 2, label: 'Map Columns',     Icon: Icons.Columns   },
    { id: 3, label: 'Processing',      Icon: Icons.Processing},
];

function StepIndicator({ current }) {
    return (
        <div className="cmw-step-indicator">
            {STEPS.map((s, i) => {
                const done = s.id < current;
                const active = s.id === current;
                return (
                    <React.Fragment key={s.id}>
                        <div className={`cmw-step ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
                            <div className="cmw-step-circle">
                                {done ? <Icons.Check /> : <s.Icon />}
                            </div>
                            <span className="cmw-step-label">{s.label}</span>
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className={`cmw-step-line ${done ? 'done' : ''}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function ColumnMappingWizard({ onClose, onUploadSuccess }) {
    const fileInputRef   = useRef(null);
    const [step, setStep]               = useState(1);
    const [file, setFile]               = useState(null);
    const [isDragging, setIsDragging]   = useState(false);
    const [headers, setHeaders]         = useState([]);
    const [mapping, setMapping]         = useState({});
    const [globalFactor, setGlobalFactor] = useState('auto');
    const [jobId, setJobId]             = useState(null);
    const [parseError, setParseError]   = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showOptional, setShowOptional] = useState(false);

    // ── File handling ──────────────────────────────────────────────────────────
    const processFile = useCallback((f) => {
        if (!f) return;
        setParseError('');

        const isExcel = f.name.toLowerCase().endsWith('.xlsx');

        if (isExcel) {
            // For Excel: we don't parse in browser, but we still need headers.
            // Send a "preview" request or just show all system fields for manual mapping.
            setFile(f);
            setHeaders([]);   // no browser-side parse for xlsx
            setMapping({});
            setStep(2);
            return;
        }

        // CSV: parse just the first row for headers
        Papa.parse(f, {
            preview: 5,
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                if (!results.meta.fields?.length) {
                    setParseError('Could not read column headers. Make sure the file has a header row.');
                    return;
                }
                const hdrs = results.meta.fields;
                setHeaders(hdrs);
                setMapping(autoDetectMapping(hdrs));
                setFile(f);
                setStep(2);
            },
            error: () => setParseError('Failed to parse the file. Please ensure it is a valid CSV.'),
        });
    }, []);

    const onFileInputChange = (e) => {
        processFile(e.target.files[0]);
        e.target.value = '';
    };

    const onDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        processFile(e.dataTransfer.files[0]);
    };

    // ── Submit upload ──────────────────────────────────────────────────────────
    const handleSubmit = async () => {
        setIsSubmitting(true);
        const form = new FormData();
        form.append('file', file);
        form.append('global_factor_type', globalFactor);
        // Pass the column mapping so the server can use correct column names
        form.append('column_mapping', JSON.stringify(mapping));

        try {
            const res = await api.post('/emissions/upload/start', form, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setJobId(res.data.job_id);
            setStep(3);
        } catch (err) {
            alert('Error starting upload: ' + (err.response?.data?.error || err.message));
        } finally {
            setIsSubmitting(false);
        }
    };

    // ── Download template ──────────────────────────────────────────────────────
    const downloadTemplate = async (fmt) => {
        try {
            const res = await api.get(`/emissions/template/${fmt}`, { responseType: 'blob' });
            const url = URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = fmt === 'excel' ? 'GHG_Emissions_Template_v2.xlsx' : 'emissions_template.csv';
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch { alert('Template download failed.'); }
    };

    // ── Validation ─────────────────────────────────────────────────────────────
    const missingRequired = REQUIRED_FIELDS.filter(f => !mapping[f.key]);
    const canProceed = missingRequired.length === 0 || headers.length === 0; // xlsx: skip client-side check

    // ─── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="cmw-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="cmw-modal">

                {/* Header */}
                <div className="cmw-header">
                    <div>
                        <h2 className="cmw-title">Import Emissions Data</h2>
                        <p className="cmw-subtitle">Upload a CSV or Excel file to bulk-import your emission records</p>
                    </div>
                    <button className="cmw-close-btn" onClick={onClose}><Icons.X /></button>
                </div>

                {/* Step Indicator */}
                <StepIndicator current={step} />

                {/* ── STEP 1: File Select ── */}
                {step === 1 && (
                    <div className="cmw-body">
                        {/* Drop zone */}
                        <div
                            className={`cmw-dropzone ${isDragging ? 'dragging' : ''}`}
                            onClick={() => fileInputRef.current.click()}
                            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                            onDragLeave={() => setIsDragging(false)}
                            onDrop={onDrop}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".csv,.xlsx"
                                style={{ display: 'none' }}
                                onChange={onFileInputChange}
                            />
                            <div className="cmw-dropzone-icon"><Icons.Upload /></div>
                            <p className="cmw-dropzone-text">
                                Drag & drop your file here, or <span>click to browse</span>
                            </p>
                            <p className="cmw-dropzone-sub">Supports .xlsx and .csv — optimised for millions of rows</p>
                            {parseError && (
                                <div className="cmw-inline-error">
                                    <Icons.Warning />{parseError}
                                </div>
                            )}
                        </div>

                        {/* Template download */}
                        <div className="cmw-template-section">
                            <p className="cmw-template-label">Don't have a file yet? Start from our template:</p>
                            <div className="cmw-template-btns">
                                <button className="cmw-template-btn" onClick={() => downloadTemplate('excel')}>
                                    <span className="cmw-template-btn-icon"><Icons.FileXlsx /></span>
                                    <span>
                                        <strong>Excel Template</strong>
                                        <small>With dropdowns, sample data & engineering sheets</small>
                                    </span>
                                </button>
                                <button className="cmw-template-btn" onClick={() => downloadTemplate('csv')}>
                                    <span className="cmw-template-btn-icon"><Icons.FileCsv /></span>
                                    <span>
                                        <strong>CSV Template</strong>
                                        <small>Lightweight flat file for maximum performance</small>
                                    </span>
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── STEP 2: Column Mapping ── */}
                {step === 2 && (
                    <div className="cmw-body">
                        {/* File badge */}
                        <div className="cmw-file-badge">
                            <div className="cmw-file-badge-icon"><Icons.FileXlsx /></div>
                            <div>
                                <p className="cmw-file-name">{file?.name}</p>
                                <p className="cmw-file-size">{file ? (file.size / 1024).toFixed(1) + ' KB' : ''}</p>
                            </div>
                            {headers.length > 0 && (
                                <div className="cmw-auto-badge">
                                    <Icons.Wand />
                                    <span>{Object.keys(mapping).length} columns auto-detected</span>
                                </div>
                            )}
                        </div>

                        {/* Excel note */}
                        {headers.length === 0 && (
                            <div className="cmw-info-banner">
                                <Icons.Warning />
                                <span>
                                    Excel files are processed server-side. If your column names match the template exactly, mapping is automatic.
                                    Otherwise, use the table below to tell us what each column should map to.
                                </span>
                            </div>
                        )}

                        {/* Missing required fields warning */}
                        {headers.length > 0 && missingRequired.length > 0 && (
                            <div className="cmw-warning-banner">
                                <Icons.Warning />
                                <span>
                                    <strong>{missingRequired.length} required field{missingRequired.length > 1 ? 's' : ''} not mapped:</strong>
                                    {' '}{missingRequired.map(f => f.label).join(', ')}
                                </span>
                            </div>
                        )}

                        {/* Mapping table */}
                        <div className="cmw-mapping-container">
                            <div className="cmw-mapping-group-label">Required Fields</div>
                            <div className="cmw-mapping-table">
                                <div className="cmw-mapping-header">
                                    <span>System Field</span>
                                    <span>Description</span>
                                    <span>Your Column</span>
                                    <span>Status</span>
                                </div>

                                {REQUIRED_FIELDS.map(field => (
                                    <MappingRow
                                        key={field.key}
                                        field={field}
                                        headers={headers}
                                        value={mapping[field.key] || ''}
                                        onChange={val => setMapping(m => ({ ...m, [field.key]: val }))}
                                    />
                                ))}
                            </div>

                            <button
                                className="cmw-optional-toggle"
                                onClick={() => setShowOptional(v => !v)}
                            >
                                <Icons.ChevronRight />
                                {showOptional ? 'Hide' : 'Show'} optional fields ({OPTIONAL_FIELDS.length})
                            </button>

                            {showOptional && (
                                <>
                                    <div className="cmw-mapping-group-label" style={{ marginTop: '12px' }}>Optional Fields</div>
                                    <div className="cmw-mapping-table">
                                        <div className="cmw-mapping-header">
                                            <span>System Field</span>
                                            <span>Description</span>
                                            <span>Your Column</span>
                                            <span>Status</span>
                                        </div>
                                        {OPTIONAL_FIELDS.map(field => (
                                            <MappingRow
                                                key={field.key}
                                                field={field}
                                                headers={headers}
                                                value={mapping[field.key] || ''}
                                                onChange={val => setMapping(m => ({ ...m, [field.key]: val }))}
                                            />
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Factor type override */}
                        <div className="cmw-factor-row">
                            <label className="cmw-factor-label">Default factor type when not specified in file</label>
                            <select
                                className="cmw-factor-select"
                                value={globalFactor}
                                onChange={e => setGlobalFactor(e.target.value)}
                            >
                                <option value="auto">Auto-detect from file</option>
                                <option value="default">Force Standard (API Compendium)</option>
                                <option value="custom">Force Custom Factors</option>
                            </select>
                        </div>
                    </div>
                )}

                {/* ── STEP 3: Processing ── */}
                {step === 3 && jobId && (
                    <div className="cmw-body cmw-body--progress">
                        <UploadProgress
                            jobId={jobId}
                            onComplete={() => {
                                if (onUploadSuccess) onUploadSuccess();
                                onClose();
                            }}
                            onCancel={onClose}
                        />
                    </div>
                )}

                {/* Footer actions */}
                {step !== 3 && (
                    <div className="cmw-footer">
                        <button
                            className="cmw-btn-ghost"
                            onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
                        >
                            {step === 1 ? (
                                <><Icons.X /> Cancel</>
                            ) : (
                                <><Icons.ArrowLeft /> Back</>
                            )}
                        </button>

                        {step === 2 && (
                            <button
                                className="cmw-btn-primary"
                                onClick={handleSubmit}
                                disabled={isSubmitting || (!canProceed && headers.length > 0)}
                            >
                                {isSubmitting ? (
                                    <span className="cmw-spinner" />
                                ) : (
                                    <Icons.Processing />
                                )}
                                {isSubmitting ? 'Starting…' : 'Start Import'}
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

// ─── Single mapping row ────────────────────────────────────────────────────────
function MappingRow({ field, headers, value, onChange }) {
    const mapped = !!value;

    return (
        <div className={`cmw-mapping-row ${!mapped && field.required ? 'unmapped' : ''}`}>
            <div className="cmw-field-name">
                {field.label}
                {field.required && <span className="cmw-required-dot" />}
            </div>
            <div className="cmw-field-hint">{field.hint}</div>
            <div className="cmw-field-select">
                {headers.length > 0 ? (
                    <select
                        className={`cmw-select ${mapped ? 'matched' : ''}`}
                        value={value}
                        onChange={e => onChange(e.target.value)}
                    >
                        <option value="">— Not mapped —</option>
                        {headers.map(h => <option key={h} value={h}>{h}</option>)}
                    </select>
                ) : (
                    <input
                        className={`cmw-text-input ${mapped ? 'matched' : ''}`}
                        placeholder="Column name in your file"
                        value={value}
                        onChange={e => onChange(e.target.value)}
                    />
                )}
            </div>
            <div className="cmw-field-status">
                {mapped
                    ? <span className="cmw-status-ok"><Icons.Check /></span>
                    : <span className="cmw-status-empty" />
                }
            </div>
        </div>
    );
}
