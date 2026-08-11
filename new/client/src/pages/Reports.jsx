import React, { useState, useEffect } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import './Reports.css';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import '../pages/Dashboard.css';

const Reports = () => {
    const { user } = useAuth();
    const toast = useToast();
    const [facilities, setFacilities] = useState([]);
    const [availableFilters, setAvailableFilters] = useState({ years: [], regions: [] });
    const [emissions, setEmissions] = useState([]);
    const [loading, setLoading] = useState(false);

    // Filters
    const [year, setYear] = useState(new Date().getFullYear().toString());
    const [month, setMonth] = useState('all');
    const [division, setDivision] = useState('all');
    const [field, setField] = useState('all');
    const [methodFilter, setMethodFilter] = useState('all');
    const [regionId, setRegionId] = useState('all');
    const [processType, setProcessType] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [groupBy, setGroupBy] = useState('none'); // none, facility, process, month

    // Pagination
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalRecords, setTotalRecords] = useState(0);
    const [apiError, setApiError] = useState(null);
    const [rawDebug, setRawDebug] = useState('');

    const [scope, setScope] = useState('all');

    const resetFilters = () => {
        setYear('all');
        setMonth('all');
        setRegionId('all');
        setProcessType('all');
        setScope('all');
        setDivision('all');
        setField('all');
        setMethodFilter('all');
        setSearchTerm('');
        setPage(1);
        toast.info("Filters reset to defaults.");
    };

    useEffect(() => {
        const loadInitialData = async () => {
            try {
                const [facRes, filterRes] = await Promise.all([
                    api.get('/facilities'),
                    api.get('/filters/available')
                ]);
                const facilitiesData = Array.isArray(facRes.data) ? facRes.data : (facRes.data?.data || []);
                setFacilities(facilitiesData);
                setAvailableFilters({
                    years: Array.isArray(filterRes.data?.years) ? filterRes.data.years : [],
                    regions: Array.isArray(filterRes.data?.regions) ? filterRes.data.regions : [],
                    segments: Array.isArray(filterRes.data?.segments) ? filterRes.data.segments : []
                });

                // Sync BOTH year pickers to the most recent year that has actual data
                if (filterRes.data.years?.length > 0) {
                    const mostRecentYear = filterRes.data.years[0].toString();
                    // If the most recent year is far in the future or has very few records, 
                    // we might want to default to 'all' or 2024.
                    // For now, let's keep the user's latest data as default.
                    setYear(mostRecentYear);
                    setReportYear(mostRecentYear);
                } else {
                    setYear('all');
                    setReportYear('all');
                }

                // Pre-select all facilities so the first report click works out-of-the-box
                if (facRes.data?.length > 0) {
                    setReportSelectedRegions(facRes.data.map(f => f.id.toString()));
                }
            } catch (err) {
                console.error("Error fetching initial data", err);
                toast.error("Failed to load filter data");
            }
        };
        loadInitialData();
    }, []);


    // Reset page to 1 whenever filters change (but not on page itself changing)
    const prevFiltersRef = React.useRef({ year, month, regionId, processType, scope, division });
    useEffect(() => {
        const prev = prevFiltersRef.current;
        const filterChanged = prev.year !== year || prev.month !== month || prev.regionId !== regionId ||
            prev.processType !== processType || prev.scope !== scope || prev.division !== division || prev.field !== field || prev.methodFilter !== methodFilter;
        prevFiltersRef.current = { year, month, regionId, processType, scope, division, field, methodFilter };
        if (filterChanged && page !== 1) {
            setPage(1);
            return; // page change will trigger the next fetchEmissions
        }
        fetchEmissions();
    }, [year, month, regionId, processType, scope, division, field, methodFilter, page, searchTerm]);

    const fetchEmissions = async () => {
        setLoading(true);
        try {
            const cleanYear = (year && year !== 'all' && year !== 'undefined' && year !== 'null') ? year : undefined;
            const params = {
                page,
                per_page: 50,
                scope,
                ...(cleanYear && { year: cleanYear }),
                ...(month !== 'all' && { month }),
                ...(regionId !== 'all' && { facility_id: regionId }),
                ...(division !== 'all' && { division: division }),
                ...(field !== 'all' && { field: field }),
                ...(methodFilter !== 'all' && { method: methodFilter }),
                ...(processType !== 'all' && { process_type: processType }),
                ...(searchTerm && { search: searchTerm })
            };

            console.log('[Reports] Fetching with params:', params);
            const res = await api.get('/emissions', { params });
            console.log('[Reports] Received records:', res.data.emissions?.length, 'Total reported by API:', res.data.total);
            setEmissions(res.data.emissions || res.data.data || res.data || []);
            setTotalRecords(res.data.total || res.data.length || 0);
            setTotalPages(res.data.pages || 1);
            setApiError(null);
            setRawDebug(JSON.stringify(res.data).substring(0, 200));
        } catch (err) {
            console.error("Error fetching emissions", err);
            setApiError(err.message + (err.response ? ' (' + err.response.status + ')' : ''));
            toast.error("Failed to load emissions data");
            setEmissions([]);
            setTotalRecords(0);
        } finally {
            setLoading(false);
        }
    };

    const handleExcelExport = async () => {
        try {
            const params = {
                scope,
                ...(year !== 'all' && { year }),
                ...(month !== 'all' && { month }),
                ...(regionId !== 'all' && { facility_id: regionId }),
                ...(processType !== 'all' && { process_type: processType }),
                format: 'excel'
            };

            const res = await api.get('/emissions/export', { params, responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
            const link = document.createElement('a');
            link.href = url;
            link.download = `emissions_${year}_${month}.xlsx`;
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                link.remove();
                window.URL.revokeObjectURL(url);
            }, 1000);
        } catch (err) {
            console.error("Export error", err);
            toast.error('Export failed. Please try again.');
        }
    };

    const handlePDFExport = async () => {
        try {
            const params = new URLSearchParams();
            params.append('scope', scope);
            if (year && year !== 'all') params.append('year', year);
            if (month && month !== 'all') params.append('month', month);
            if (regionId && regionId !== 'all') params.append('facility_id', regionId);
            if (processType && processType !== 'all') params.append('process_type', processType);

            const response = await api.get(`/reports/export?${params.toString()}`, {
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
            const link = document.createElement('a');
            link.href = url;
            const yearStr = year && year !== 'all' ? year : 'all';
            const monthStr = month && month !== 'all' ? month : 'all';
            link.download = `emissions_${yearStr}_${monthStr}.pdf`;
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                link.remove();
                window.URL.revokeObjectURL(url);
            }, 1000);
        } catch (error) {
            console.error('PDF export failed:', error);
            toast.error('Failed to export PDF. Please try again.');
        }
    };

    const handleOGMPExport = async () => {
        try {
            toast.info('Generating OGMP 2.0 Excel Workbook...');
            const yr = reportYear !== 'all' ? reportYear : (year !== 'all' ? year : '2024');
            const response = await api.get(`/reports/ogmp-export?year=${yr}`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
            const link = document.createElement('a');
            link.href = url;
            link.download = `OGMP_2.0_Methane_Report_${yr}.xlsx`;
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                link.remove();
                window.URL.revokeObjectURL(url);
            }, 1000);
            toast.success(`OGMP 2.0 Excel report for ${yr} downloaded successfully!`);
        } catch (error) {
            console.error('OGMP Excel export failed:', error);
            toast.error('Failed to export OGMP 2.0 Excel report.');
        }
    };

    const handleISOReport = async () => {
        setLoading(true);
        toast.info("Generating ISO 14064-1 Report...");
        try {
            // Import dynamically or assume imported at top if possible
            const { generateModernPDF } = await import('../utils/ModernReportGenerator');

            const filters = {
                year,
                scope,
                regionId,
                processType
            };

            await generateModernPDF(api, filters);
            toast.success("Report generated successfully!");
        } catch (err) {
            console.error("Report Generation Error", err);
            toast.error("Failed to generate report.");
        } finally {
            setLoading(false);
        }
    };

    const getGroupedData = () => {
        if (groupBy === 'none') return emissions;
        const grouped = {};
        emissions.forEach(em => {
            let key;
            if (groupBy === 'facility') key = em.facility_name || 'Unknown';
            else if (groupBy === 'process') key = em.process_type || 'Unknown';
            else if (groupBy === 'month') key = `${em.year}-${String(em.month).padStart(2, '0')}`;
            else if (groupBy === 'scope') key = `Scope ${em.scope}`;

            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(em);
        });
        return grouped;
    };

    const formatNumber = (num) => {
        if (num === null || num === undefined) return '0.00';
        return parseFloat(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 3 });
    };

    // Report Generation State
    const [reportYear, setReportYear] = useState(new Date().getFullYear().toString());
    const [comparisonYear, setComparisonYear] = useState('none'); // [NEW] Comparison Year State
    const [reportSelectedRegions, setReportSelectedRegions] = useState([]); // Multiselect

    // Derived options
    const regionOptions = facilities.map(f => ({
        value: f.id.toString(),
        label: f.name,
        subLabel: f.field
    }));

    const handleISOReportWrapper = async () => {
        if (reportSelectedRegions.length === 0) {
            toast.error("Please select at least one region/facility.");
            return;
        }

        setLoading(true);
        toast.info("Generating ISO 14064-1 Report...");
        try {
            const { generateModernPDF } = await import('../utils/ModernReportGenerator');

            // Pass the specific report filters, not the grid filters
            // If ALL regions selected, pass 'all'? Or pass the list? 
            // The API expects 'all' or a single ID usually, but for a REPORT we might need to filter client-side 
            // OR the backend needs to support list. 
            // Legacy logic: Checked "all" (or just selected year) -> fetch all -> filter client side.
            // ModernReportGenerator sends params.

            // STRATEGY: 
            // If reportSelectedRegions.length === facilities.length => regionId: 'all'
            // Else => we need to handle multi-region. 
            // The current ModernReportGenerator logic: `regionId !== 'all' ? regionId : undefined`. 
            // It only handles ONE region or ALL.
            // To support multi-select that isn't ALL, we might need to fetch ALL and filter in Generator?
            // Yes, ModernReportGenerator fetches `limit: 'all'`. 
            // We can pass the `reportSelectedRegions` list to strict filter in JS.

            const isAllRegions = reportSelectedRegions.length === facilities.length;

            const filters = {
                year: reportYear,
                comparisonYear: comparisonYear !== 'none' ? comparisonYear : undefined, // [NEW] Pass comparison year
                scope: 'all', // Fixed to Full Inventory for this specific report card? Or add scope selector? Legacy had just Year/Facilities.
                regionId: isAllRegions ? 'all' : reportSelectedRegions, // Pass array if subset
                processType: 'all'
            };

            // We need to update ModernReportGenerator to handle array of regionIds if we pass it.
            // Or we just let it fetch 'all' and it filters? 
            // Let's rely on ModernReportGenerator to handle the data. 
            // Currently it uses params directly. 
            // We should modify ModernReportGenerator.js to filter by the list if provided.

            await generateModernPDF(api, filters);
            toast.success("Report generated successfully!");
        } catch (err) {
            console.error("Report Generation Error", err);
            toast.error("Failed to generate report.");
        } finally {
            setLoading(false);
        }
    };

    // Chips helper
    const removeRegion = (val) => {
        setReportSelectedRegions(prev => prev.filter(v => v !== val));
    };

    return (
        <div className="reports-page">
            <header className="top-bar">
                <div className="breadcrumbs">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <line x1="10" y1="9" x2="8" y2="9" />
                    </svg>
                    <span>Dashboard</span>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>/</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Reports</span>
                </div>
                <div className="top-actions">
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{user?.fullName || 'User'}</span>
                </div>
            </header>

            <div className="reports-container">
                <div className="content-wrapper">

                    <div className="reports-header">
                        <div className="reports-title">
                            <h2>Emission Database</h2>
                            <p className="reports-subtitle">
                                Complete history of all recorded emissions and compliance data.
                                <span style={{ marginLeft: '10px', color: 'var(--primary-color)', fontWeight: 600 }}>
                                    Total Records: {totalRecords} | Showing: {emissions.length}
                                </span>
                            </p>
                        </div>
                        <div className="reports-actions">
                            <button className="btn-action" onClick={resetFilters} style={{ background: '#f8fafc', color: '#64748b', border: '1px solid #e2e8f0' }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginRight: '6px' }}>
                                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                                    <path d="M3 3v5h5" />
                                </svg>
                                Reset Filters
                            </button>
                            <button className="btn-action btn-excel" onClick={handleOGMPExport} style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#ffffff', border: 'none' }}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                                OGMP 2.0 (Excel)
                            </button>
                            <button className="btn-action btn-excel" onClick={handleExcelExport}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                                Excel Export
                            </button>
                            <button className="btn-action btn-pdf" onClick={handlePDFExport}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                </svg>
                                PDF Report
                            </button>
                        </div>
                    </div>

                    {/* NEW: Create Report Card (Matches Legacy UI) */}
                    <div className="create-report-card" style={{ marginBottom: '24px' }}>
                        <div className="card-header">
                            <div className="card-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                    <line x1="12" y1="18" x2="12" y2="12" />
                                    <line x1="9" y1="15" x2="15" y2="15" />
                                </svg>
                            </div>
                            <h3 className="card-title">Create New Report</h3>
                        </div>

                        <div className="report-controls-grid" style={{ alignItems: 'end' }}>
                            <div className="control-group">
                                <label className="input-label">Reporting Year <span style={{ color: 'var(--danger)' }}>*</span></label>
                                <select className="component-select" value={reportYear} onChange={(e) => setReportYear(e.target.value)}>
                                    <option value="all">All Years</option>
                                    {availableFilters.years.length > 0 ? (
                                        availableFilters.years.map(y => <option key={y} value={y}>{y}</option>)
                                    ) : (
                                        <option value={new Date().getFullYear()}>{new Date().getFullYear()}</option>
                                    )}
                                </select>
                            </div>

                            <div className="control-group">
                                <label className="input-label">Compare With</label>
                                <select className="component-select" value={comparisonYear} onChange={(e) => setComparisonYear(e.target.value)}>
                                    <option value="none">None (Single Year)</option>
                                    {availableFilters.years.filter(y => y.toString() !== reportYear).map(y => (
                                        <option key={y} value={y}>{y}</option>
                                    ))}
                                    <option value="baseline">Baseline (2020)</option>
                                </select>
                            </div>

                            <div className="control-group" style={{ flex: 2 }}>
                                <label className="input-label">Regions / Facilities <span style={{ color: 'var(--danger)' }}>*</span></label>
                                {/* MultiSelect Component */}
                                <React.Suspense fallback={<div>Loading...</div>}>
                                    <MultiSelectDropdown
                                        options={regionOptions}
                                        selectedValues={reportSelectedRegions}
                                        onChange={setReportSelectedRegions}
                                        label="Select Regions..."
                                    />
                                </React.Suspense>
                            </div>

                            <button
                                className="btn-create"
                                onClick={handleISOReportWrapper}
                                disabled={loading}
                                style={{
                                    opacity: loading ? 0.7 : 1,
                                    cursor: loading ? 'not-allowed' : 'pointer'
                                }}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <line x1="12" y1="5" x2="12" y2="19" />
                                    <line x1="5" y1="12" x2="19" y2="12" />
                                </svg>
                                {loading ? 'Generating...' : 'Create Report'}
                            </button>
                        </div>

                        {/* Chips */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '15px' }}>
                            {reportSelectedRegions.map(rId => {
                                const rName = facilities.find(f => f.id.toString() === rId)?.name || rId;
                                return (
                                    <span key={rId} style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        padding: '4px 10px',
                                        borderRadius: '16px',
                                        background: 'rgba(255, 107, 0, 0.1)',
                                        color: 'var(--primary-color)',
                                        fontSize: '0.85rem'
                                    }}>
                                        {rName}
                                        <button
                                            onClick={() => removeRegion(rId)}
                                            style={{ background: 'none', border: 'none', color: 'inherit', marginLeft: '6px', cursor: 'pointer', padding: 0 }}
                                        >
                                            ×
                                        </button>
                                    </span>
                                );
                            })}
                        </div>
                    </div>

                    {/* Filter Card */}
                    <div className="create-report-card">
                        <div className="card-header">
                            <div className="card-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                                </svg>
                            </div>
                            <h3 className="card-title">Filter & Group Data</h3>
                        </div>

                        <div className="report-controls-grid">
                            <div className="control-group">
                                <label className="input-label">Inventory Scope</label>
                                <select className="component-select" value={scope} onChange={(e) => setScope(e.target.value)}>
                                    <option value="all">Total Inventory (Scope 1,2,3)</option>
                                    <option value="1">Scope 1 (Direct)</option>
                                    <option value="2">Scope 2 (Indirect)</option>
                                    <option value="3">Scope 3 (Value Chain)</option>
                                </select>
                            </div>

                            <div className="control-group">
                                <label className="input-label">Reporting Year</label>
                                <select className="component-select" value={year} onChange={(e) => {
                                    console.log('[Reports] User changed Year to:', e.target.value);
                                    setYear(e.target.value);
                                }}>
                                    <option value="all">All Years</option>
                                    {availableFilters.years.map(y => (
                                        <option key={y} value={y}>{y}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="control-group">
                                <label className="input-label">Month</label>
                                <select className="component-select" value={month} onChange={(e) => setMonth(e.target.value)}>
                                    <option value="all">All Months</option>
                                    {[...Array(12)].map((_, i) => (
                                        <option key={i + 1} value={i + 1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="control-group">
                                <label className="input-label">Region (Grid)</label>
                                <select className="component-select" value={regionId} onChange={(e) => setRegionId(e.target.value)}>
                                    <option value="all">All Regions</option>
                                    {availableFilters.regions.map(f => (
                                        <option key={f.id} value={f.id}>{f.name} {f.field ? ` - ${f.field}` : ''}</option>
                                    ))}
                                </select>
                            </div>

                            {scope === '1' && (
                                <div className="control-group">
                                    <label className="input-label">Process Type</label>
                                    <select className="component-select" value={processType} onChange={(e) => setProcessType(e.target.value)}>
                                        <option value="all">All Processes</option>
                                        <option value="combustion">Stationary Combustion</option>
                                        <option value="mobile">Mobile Combustion</option>
                                        <option value="flaring">Flaring</option>
                                        <option value="venting">Venting</option>
                                        <option value="fugitive">Fugitive Emissions</option>
                                        <option value="pneumatic">Pneumatic Devices</option>
                                        <option value="tank">Storage Tank</option>
                                    </select>
                                </div>
                            )}
                            <div className="control-group">
                                <label className="input-label">Division</label>
                                <select className="component-select" value={division} onChange={(e) => setDivision(e.target.value)}>
                                    <option value="all">All Divisions</option>
                                    {[...new Set(facilities.map(f => f.division))].filter(Boolean).map(div => (
                                        <option key={div} value={div}>{div}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="control-group">
                                <label className="input-label">Field</label>
                                <select className="component-select" value={field} onChange={(e) => setField(e.target.value)}>
                                    <option value="all">All Fields</option>
                                    {[...new Set(facilities.map(f => f.field))].filter(Boolean).map(fld => (
                                        <option key={fld} value={fld}>{fld}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="control-group">
                                <label className="input-label">Calc Method</label>
                                <select className="component-select" value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)}>
                                    <option value="all">All Methods</option>
                                    <option value="custom">Custom Factor</option>
                                    <option value="API">API Engine</option>
                                    <option value="Location-based">Location-based</option>
                                </select>
                            </div>
                            <div className="control-group">
                                <label className="input-label">Group By</label>
                                <select className="component-select" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                                    <option value="none">No Grouping</option>
                                    <option value="facility">By Facility</option>
                                    <option value="process">By Category/Process</option>
                                    <option value="month">By Month</option>
                                    <option value="scope">By Scope</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="filters-container">
                        <div className="search-input-wrapper">
                            <label className="input-label">Search</label>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type="text"
                                    className="search-input"
                                    placeholder="Search records..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Data Grid */}
                    {loading && <div style={{ minHeight: '300px' }}><LoadingSpinner /></div>}

                    {!loading && emissions.length === 0 && (
                        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                            No emission records found. Adjust your filters or add new emissions.
                        </div>
                    )}

                    {!loading && emissions.length > 0 && (
                        <div className="table-container">
                            <div className="grid-header">
                                <div className="cell">ID</div>
                                <div className="cell">Date</div>
                                <div className="cell">Scope</div>
                                <div className="cell">Division</div>
                                <div className="cell">Field</div>
                                <div className="cell">Facility</div>
                                <div className="cell">Group</div>
                                <div className="cell">Equipment</div>
                                <div className="cell">Category/Process</div>
                                <div className="cell">Fuel/Source</div>
                                <div className="cell">Factor Type</div>
                                <div className="cell cell-number">Qty</div>
                                <div className="cell cell-number">Total (tCO₂e)</div>
                                <div className="cell">Status</div>
                            </div>
                            {/* Rows */}
                            {emissions.map(row => (
                                <div key={row.id} className="grid-row">
                                    <div className="cell" style={{ fontSize: '0.75rem', opacity: 0.7 }}>{row.id}</div>
                                    <div className="cell">{row.month}/{row.year}</div>
                                    <div className="cell">
                                        <span className={`scope-badge scope-${row.scope}`}>
                                            Scope {row.scope}
                                        </span>
                                    </div>
                                    <div className="cell">{row.division || 'N/A'}</div>
                                    <div className="cell">{row.field || 'N/A'}</div>
                                    <div className="cell">{row.facility_name || 'N/A'}</div>
                                    <div className="cell">{row.group_name || 'N/A'}</div>
                                    <div className="cell">{row.equipment_id || 'N/A'}</div>
                                    <div className="cell" style={{ fontWeight: 500 }}>{row.process_type}</div>
                                    <div className="cell">{row.fuel || 'N/A'}</div>
                                    <div className="cell" style={{ fontSize: '0.85rem' }}>{row.factor_type || 'N/A'}</div>
                                    <div className="cell cell-number">
                                        {row.amount ? formatNumber(row.amount) : '-'}
                                        <span style={{ fontSize: '0.7rem', marginLeft: '4px', opacity: 0.7 }}>{row.unit}</span>
                                    </div>
                                    <div className="cell cell-number cell-total" style={{ color: 'var(--primary-color)', fontWeight: 700 }}>
                                        {/* BUG-UI-06 FIX: Show '—' for null instead of misleading '0.00' */}
                                        {row.co2e_total != null ? formatNumber(row.co2e_total) : '—'}
                                    </div>
                                    <div className="cell">
                                        <span style={{ fontSize: '0.8rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
                                            {row.status || 'Verified'}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {!loading && totalPages > 1 && (
                        <div className="pagination-wrapper">
                            <button className="btn-page" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</button>
                            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                Page {page} of {totalPages} ({totalRecords} records)
                            </span>
                            <button className="btn-page" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</button>
                        </div>
                    )}

                </div>
            </div >
        </div >
    );
};

export default Reports;
