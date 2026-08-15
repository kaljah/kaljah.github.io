import re

with open('new/client/src/pages/ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. State
state_cbam = '''    const [cbamExports, setCbamExports] = useState([]);'''
content = content.replace('    const [ogmpSurveys, setOgmpSurveys] = useState([]);', state_cbam + '\n    const [ogmpSurveys, setOgmpSurveys] = useState([]);')

# 2. Form State
form_cbam = '''    const [cbamForm, setCbamForm] = useState({
        id: null, activity: '', division: '', facility_id: '',
        year: new Date().getFullYear(), month: 1,
        product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
        quantity_tonnes: '', export_destination: 'EU',
        specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
    });
    const [editingCbamId, setEditingCbamId] = useState(null);'''
content = content.replace('    const [ogmpForm, setOgmpForm] = useState({', form_cbam + '\n\n    const [ogmpForm, setOgmpForm] = useState({')

# 3. Fetch in useEffect
content = content.replace('        fetchOgmpSurveys();\n    }, []);', '        fetchCbamExports();\n        fetchOgmpSurveys();\n    }, []);')

# 4. Autofill
content = content.replace('        setOgmpForm(prev => ({ ...prev, ...autoFill }));', '        setCbamForm(prev => ({ ...prev, ...autoFill }));\n        setOgmpForm(prev => ({ ...prev, ...autoFill }));')

# 5. Fetch func
fetch_cbam = '''    const fetchCbamExports = async () => {
        try {
            const res = await api.get('/data/cbam-exports');
            setCbamExports(res.data || []);
        } catch (err) { console.error(err); }
    };'''
content = content.replace('    const fetchOgmpSurveys = async () => {', fetch_cbam + '\n\n    const fetchOgmpSurveys = async () => {')

# 6. Save/Delete
save_cbam = '''    const handleSaveCbamExport = async () => {
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
            await api.delete(/data/cbam-exports/\);
            toast.success('CBAM export record deleted');
            fetchCbamExports();
        } catch (err) { toast.error('Failed to delete CBAM record'); }
    };'''
content = content.replace('    const handleSaveOgmpSurvey = async () => {', save_cbam + '\n\n    const handleSaveOgmpSurvey = async () => {')

# 7. Tab UI
tab_cbam = '''                                <button
                                    className={	ab-btn \}
                                    onClick={() => { setActiveTab('cbam'); setCurrentPage(1); }}
                                >
                                    <FileText size={18} />
                                    CBAM Products
                                </button>'''
content = content.replace('''                                <button
                                    className={	ab-btn }''', tab_cbam + '\n' + '''                                <button
                                    className={	ab-btn }''')

# 8. Filter UI
filter_cbam = '''    const filteredCbam = cbamExports.filter(item => {
        if (filterFacility && filterFacility !== 'all' && item.facility_id?.toString() !== filterFacility) return false;
        if (filterYear && filterYear !== 'all' && item.year?.toString() !== filterYear) return false;
        return true;
    });'''
content = content.replace('    const filteredOgmp = ogmpSurveys.filter(item => {', filter_cbam + '\n\n    const filteredOgmp = ogmpSurveys.filter(item => {')

with open('new/client/src/pages/ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
