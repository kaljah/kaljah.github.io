import re

with open('DashboardEnhanced.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state
state_code = """  const [variance, setVariance] = useState({ emissions: "—", intensity: "—" });
  const [pendingCount, setPendingCount] = useState(0);"""
content = content.replace('  const [variance, setVariance] = useState({ emissions: "—", intensity: "—" });', state_code)

# 2. Add fetch inside loadDashboardData near line 175
fetch_code = """      // Part 3: Optimized Batch Dashboard API Call
      const batchRes = await api.get(`/dashboard/batch-all?${filterParams}`);
      const batch = batchRes.data;

      if (user?.role === 'admin' || user?.role === 'superuser') {
        try {
          const pRes = await api.get('/emissions/pending');
          setPendingCount(pRes.data.total_pending || 0);
        } catch (e) { console.error(e); }
      }"""
content = content.replace('      // Part 3: Optimized Batch Dashboard API Call\n      const batchRes = await api.get(`/dashboard/batch-all?${filterParams}`);\n      const batch = batchRes.data;', fetch_code)

# 3. Add banner rendering
banner_code = """        <div className="dashboard-header-row">
          <h1 className="grid-title">GHG Emissions Dashboard</h1>
          <div className="live-badge">
            <div className="pulse-dot"></div>
            Live Content • Updated {lastUpdated}
          </div>
        </div>

        {pendingCount > 0 && (
          <div style={{ background: '#fefce8', border: '1px solid #fef08a', borderRadius: '8px', padding: '16px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ background: '#eab308', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem', color: '#854d0e' }}>Pending Data Review</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.875rem', color: '#a16207' }}>
                  There are <strong>{pendingCount}</strong> emission records pending your approval. These values are excluded from the dashboard until verified.
                </p>
              </div>
            </div>
            <button 
              className="btn-primary" 
              style={{ background: '#ca8a04', whiteSpace: 'nowrap' }}
              onClick={() => navigate('/manage-data', { state: { tab: 'pending' } })}
            >
              Review Now
            </button>
          </div>
        )}"""
content = content.replace("""        <div className="dashboard-header-row">
          <h1 className="grid-title">GHG Emissions Dashboard</h1>
          <div className="live-badge">
            <div className="pulse-dot"></div>
            Live Content • Updated {lastUpdated}
          </div>
        </div>""", banner_code)

with open('DashboardEnhanced.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching dashboard for pending count banner")
