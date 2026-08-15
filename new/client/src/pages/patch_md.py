import re

with open('ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add tab button
tab_btn = """                        <div className={`manage-nav-item ${activeTab === 'goals' ? 'active' : ''}`} onClick={() => handleTabChange('goals')}>
                            <Target size={16} /> Emission Goals
                        </div>
                        <div className={`manage-nav-item ${activeTab === 'sbti' ? 'active' : ''}`} onClick={() => handleTabChange('sbti')}>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{width: 16, height: 16}}>
                              <path d="M3 3v18h18" />
                              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3" />
                            </svg>
                            SBTi Targets
                        </div>"""
content = content.replace("                        <div className={`manage-nav-item ${activeTab === 'goals' ? 'active' : ''}`} onClick={() => handleTabChange('goals')}>\n                            <Target size={16} /> Emission Goals\n                        </div>", tab_btn)

# 2. Add state and fetch logic for SBTi
sbti_state = """    const [sbtiConfig, setSbtiConfig] = useState({
        base_year: 2024,
        base_year_emissions: 0,
        target_year: 2050,
        reduction_rate_pct: 4.2,
        pathway_type: "1.5C"
    });
    const [hasSbti, setHasSbti] = useState(false);

    const fetchSbti = async () => {
        try {
            const res = await api.get('/manage/sbti');
            if (res.data.has_target) {
                setHasSbti(true);
                setSbtiConfig({
                    base_year: res.data.base_year,
                    base_year_emissions: res.data.base_year_emissions,
                    target_year: res.data.target_year,
                    reduction_rate_pct: res.data.reduction_rate_pct,
                    pathway_type: res.data.pathway_type
                });
            }
        } catch (e) {}
    };

    const handleSaveSbti = async () => {
        try {
            await api.post('/manage/sbti', sbtiConfig);
            toast.show('SBTi Target saved successfully', 'success');
            setHasSbti(true);
        } catch (e) {
            toast.show('Failed to save SBTi Target', 'error');
        }
    };
"""
content = content.replace("    const [activeTab, setActiveTab] = useState('factors');", "    const [activeTab, setActiveTab] = useState('factors');\n" + sbti_state)

# 3. Add fetchSbti to useEffect
fetch_all_re = r'(const fetchAllData = async \(\) => {[\s\S]*?fetchGoals\(\);)'
content = re.sub(fetch_all_re, r'\1\n            fetchSbti();', content)

# 4. Add the SBTi Tab Content right after the goals tab content ends
sbti_content = """
                        {/* ─── SBTI TARGETS TAB ────────────────────────────────────────────── */}
                        {activeTab === 'sbti' && (
                            <div className="manage-tab-content fade-in">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                                    <div>
                                        <h2 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: '0 0 4px 0' }}>SBTi Trajectory Configuration</h2>
                                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                            Configure your Science Based Targets initiative (SBTi) parameters to model reduction pathways on the dashboard.
                                        </p>
                                    </div>
                                    <button className="action-btn" onClick={handleSaveSbti}>
                                        Save Configuration
                                    </button>
                                </div>

                                <div className="glass-panel" style={{ padding: '24px', maxWidth: '600px' }}>
                                    <div className="form-grid">
                                        <div className="input-group">
                                            <label>Base Year</label>
                                            <input 
                                                type="number" 
                                                className="mole-input" 
                                                value={sbtiConfig.base_year} 
                                                onChange={e => setSbtiConfig({...sbtiConfig, base_year: e.target.value})}
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Base Year Emissions (tCO₂e)</label>
                                            <input 
                                                type="number" 
                                                className="mole-input" 
                                                value={sbtiConfig.base_year_emissions} 
                                                onChange={e => setSbtiConfig({...sbtiConfig, base_year_emissions: e.target.value})}
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Target Year</label>
                                            <input 
                                                type="number" 
                                                className="mole-input" 
                                                value={sbtiConfig.target_year} 
                                                onChange={e => setSbtiConfig({...sbtiConfig, target_year: e.target.value})}
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Annual Reduction Rate (%)</label>
                                            <input 
                                                type="number" 
                                                step="0.1"
                                                className="mole-input" 
                                                value={sbtiConfig.reduction_rate_pct} 
                                                onChange={e => setSbtiConfig({...sbtiConfig, reduction_rate_pct: e.target.value})}
                                            />
                                        </div>
                                        <div className="input-group" style={{ gridColumn: '1 / -1' }}>
                                            <label>Pathway Type</label>
                                            <select 
                                                className="component-select"
                                                value={sbtiConfig.pathway_type}
                                                onChange={e => setSbtiConfig({...sbtiConfig, pathway_type: e.target.value})}
                                            >
                                                <option value="1.5C">1.5°C Aligned (4.2% minimum reduction)</option>
                                                <option value="WB2C">Well Below 2°C (2.5% minimum reduction)</option>
                                            </select>
                                        </div>
                                    </div>
                                    
                                    {hasSbti && (
                                        <div style={{ marginTop: '20px', padding: '12px', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '6px', color: '#065f46', fontSize: '0.875rem' }}>
                                            <CheckCircle size={16} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
                                            SBTi target is active. Dashboard will now render your trajectory pathway.
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
"""
content = content.replace("                        {/* ─── MITIGATION PROJECTS TAB ──────────────────────────────────────── */} ", sbti_content + "\n                        {/* ─── MITIGATION PROJECTS TAB ──────────────────────────────────────── */} ")


with open('ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching ManageData.jsx for SBTi config tab")
