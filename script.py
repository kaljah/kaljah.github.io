import sys
with open('new/client/src/pages/ManageData.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'const [ogmpSurveys, setOgmpSurveys] = useState([]);' in line:
        new_lines.append('  const [cbamExports, setCbamExports] = useState([]);\n')
    
    if 'const [ogmpForm, setOgmpForm] = useState({' in line:
        new_lines.append('  const [cbamForm, setCbamForm] = useState({\n')
        new_lines.append('    id: null,\n')
        new_lines.append('    activity: "",\n')
        new_lines.append('    division: "",\n')
        new_lines.append('    facility_id: "",\n')
        new_lines.append('    year: new Date().getFullYear(),\n')
        new_lines.append('    month: 1,\n')
        new_lines.append('    product_name: "Crude Petroleum Oil",\n')
        new_lines.append('    cn_code: "2709 00",\n')
        new_lines.append('    quantity_tonnes: "",\n')
        new_lines.append('    export_destination: "EU",\n')
        new_lines.append('    specific_embedded_direct: "",\n')
        new_lines.append('    specific_embedded_indirect: "",\n')
        new_lines.append('    notes: "",\n')
        new_lines.append('  });\n')
        new_lines.append('  const [editingCbamId, setEditingCbamId] = useState(null);\n\n')

    if 'fetchOgmpSurveys();' in line and '}, []);' in lines[i+1]:
        new_lines.append('    fetchCbamExports();\n')
        
    if 'setOgmpForm((prev) => ({ ...prev, ...autoFill }));' in line or 'setOgmpForm(prev => ({ ...prev, ...autoFill }));' in line:
        new_lines.append('    setCbamForm((prev) => ({ ...prev, ...autoFill }));\n')

    if 'const fetchOgmpSurveys = async () => {' in line:
        new_lines.append('''  const fetchCbamExports = async () => {
    try {
      const res = await api.get('/data/cbam-exports');
      setCbamExports(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };\n\n''')

    if 'const handleSaveOgmpSurvey = async () => {' in line:
        new_lines.append('''  const handleSaveCbamExport = async () => {
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
      toast.error(err?.response?.data?.error || 'Failed to save CBAM record');
    }
  };

  const handleDeleteCbamExport = async (id) => {
    if (!window.confirm('Delete this CBAM export record?')) return;
    try {
      await api.delete('/data/cbam-exports/' + id);
      toast.success('CBAM export record deleted');
      fetchCbamExports();
    } catch (err) {
      toast.error('Failed to delete CBAM record');
    }
  };\n\n''')

    if 'onClick={() => handleTabChange("ogmp")}' in line:
        if 'className={manage-nav-item' in lines[i-1]:
            # This is the tab button. Let's add CBAM tab right before it.
            new_lines.append('''        <button
          className={manage-nav-item \}
          onClick={() => handleTabChange("cbam")}
        >
          <FileText size={18} />
          CBAM Products
        </button>\n''')

    if 'const filteredOgmp = ogmpSurveys.filter((item) => {' in line:
        new_lines.append('''  const filteredCbam = cbamExports.filter((item) => {
    if (filterFacility && filterFacility !== "all" && item.facility_id?.toString() !== filterFacility) return false;
    if (filterYear && filterYear !== "all" && item.year?.toString() !== filterYear) return false;
    return true;
  });\n\n''')
        
    new_lines.append(line)

with open('new/client/src/pages/ManageData.jsx', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
