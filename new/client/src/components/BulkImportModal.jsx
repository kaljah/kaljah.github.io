import React, { useState, useRef } from 'react';
import api from '../api';
import Modal from './Modal';
import { useToast } from './Toast';
import { FileText, Upload, AlertCircle, CheckCircle2, Loader2, Info } from 'lucide-react';
import Papa from 'papaparse'; // NEW-05 FIX: use PapaParse instead of fragile string splitting
import { PROCESS_TYPES } from '../utils/EmissionFactors';
import './BulkImportModal.css';

const BulkImportModal = ({ isOpen, onClose, type, onImportSuccess }) => {
    const toast = useToast();
    const fileInputRef = useRef(null);
    const [file, setFile] = useState(null);
    const [csvData, setCsvData] = useState([]);
    const [headers, setHeaders] = useState([]);
    const [mapping, setMapping] = useState({});
    const [step, setStep] = useState(1); // 1: Upload, 2: Mapping, 3: Preview
    const [loading, setLoading] = useState(false);
    const [showCheatSheet, setShowCheatSheet] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);
    const [mappedRecords, setMappedRecords] = useState([]);

    const VALID_FUELS = ["Natural Gas", "Diesel (No. 2 Fuel Oil)", "Crude Oil", "Motor Gasoline", "LPG", "Propane", "Fuel Oil"];
    const VALID_UNITS = ["scf", "m3", "gal", "bbl", "tonnes/yr", "kg", "tonne"];

    const HIERARCHY = {
        'Exploration & Production': ['Production', 'Association'],
        'Liquifaction and Separation': ['LNG', 'LPG'],
        'Refining and Petrochemicals': ['Refining', 'Petrochemicals'],
        'Transport (TRC)': ['TRC']
    };

    // Templates for different import types
    const TEMPLATES = {
        sources: [
            { id: 'activity', label: 'Activity', required: true, hint: 'e.g. Exploration & Production' },
            { id: 'division', label: 'Division', required: true, hint: 'e.g. Production, Association' },
            { id: 'facility_id', label: 'Region', required: true, hint: 'e.g. Hassi Messaoud' },
            { id: 'field', label: 'Field', required: false },
            { id: 'name', label: 'Equipment Name', required: true },
            { id: 'equipment_id', label: 'Equipment ID', required: false },
            { id: 'type', label: 'Process Type', required: true, hint: 'e.g. combustion, flaring' },
            { id: 'fuel_type', label: 'Fuel Type', required: false, hint: 'e.g. Natural Gas' },
            { id: 'amount', label: 'Quantity', required: false, hint: 'Optional initial activity data' },
            { id: 'unit', label: 'Unit', required: false, hint: 'e.g. scf, m3, gal' },
            { id: 'year', label: 'Year', required: false },
            { id: 'month', label: 'Month', required: false }
        ],
        activity: [
            { id: 'activity', label: 'Activity', required: true },
            { id: 'division', label: 'Division', required: true },
            { id: 'facility_id', label: 'Region', required: true },
            { id: 'field', label: 'Field', required: false },
            { id: 'year', label: 'Year', required: true },
            { id: 'month', label: 'Month', required: true },
            { id: 'process_type', label: 'Process Type', required: true },
            { id: 'fuel', label: 'Fuel/Gas Type', required: true },
            { id: 'amount', label: 'Quantity', required: true },
            { id: 'unit', label: 'Unit', required: true },
            { id: 'equipment_id', label: 'Equipment ID', required: false },
            // Tier 3 parameters
            { id: 'flare_type', label: 'Flare Type', required: false, hint: 'elevated / enclosed_ground' },
            { id: 'ch4_content', label: 'CH4 %', required: false, hint: 'e.g. 85.5' },
            { id: 'hhv', label: 'HHV', required: false, hint: 'Btu/scf or Btu/gal' },
            { id: 'comp_flare_eff', label: 'Efficiency %', required: false, hint: 'Combustion/Destruction eff' },
            { id: 'hours', label: 'Hours', required: false, hint: 'Operating hours' },
            { id: 'tank_gor', label: 'GOR', required: false, hint: 'Gas-Oil Ratio' },
            { id: 'tank_api_gravity', label: 'API Gravity', required: false }
        ],
        activity_scope2: [
            { id: 'facility_id', label: 'Region', required: true },
            { id: 'year', label: 'Year', required: true },
            { id: 'month', label: 'Month', required: true },
            { id: 'grid_region', label: 'Grid Region', required: true },
            { id: 'consumption', label: 'Consumption', required: true },
            { id: 'unit', label: 'Unit', required: true, hint: 'kWh, MWh, GWh' }
        ],
        activity_scope3: [
            { id: 'facility_id', label: 'Region', required: true },
            { id: 'year', label: 'Year', required: true },
            { id: 'month', label: 'Month', required: true },
            { id: 'category', label: 'Category #', required: true, hint: '1-15' },
            { id: 'sub_category', label: 'Activity Type', required: true, hint: 'e.g. Steel, Flight' },
            { id: 'amount', label: 'Quantity', required: true },
            { id: 'unit', label: 'Unit', required: true }
        ],
        custom_factors: [
            { id: 'name', label: 'Factor Name', required: true, hint: 'e.g. Specialized Gas' },
            { id: 'parent_fuel', label: 'Parent API Fuel', required: false, hint: 'e.g. Natural Gas' },
            { id: 'unit', label: 'Unit', required: true, hint: 'e.g. scf, m3' },
            { id: 'co2_factor', label: 'CO2 Factor', required: true, hint: 'Numeric value' },
            { id: 'ch4_factor', label: 'CH4 Factor', required: false, hint: 'Numeric value' },
            { id: 'n2o_factor', label: 'N2O Factor', required: false, hint: 'Numeric value' },
            { id: 'co_factor', label: 'CO Factor', required: false, hint: 'Numeric value' },
            { id: 'co2_uncertainty', label: 'CO2 Uncertainty (%)', required: false, hint: 'e.g. 5' },
            { id: 'ch4_uncertainty', label: 'CH4 Uncertainty (%)', required: false, hint: 'e.g. 50' },
            { id: 'n2o_uncertainty', label: 'N2O Uncertainty (%)', required: false, hint: 'e.g. 150' },
            { id: 'usage', label: 'Usage', required: false, hint: 'e.g. combustion' }
        ],
        production: [
            { id: 'facility_id', label: 'Region', required: true },
            { id: 'activity', label: 'Activity', required: false },
            { id: 'division', label: 'Division', required: false },
            { id: 'field', label: 'Field', required: false },
            { id: 'year', label: 'Year', required: true },
            { id: 'month', label: 'Month', required: true },
            { id: 'oil_amount', label: 'Oil Quantity', required: false },
            { id: 'oil_unit', label: 'Oil Unit', required: false, hint: 'bbl' },
            { id: 'gas_amount', label: 'Gas Quantity', required: false },
            { id: 'gas_unit', label: 'Gas Unit', required: false, hint: 'mscf' }
        ],
        mitigation: [
            { id: 'facility_id', label: 'Region', required: true },
            { id: 'name', label: 'Project Name', required: true },
            { id: 'project_type', label: 'Type', required: true, hint: 'e.g. CCUS, REC' },
            { id: 'year', label: 'Year', required: true },
            { id: 'quantity_tco2e', label: 'tCO2e Avoided', required: true },
            { id: 'status', label: 'Status', required: false, hint: 'Active, Planned' },
            { id: 'start_date', label: 'Start Date', required: false, hint: 'YYYY-MM-DD' },
            { id: 'end_date', label: 'End Date', required: false, hint: 'YYYY-MM-DD' },
            { id: 'investment_amount', label: 'Investment', required: false },
            { id: 'description', label: 'Description', required: false }
        ]
    };

    const currentTemplate = TEMPLATES[type] || [];

    const downloadTemplate = () => {
        const headers = currentTemplate.map(t => t.id).join(',');

        // Generate a sample row for each process type to show variety
        const sampleRows = Object.keys(PROCESS_TYPES).map((procType, index) => {
            return currentTemplate.map(t => {
                if (t.id === 'year') return '2024';
                if (t.id === 'month') return '1';
                if (t.id === 'activity') return 'Exploration & Production';
                if (t.id === 'division') return 'Production';
                if (t.id === 'facility_id') return 'Hassi Messaoud';
                if (t.id === 'field') return 'Bir Berkine';
                if (t.id === 'type' || t.id === 'process_type') return procType;
                if (t.id === 'equipment_id') return `EQ-${100 + index}`;
                if (t.id === 'name') return `${PROCESS_TYPES[procType]} Unit`;
                if (t.id === 'fuel' || t.id === 'fuel_type') {
                    if (procType === 'combustion' || procType === 'flaring' || procType === 'venting') return 'Natural Gas';
                    if (procType === 'mobile') return 'Diesel';
                    return '-';
                }
                if (t.id === 'unit') {
                    if (procType === 'combustion') return 'scf';
                    if (procType === 'flaring' || procType === 'venting') return 'm3';
                    if (procType === 'mobile') return 'gal';
                    return 'tonnes/yr';
                }
                if (t.id === 'amount') return procType === 'mobile' ? '500' : '1000';
                if (t.id === 'flare_type') return procType === 'flaring' ? 'elevated' : '-';
                if (t.id === 'ch4_content') return (procType === 'flaring' || procType === 'venting' || procType === 'pneumatic') ? '85.5' : '-';
                if (t.id === 'hhv') return procType === 'combustion' ? '1050' : '-';
                if (t.id === 'comp_flare_eff') return (procType === 'flaring' || procType === 'combustion') ? '98.0' : '-';
                if (t.id === 'hours') return '8760';
                if (t.id === 'tank_gor') return procType === 'tank' ? '500' : '-';
                if (t.id === 'tank_api_gravity') return procType === 'tank' ? '35' : '-';
                return '';
            }).join(',');
        }).join('\n');

        let csvContent = `${headers}\n${sampleRows}`;
        
        if (type === 'custom_factors') {
            csvContent = `${headers}\nSpecialized Generator Gas,Natural Gas,scf,53.06,0.001,0.0001,0,5,50,150,combustion`;
        }
        if (type === 'production') {
            csvContent = `${headers}\nHassi Messaoud,Exploration & Production,Production,Bir Berkine,2024,1,50000,bbl,12000,mscf`;
        }
        if (type === 'mitigation') {
            csvContent = `${headers}\nHassi Messaoud,Solar Farm A,REC,2024,1500,Active,2024-01-01,,500000,Solar panel installation`;
        }
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${type}_import_template.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            parseCSV(selectedFile);
        }
    };

    const parseCSV = (file) => {
        // NEW-05 FIX: use PapaParse for robust CSV parsing (handles quotes and commas in values)
        Papa.parse(file, {
            header: false,
            skipEmptyLines: true,
            complete: (results) => {
                const data = results.data;
                if (!data || data.length === 0) {
                    setLoading(false);
                    return toast.error('Empty file');
                }

                const csvHeaders = data[0].map(h => (h || '').trim());
                const dataRows = data.slice(1).map(row => row.map(v => (v || '').trim()));

                setHeaders(csvHeaders);
                setCsvData(dataRows);

                // Auto-mapping logic
                const initialMapping = {};
                currentTemplate.forEach(t => {
                    const match = csvHeaders.find(h =>
                        h.toLowerCase() === t.id.toLowerCase() ||
                        h.toLowerCase() === t.label.toLowerCase() ||
                        h.toLowerCase().replace(/[^a-z0-9]/g, '') === t.id.toLowerCase().replace(/[^a-z0-9]/g, '')
                    );
                    if (match) initialMapping[t.id] = match;
                });
                setMapping(initialMapping);
                setLoading(false);
                setStep(2);
            },
            error: (error) => {
                setLoading(false);
                toast.error(`Failed to parse CSV: ${error.message}`);
            }
        });
    };

    const validateData = () => {
        const errors = [];
        const records = csvData.map((row, rowIndex) => {
            const record = {};
            currentTemplate.forEach(t => {
                const header = mapping[t.id];
                const index = headers.indexOf(header);
                if (index !== -1) record[t.id] = row[index];
            });

            // Check Process Type
            if (record.type && !PROCESS_TYPES[record.type.toLowerCase()]) {
                errors.push(`Row ${rowIndex + 1}: Invalid Process Type "${record.type}"`);
            }
            if (record.process_type && !PROCESS_TYPES[record.process_type.toLowerCase()]) {
                errors.push(`Row ${rowIndex + 1}: Invalid Process Type "${record.process_type}"`);
            }

            // Check Hierarchy
            if (record.activity && !HIERARCHY[record.activity]) {
                errors.push(`Row ${rowIndex + 1}: Unknown Activity "${record.activity}"`);
            } else if (record.activity && record.division && !HIERARCHY[record.activity].includes(record.division)) {
                errors.push(`Row ${rowIndex + 1}: Division "${record.division}" does not belong to "${record.activity}"`);
            }

            return record;
        });

        setValidationErrors(errors);
        return errors.length === 0;
    };

    const handlePreview = () => {
        setLoading(true);

        // Wrap in setTimeout to allow the loader to render before heavy processing
        setTimeout(() => {
            const errors = [];

            // Pre-calculate header indices for performance (O(Columns) instead of O(Rows * Columns * Headers))
            const headerIndexMap = {};
            currentTemplate.forEach(t => {
                const header = mapping[t.id];
                headerIndexMap[t.id] = headers.indexOf(header);
            });

            const records = csvData.map((row, rowIndex) => {
                const record = {};
                currentTemplate.forEach(t => {
                    const index = headerIndexMap[t.id];
                    if (index !== -1 && index !== undefined) record[t.id] = row[index];
                });

                // Validation checks
                if (record.type && !PROCESS_TYPES[record.type.toLowerCase()]) {
                    errors.push(`Row ${rowIndex + 1}: Invalid Process Type "${record.type}"`);
                }
                if (record.process_type && !PROCESS_TYPES[record.process_type.toLowerCase()]) {
                    errors.push(`Row ${rowIndex + 1}: Invalid Process Type "${record.process_type}"`);
                }

                if (record.activity && !HIERARCHY[record.activity]) {
                    errors.push(`Row ${rowIndex + 1}: Unknown Activity "${record.activity}"`);
                } else if (record.activity && record.division && !HIERARCHY[record.activity].includes(record.division)) {
                    errors.push(`Row ${rowIndex + 1}: Division "${record.division}" does not belong to "${record.activity}"`);
                }

                return record;
            });

            setMappedRecords(records);
            setValidationErrors(errors);
            setLoading(false);
            setStep(3);
        }, 50);
    };

    const handleImport = async () => {
        if (validationErrors.length > 0) {
            toast.error("Please fix validation errors before importing.");
            return;
        }
        setLoading(true);
        try {
            let endpoint = '/emissions/bulk-upload';
            if (type === 'sources') endpoint = '/sources/bulk-import';
            if (type === 'activity_scope2') endpoint = '/scope2/bulk-import';
            if (type === 'activity_scope3') endpoint = '/scope3/bulk-import';
            if (type === 'custom_factors') endpoint = '/custom-factors/import';
            if (type === 'production') endpoint = '/data/production/bulk-import';
            if (type === 'mitigation') endpoint = '/mitigation/bulk-import';

            let payload = { records: mappedRecords, confirm: true };
            if (type === 'custom_factors') {
                endpoint = '/custom-factors/import';
                payload = { factors: mappedRecords };
            }

            const res = await api.post(endpoint, payload);
            toast.success(res.data.message || 'Import successful');
            if (onImportSuccess) onImportSuccess();
            onClose();
        } catch (error) {
            console.error('Import failed:', error);
            const serverError = error.response?.data?.error || 'Server error';
            const details = error.response?.data?.details;

            if (details && Array.isArray(details)) {
                // Show first 3 errors and summary
                const errorSummary = details.slice(0, 3).join('\n');
                const remaining = details.length > 3 ? `\n...and ${details.length - 3} more errors` : '';
                toast.error(
                    <div>
                        <strong>{serverError}</strong>
                        <div style={{ fontSize: '0.8em', marginTop: '4px', whiteSpace: 'pre-wrap' }}>
                            {errorSummary}{remaining}
                        </div>
                    </div>,
                    { duration: 6000 }
                );
            } else {
                toast.error(`Import failed: ${serverError}`);
            }
        } finally {
            setLoading(false);
        }
    };

    const isMappingValid = () => {
        return currentTemplate
            .filter(t => t.required)
            .every(t => mapping[t.id]);
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Bulk Import: ${type === 'sources' ? 'Equipment' : (type === 'custom_factors' ? 'Custom Factors' : 'Activity Data')}`} maxWidth="700px">
            <div className="import-modal-content">
                {step === 1 && (
                    <div className="upload-zone" onClick={() => fileInputRef.current.click()}>
                        <Upload size={48} style={{ color: 'var(--sonatrach-orange)', marginBottom: '16px' }} />
                        <h3>Click or Drag CSV File</h3>
                        <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Standard CSV format with headers</p>
                        <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv" style={{ display: 'none' }} />

                        <div className="template-download" onClick={(e) => { e.stopPropagation(); downloadTemplate(); }}>
                            <FileText size={14} />
                            <span>Download sample CSV template</span>
                        </div>

                        <div className="cheat-sheet-toggle" onClick={(e) => { e.stopPropagation(); setShowCheatSheet(!showCheatSheet); }}>
                            <Info size={14} />
                            <span>{showCheatSheet ? 'Hide System Identifiers' : 'Show System Identifiers (Cheat Sheet)'}</span>
                        </div>

                        {showCheatSheet && (
                            <div className="cheat-sheet-content" onClick={(e) => e.stopPropagation()}>
                                <div className="cheat-section">
                                    <strong>Activities & Divisions:</strong>
                                    <ul>
                                        {Object.entries(HIERARCHY).map(([act, divs]) => (
                                            <li key={act}>{act}: <i>{divs.join(', ')}</i></li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="cheat-section">
                                    <strong>Process Types (Codes):</strong>
                                    <div className="tag-cloud">
                                        {Object.keys(PROCESS_TYPES).map(t => <span key={t} className="id-tag">{t}</span>)}
                                    </div>
                                </div>
                                <div className="cheat-section">
                                    <strong>Common Units:</strong>
                                    <div className="tag-cloud">
                                        {VALID_UNITS.map(u => <span key={u} className="id-tag">{u}</span>)}
                                    </div>
                                </div>
                                <div className="cheat-section">
                                    <strong>Engineering Params:</strong>
                                    <ul style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                                        <li><b>Flare Type:</b> elevated, enclosed_ground, pit</li>
                                        <li><b>HHV:</b> Natural Gas (~1050), Diesel (~138000)</li>
                                        <li><b>Efficiency:</b> 98.0 for Flaring default</li>
                                        <li><b>GOR:</b> Gas-Oil Ratio for Tank Flash</li>
                                    </ul>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {step === 2 && (
                    <>
                        <div className="file-info">
                            <FileText size={20} style={{ color: 'var(--sonatrach-orange)' }} />
                            <span>{file?.name} ({csvData.length} records detected)</span>
                        </div>

                        <div className="mapping-container">
                            <h4 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Loader2 size={16} className="spin" style={{ display: loading ? 'block' : 'none' }} />
                                Map CSV Columns to System Fields
                            </h4>
                            <div className="mapping-grid">
                                {currentTemplate.map(t => (
                                    <div key={t.id} className="mapping-row">
                                        <div className="mapping-label">
                                            {t.label} {t.required && <span style={{ color: '#ef4444' }}>*</span>}
                                            {t.hint && <div style={{ fontSize: '0.75rem', fontWeight: 400, opacity: 0.6 }}>{t.hint}</div>}
                                        </div>
                                        <select
                                            className="mapping-select"
                                            value={mapping[t.id] || ''}
                                            onChange={(e) => setMapping({ ...mapping, [t.id]: e.target.value })}
                                        >
                                            <option value="">-- Discard Field --</option>
                                            {headers.map(h => <option key={h} value={h}>{h}</option>)}
                                        </select>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="import-tip">
                            <Info size={14} />
                            <span>Make sure units (e.g. m3, bbl) and process types match the system identifiers.</span>
                        </div>

                        <div className="import-actions">
                            <button className="action-btn" style={{ background: 'var(--text-secondary)' }} onClick={() => setStep(1)}>Back</button>
                            <button
                                className="action-btn"
                                disabled={!isMappingValid()}
                                onClick={handlePreview}
                            >
                                Preview Data
                            </button>
                        </div>
                    </>
                )}

                {step === 3 && (
                    <>
                        <div className="preview-header">
                            <h4><CheckCircle2 size={18} style={{ color: validationErrors.length ? '#ef4444' : '#10b981' }} /> Preview & Validate</h4>
                            <span>{mappedRecords.length} records mapped</span>
                        </div>

                        {validationErrors.length > 0 && (
                            <div className="validation-error-box">
                                <h5><AlertCircle size={16} /> Validation Errors Found</h5>
                                <ul>
                                    {validationErrors.slice(0, 5).map((err, i) => <li key={i}>{err}</li>)}
                                    {validationErrors.length > 5 && <li>...and {validationErrors.length - 5} more</li>}
                                </ul>
                                <p style={{ marginTop: '8px', fontSize: '0.75rem' }}>Please go back and check your CSV identifiers.</p>
                            </div>
                        )}

                        <div className="preview-table-container">
                            <table className="preview-table">
                                <thead>
                                    <tr>
                                        {currentTemplate.map(t => <th key={t.id}>{t.label}</th>)}
                                    </tr>
                                </thead>
                                <tbody>
                                    {mappedRecords.slice(0, 10).map((rec, i) => (
                                        <tr key={i}>
                                            {currentTemplate.map(t => {
                                                const value = rec[t.id];
                                                const isHierarchyError = (t.id === 'activity' || t.id === 'division') && rec.activity && rec.division && !HIERARCHY[rec.activity]?.includes(rec.division);

                                                return (
                                                    <td key={t.id} style={{ color: isHierarchyError ? '#ef4444' : 'inherit' }}>
                                                        {value || '-'}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {mappedRecords.length > 10 && <div className="preview-more">Showing first 10 records...</div>}
                        </div>

                        <div className="import-actions">
                            <button className="action-btn" style={{ background: 'var(--text-secondary)' }} onClick={() => setStep(2)}>Back to Mapping</button>
                            <button
                                className="action-btn"
                                disabled={validationErrors.length > 0 || loading}
                                onClick={handleImport}
                            >
                                {loading ? <Loader2 size={16} className="spin" /> : 'Confirm & Import Store'}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </Modal>
    );
};

export default BulkImportModal;
