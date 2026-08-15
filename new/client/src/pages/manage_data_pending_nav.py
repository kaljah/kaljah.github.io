import re

with open('ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state for pending emissions
state_code = """    const [goals, setGoals] = useState([]);
    const [baseYears, setBaseYears] = useState([]);
    const [pendingEmissions, setPendingEmissions] = useState({ scope1: [], scope2: [], scope3: [], total_pending: 0 });"""
content = content.replace('    const [goals, setGoals] = useState([]);\n    const [baseYears, setBaseYears] = useState([]);', state_code)

# 2. Add fetchPendingEmissions function
fetch_func = """    const fetchBaseYears = async () => {
        try {
            const res = await api.get('/manage/base-year');
            setBaseYears(res.data);
        } catch (error) {
            console.error("Error fetching base years", error);
        }
    };

    const fetchPendingEmissions = async () => {
        if (user?.role !== 'admin' && user?.role !== 'superuser') return;
        try {
            const res = await api.get('/emissions/pending');
            setPendingEmissions(res.data);
        } catch (error) {
            console.error("Error fetching pending emissions", error);
        }
    };
"""
content = content.replace("""    const fetchBaseYears = async () => {
        try {
            const res = await api.get('/manage/base-year');
            setBaseYears(res.data);
        } catch (error) {
            console.error("Error fetching base years", error);
        }
    };""", fetch_func)

# 3. Add to useEffect
use_effect = """        fetchOgmpSurveys();
        fetchGoals();
        fetchBaseYears();
        fetchPendingEmissions();
    }, []);"""
content = content.replace("""        fetchOgmpSurveys();
        fetchGoals();
        fetchBaseYears();
    }, []);""", use_effect)

# 4. Add the tab in nav
nav_tab = """                        <div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`} onClick={() => handleTabChange('factors')}>
                            <Settings size={18} /> Emission Factors
                        </div>
                        {(user?.role === 'admin' || user?.role === 'superuser') && (
                            <div className={`manage-nav-item ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => handleTabChange('pending')}>
                                <AlertCircle size={18} /> Pending Review {pendingEmissions.total_pending > 0 && <span style={{background: 'var(--up-warn, #eab308)', color: '#fff', borderRadius: '12px', padding: '2px 8px', fontSize: '0.75rem', marginLeft: '6px'}}>{pendingEmissions.total_pending}</span>}
                            </div>
                        )}
                        {user?.role === 'admin' && ("""
content = content.replace("""                        <div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`} onClick={() => handleTabChange('factors')}>
                            <Settings size={18} /> Emission Factors
                        </div>
                        {user?.role === 'admin' && (""", nav_tab)

with open('ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done inserting pending states and tabs")
