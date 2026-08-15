def fix_manage_data_ui():
    with open('temp_old/cbam_diff_new_client_src_pages_ManageData.jsx.txt', 'r', encoding='utf-8', errors='replace') as f:
        diff = f.read()

    cbam_ui = []
    in_block = False
    for line in diff.split('\n'):
        if line.startswith('-                        {activeTab === \'cbam\' && ('):
            in_block = True
        if in_block:
            if line.startswith('-                        {activeTab === \'ogmp\' && ('):
                break
            if line.startswith('-'):
                cbam_ui.append(line[1:].replace('tCO"??e', 'tCO2e').replace('tCO"??', 'tCO2'))

    with open('new/client/src/pages/ManageData.jsx', 'r', encoding='utf-8') as f:
        content = f.read()

    if 'activeTab === \'cbam\' && (' not in content:
        cbam_ui_str = '\n'.join(cbam_ui) + '\n\n'
        content = content.replace('                        {activeTab === \'ogmp\' && (', cbam_ui_str + '                        {activeTab === \'ogmp\' && (')
        with open('new/client/src/pages/ManageData.jsx', 'w', encoding='utf-8') as f:
            f.write(content)
        print('fixed manage data ui')

def fix_carbon_intensity():
    with open('new/client/src/pages/CarbonIntensity.jsx', 'r', encoding='utf-8') as f:
        content = f.read()

    if 'const [cbamProducts, setCbamProducts] = useState([]);' not in content:
        state_cbam = '''    const [cbamProducts, setCbamProducts] = useState([]);'''
        content = content.replace('    const [activeGwpStandard, setActiveGwpStandard] = useState(\'AR5\');', state_cbam + '\n    const [activeGwpStandard, setActiveGwpStandard] = useState(\'AR5\');')

    if 'const loadCbamData = async () => {' not in content:
        fetch_cbam = '''    const loadCbamData = async () => {
        try {
            const params = new URLSearchParams();
            if (selectedYear && selectedYear !== 'all') params.append('year', selectedYear);
            if (currentRegion && currentRegion !== 'all') params.append('facilityId', currentRegion);
            const res = await api.get('/data/cbam-exports?' + params.toString()).catch(() => ({ data: [] }));
            setCbamProducts(res.data || []);
        } catch (error) {
            console.error('CBAM load error:', error);
        }
    };'''
        content = content.replace('    const loadTrendData = async (endYear) => {', fetch_cbam + '\n\n    const loadTrendData = async (endYear) => {')
        content = content.replace('        loadTrendData(selectedYear);', '        loadTrendData(selectedYear);\n        loadCbamData();')

    if '{/* EU CBAM COMPLIANCE & PRODUCT EMBODIMENT SECTION */}' not in content:
        with open('temp_old/cbam_diff_new_client_src_pages_CarbonIntensity.jsx.txt', 'r', encoding='utf-8', errors='replace') as f:
            diff = f.read()
        cbam_ui = []
        in_block = False
        for line in diff.split('\n'):
            if line.startswith('-                {/* EU CBAM COMPLIANCE & PRODUCT EMBODIMENT SECTION */}'):
                in_block = True
            if in_block:
                if line.startswith('-                {/* Regional Bar Charts */}'):
                    break
                if line.startswith('-'):
                    cbam_ui.append(line[1:].replace('tCO"??e', 'tCO2e').replace('tCO"??', 'tCO2'))

        cbam_ui_str = '\n'.join(cbam_ui) + '\n\n'
        content = content.replace('                {/* Regional Bar Charts */}', cbam_ui_str + '                {/* Regional Bar Charts */}')
    
    with open('new/client/src/pages/CarbonIntensity.jsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print('fixed carbon intensity')

fix_manage_data_ui()
fix_carbon_intensity()
