import re

with open('ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

pending_tab_jsx = """                        {activeTab === 'pending' && (user?.role === 'admin' || user?.role === 'superuser') && (
                            <div className="manage-tab-content">
                                <div className="manage-tab-header">
                                    <div>
                                        <h2>Pending Review</h2>
                                        <p>Review and approve emission records uploaded via bulk import.</p>
                                    </div>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <button className="btn-primary" onClick={fetchPendingEmissions}>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16, marginRight: 8 }}><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 2v6h6"/></svg>
                                            Refresh
                                        </button>
                                    </div>
                                </div>
                                
                                {['scope1', 'scope2', 'scope3'].map(scopeKey => {
                                    const records = pendingEmissions[scopeKey] || [];
                                    if (records.length === 0) return null;
                                    
                                    const scopeNumber = scopeKey.replace('scope', '');
                                    
                                    return (
                                        <div key={scopeKey} className="manage-card" style={{ marginBottom: '24px' }}>
                                            <div className="manage-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <h3>Scope {scopeNumber} Pending Imports ({records.length})</h3>
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    <button 
                                                        className="btn-primary" 
                                                        style={{ background: '#10b981' }}
                                                        onClick={async () => {
                                                            if (!window.confirm(`Approve all ${records.length} pending Scope ${scopeNumber} records?`)) return;
                                                            try {
                                                                await api.post('/emissions/approve/batch', { ids: records.map(r => r.id), scope: scopeNumber });
                                                                toast.success(`Approved ${records.length} records`);
                                                                fetchPendingEmissions();
                                                            } catch (err) {
                                                                toast.error("Failed to approve batch");
                                                            }
                                                        }}
                                                    >
                                                        Approve All
                                                    </button>
                                                    <button 
                                                        className="btn-delete"
                                                        onClick={async () => {
                                                            if (!window.confirm(`Reject all ${records.length} pending Scope ${scopeNumber} records? This will delete them permanently.`)) return;
                                                            try {
                                                                await api.post('/emissions/reject/batch', { ids: records.map(r => r.id), scope: scopeNumber });
                                                                toast.success(`Rejected ${records.length} records`);
                                                                fetchPendingEmissions();
                                                            } catch (err) {
                                                                toast.error("Failed to reject batch");
                                                            }
                                                        }}
                                                    >
                                                        Reject All
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="manage-card-body" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                                <table className="manage-table">
                                                    <thead>
                                                        <tr>
                                                            <th>ID</th>
                                                            <th>Date</th>
                                                            <th>Facility</th>
                                                            {scopeNumber === '1' && <><th>Process</th><th>Fuel</th><th>Qty</th></>}
                                                            {scopeNumber === '2' && <><th>Source Type</th><th>kWh</th></>}
                                                            {scopeNumber === '3' && <><th>Category</th></>}
                                                            <th>tCO2e</th>
                                                            <th style={{ width: '120px' }}>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {records.map(r => (
                                                            <tr key={r.id}>
                                                                <td><span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{String(r.id).slice(-6)}</span></td>
                                                                <td>{r.year}-{String(r.month).padStart(2, '0')}</td>
                                                                <td>{facilities.find(f => f.id === r.facility_id)?.name || r.facility_id}</td>
                                                                {scopeNumber === '1' && <><td>{r.process_type}</td><td>{r.fuel_type}</td><td>{r.quantity} {r.unit}</td></>}
                                                                {scopeNumber === '2' && <><td>{r.source_type}</td><td>{r.electricity_kwh}</td></>}
                                                                {scopeNumber === '3' && <><td>{r.category}</td></>}
                                                                <td style={{ fontWeight: 600 }}>{(r.co2e_total || r.co2e || 0).toFixed(2)}</td>
                                                                <td>
                                                                    <div style={{ display: 'flex', gap: '8px' }}>
                                                                        <button 
                                                                            className="action-btn" 
                                                                            style={{ color: '#10b981', border: '1px solid #10b981', padding: '2px 8px' }}
                                                                            onClick={async () => {
                                                                                try {
                                                                                    await api.post(`/emissions/approve/${r.id}`);
                                                                                    toast.success('Record approved');
                                                                                    fetchPendingEmissions();
                                                                                } catch (e) {
                                                                                    toast.error('Failed to approve');
                                                                                }
                                                                            }}
                                                                        >
                                                                            ✓
                                                                        </button>
                                                                        <button 
                                                                            className="action-btn" 
                                                                            style={{ color: '#ef4444', border: '1px solid #ef4444', padding: '2px 8px' }}
                                                                            onClick={async () => {
                                                                                try {
                                                                                    await api.post(`/emissions/reject/${r.id}`);
                                                                                    toast.success('Record rejected');
                                                                                    fetchPendingEmissions();
                                                                                } catch (e) {
                                                                                    toast.error('Failed to reject');
                                                                                }
                                                                            }}
                                                                        >
                                                                            ✕
                                                                        </button>
                                                                    </div>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    );
                                })}
                                
                                {pendingEmissions.total_pending === 0 && (
                                    <div style={{ textAlign: 'center', padding: '64px', background: '#f9fafb', borderRadius: '12px', border: '1px dashed #e5e7eb' }}>
                                        <CheckCircle size={48} color="#10b981" style={{ margin: '0 auto 16px auto', opacity: 0.5 }} />
                                        <h3 style={{ margin: '0 0 8px 0', color: '#374151' }}>All caught up!</h3>
                                        <p style={{ color: '#6b7280', margin: 0 }}>There are no emission records pending review.</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {activeTab === 'factors' && ("""

content = content.replace("                        {activeTab === 'factors' && (", pending_tab_jsx)

with open('ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done inserting pending tab UI")
