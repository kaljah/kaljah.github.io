import React, { useState, useEffect } from 'react';
import api from '../api';
import CustomDropdown from './CustomDropdown';
import { useToast } from './Toast';
import { formatNumber } from '../utils/formatters';
import ColumnMappingWizard from './ColumnMappingWizard';
import { Upload, Trash2 } from 'lucide-react';
import './ScopeTables.css';

const Scope3Form = () => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [year, setYear] = useState(new Date().getFullYear());
    const [month, setMonth] = useState(new Date().getMonth() + 1);
    const [facilityId, setFacilityId] = useState('');
    const [category, setCategory] = useState('11');
    const [activityType, setActivityType] = useState('');
    const [amount, setAmount] = useState('');
    const [unit, setUnit] = useState('');
    const [emissionFactor, setEmissionFactor] = useState('');
    const [baseUnit, setBaseUnit] = useState('');
    const [baseFactor, setBaseFactor] = useState(0);

    const UNIT_MULTIPLIERS = {
        'kg': { 'kg': 1, 'tonne': 1000, 'ton': 907.185, 'lb': 0.453592 },
        'bbl': { 'bbl': 1, 'gal': 1/42, 'm3': 6.2898, 'L': 0.0062898 },
        'gal': { 'gal': 1, 'bbl': 42, 'L': 0.264172, 'm3': 264.172 },
        'mcf': { 'mcf': 1, 'scf': 0.001, 'm3': 0.0353147 },
        'kWh': { 'kWh': 1, 'MWh': 1000 },
        'ton-km': { 'ton-km': 1, 'ton-mile': 1.45997 },
        'passenger-km': { 'passenger-km': 1, 'passenger-mile': 1.60934 },
        'km': { 'km': 1, 'mile': 1.60934 },
        'sq ft': { 'sq ft': 1, 'sq m': 10.7639 },
        'USD': { 'USD': 1, 'EUR': 1.1, 'DZD': 0.0074 },
        'day': { 'day': 1, 'week': 5, 'month': 20, 'year': 240 }
    };

    const [facilities, setFacilities] = useState([]);
    const [entries, setEntries] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [importModal, setImportModal] = useState({ isOpen: false, type: 'activity_scope3' });
    const RECORDS_PER_PAGE = 10;

    const SCOPE3_CATEGORIES = {
        '1': { name: 'Purchased Goods & Services', type: 'upstream' },
        '2': { name: 'Capital Goods', type: 'upstream' },
        '3': { name: 'Fuel & Energy-Related', type: 'upstream' },
        '4': { name: 'Upstream Transportation', type: 'upstream' },
        '5': { name: 'Waste Generated', type: 'upstream' },
        '6': { name: 'Business Travel', type: 'upstream' },
        '7': { name: 'Employee Commuting', type: 'upstream' },
        '8': { name: 'Upstream Leased Assets', type: 'upstream' },
        '9': { name: 'Downstream Transportation', type: 'downstream' },
        '10': { name: 'Processing of Sold Products', type: 'downstream' },
        '11': { name: 'Use of Sold Products', type: 'downstream' },
        '12': { name: 'End-of-Life Treatment', type: 'downstream' },
        '13': { name: 'Downstream Leased Assets', type: 'downstream' },
        '14': { name: 'Franchises', type: 'downstream' },
        '15': { name: 'Investments', type: 'downstream' }
    };

    const CATEGORY_ACTIVITIES = {
        '1': [
            { value: 'Steel', unit: 'kg', factor: 1.85 },
            { value: 'Cement', unit: 'kg', factor: 0.82 },
            { value: 'Chemicals', unit: 'kg', factor: 2.1 },
            { value: 'Equipment', unit: 'USD', factor: 0.42 },
            { value: 'Services', unit: 'USD', factor: 0.18 }
        ],
        '2': [
            { value: 'Machinery & Equipment', unit: 'USD', factor: 0.45 },
            { value: 'Buildings & Infrastructure', unit: 'USD', factor: 0.85 },
            { value: 'IT Equipment', unit: 'USD', factor: 0.35 }
        ],
        '3': [
            { value: 'Upstream of Purchased Fuels', unit: 'kg', factor: 0.25 },
            { value: 'T&D Losses (Electricity)', unit: 'kWh', factor: 0.05 }
        ],
        '4': [
            { value: 'Truck Transport', unit: 'ton-km', factor: 0.062 },
            { value: 'Rail Transport', unit: 'ton-km', factor: 0.022 },
            { value: 'Ship Transport', unit: 'ton-km', factor: 0.011 },
            { value: 'Pipeline Transport', unit: 'ton-km', factor: 0.005 }
        ],
        '5': [
            { value: 'Landfill', unit: 'kg', factor: 0.57 },
            { value: 'Incineration', unit: 'kg', factor: 0.021 },
            { value: 'Recycling', unit: 'kg', factor: 0.012 },
            { value: 'Composting', unit: 'kg', factor: 0.008 }
        ],
        '6': [
            { value: 'Air - Domestic', unit: 'passenger-km', factor: 0.255 },
            { value: 'Air - International', unit: 'passenger-km', factor: 0.195 },
            { value: 'Car - Gasoline', unit: 'km', factor: 0.192 },
            { value: 'Car - Diesel', unit: 'km', factor: 0.171 },
            { value: 'Train', unit: 'passenger-km', factor: 0.041 }
        ],
        '7': [
            { value: 'Car Commute (Gasoline)', unit: 'passenger-km', factor: 0.192 },
            { value: 'Public Transit (Bus/Train)', unit: 'passenger-km', factor: 0.05 },
            { value: 'Teleworking', unit: 'day', factor: 1.5 }
        ],
        '8': [
            { value: 'Leased Office Space', unit: 'sq ft', factor: 5.5 },
            { value: 'Leased Vehicles', unit: 'km', factor: 0.2 }
        ],
        '9': [
            { value: 'Truck Transport', unit: 'ton-km', factor: 0.062 },
            { value: 'Rail Transport', unit: 'ton-km', factor: 0.022 },
            { value: 'Ship Transport', unit: 'ton-km', factor: 0.011 },
            { value: 'Pipeline Transport', unit: 'ton-km', factor: 0.005 }
        ],
        '10': [
            { value: 'Processing (Electricity)', unit: 'kWh', factor: 0.4 },
            { value: 'Processing (Natural Gas)', unit: 'mcf', factor: 54.6 }
        ],
        '11': [
            { value: 'Crude Oil', unit: 'bbl', factor: 433.7 },
            { value: 'Natural Gas', unit: 'mcf', factor: 54.6 },
            { value: 'NGL - Ethane', unit: 'gal', factor: 3.93 },
            { value: 'NGL - Propane', unit: 'gal', factor: 5.74 },
            { value: 'NGL - Butane', unit: 'gal', factor: 6.38 },
            { value: 'NGL - Mixed', unit: 'gal', factor: 5.5 }
        ],
        '12': [
            { value: 'Landfill', unit: 'kg', factor: 0.57 },
            { value: 'Recycling', unit: 'kg', factor: 0.012 },
            { value: 'Incineration', unit: 'kg', factor: 0.021 }
        ],
        '13': [
            { value: 'Downstream Leased Space', unit: 'sq ft', factor: 5.5 }
        ],
        '14': [
            { value: 'Retail Franchise', unit: 'sq ft', factor: 10.0 }
        ],
        '15': [
            { value: 'Equity Investments', unit: 'USD', factor: 0.001 },
            { value: 'Project Finance', unit: 'USD', factor: 0.005 }
        ]
    };

    useEffect(() => {
        loadFacilities();
        loadEntries();
    }, []);

    useEffect(() => {
        loadEntries();
    }, [currentPage]);

    useEffect(() => {
        const activities = CATEGORY_ACTIVITIES[category];
        if (activities && activities.length > 0) {
            setActivityType(activities[0].value);
            setBaseUnit(activities[0].unit);
            setBaseFactor(activities[0].factor);
            setUnit(activities[0].unit);
            setEmissionFactor(activities[0].factor.toString());
        } else {
            setActivityType('');
            setUnit('');
            setEmissionFactor('');
        }
    }, [category]);

    useEffect(() => {
        const activities = CATEGORY_ACTIVITIES[category];
        if (activities) {
            const activity = activities.find(a => a.value === activityType);
            if (activity) {
                setBaseUnit(activity.unit);
                setBaseFactor(activity.factor);
                setUnit(activity.unit);
                setEmissionFactor(activity.factor.toString());
            }
        }
    }, [activityType, category]);

    const handleUnitChange = (newUnit) => {
        setUnit(newUnit);
        if (UNIT_MULTIPLIERS[baseUnit] && UNIT_MULTIPLIERS[baseUnit][newUnit]) {
            const multiplier = UNIT_MULTIPLIERS[baseUnit][newUnit];
            const newFactor = baseFactor * multiplier;
            // Round to 5 decimal places to avoid floating point weirdness
            setEmissionFactor(parseFloat(newFactor.toFixed(5)).toString());
        }
    };

    const loadFacilities = async () => {
        try {
            const res = await api.get('/facilities');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setFacilities(data);
        } catch (error) {
            console.error('Failed to load facilities:', error);
            toast.error('Failed to load regions');
        }
    };

    const loadEntries = async () => {
        setLoading(true);
        try {
            const res = await api.get('/scope3');
            const allEntries = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            const start = (currentPage - 1) * RECORDS_PER_PAGE;
            const end = start + RECORDS_PER_PAGE;
            setEntries(allEntries.slice(start, end));
            setTotalPages(Math.ceil(allEntries.length / RECORDS_PER_PAGE));
        } catch (error) {
            console.error('Failed to load entries:', error);
            toast.error('Failed to load Scope 3 data');
        } finally {
            setLoading(false);
        }
    };

    const handleAddEntry = async (status = 'Verified') => {
        if (!year || !month || !facilityId || !category || !activityType || !amount || !emissionFactor) {
            toast.warning('Please fill in all required fields');
            return;
        }

        try {
            const amt = parseFloat(amount);
            const ef = parseFloat(emissionFactor);
            const totalEmissions = (amt * ef) / 1000;

            const payload = {
                year: parseInt(year),
                month: parseInt(month),
                facility_id: parseInt(facilityId),
                category: parseInt(category), // or string
                sub_category: activityType,
                activity_data: amt,
                unit: unit,
                emission_factor: ef,
                co2e: totalEmissions,
                notes: SCOPE3_CATEGORIES[category].name,
                status: status
            };

            await api.post('/scope3', payload);
            toast.success(status === 'Draft' ? 'Entry saved as draft' : 'Scope 3 entry added successfully');
            setAmount('');
            setCurrentPage(1);
            loadEntries();
        } catch (error) {
            console.error('Failed to add entry:', error);
            toast.error('Failed to add entry');
        }
    };

    const handleImportSuccess = () => {
        loadEntries();
        toast.success('Records imported successfully!');
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this entry?')) return;
        try {
            await api.delete(`/scope3/${id}`);
            toast.success('Entry deleted');
            loadEntries();
        } catch (error) {
            console.error('Failed to delete:', error);
            toast.error('Failed to delete entry');
        }
    };

    const getCategoryOptions = () => [
        { value: '', label: 'Select Category...', disabled: true },
        { value: '1', label: 'Cat 1: Purchased Goods & Services' },
        { value: '2', label: 'Cat 2: Capital Goods' },
        { value: '3', label: 'Cat 3: Fuel & Energy-Related' },
        { value: '4', label: 'Cat 4: Upstream Transportation' },
        { value: '5', label: 'Cat 5: Waste Generated' },
        { value: '6', label: 'Cat 6: Business Travel' },
        { value: '7', label: 'Cat 7: Employee Commuting' },
        { value: '8', label: 'Cat 8: Upstream Leased Assets' },
        { value: '9', label: 'Cat 9: Downstream Transportation' },
        { value: '10', label: 'Cat 10: Processing of Sold Products' },
        { value: '11', label: 'Cat 11: Use of Sold Products' },
        { value: '12', label: 'Cat 12: End-of-Life Treatment' },
        { value: '13', label: 'Cat 13: Downstream Leased Assets' },
        { value: '14', label: 'Cat 14: Franchises' },
        { value: '15', label: 'Cat 15: Investments' }
    ];

    const getActivityOptions = () => {
        const activities = CATEGORY_ACTIVITIES[category];
        if (!activities) return [{ value: '', label: 'Select category first...', disabled: true }];
        return activities.map(a => ({ value: a.value, label: a.value }));
    };

    const getFacilityOptions = () => [
        { value: '', label: 'Select Facility...' },
        ...facilities.map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
    ];

    return (
        <div className="scope-form">
            <div className="calc-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0 }}>New Scope 3 Entry</h3>
                    <div style={{ textAlign: 'right' }}>
                        <span style={{ color: '#8b5cf6', fontWeight: 600, fontSize: '0.9rem' }}>Scope 3: Other Indirect</span>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '20px' }}>
                    <div className="input-group">
                        <label>Year</label>
                        <input type="number" className="mole-input" value={year || ''} onChange={(e) => setYear(e.target.value)} />
                    </div>
                    <div className="input-group">
                        <label>Month</label>
                        <select className="component-select" value={month || 1} onChange={(e) => setMonth(e.target.value)}>
                            {[...Array(12)].map((_, i) => (
                                <option key={i + 1} value={i + 1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>
                            ))}
                        </select>
                    </div>
                    <div className="input-group">
                        <label>Facility</label>
                        <CustomDropdown options={getFacilityOptions()} value={facilityId || ''} onChange={setFacilityId} />
                    </div>
                    <div className="input-group">
                        <label>Category</label>
                        <CustomDropdown options={getCategoryOptions()} value={category} onChange={setCategory} />
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
                    <div className="input-group">
                        <label>Activity Type</label>
                        <CustomDropdown options={getActivityOptions()} value={activityType} onChange={setActivityType} />
                    </div>
                    <div className="input-group">
                        <label>Amount</label>
                        <input type="number" className="mole-input" value={amount || ''} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" step="0.01" />
                    </div>
                    <div className="input-group">
                        <label>Unit</label>
                        {UNIT_MULTIPLIERS[baseUnit] ? (
                            <select className="component-select" value={unit} onChange={(e) => handleUnitChange(e.target.value)}>
                                {Object.keys(UNIT_MULTIPLIERS[baseUnit]).map(u => (
                                    <option key={u} value={u}>{u}</option>
                                ))}
                            </select>
                        ) : (
                            <input type="text" className="mole-input" value={unit} readOnly style={{ background: 'rgba(255,255,255,0.03)', cursor: 'not-allowed' }} />
                        )}
                    </div>
                    <div className="input-group">
                        <label>EF (kg CO₂e/unit)</label>
                        <input type="number" className="mole-input" value={emissionFactor || ''} onChange={(e) => setEmissionFactor(e.target.value)} step="0.01" />
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', marginTop: '30px', justifyContent: 'flex-end' }}>
                    <button
                        className="btn-add-activity"
                        onClick={() => handleAddEntry('Verified')}
                        style={{ flex: 2, padding: '12px' }}
                    >
                        + Add Scope 3 Entry
                    </button>
                </div>

                {importModal.isOpen && (
                    <ColumnMappingWizard
                        onClose={() => setImportModal({ ...importModal, isOpen: false })}
                        onUploadSuccess={handleImportSuccess}
                        type={importModal.type}
                    />
                )}
            </div>

            <div className="calculator-grid-container" style={{ marginTop: '30px' }}>
                <div className="table-controls">
                    <strong>Documented Scope 3 Emissions</strong>
                </div>
                <div className="table-scroll-container">
                    <table className="excel-table">
                        <thead>
                            <tr>
                                <th>Year</th>
                                <th>Facility</th>
                                <th>Category</th>
                                <th>Activity/Product</th>
                                <th>Volume</th>
                                <th>EF (kg/unit)</th>
                                <th>Total (tCO₂e)</th>
                                <th style={{ textAlign: 'center' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {entries.length === 0 ? (
                                <tr>
                                    <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No entries yet</td>
                                </tr>
                            ) : (
                                entries.map(entry => (
                                    <tr key={entry.id}>
                                        <td>{entry.year}</td>
                                        <td>{facilities.find(f => f.id === entry.facility_id)?.name || 'Unknown'}</td>
                                        <td>{entry.category}</td>
                                        <td>{entry.sub_category || entry.product_type}</td>
                                        <td>{formatNumber(entry.activity_data || entry.volume, 2)} {entry.unit}</td>
                                        <td>{formatNumber(entry.emission_factor, 2)}</td>
                                        <td style={{ color: '#8b5cf6', fontWeight: 600 }}>
                                            {formatNumber(entry.co2e || entry.emissions_tco2e, 3)}
                                            {entry.status === 'Draft' && (
                                                <span style={{
                                                    marginLeft: '8px',
                                                    fontSize: '0.65rem',
                                                    background: '#fee2e2',
                                                    color: '#b91c1c',
                                                    padding: '1px 5px',
                                                    borderRadius: '4px'
                                                }}>Draft</span>
                                            )}
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <button className="icon-button" onClick={() => handleDelete(entry.id)} style={{ color: '#ef4444' }} title="Delete">
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                        <tfoot>
                            <tr style={{ backgroundColor: '#f9fafb', fontWeight: 'bold' }}>
                                <td colSpan="6" style={{ textAlign: 'right', paddingRight: '15px' }}>Total (Page):</td>
                                <td style={{ color: '#8b5cf6' }}>
                                    {formatNumber(entries.reduce((sum, e) => sum + (e.co2e || e.emissions_tco2e || 0), 0), 3)}
                                </td>
                                <td></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                <div className="pagination-controls">
                    <button className="action-btn secondary" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>Previous</button>
                    <span style={{ color: 'var(--text-secondary)' }}>Page {currentPage} of {totalPages}</span>
                    <button className="action-btn secondary" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>Next</button>
                </div>
            </div>
        </div >
    );
};

export default Scope3Form;
