import React, { useState, useEffect } from 'react';
import api from '../api';
import CustomDropdown from '../components/CustomDropdown';
import { PROCESS_TYPES } from '../utils/EmissionFactors';
import { GWP_AR5, BOUNDARY_OPTIONS } from '../constants';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import BulkImportModal from '../components/BulkImportModal';
import ErrorBoundary from '../components/ErrorBoundary'; // FE-03 FIX
import { useAuth } from '../context/AuthContext';
import { ChevronRight, Download, Plus, Search, MapPin, Layers, Settings, FileText, Database, Shield, Zap, Upload } from 'lucide-react';
import './ManageData.css';
import '../pages/Dashboard.css';


const PaginationControls = ({ currentPage, totalItems, itemsPerPage, onPageChange }) => {
    const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', padding: '16px 0', borderTop: '1px solid #e5e7eb' }}>
            <button 
                className="btn-ghost" 
                disabled={currentPage <= 1} 
                onClick={() => onPageChange(currentPage - 1)}
                style={{ opacity: currentPage <= 1 ? 0.5 : 1, cursor: currentPage <= 1 ? 'not-allowed' : 'pointer', padding: '6px 12px' }}
            >
                Previous
            </button>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Page {currentPage} of {totalPages}
            </span>
            <button 
                className="btn-ghost" 
                disabled={currentPage >= totalPages} 
                onClick={() => onPageChange(currentPage + 1)}
                style={{ opacity: currentPage >= totalPages ? 0.5 : 1, cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer', padding: '6px 12px' }}
            >
                Next
            </button>
        </div>
    );
};

const ManageDataInner = () => {
    const { user } = useAuth();


    const HIERARCHY = {
        'EP': ['Production', 'Association'],
        'LQS': ['LNG', 'LPG'],
        'RPC': ['Refining', 'Petrochemicals'],
        'TRC': ['TRC']
    };

    const ACTIVITY_LABELS = {
        'EP': 'Exploration & Production',
        'LQS': 'Liquifaction and Separation',
        'RPC': 'Refining and Petrochemicals',
        'TRC': 'Transport (TRC)'
    };

    // Derive available activities from the already-permission-filtered facilities list
    const getAvailableActivities = (facilitiesList = facilities) => {
        const acts = [...new Set(facilitiesList.map(f => f.activity).filter(Boolean))];
        // Sort by the defined hierarchy order, then alphabetically for unknowns
        const order = Object.keys(HIERARCHY);
        return acts.sort((a, b) => {
            const ia = order.indexOf(a);
            const ib = order.indexOf(b);
            if (ia !== -1 && ib !== -1) return ia - ib;
            if (ia !== -1) return -1;
            if (ib !== -1) return 1;
            return a.localeCompare(b);
        });
    };

    // Derive available divisions for a given activity from the filtered facilities list
    const getAvailableDivisions = (activity, facilitiesList = facilities) => {
        if (!activity) return [];
        return [...new Set(
            facilitiesList.filter(f => f.activity === activity).map(f => f.division).filter(Boolean)
        )].sort();
    };

    const toast = useToast();
    const [activeTab, setActiveTab] = useState('factors');
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // Filter & Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 15;
    
    const [filterActivity, setFilterActivity] = useState('');
    const [filterDivision, setFilterDivision] = useState('');
    const [filterRegion, setFilterRegion] = useState('');
    const [filterYear, setFilterYear] = useState('');

    useEffect(() => {
        setCurrentPage(1);
    }, [activeTab, searchTerm, filterActivity, filterDivision, filterRegion, filterYear]);


    // Data State
    const [facilities, setFacilities] = useState([]);
    const [customFactors, setCustomFactors] = useState([]);
    const [productionData, setProductionData] = useState([]);
    const [availableFilters, setAvailableFilters] = useState({ years: [], regions: [] });
    const [importModal, setImportModal] = useState({ isOpen: false, type: 'sources' });
    const [sources, setSources] = useState([]);
    const [mitigations, setMitigations] = useState([]);
    const [cbamExports, setCbamExports] = useState([]);
    const [ogmpSurveys, setOgmpSurveys] = useState([]);

    // Forms State
    const [facilityForm, setFacilityForm] = useState({
        name: '', activity: '', division: '', field: '', location: '',
        boundary_type: '', boundary_detail: '',
        segment: '', latitude: '', longitude: ''
    });

    const [factorForm, setFactorForm] = useState({
        factor_name: '', parent_fuel: '', unit: 'scf',
        co2_factor: '', ch4_factor: '', n2o_factor: '',
        co_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: ''
    });
    const [editingFactorId, setEditingFactorId] = useState(null);

    const [prodForm, setProdForm] = useState({
        activity: '', division: '', facility_id: '',
        month: 1, year: new Date().getFullYear(),
        oil_amount: '', oil_unit: 'bbl',
        gas_amount: '', gas_unit: 'mscf'
    });

    const [sourceForm, setSourceForm] = useState({
        activity: '', division: '', facility_id: '',
        name: '', type: '', equipment_id: '', fuel_type: '',
        design_capacity: '', description: '', status: 'Active'
    });

    const [mitigationForm, setMitigationForm] = useState({
        activity: '', division: '', facility_id: '',
        name: '', year: new Date().getFullYear(), type: 'CCUS',
        quantity_tco2e: '', status: 'Active', reference_id: '', notes: ''
    });

    const [cbamForm, setCbamForm] = useState({
        id: null, activity: '', division: '', facility_id: '',
        year: new Date().getFullYear(), month: 1,
        product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
        quantity_tonnes: '', export_destination: 'EU',
        specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
    });
    const [editingCbamId, setEditingCbamId] = useState(null);

    const [ogmpForm, setOgmpForm] = useState({
        id: null, activity: '', division: '', facility_id: '',
        year: new Date().getFullYear(),
        survey_date: new Date().toISOString().split('T')[0],
        survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
        measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
    });
    const [editingOgmpId, setEditingOgmpId] = useState(null);

    const [workbench, setWorkbench] = useState({
        meter_precision: 5.0, lab_precision: 2.0, gwp_uncertainty: 15.0
    });

    // Fetch Data on Load
    useEffect(() => {
        fetchFacilities();
        fetchCustomFactors();
        fetchProduction();
        fetchSources();
        fetchMitigations();
        fetchCbamExports();
        fetchOgmpSurveys();
    }, []);

    // Auto-populate forms based on user's accessible facilities
    // Admin users: skip (keep all dropdowns optional)
    // Non-admin users: cascade-fill activity → division → region when unambiguous
    useEffect(() => {
        if (facilities.length === 0) return;
        if (user?.role === 'admin') return;

        // Step 1: unique activities the user can see
        const availableActivities = [...new Set(facilities.map(f => f.activity).filter(Boolean))];
        const autoActivity = availableActivities.length === 1 ? availableActivities[0] : '';

        // Step 2: unique divisions within that activity
        const availableDivisions = autoActivity
            ? [...new Set(facilities.filter(f => f.activity === autoActivity).map(f => f.division).filter(Boolean))]
            : [];
        const autoDivision = availableDivisions.length === 1 ? availableDivisions[0] : '';

        // Step 3: facilities matching the resolved activity + division
        const matchingFacilities = facilities.filter(f =>
            (!autoActivity || f.activity === autoActivity) &&
            (!autoDivision || f.division === autoDivision)
        );
        const autoFacilityId = matchingFacilities.length === 1 ? matchingFacilities[0].id.toString() : '';

        const autoFill = { activity: autoActivity, division: autoDivision, facility_id: autoFacilityId };

        setProdForm(prev => ({ ...prev, ...autoFill }));
        setSourceForm(prev => ({ ...prev, ...autoFill }));
        setMitigationForm(prev => ({ ...prev, ...autoFill }));
        setCbamForm(prev => ({ ...prev, ...autoFill }));
        setOgmpForm(prev => ({ ...prev, ...autoFill }));
    }, [facilities]);

    // API Calls
    const fetchFacilities = async () => {
        try {
            const res = await api.get('/facilities/');
            setFacilities(res.data);
            const regions = [...new Set(res.data.map(f => f.location))].filter(Boolean);
            setAvailableFilters(prev => ({ ...prev, regions }));
        } catch (err) { console.error(err); }
    };

    const fetchCustomFactors = async () => {
        try {
            const res = await api.get('/custom-factors/');
            setCustomFactors(res.data);
        } catch (err) { console.error(err); }
    };

    const fetchProduction = async () => {
        try {
            const res = await api.get('/data/production/');
            setProductionData(res.data);
            const years = [...new Set(res.data.map(d => d.year))].sort((a, b) => b - a);
            setAvailableFilters(prev => ({ ...prev, years }));
        } catch (err) { console.error(err); }
    };

    const fetchSources = async () => {
        try {
            const res = await api.get('/sources/');
            setSources(res.data);
        } catch (err) { console.error(err); }
    };

    const fetchMitigations = async () => {
        try {
            const res = await api.get('/mitigation/');
            setMitigations(res.data);
        } catch (err) { console.error(err); }
    };

    const fetchCbamExports = async () => {
        try {
            const res = await api.get('/data/cbam-exports');
            setCbamExports(res.data || []);
        } catch (err) { console.error(err); }
    };

    const fetchOgmpSurveys = async () => {
        try {
            const res = await api.get('/data/ogmp-surveys');
            setOgmpSurveys(res.data || []);
        } catch (err) { console.error(err); }
    };


    // Handlers
    const handleAddFacility = async () => {
        if (!facilityForm.name || !facilityForm.activity || !facilityForm.division) {
            return toast.error('Name, Activity, and Division are required');
        }
        try {
            // Construct combined boundary_notes
            const fullBoundary = facilityForm.boundary_detail
                ? `${facilityForm.boundary_type} - ${facilityForm.boundary_detail}`
                : facilityForm.boundary_type;

            await api.post('/facilities/', {
                ...facilityForm,
                boundary_notes: fullBoundary // Map back to API field
            });
            toast.success('Region added!');
            setFacilityForm({
                name: '', activity: '', division: '', field: '', location: '',
                boundary_type: '', boundary_detail: '',
                segment: '', latitude: '', longitude: ''
            });
            fetchFacilities();
        } catch (err) { toast.error('Failed to add region'); }
    };

    const handleSaveFactor = async () => {
        if (!factorForm.factor_name) return toast.error('Name required');
        try {
            if (editingFactorId) {
                await api.put(`/custom-factors/${editingFactorId}`, factorForm);
                toast.success('Factor updated!');
            } else {
                await api.post('/custom-factors/', factorForm);
                toast.success('Factor added!');
            }
            setFactorForm({ factor_name: '', parent_fuel: '', unit: 'scf', co2_factor: '', ch4_factor: '', n2o_factor: '', co_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: '' });
            setEditingFactorId(null);
            fetchCustomFactors();
        } catch (err) { toast.error('Failed to save factor'); }
    };

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        setSearchTerm('');
    };

    const handleDeleteFactor = async (id) => {
        if (!confirm('Delete this factor?')) return;
        try {
            await api.delete(`/custom-factors/${id}`);
            toast.success('Factor deleted!');
            fetchCustomFactors();
        } catch (err) { toast.error('Failed to delete factor'); }
    };

    const handleEditFactor = (factor) => {
        setFactorForm({
            factor_name: factor.factor_name,
            parent_fuel: factor.parent_fuel || '',
            unit: factor.unit || 'scf',
            co2_factor: factor.co2_factor || '',
            ch4_factor: factor.ch4_factor || '',
            n2o_factor: factor.n2o_factor || '',
            co_factor: factor.co_factor || '',
            co2_uncertainty: factor.co2_uncertainty || '',
            ch4_uncertainty: factor.ch4_uncertainty || '',
            n2o_uncertainty: factor.n2o_uncertainty || ''
        });
        setEditingFactorId(factor.id);
    };

    const handleSaveProduction = async () => {
        if (!prodForm.facility_id || !prodForm.year || !prodForm.month) {
            return toast.error('Region, Year and Month are required');
        }
        try {
            await api.post('/data/production/', {
                ...prodForm,
                oil_amount: parseFloat(prodForm.oil_amount) || 0,
                gas_amount: parseFloat(prodForm.gas_amount) || 0
            });
            toast.success('Production record saved!');
            fetchProduction();
        } catch (err) { toast.error('Failed to save production'); }
    };

    const handleSaveSource = async () => {
        if (!sourceForm.facility_id || !sourceForm.name) return toast.error('Name and Region required');
        try {
            await api.post('/sources/', sourceForm);
            toast.success('Source added!');
            fetchSources();
            setSourceForm({ ...sourceForm, name: '', fuel_type: '', design_capacity: '', description: '' });
        } catch (err) { toast.error('Failed to add source'); }
    };

    const handleSaveMitigation = async () => {
        if (!mitigationForm.quantity_tco2e) return toast.error('Quantity required');
        try {
            await api.post('/mitigation/', mitigationForm);
            toast.success('Mitigation record saved!');
            fetchMitigations();
            setMitigationForm({ ...mitigationForm, quantity_tco2e: '', notes: '', reference_id: '', name: '' });
        } catch (err) { toast.error('Failed to save mitigation'); }
    };

    const handleSaveCbamExport = async () => {
        if (!cbamForm.facility_id || !cbamForm.product_name || !cbamForm.quantity_tonnes) {
            return toast.error('Facility, Product Name, and Export Quantity are required');
        }
        try {
            await api.post('/data/cbam-exports', {
                id: editingCbamId || undefined,
                facility_id: parseInt(cbamForm.facility_id),
                year: parseInt(cbamForm.year),
                month: parseInt(cbamForm.month),
                product_name: cbamForm.product_name,
                cn_code: cbamForm.cn_code,
                quantity_tonnes: parseFloat(cbamForm.quantity_tonnes),
                export_destination: cbamForm.export_destination,
                specific_embedded_direct: cbamForm.specific_embedded_direct ? parseFloat(cbamForm.specific_embedded_direct) : 0.0,
                specific_embedded_indirect: cbamForm.specific_embedded_indirect ? parseFloat(cbamForm.specific_embedded_indirect) : 0.0,
                notes: cbamForm.notes
            });
            toast.success(editingCbamId ? 'CBAM export record updated!' : 'CBAM export record saved!');
            setEditingCbamId(null);
            setCbamForm({
                id: null, activity: cbamForm.activity, division: cbamForm.division, facility_id: cbamForm.facility_id,
                year: new Date().getFullYear(), month: 1,
                product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
                quantity_tonnes: '', export_destination: 'EU',
                specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
            });
            fetchCbamExports();
        } catch (err) {
            toast.error(err.response?.data?.error || 'Failed to save CBAM record');
        }
    };

    const handleDeleteCbamExport = async (id) => {
        if (!confirm('Delete this CBAM export record?')) return;
        try {
            await api.delete(`/data/cbam-exports/${id}`);
            toast.success('CBAM export record deleted');
            fetchCbamExports();
        } catch (err) {
            toast.error('Failed to delete CBAM record');
        }
    };

    const handleSaveOgmpSurvey = async () => {
        if (!ogmpForm.facility_id || !ogmpForm.survey_date || ogmpForm.measured_rate_kg_hr === '') {
            return toast.error('Facility, Survey Date, and Measured Rate are required');
        }
        try {
            await api.post('/data/ogmp-surveys', {
                id: editingOgmpId || undefined,
                facility_id: parseInt(ogmpForm.facility_id),
                year: parseInt(ogmpForm.year),
                survey_date: ogmpForm.survey_date,
                survey_type: ogmpForm.survey_type,
                measured_rate_kg_hr: parseFloat(ogmpForm.measured_rate_kg_hr),
                reconciliation_status: ogmpForm.reconciliation_status,
                operator_notes: ogmpForm.operator_notes
            });
            toast.success(editingOgmpId ? 'OGMP survey record updated!' : 'OGMP survey record saved!');
            setEditingOgmpId(null);
            setOgmpForm({
                id: null, activity: ogmpForm.activity, division: ogmpForm.division, facility_id: ogmpForm.facility_id,
                year: new Date().getFullYear(),
                survey_date: new Date().toISOString().split('T')[0],
                survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
                measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
            });
            fetchOgmpSurveys();
        } catch (err) {
            toast.error(err.response?.data?.error || 'Failed to save OGMP survey');
        }
    };

    const handleDeleteOgmpSurvey = async (id) => {
        if (!confirm('Delete this OGMP survey record?')) return;
        try {
            await api.delete(`/data/ogmp-surveys/${id}`);
            toast.success('OGMP survey record deleted');
            fetchOgmpSurveys();
        } catch (err) {
            toast.error('Failed to delete OGMP survey');
        }
    };

    const handleFactorChange = (e) => {
        setFactorForm({ ...factorForm, [e.target.name]: e.target.value });
    };

    const handleFacilityChange = (e) => {
        setFacilityForm({ ...facilityForm, [e.target.name]: e.target.value });
    };

    // Conversion Helpers
    const openGasConverter = () => {
        const value = prompt("Enter Gas amount in m³ to convert to mcf (x 0.0353147):");
        if (value && !isNaN(value)) {
            const mcf = (parseFloat(value) * 0.0353147).toFixed(2);
            setProdForm({ ...prodForm, gas_amount: mcf });
            toast.success(`Converted ${value} m³ to ${mcf} mcf`);
        }
    };

    const openOilConverter = () => {
        const value = prompt("Enter Oil amount in m³ to convert to bbl (x 6.28981):");
        if (value && !isNaN(value)) {
            const bbl = (parseFloat(value) * 6.28981).toFixed(2);
            setProdForm({ ...prodForm, oil_amount: bbl });
            toast.success(`Converted ${value} m³ to ${bbl} bbl`);
        }
    };

    // CSV Logic
    const exportToCSV = (data, filename) => {
        if (!data || data.length === 0) return toast.info('No data to export');
        const headers = Object.keys(data[0]).join(',');
        const rows = data.map(obj => Object.values(obj).join(',')).join('\n');
        const csvContent = "data:text/csv;charset=utf-8," + headers + "\n" + rows;
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleImportCSV = async (file, type) => {
        toast.info(`Importing ${type} CSV... (Logic to be handled by backend)`);
    };


    // --- Pre-calculate Filtered Data for Pagination ---
    const getFilteredFactors = () => customFactors.filter(f => f.factor_name.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const getFilteredFacilities = () => facilities.filter(f => {
        const matchesSearch = f.name.toLowerCase().includes(searchTerm.toLowerCase()) || (f.location?.toLowerCase() || '').includes(searchTerm.toLowerCase()) || (f.field?.toLowerCase() || '').includes(searchTerm.toLowerCase());
        const matchesActivity = filterActivity ? f.activity === filterActivity : true;
        const matchesDivision = filterDivision ? f.division === filterDivision : true;
        const matchesRegion = filterRegion ? f.location === filterRegion : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion;
    });

    const getFilteredProduction = () => productionData.filter(d => {
        const fac = facilities.find(f => f.id === d.facilityId);
        const facName = fac ? fac.name.toLowerCase() : String(d.facilityId).toLowerCase();
        const matchesSearch = facName.includes(searchTerm.toLowerCase()) || d.year.toString().includes(searchTerm) || (d.activity?.toLowerCase() || '').includes(searchTerm.toLowerCase());
        const matchesActivity = filterActivity ? d.activity === filterActivity : true;
        const matchesDivision = filterDivision ? d.division === filterDivision : true;
        const matchesRegion = filterRegion ? (fac && fac.location === filterRegion) : true;
        const matchesYear = filterYear ? d.year.toString() === filterYear.toString() : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion && matchesYear;
    });

    const getFilteredSources = () => sources.filter(s => {
        const fac = facilities.find(f => f.id === s.facility_id);
        const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) || (s.equipment_id?.toLowerCase() || '').includes(searchTerm.toLowerCase()) || (s.type?.toLowerCase() || '').includes(searchTerm.toLowerCase());
        const matchesActivity = filterActivity ? (fac && fac.activity === filterActivity) : true;
        const matchesDivision = filterDivision ? (fac && fac.division === filterDivision) : true;
        const matchesRegion = filterRegion ? (fac && fac.location === filterRegion) : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion;
    });

    const getFilteredMitigations = () => mitigations.filter(m => {
        const fac = facilities.find(f => f.id === m.facility_id);
        const matchesSearch = (m.name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) || m.type.toLowerCase().includes(searchTerm.toLowerCase()) || (m.notes?.toLowerCase() || '').includes(searchTerm.toLowerCase()) || m.year.toString().includes(searchTerm);
        const matchesActivity = filterActivity ? m.activity === filterActivity : true;
        const matchesDivision = filterDivision ? m.division === filterDivision : true;
        const matchesRegion = filterRegion ? m.region === filterRegion : true;
        const matchesYear = filterYear ? m.year.toString() === filterYear.toString() : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion && matchesYear;
    });

    const getFilteredCbam = () => cbamExports.filter(c => {
        const fid = c.facility_id || c.facilityId;
        const fac = facilities.find(f => f.id === fid);
        const pName = c.product_name || c.productName || '';
        const cn = c.cn_code || c.cnCode || '';
        const dest = c.export_destination || c.exportDestination || '';
        const fName = c.facility_name || c.facilityName || fac?.name || '';
        const yr = (c.year || '').toString();

        const matchesSearch = pName.toLowerCase().includes(searchTerm.toLowerCase()) ||
            cn.toLowerCase().includes(searchTerm.toLowerCase()) ||
            dest.toLowerCase().includes(searchTerm.toLowerCase()) ||
            fName.toLowerCase().includes(searchTerm.toLowerCase()) ||
            yr.includes(searchTerm);
        const matchesActivity = filterActivity ? (fac && fac.activity === filterActivity) : true;
        const matchesDivision = filterDivision ? (fac && fac.division === filterDivision) : true;
        const matchesRegion = filterRegion ? (fac && fac.location === filterRegion) : true;
        const matchesYear = filterYear ? yr === filterYear.toString() : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion && matchesYear;
    });

    const getFilteredOgmp = () => ogmpSurveys.filter(o => {
        const fid = o.facility_id || o.facilityId;
        const fac = facilities.find(f => f.id === fid);
        const sType = o.survey_type || o.surveyType || '';
        const fName = o.facility_name || o.facilityName || fac?.name || '';
        const rStatus = o.reconciliation_status || o.reconciliationStatus || '';
        const yr = (o.year || (o.survey_date || o.surveyDate ? new Date(o.survey_date || o.surveyDate).getFullYear() : '')).toString();

        const matchesSearch = sType.toLowerCase().includes(searchTerm.toLowerCase()) ||
            fName.toLowerCase().includes(searchTerm.toLowerCase()) ||
            rStatus.toLowerCase().includes(searchTerm.toLowerCase()) ||
            yr.includes(searchTerm);
        const matchesActivity = filterActivity ? (fac && fac.activity === filterActivity) : true;
        const matchesDivision = filterDivision ? (fac && fac.division === filterDivision) : true;
        const matchesRegion = filterRegion ? (fac && fac.location === filterRegion) : true;
        const matchesYear = filterYear ? yr === filterYear.toString() : true;
        return matchesSearch && matchesActivity && matchesDivision && matchesRegion && matchesYear;
    });

    const filteredFactors = getFilteredFactors();
    const filteredFacilities = getFilteredFacilities();
    const filteredProduction = getFilteredProduction();
    const filteredSources = getFilteredSources();
    const filteredMitigations = getFilteredMitigations();
    const filteredCbam = getFilteredCbam();
    const filteredOgmp = getFilteredOgmp();

    return (
        <div className="manage-data-page" >
            {loading && <LoadingSpinner message="Loading Data..." fullScreen />}
            < header className="top-bar" >
                <div className="breadcrumbs">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
                        <rect x="3" y="3" width="7" height="7" />
                        <rect x="14" y="3" width="7" height="7" />
                        <rect x="14" y="14" width="7" height="7" />
                        <rect x="3" y="14" width="7" height="7" />
                    </svg>
                    <span>Dashboard</span>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>/</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Manage Data</span>
                </div>
                <div className="top-actions">
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{user?.fullName || 'User'}</span>
                </div>
            </header >

            <div className="manage-container">
                <div className="manage-layout">
                    {/* Sidebar Navigation */}
                    <aside className="manage-nav-panel">
                        <h3 style={{ margin: '0 0 16px 12px', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-secondary)' }}>
                            Management
                        </h3>
                        <div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`} onClick={() => handleTabChange('factors')}>
                            <span>Emission Factors</span>
                        </div>
                        {user?.role === 'admin' && (
                            <div className={`manage-nav-item ${activeTab === 'facilities' ? 'active' : ''}`} onClick={() => handleTabChange('facilities')}>
                                <span>Regions</span>
                            </div>
                        )}
                        <div className={`manage-nav-item ${activeTab === 'production' ? 'active' : ''}`} onClick={() => handleTabChange('production')}>
                            <span>Production Data</span>
                        </div>
                        <div className={`manage-nav-item ${activeTab === 'sources' ? 'active' : ''}`} onClick={() => handleTabChange('sources')}>
                            <span>Emission Sources</span>
                        </div>
                        <div className={`manage-nav-item ${activeTab === 'mitigation' ? 'active' : ''}`} onClick={() => handleTabChange('mitigation')}>
                            <span>Mitigation Projects</span>
                        </div>
                        <div className={`manage-nav-item ${activeTab === 'cbam' ? 'active' : ''}`} onClick={() => handleTabChange('cbam')}>
                            <span>CBAM Export Products</span>
                        </div>
                        <div className={`manage-nav-item ${activeTab === 'ogmp' ? 'active' : ''}`} onClick={() => handleTabChange('ogmp')}>
                            <span>OGMP 2.0 Surveys</span>
                        </div>

                    </aside>

                    {/* Content Area */}
                    <section style={{ flex: 1 }}>
                        <div style={{ marginBottom: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                            <div style={{ position: 'relative', flex: 1, minWidth: '250px' }}>
                                <Search className="search-icon" size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                                <input
                                    type="text"
                                    placeholder={`Search ${activeTab}...`}
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="mole-input"
                                    style={{ paddingLeft: '40px', background: 'white', width: '100%' }}
                                />
                            </div>
                            
                            {activeTab !== 'factors' && (
                                <>
                                    <select value={filterActivity} onChange={(e) => { setFilterActivity(e.target.value); setFilterDivision(''); }} className="component-select" style={{ width: 'auto' }}>
                                        <option value="">All Activities</option>
                                        {Object.keys(HIERARCHY).map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a]}</option>)}
                                    </select>

                                    <select value={filterDivision} onChange={(e) => setFilterDivision(e.target.value)} className="component-select" style={{ width: 'auto' }} disabled={!filterActivity}>
                                        <option value="">All Divisions</option>
                                        {filterActivity && HIERARCHY[filterActivity] && HIERARCHY[filterActivity].map(d => <option key={d} value={d}>{d}</option>)}
                                    </select>

                                    <select value={filterRegion} onChange={(e) => setFilterRegion(e.target.value)} className="component-select" style={{ width: 'auto' }}>
                                        <option value="">All Regions</option>
                                        {availableFilters.regions?.map(r => <option key={r} value={r}>{r}</option>)}
                                    </select>

                                    {(activeTab === 'production' || activeTab === 'mitigation') && (
                                        <select value={filterYear} onChange={(e) => setFilterYear(e.target.value)} className="component-select" style={{ width: 'auto' }}>
                                            <option value="">All Years</option>
                                            {availableFilters.years?.map(y => <option key={y} value={y}>{y}</option>)}
                                        </select>
                                    )}
                                    
                                    {(filterActivity || filterDivision || filterRegion || filterYear) && (
                                        <button className="btn-ghost" onClick={() => { setFilterActivity(''); setFilterDivision(''); setFilterRegion(''); setFilterYear(''); }} style={{ color: 'var(--text-secondary)', padding: '6px 12px', fontSize: '0.85rem' }}>
                                            Clear Filters
                                        </button>
                                    )}
                                </>
                            )}
                        </div>

                        {/* Factors Tab */}
                        {activeTab === 'factors' && (
                            <div className="manage-card">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                                    <div>
                                        <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Custom Emission Factors</h2>
                                        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Define custom factors for specialized equipment.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'custom_factors' })}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}
                                    >
                                        <Upload size={16} /> Bulk Import (CSV)
                                    </button>
                                </div>
                                {/* Create/Edit Form */}
                                <div className="grid-forms">
                                    <div className="input-group">
                                        <label>Factor Name</label>
                                        <input
                                            type="text"
                                            name="factor_name"
                                            value={factorForm.factor_name}
                                            onChange={handleFactorChange}
                                            className="mole-input"
                                            placeholder="e.g. Flare High Efficiency"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Parent Fuel (Internal Reference)</label>
                                        <select
                                            name="parent_fuel"
                                            value={factorForm.parent_fuel}
                                            onChange={(e) => setFactorForm({ ...factorForm, parent_fuel: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">Searchable Reference...</option>
                                            <option value="Natural Gas">Natural Gas (Standard)</option>
                                            <option value="Diesel">Diesel (Generic)</option>
                                            <option value="Gasoline">Gasoline (Generic)</option>
                                            <option value="Propane">Propane (Generic)</option>
                                            <option value="Crude Oil">Crude Oil (Heavy)</option>
                                            <option value="Fuel Oil">Fuel Oil (No. 4/6)</option>
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Unit</label>
                                        <select
                                            name="unit"
                                            value={factorForm.unit}
                                            onChange={handleFactorChange}
                                            className="component-select"
                                        >
                                            <option value="scf">scf</option>
                                            <option value="m³">m³</option>
                                            <option value="gal">gal</option>
                                            <option value="bbl">bbl</option>
                                            <option value="kg">kg</option>
                                            <option value="tonne">tonne</option>
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>CO₂ Factor (kg/unit)</label>
                                        <input
                                            type="number"
                                            name="co2_factor"
                                            value={factorForm.co2_factor}
                                            onChange={handleFactorChange}
                                            className="mole-input"
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>CH₄ Factor (kg/unit)</label>
                                        <input
                                            type="number"
                                            name="ch4_factor"
                                            value={factorForm.ch4_factor}
                                            onChange={handleFactorChange}
                                            className="mole-input"
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>N₂O Factor (kg/unit)</label>
                                        <input
                                            type="number"
                                            name="n2o_factor"
                                            value={factorForm.n2o_factor}
                                            onChange={handleFactorChange}
                                            className="mole-input"
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>CO₂ Uncertainty (±%)</label>
                                        <input type="number" name="co2_uncertainty" value={factorForm.co2_uncertainty} onChange={handleFactorChange} className="mole-input" placeholder="e.g. 5.0" step="0.1" />
                                    </div>
                                    <div className="input-group">
                                        <label>CH₄ Uncertainty (±%)</label>
                                        <input type="number" name="ch4_uncertainty" value={factorForm.ch4_uncertainty} onChange={handleFactorChange} className="mole-input" placeholder="e.g. 50.0" step="0.1" />
                                    </div>
                                    <div className="input-group">
                                        <label>N₂O Uncertainty (±%)</label>
                                        <input type="number" name="n2o_uncertainty" value={factorForm.n2o_uncertainty} onChange={handleFactorChange} className="mole-input" placeholder="e.g. 150.0" step="0.1" />
                                    </div>
                                </div>

                                {/* EF Uncertainty Workbench */}
                                <div style={{ marginTop: '20px', padding: '20px', background: 'rgba(30, 41, 59, 0.03)', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.05)' }}>
                                    <h4 style={{ margin: '0 0 15px 0', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <Database size={16} /> EF Uncertainty Workbench (ISO 14064-1 compliant)
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>Meter Precision (±%)</label>
                                            <input type="number" step="0.1" value={workbench.meter_precision} onChange={(e) => setWorkbench({ ...workbench, meter_precision: parseFloat(e.target.value) || 0 })} className="mole-input" style={{ padding: '8px' }} />
                                        </div>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>Lab Analysis (±%)</label>
                                            <input type="number" step="0.1" value={workbench.lab_precision} onChange={(e) => setWorkbench({ ...workbench, lab_precision: parseFloat(e.target.value) || 0 })} className="mole-input" style={{ padding: '8px' }} />
                                        </div>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>GWP Standard Selection</label>
                                            <select
                                                className="component-select"
                                                style={{ padding: '8px', fontSize: '0.85rem' }}
                                                value={workbench.gwp_uncertainty}
                                                onChange={(e) => setWorkbench({ ...workbench, gwp_uncertainty: parseFloat(e.target.value) || 0 })}
                                            >
                                                <option value="20.0">IPCC AR4 (±20.0%)</option>
                                                <option value="15.0">IPCC AR5 (±15.0%)</option>
                                                <option value="11.0">IPCC AR6 (±11.0%)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <button
                                        className="btn-ghost"
                                        style={{ marginTop: '15px', color: '#3b82f6', fontWeight: 600, fontSize: '0.85rem' }}
                                        onClick={() => {
                                            const co2_u = Math.sqrt(
                                                Math.pow(workbench.meter_precision, 2) +
                                                Math.pow(workbench.lab_precision, 2)
                                            );
                                            // IPCC typically suggests ±50% for CH4 and ±150% for N2O technology uncertainty
                                            const ch4_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(50.0, 2));
                                            const n2o_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(150.0, 2));
                                            
                                            setFactorForm({ 
                                                ...factorForm, 
                                                co2_uncertainty: co2_u.toFixed(2),
                                                ch4_uncertainty: ch4_u.toFixed(2),
                                                n2o_uncertainty: n2o_u.toFixed(2)
                                            });
                                        }}
                                    >
                                        Calculate Combined Uncertainty (SRSS)
                                    </button>
                                </div>

                                <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveFactor}>
                                        {editingFactorId ? 'Update Factor' : 'Save Factor'}
                                    </button>
                                    {editingFactorId && (
                                        <button
                                            className="action-btn"
                                            onClick={() => {
                                                setEditingFactorId(null);
                                                setFactorForm({
                                                    factor_name: '', parent_fuel: '', unit: 'scf',
                                                    co2_factor: '', ch4_factor: '', n2o_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>
                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                        <h3 style={{ margin: 0 }}>Custom Factors</h3>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Factor Name</th>
                                                <th>Unit</th>
                                                <th>CO2</th>
                                                <th>CH4</th>
                                                <th>N2O</th>
                                                <th>CO₂ Unc.</th>
                                                <th>CH₄ Unc.</th>
                                                <th>N₂O Unc.</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredFactors.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(f => (
                                                <tr key={f.id}>
                                                    <td>{f.factor_name}</td>
                                                    <td>{f.unit}</td>
                                                    <td>{f.co2_factor}</td>
                                                    <td>{f.ch4_factor}</td>
                                                    <td>{f.n2o_factor}</td>
                                                    <td style={{ color: f.co2_uncertainty ? '#10b981' : 'inherit' }}>{f.co2_uncertainty ? `±${f.co2_uncertainty}%` : '—'}</td>
                                                    <td style={{ color: f.ch4_uncertainty ? '#3b82f6' : 'inherit' }}>{f.ch4_uncertainty ? `±${f.ch4_uncertainty}%` : '—'}</td>
                                                    <td style={{ color: f.n2o_uncertainty ? '#8b5cf6' : 'inherit' }}>{f.n2o_uncertainty ? `±${f.n2o_uncertainty}%` : '—'}</td>
                                                    <td>
                                                        <button onClick={() => handleEditFactor(f)}>Edit</button>
                                                        <button onClick={() => handleDeleteFactor(f.id)}>Delete</button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredFactors.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {/* Regions Tab — Admin only */}
                        {activeTab === 'facilities' && user?.role === 'admin' && (
                            <div className="manage-card">
                                <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Active Regions</h2>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Manage operational regions and their boundaries.</p>


                                {/* Add Region form — Admin only */}
                                {user?.role === 'admin' && (
                                    <>
                                        <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                            <div className="input-group">
                                                <label>Region Name</label>
                                                <input type="text" name="name" value={facilityForm.name} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. Hassi R'Mel" />
                                            </div>
                                            <div className="input-group">
                                                <label>Activity</label>
                                                <select name="activity" value={facilityForm.activity} onChange={(e) => setFacilityForm({ ...facilityForm, activity: e.target.value, division: '' })} className="component-select">
                                                    <option value="">Select Activity</option>
                                                    {Object.keys(HIERARCHY).map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a]}</option>)}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Division</label>
                                                <select name="division" value={facilityForm.division} onChange={handleFacilityChange} className="component-select" disabled={!facilityForm.activity}>
                                                    <option value="">Select Division</option>
                                                    {facilityForm.activity && HIERARCHY[facilityForm.activity] && HIERARCHY[facilityForm.activity].map(d => <option key={d} value={d}>{d}</option>)}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Field / Block</label>
                                                <input type="text" name="field" value={facilityForm.field} onChange={handleFacilityChange} className="mole-input" placeholder="Optional" />
                                            </div>
                                            <div className="input-group">
                                                <label>Location (Wilaya)</label>
                                                <input type="text" name="location" value={facilityForm.location} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. Laghouat" />
                                            </div>
                                            <div className="input-group">
                                                <label>Consolidation Approach</label>
                                                <select
                                                    name="boundary_type"
                                                    value={facilityForm.boundary_type}
                                                    onChange={(e) => setFacilityForm({ ...facilityForm, boundary_type: e.target.value, boundary_detail: '' })}
                                                    className="component-select"
                                                >
                                                    <option value="">Select Approach</option>
                                                    {Object.keys(BOUNDARY_OPTIONS).map(opt => (
                                                        <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Boundary Details</label>
                                                <select
                                                    name="boundary_detail"
                                                    value={facilityForm.boundary_detail}
                                                    onChange={(e) => setFacilityForm({ ...facilityForm, boundary_detail: e.target.value })}
                                                    className="component-select"
                                                    disabled={!facilityForm.boundary_type}
                                                >
                                                    <option value="">Select Details</option>
                                                    {facilityForm.boundary_type && BOUNDARY_OPTIONS[facilityForm.boundary_type]?.map(detail => (
                                                        <option key={detail} value={detail}>{detail}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Segment</label>
                                                <input type="text" name="segment" value={facilityForm.segment} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. Upstream" />
                                            </div>
                                            <div className="input-group">
                                                <label>Latitude</label>
                                                <input type="number" step="any" name="latitude" value={facilityForm.latitude} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. 33.8" />
                                            </div>
                                            <div className="input-group">
                                                <label>Longitude</label>
                                                <input type="number" step="any" name="longitude" value={facilityForm.longitude} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. 6.07" />
                                            </div>
                                        </div>

                                        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                            <button className="action-btn" onClick={handleAddFacility}>Add Region</button>
                                            <button className="action-btn" onClick={() => exportToCSV(facilities, 'regions_export.csv')} style={{ background: 'var(--text-secondary)' }}>Export CSV</button>
                                            <label className="action-btn" style={{ background: 'var(--text-secondary)', cursor: 'pointer' }}>
                                                Import CSV
                                                <input type="file" style={{ display: 'none' }} onChange={(e) => handleImportCSV(e.target.files[0], 'Regions')} />
                                            </label>
                                        </div>
                                    </>
                                )}

                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <h3>Active Regions</h3>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Region Name</th>
                                                <th>Activity</th>
                                                <th>Division</th>
                                                <th>Location</th>
                                                <th>Boundary</th>
                                                <th>Segment</th>
                                                <th>Coordinates</th>
                                                {user?.role === 'admin' && <th style={{ textAlign: 'center' }}>Actions</th>}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredFacilities.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(f => (
                                                <tr key={f.id}>
                                                    <td><strong>{f.name}</strong></td>
                                                    <td>{ACTIVITY_LABELS[f.activity] || f.activity}</td>
                                                    <td>{f.division}</td>
                                                    <td>{f.location || '-'}</td>
                                                    <td>{f.boundary_notes || '-'}</td>
                                                    <td>{f.segment || '-'}</td>
                                                    <td style={{ fontSize: '0.8rem' }}>{f.latitude ? `${f.latitude}, ${f.longitude}` : 'Not Set'}</td>
                                                    {user?.role === 'admin' && (
                                                        <td style={{ textAlign: 'center' }}>
                                                            <button
                                                                className="btn-delete"
                                                                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                                                onClick={async () => {
                                                                    if (confirm('Delete this region?')) {
                                                                        try {
                                                                            await api.delete(`/facilities/${f.id}`);
                                                                            toast.success('Region deleted!');
                                                                            fetchFacilities();
                                                                        } catch (err) {
                                                                            toast.error('Failed to delete region');
                                                                        }
                                                                    }
                                                                }}
                                                            >
                                                                Delete
                                                            </button>
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                            {(filteredFacilities.length === 0) && (
                                                    <tr>
                                                        <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                            No regions found.
                                                        </td>
                                                    </tr>
                                                )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredFacilities.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {/* Production Tab */}
                        {activeTab === 'production' && (
                            <div className="manage-card">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                                    <div>
                                        <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Annual Production Records</h2>
                                        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Manage annual production data for emission intensity reporting.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'production' })}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}
                                    >
                                        <Upload size={16} /> Bulk Import (CSV)
                                    </button>
                                </div>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Activity
                                            {user?.role !== 'admin' && getAvailableActivities().length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={prodForm.activity}
                                            onChange={(e) => setProdForm({ ...prodForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={user?.role !== 'admin' && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Division
                                            {user?.role !== 'admin' && getAvailableDivisions(prodForm.activity).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={prodForm.division}
                                            onChange={(e) => setProdForm({ ...prodForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!prodForm.activity || (user?.role !== 'admin' && getAvailableDivisions(prodForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(prodForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Region
                                            {user?.role !== 'admin' && facilities.filter(f => f.activity === prodForm.activity && f.division === prodForm.division).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === prodForm.activity && f.division === prodForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={prodForm.facility_id}
                                            onChange={(val) => setProdForm({ ...prodForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!prodForm.division || (user?.role !== 'admin' && facilities.filter(f => f.activity === prodForm.activity && f.division === prodForm.division).length === 1)}
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Month</label>
                                        <select
                                            value={prodForm.month}
                                            onChange={(e) => setProdForm({ ...prodForm, month: parseInt(e.target.value) })}
                                            className="component-select"
                                        >
                                            {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                                <option key={m} value={m}>{new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Year</label>
                                        <input type="number" value={prodForm.year} onChange={(e) => setProdForm({ ...prodForm, year: e.target.value })} className="mole-input" />
                                    </div>
                                    <div className="input-group">
                                        <label>Oil ({prodForm.oil_unit}) <button onClick={openOilConverter} style={{ fontSize: '0.65rem', padding: '2px 4px', marginLeft: '8px', cursor: 'pointer', background: 'var(--accent-color)', color: 'white', border: 'none', borderRadius: '3px' }}>Convert m³</button></label>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <input type="number" value={prodForm.oil_amount} onChange={(e) => setProdForm({ ...prodForm, oil_amount: e.target.value })} className="mole-input" placeholder="0.0" style={{ flex: 1 }} />
                                            <select value={prodForm.oil_unit} onChange={(e) => setProdForm({ ...prodForm, oil_unit: e.target.value })} className="component-select" style={{ width: '80px' }}>
                                                <option value="bbl">bbl</option>
                                                <option value="m³">m³</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="input-group">
                                        <label>Gas ({prodForm.gas_unit}) <button onClick={openGasConverter} style={{ fontSize: '0.65rem', padding: '2px 4px', marginLeft: '8px', cursor: 'pointer', background: 'var(--accent-color)', color: 'white', border: 'none', borderRadius: '3px' }}>Convert m³</button></label>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <input type="number" value={prodForm.gas_amount} onChange={(e) => setProdForm({ ...prodForm, gas_amount: e.target.value })} className="mole-input" placeholder="0.0" style={{ flex: 1 }} />
                                            <select value={prodForm.gas_unit} onChange={(e) => setProdForm({ ...prodForm, gas_unit: e.target.value })} className="component-select" style={{ width: '80px' }}>
                                                <option value="mscf">mscf</option>
                                                <option value="m³">m³</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveProduction}>Save Record</button>
                                    <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'activity' })} style={{ background: '#10b981' }}>
                                        <Upload size={16} /> Import Activity CSV
                                    </button>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
                                    <button className="action-btn" onClick={() => exportToCSV(productionData, 'production_data.csv')} style={{ background: 'var(--text-secondary)' }}>Export CSV</button>
                                </div>


                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Activity</th>
                                                <th>Division</th>
                                                <th>Region</th>
                                                <th>Year</th>
                                                <th>Month</th>
                                                <th style={{ textAlign: 'right' }}>Oil (bbl)</th>
                                                <th style={{ textAlign: 'right' }}>Gas (mcf)</th>
                                                <th style={{ textAlign: 'center' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredProduction.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(d => (
                                                <tr key={d.id}>
                                                    <td>{ACTIVITY_LABELS[d.activity] || d.activity || '-'}</td>
                                                    <td>{d.division || '-'}</td>
                                                    <td>
                                                        {(() => {
                                                            const fac = facilities.find(f => f.id === d.facilityId);
                                                            if (!fac) return d.facilityId;
                                                            return <>{fac.name}{fac.field && <span style={{ fontSize: '0.85em', color: '#9ca3af', fontWeight: 400 }}>-{fac.field}</span>}</>;
                                                        })()}
                                                    </td>
                                                    <td>{d.year}</td>
                                                    <td>{new Date(2000, d.month - 1).toLocaleString('default', { month: 'short' })}</td>
                                                    <td style={{ textAlign: 'right' }}>{(d.oil || 0).toLocaleString()} {d.oilUnit || 'bbl'}</td>
                                                    <td style={{ textAlign: 'right' }}>{(d.gas || 0).toLocaleString()} {d.gasUnit || 'mscf'}</td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <button
                                                            className="btn-delete"
                                                            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                                            onClick={async () => {
                                                                if (confirm('Delete this production record?')) {
                                                                    try {
                                                                        await api.delete(`/data/production/${d.id}`);
                                                                        toast.success('Production record deleted!');
                                                                        fetchProduction();
                                                                    } catch (err) {
                                                                        toast.error('Failed to delete production record');
                                                                    }
                                                                }
                                                            }}
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredProduction.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {/* Sources Tab */}
                        {activeTab === 'sources' && (
                            <div className="manage-card">
                                <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Emission Sources Inventory</h2>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Manage operational equipment and emission sources.</p>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Activity
                                            {user?.role !== 'admin' && getAvailableActivities().length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={sourceForm.activity}
                                            onChange={(e) => setSourceForm({ ...sourceForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={user?.role !== 'admin' && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Division
                                            {user?.role !== 'admin' && getAvailableDivisions(sourceForm.activity).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={sourceForm.division}
                                            onChange={(e) => setSourceForm({ ...sourceForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!sourceForm.activity || (user?.role !== 'admin' && getAvailableDivisions(sourceForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(sourceForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Region
                                            {user?.role !== 'admin' && facilities.filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={sourceForm.facility_id}
                                            onChange={(val) => setSourceForm({ ...sourceForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!sourceForm.division || (user?.role !== 'admin' && facilities.filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1)}
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Source Name</label>
                                        <input type="text" value={sourceForm.name} onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })} className="mole-input" placeholder="e.g. Flare A" />
                                    </div>
                                    <div className="input-group">
                                        <label>Type</label>
                                        <select value={sourceForm.type} onChange={(e) => setSourceForm({ ...sourceForm, type: e.target.value })} className="component-select">
                                            <option value="">Select Type</option>
                                            {Object.entries(PROCESS_TYPES).map(([val, label]) => (
                                                <option key={val} value={val}>{label}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Equipment ID (Optional)</label>
                                        <input type="text" value={sourceForm.equipment_id} onChange={(e) => setSourceForm({ ...sourceForm, equipment_id: e.target.value })} className="mole-input" placeholder="e.g. COMP-001" />
                                    </div>
                                    <div className="input-group">
                                        <label>Fuel</label>
                                        <input type="text" value={sourceForm.fuel_type} onChange={(e) => setSourceForm({ ...sourceForm, fuel_type: e.target.value })} className="mole-input" />
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveSource}>Add Source</button>
                                    <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'sources' })} style={{ background: '#10b981' }}>
                                        <Upload size={16} /> Import Sources CSV
                                    </button>
                                    <button className="action-btn" onClick={() => exportToCSV(sources, 'emission_sources.csv')} style={{ background: 'var(--text-secondary)' }}>Export CSV</button>
                                </div>


                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Equipment ID</th>
                                                <th>Type</th>
                                                <th>Region</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredSources.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(s => (
                                                <tr key={s.id}>
                                                    <td><strong>{s.name}</strong></td>
                                                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.equipment_id || '-'}</td>
                                                    <td>{PROCESS_TYPES[s.type] || s.type}</td>
                                                    <td>
                                                        {(() => {
                                                            const fac = facilities.find(f => f.id === s.facility_id);
                                                            if (!fac) return s.facility_id;
                                                            return <>{fac.name}{fac.field && <span style={{ fontSize: '0.85em', color: '#9ca3af', fontWeight: 400 }}>-{fac.field}</span>}</>;
                                                        })()}
                                                    </td>
                                                    <td>{s.status}</td>
                                                    <td>
                                                        <button className="btn-delete" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={async () => {
                                                            if (confirm('Delete?')) { await api.delete(`/sources/${s.id}`); fetchSources(); }
                                                        }}>Delete</button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredSources.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {/* Mitigation Tab */}
                        {activeTab === 'mitigation' && (
                            <div className="manage-card">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                                    <div>
                                        <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Mitigation Projects</h2>
                                        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Record CCUS, RECs, and Carbon Offsets.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'mitigation' })}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}
                                    >
                                        <Upload size={16} /> Bulk Import (CSV)
                                    </button>
                                </div>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Activity
                                            {user?.role !== 'admin' && getAvailableActivities().length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={mitigationForm.activity}
                                            onChange={(e) => setMitigationForm({ ...mitigationForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={user?.role !== 'admin' && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Division
                                            {user?.role !== 'admin' && getAvailableDivisions(mitigationForm.activity).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <select
                                            value={mitigationForm.division}
                                            onChange={(e) => setMitigationForm({ ...mitigationForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!mitigationForm.activity || (user?.role !== 'admin' && getAvailableDivisions(mitigationForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(mitigationForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Region
                                            {user?.role !== 'admin' && facilities.filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={mitigationForm.facility_id}
                                            onChange={(val) => setMitigationForm({ ...mitigationForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!mitigationForm.division || (user?.role !== 'admin' && facilities.filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1)}
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Project Name</label>
                                        <input type="text" value={mitigationForm.name} onChange={(e) => setMitigationForm({ ...mitigationForm, name: e.target.value })} className="mole-input" placeholder="e.g. Flare Reduction Unit 1" />
                                    </div>

                                    <div className="input-group">
                                        <label>Year</label>
                                        <input type="number" value={mitigationForm.year} onChange={(e) => setMitigationForm({ ...mitigationForm, year: e.target.value })} className="mole-input" />
                                    </div>
                                    <div className="input-group">
                                        <label>Type</label>
                                        <select value={mitigationForm.type} onChange={(e) => setMitigationForm({ ...mitigationForm, type: e.target.value })} className="component-select">
                                            <option value="CCUS">CCUS (Carbon Capture)</option>
                                            <option value="REC">REC (Renewable Energy Credit)</option>
                                            <option value="Offset">Carbon Offset</option>
                                            <option value="Efficiency">Energy Efficiency</option>
                                            <option value="Process">Process Improvement</option>
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Quantity (tCO₂e)</label>
                                        <input type="number" value={mitigationForm.quantity_tco2e} onChange={(e) => setMitigationForm({ ...mitigationForm, quantity_tco2e: e.target.value })} className="mole-input" placeholder="0.0" />
                                    </div>
                                    <div className="input-group">
                                        <label>Status</label>
                                        <select value={mitigationForm.status} onChange={(e) => setMitigationForm({ ...mitigationForm, status: e.target.value })} className="component-select">
                                            <option value="Active">Active</option>
                                            <option value="Planned">Planned</option>
                                            <option value="Completed">Completed</option>
                                        </select>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveMitigation}>Save Record</button>
                                    <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'mitigation' })} style={{ background: '#10b981' }}>
                                        <Upload size={16} /> Import Mitigation CSV
                                    </button>
                                </div>

                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <h3>Mitigation Records</h3>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Project Name</th>
                                                <th>Activity</th>
                                                <th>Region</th>
                                                <th>Year</th>
                                                <th>Type</th>
                                                <th>Status</th>
                                                <th style={{ textAlign: 'right' }}>Quantity (tCO₂e)</th>
                                                <th style={{ textAlign: 'center' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredMitigations.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(m => (
                                                <tr key={m.id}>
                                                    <td><strong>{m.name || m.mitigation_type}</strong></td>
                                                    <td>{ACTIVITY_LABELS[m.activity] || m.activity || '-'}</td>
                                                    <td>
                                                        {m.region || '-'}
                                                        {m.division && m.division !== '-' ? <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{m.division}</div> : null}
                                                    </td>
                                                    <td>{m.year}</td>
                                                    <td>{m.mitigation_type || m.type}</td>
                                                    <td>
                                                        <span className={`status-badge ${m.status?.toLowerCase() || 'active'}`}>
                                                            {m.status || 'Active'}
                                                        </span>
                                                    </td>
                                                    <td style={{ textAlign: 'right', color: '#10b981', fontWeight: 600 }}>
                                                        -{parseFloat(m.quantity_tco2e).toLocaleString()}
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <button
                                                            className="btn-delete"
                                                            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                                            onClick={async () => {
                                                                if (confirm('Delete?')) {
                                                                    await api.delete(`/mitigation/${m.id}`);
                                                                    fetchMitigations();
                                                                }
                                                            }}
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {mitigations.length === 0 && (
                                                <tr>
                                                    <td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                        No mitigation projects recorded yet.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredMitigations.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {activeTab === 'cbam' && (
                            <div className="tab-pane active">
                                <div className="section-header" style={{ marginBottom: '24px' }}>
                                    <h2>EU CBAM Export & Embedded Emission Tracking</h2>
                                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                                        Record product exports subject to EU Carbon Border Adjustment Mechanism (CBAM) with direct and indirect embedded emissions under EU Regulation (EU) 2023/956.
                                    </p>
                                </div>

                                <div className="form-grid-3">
                                    <div className="input-group">
                                        <label>Activity</label>
                                        <select
                                            value={cbamForm.activity}
                                            onChange={(e) => {
                                                const act = e.target.value;
                                                const divs = getAvailableDivisions(act);
                                                const autoDiv = divs.length === 1 ? divs[0] : '';
                                                const facs = facilities.filter(f => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setCbamForm({ ...cbamForm, activity: act, division: autoDiv, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Activity --</option>
                                            {getAvailableActivities().map(a => (
                                                <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Division</label>
                                        <select
                                            value={cbamForm.division}
                                            onChange={(e) => {
                                                const div = e.target.value;
                                                const facs = facilities.filter(f => (!cbamForm.activity || f.activity === cbamForm.activity) && (!div || f.division === div));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setCbamForm({ ...cbamForm, division: div, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                            disabled={!cbamForm.activity}
                                        >
                                            <option value="">-- Select Division --</option>
                                            {getAvailableDivisions(cbamForm.activity).map(d => (
                                                <option key={d} value={d}>{d}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Facility / Region *</label>
                                        <select
                                            value={cbamForm.facility_id}
                                            onChange={(e) => setCbamForm({ ...cbamForm, facility_id: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Facility --</option>
                                            {facilities
                                                .filter(f => (!cbamForm.activity || f.activity === cbamForm.activity) && (!cbamForm.division || f.division === cbamForm.division))
                                                .map(f => (
                                                    <option key={f.id} value={f.id}>{f.name} ({f.location || f.field || 'General'})</option>
                                                ))
                                            }
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Product Name *</label>
                                        <input
                                            type="text"
                                            value={cbamForm.product_name}
                                            onChange={(e) => setCbamForm({ ...cbamForm, product_name: e.target.value })}
                                            className="mole-input"
                                            placeholder="e.g. Export Blend Crude Oil"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>EU CN Code *</label>
                                        <select
                                            value={cbamForm.cn_code}
                                            onChange={(e) => setCbamForm({ ...cbamForm, cn_code: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="2709 00">2709 00 - Crude Petroleum Oil</option>
                                            <option value="2711 11">2711 11 - Natural Gas (Liquefied / LNG)</option>
                                            <option value="2711 21">2711 21 - Natural Gas (Gaseous / Pipeline)</option>
                                            <option value="2710 12">2710 12 - Light Oils & Preparations</option>
                                            <option value="2710 19">2710 19 - Heavy Oils / Diesel / Gas Oil</option>
                                            <option value="2814 10">2814 10 - Anhydrous Ammonia</option>
                                            <option value="2901 21">2901 21 - Ethylene / Petrochemicals</option>
                                            <option value="3102 10">3102 10 - Urea & Nitrogenous Fertilizers</option>
                                            <option value="Custom">Custom / Other CN Code</option>
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Export Destination</label>
                                        <select
                                            value={cbamForm.export_destination}
                                            onChange={(e) => setCbamForm({ ...cbamForm, export_destination: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="EU">European Union (EU-27)</option>
                                            <option value="UK">United Kingdom</option>
                                            <option value="US">United States</option>
                                            <option value="APAC">Asia-Pacific</option>
                                            <option value="Non-EU">Other Non-EU</option>
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Reporting Year</label>
                                        <input
                                            type="number"
                                            value={cbamForm.year}
                                            onChange={(e) => setCbamForm({ ...cbamForm, year: e.target.value })}
                                            className="mole-input"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Reporting Month</label>
                                        <select
                                            value={cbamForm.month}
                                            onChange={(e) => setCbamForm({ ...cbamForm, month: e.target.value })}
                                            className="component-select"
                                        >
                                            {Array.from({ length: 12 }, (_, i) => (
                                                <option key={i + 1} value={i + 1}>
                                                    {new Date(2000, i).toLocaleString('default', { month: 'long' })}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Export Quantity (Metric Tonnes) *</label>
                                        <input
                                            type="number"
                                            value={cbamForm.quantity_tonnes}
                                            onChange={(e) => setCbamForm({ ...cbamForm, quantity_tonnes: e.target.value })}
                                            className="mole-input"
                                            placeholder="0.00"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Direct Specific Embedded (tCO₂e / t)</label>
                                        <input
                                            type="number"
                                            step="0.001"
                                            value={cbamForm.specific_embedded_direct}
                                            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_direct: e.target.value })}
                                            className="mole-input"
                                            placeholder="0.000"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Indirect Specific Embedded (tCO₂e / t)</label>
                                        <input
                                            type="number"
                                            step="0.001"
                                            value={cbamForm.specific_embedded_indirect}
                                            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_indirect: e.target.value })}
                                            className="mole-input"
                                            placeholder="0.000"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Notes & Verification References</label>
                                        <input
                                            type="text"
                                            value={cbamForm.notes}
                                            onChange={(e) => setCbamForm({ ...cbamForm, notes: e.target.value })}
                                            className="mole-input"
                                            placeholder="Accredited Verifier / Certificate ID"
                                        />
                                    </div>
                                </div>

                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveCbamExport}>
                                        {editingCbamId ? 'Update CBAM Record' : 'Save CBAM Record'}
                                    </button>
                                    {editingCbamId && (
                                        <button
                                            className="action-btn"
                                            style={{ background: 'var(--text-secondary)' }}
                                            onClick={() => {
                                                setEditingCbamId(null);
                                                setCbamForm({
                                                    id: null, activity: '', division: '', facility_id: '',
                                                    year: new Date().getFullYear(), month: 1,
                                                    product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
                                                    quantity_tonnes: '', export_destination: 'EU',
                                                    specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>

                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                        <h3>CBAM Product Export Records</h3>
                                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                            Total Records: {filteredCbam.length}
                                        </span>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Facility</th>
                                                <th>Product</th>
                                                <th>EU CN Code</th>
                                                <th>Period</th>
                                                <th>Destination</th>
                                                <th style={{ textAlign: 'right' }}>Quantity (t)</th>
                                                <th style={{ textAlign: 'right' }}>Direct (tCO₂e/t)</th>
                                                <th style={{ textAlign: 'right' }}>Indirect (tCO₂e/t)</th>
                                                <th style={{ textAlign: 'right' }}>Total Embedded (tCO₂e)</th>
                                                <th style={{ textAlign: 'center' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredCbam.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(c => {
                                                const fid = c.facility_id || c.facilityId;
                                                const fac = facilities.find(f => f.id === fid);
                                                const fName = c.facility_name || c.facilityName || fac?.name || `Facility #${fid}`;
                                                const pName = c.product_name || c.productName || 'Product';
                                                const cn = c.cn_code || c.cnCode || '-';
                                                const dest = c.export_destination || c.exportDestination || 'EU';
                                                const qTonnes = parseFloat(c.quantity_tonnes ?? c.quantityTonnes ?? 0);
                                                const direct = parseFloat(c.specific_embedded_direct ?? c.specificEmbeddedDirect ?? 0);
                                                const indirect = parseFloat(c.specific_embedded_indirect ?? c.specificEmbeddedIndirect ?? 0);
                                                const totalEmbedded = (direct + indirect) * qTonnes;
                                                return (
                                                    <tr key={c.id}>
                                                        <td><strong>{fName}</strong></td>
                                                        <td>{pName}</td>
                                                        <td><span style={{ fontFamily: 'monospace', background: 'var(--bg-card)', padding: '2px 6px', borderRadius: '4px' }}>{cn}</span></td>
                                                        <td>{c.year} - M{c.month || '1'}</td>
                                                        <td><span className="status-badge active">{dest}</span></td>
                                                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{qTonnes.toLocaleString()}</td>
                                                        <td style={{ textAlign: 'right' }}>{direct.toFixed(3)}</td>
                                                        <td style={{ textAlign: 'right' }}>{indirect.toFixed(3)}</td>
                                                        <td style={{ textAlign: 'right', color: '#3b82f6', fontWeight: 700 }}>
                                                            {totalEmbedded.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                                                        </td>
                                                        <td style={{ textAlign: 'center' }}>
                                                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                                                <button
                                                                    className="action-btn"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem', background: '#3b82f6' }}
                                                                    onClick={() => {
                                                                        setEditingCbamId(c.id);
                                                                        setCbamForm({
                                                                            id: c.id,
                                                                            activity: fac?.activity || '',
                                                                            division: fac?.division || '',
                                                                            facility_id: fid ? fid.toString() : '',
                                                                            year: c.year,
                                                                            month: c.month || 1,
                                                                            product_name: pName,
                                                                            cn_code: cn,
                                                                            quantity_tonnes: qTonnes.toString(),
                                                                            export_destination: dest,
                                                                            specific_embedded_direct: direct ? direct.toString() : '',
                                                                            specific_embedded_indirect: indirect ? indirect.toString() : '',
                                                                            notes: c.notes || ''
                                                                        });
                                                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                                                    }}
                                                                >
                                                                    Edit
                                                                </button>
                                                                <button
                                                                    className="btn-delete"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                                                    onClick={() => handleDeleteCbamExport(c.id)}
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                            {filteredCbam.length === 0 && (
                                                <tr>
                                                    <td colSpan="10" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                        No CBAM product export records found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredCbam.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}

                        {activeTab === 'ogmp' && (
                            <div className="tab-pane active">
                                <div className="section-header" style={{ marginBottom: '24px' }}>
                                    <h2>OGMP 2.0 Level 4 & 5 Top-Down / Bottom-Up Surveys</h2>
                                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                                        Log site-level top-down measurements (satellite, aerial LiDAR, drone, ground OGI) to reconcile against inventory estimates under Oil and Gas Methane Partnership (OGMP 2.0) Level 4/5 standards.
                                    </p>
                                </div>

                                <div className="form-grid-3">
                                    <div className="input-group">
                                        <label>Activity</label>
                                        <select
                                            value={ogmpForm.activity}
                                            onChange={(e) => {
                                                const act = e.target.value;
                                                const divs = getAvailableDivisions(act);
                                                const autoDiv = divs.length === 1 ? divs[0] : '';
                                                const facs = facilities.filter(f => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setOgmpForm({ ...ogmpForm, activity: act, division: autoDiv, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Activity --</option>
                                            {getAvailableActivities().map(a => (
                                                <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Division</label>
                                        <select
                                            value={ogmpForm.division}
                                            onChange={(e) => {
                                                const div = e.target.value;
                                                const facs = facilities.filter(f => (!ogmpForm.activity || f.activity === ogmpForm.activity) && (!div || f.division === div));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setOgmpForm({ ...ogmpForm, division: div, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                            disabled={!ogmpForm.activity}
                                        >
                                            <option value="">-- Select Division --</option>
                                            {getAvailableDivisions(ogmpForm.activity).map(d => (
                                                <option key={d} value={d}>{d}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Facility / Region *</label>
                                        <select
                                            value={ogmpForm.facility_id}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, facility_id: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Facility --</option>
                                            {facilities
                                                .filter(f => (!ogmpForm.activity || f.activity === ogmpForm.activity) && (!ogmpForm.division || f.division === ogmpForm.division))
                                                .map(f => (
                                                    <option key={f.id} value={f.id}>{f.name} ({f.location || f.field || 'General'})</option>
                                                ))
                                            }
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Survey Date *</label>
                                        <input
                                            type="date"
                                            value={ogmpForm.survey_date}
                                            onChange={(e) => {
                                                const dateVal = e.target.value;
                                                const yr = dateVal ? new Date(dateVal).getFullYear() : ogmpForm.year;
                                                setOgmpForm({ ...ogmpForm, survey_date: dateVal, year: yr });
                                            }}
                                            className="mole-input"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Measurement Technology (Level 4/5) *</label>
                                        <select
                                            value={ogmpForm.survey_type}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, survey_type: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="Satellite (Sentinel-5P/MethaneSAT)">Satellite (Sentinel-5P / MethaneSAT / GHGSat)</option>
                                            <option value="Aircraft OGI / Hyperspectral">Aircraft Hyperspectral / LiDAR Aerial</option>
                                            <option value="Drone / UAV LiDAR Scanning">Drone / UAV Tunable Diode Laser (TDLAS)</option>
                                            <option value="Ground Mobile / OGI FLIR Camera">Ground Mobile / Optical Gas Imaging (OGI FLIR)</option>
                                            <option value="Fixed Continuous Sensor Array">Fixed Continuous Point Sensor Array</option>
                                            <option value="Bottom-Up Source Component Measurement">Bottom-Up High-Flow Component Sampling</option>
                                        </select>
                                    </div>

                                    <div className="input-group">
                                        <label>Measured Emission Rate (kg CH₄ / hr) *</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={ogmpForm.measured_rate_kg_hr}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, measured_rate_kg_hr: e.target.value })}
                                            className="mole-input"
                                            placeholder="0.0"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Reconciliation Status</label>
                                        <select
                                            value={ogmpForm.reconciliation_status}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, reconciliation_status: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="Reconciled">Reconciled (Within Uncertainty Margin)</option>
                                            <option value="Discrepancy Detected">Discrepancy Detected (Bottom-Up Underestimated)</option>
                                            <option value="Investigation Pending">Investigation Pending / Root Cause Analysis</option>
                                            <option value="Under Review">Under Review by Operations</option>
                                        </select>
                                    </div>

                                    <div className="input-group" style={{ gridColumn: 'span 2' }}>
                                        <label>Operator Notes & Campaign Metadata</label>
                                        <input
                                            type="text"
                                            value={ogmpForm.operator_notes}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, operator_notes: e.target.value })}
                                            className="mole-input"
                                            placeholder="Wind speed, flight altitude, pass number, observation conditions"
                                        />
                                    </div>
                                </div>

                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveOgmpSurvey}>
                                        {editingOgmpId ? 'Update Survey Record' : 'Save OGMP Survey'}
                                    </button>
                                    {editingOgmpId && (
                                        <button
                                            className="action-btn"
                                            style={{ background: 'var(--text-secondary)' }}
                                            onClick={() => {
                                                setEditingOgmpId(null);
                                                setOgmpForm({
                                                    id: null, activity: '', division: '', facility_id: '',
                                                    year: new Date().getFullYear(),
                                                    survey_date: new Date().toISOString().split('T')[0],
                                                    survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
                                                    measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>

                                <div className="table-container" style={{ marginTop: '40px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                        <h3>OGMP 2.0 Survey Records</h3>
                                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                            Total Surveys: {filteredOgmp.length}
                                        </span>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Facility</th>
                                                <th>Survey Date</th>
                                                <th>Measurement Method</th>
                                                <th style={{ textAlign: 'right' }}>Measured Rate (kg CH₄/hr)</th>
                                                <th style={{ textAlign: 'right' }}>Annualized (tCH₄/yr)</th>
                                                <th>Reconciliation Status</th>
                                                <th>Campaign Notes</th>
                                                <th style={{ textAlign: 'center' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredOgmp.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(o => {
                                                const fid = o.facility_id || o.facilityId;
                                                const fac = facilities.find(f => f.id === fid);
                                                const fName = o.facility_name || o.facilityName || fac?.name || `Facility #${fid}`;
                                                const sDate = o.survey_date || o.surveyDate || '';
                                                const sType = o.survey_type || o.surveyType || 'Satellite';
                                                const mRate = parseFloat(o.measured_rate_kg_hr ?? o.measuredRateKgHr ?? 0);
                                                const annualizedTonne = o.estimated_annual_tch4 ?? o.estimatedAnnualTch4 ?? ((mRate * 8760) / 1000.0);
                                                const rStatus = o.reconciliation_status || o.reconciliationStatus || 'Reconciled';
                                                const isReconciled = rStatus === 'Reconciled';
                                                const notes = o.operator_notes || o.operatorNotes || '-';

                                                return (
                                                    <tr key={o.id}>
                                                        <td><strong>{fName}</strong></td>
                                                        <td>{sDate}</td>
                                                        <td>
                                                            <span style={{ fontWeight: 500 }}>{sType}</span>
                                                        </td>
                                                        <td style={{ textAlign: 'right', fontWeight: 600 }}>
                                                            {mRate.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
                                                        </td>
                                                        <td style={{ textAlign: 'right', color: '#10b981', fontWeight: 700 }}>
                                                            {parseFloat(annualizedTonne).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                                                        </td>
                                                        <td>
                                                            <span className={`status-badge ${isReconciled ? 'active' : 'planned'}`} style={{
                                                                background: isReconciled ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                                                                color: isReconciled ? '#10b981' : '#ef4444',
                                                                borderColor: isReconciled ? '#10b981' : '#ef4444'
                                                            }}>
                                                                {rStatus}
                                                            </span>
                                                        </td>
                                                        <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{notes}</td>
                                                        <td style={{ textAlign: 'center' }}>
                                                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                                                <button
                                                                    className="action-btn"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem', background: '#3b82f6' }}
                                                                    onClick={() => {
                                                                        setEditingOgmpId(o.id);
                                                                        setOgmpForm({
                                                                            id: o.id,
                                                                            activity: fac?.activity || '',
                                                                            division: fac?.division || '',
                                                                            facility_id: fid ? fid.toString() : '',
                                                                            year: o.year || (sDate ? new Date(sDate).getFullYear() : new Date().getFullYear()),
                                                                            survey_date: sDate,
                                                                            survey_type: sType,
                                                                            measured_rate_kg_hr: mRate.toString(),
                                                                            reconciliation_status: rStatus,
                                                                            operator_notes: notes === '-' ? '' : notes
                                                                        });
                                                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                                                    }}
                                                                >
                                                                    Edit
                                                                </button>
                                                                <button
                                                                    className="btn-delete"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                                                    onClick={() => handleDeleteOgmpSurvey(o.id)}
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                            {filteredOgmp.length === 0 && (
                                                <tr>
                                                    <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                        No OGMP survey records found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredOgmp.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
                        )}
                    </section>
                </div>
            </div>

            <BulkImportModal
                isOpen={importModal.isOpen}
                onClose={() => setImportModal({ ...importModal, isOpen: false })}
                type={importModal.type}
                onImportSuccess={() => {
                    if (importModal.type === 'sources') fetchSources();
                    if (importModal.type === 'custom_factors') fetchCustomFactors();
                    if (importModal.type === 'activity') {
                        fetchProduction();
                        toast.success('Activity data imported and emissions calculated!');
                    }
                    if (importModal.type === 'production') fetchProduction();
                    if (importModal.type === 'mitigation') fetchMitigations();
                }}
            />
        </div >
    );
};

// FE-03 FIX: Wrap inner component in ErrorBoundary
const ManageData = () => (
    <ErrorBoundary>
        <ManageDataInner />
    </ErrorBoundary>
);

export default ManageData;
