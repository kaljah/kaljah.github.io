import React, { useState } from 'react';
import api from '../api';
import { useToast } from '../components/Toast';
import { useAuth } from '../context/AuthContext';
import { Database, RefreshCw, CheckCircle, AlertCircle, HardDrive } from 'lucide-react';
import './ManageData.css';

const ErpSync = () => {
    const { user } = useAuth();
    const toast = useToast();
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncResult, setSyncResult] = useState(null);

    const handleSync = async () => {
        setIsSyncing(true);
        setSyncResult(null);
        try {
            const res = await api.post('/emissions/erp/sync');
            if (res.data.success) {
                setSyncResult({
                    status: 'success',
                    message: res.data.message,
                    synced_records: res.data.synced_records
                });
                toast.show(res.data.message, 'success');
            } else {
                throw new Error(res.data.error || 'Sync failed');
            }
        } catch (error) {
            console.error('ERP Sync error:', error);
            const errorMsg = error.response?.data?.error || error.message || 'Failed to sync with ERP system';
            setSyncResult({
                status: 'error',
                message: errorMsg
            });
            toast.show(errorMsg, 'error');
        } finally {
            setIsSyncing(false);
        }
    };

    return (
        <div className="page-container fade-in">
            <header className="page-header">
                <div>
                    <h1 className="page-title">
                        <Database size={24} style={{ marginRight: '12px', verticalAlign: 'middle', color: '#6366f1' }} />
                        ERP Integration & Sync
                    </h1>
                    <p className="page-subtitle">Synchronize activity and spend data directly from your enterprise systems (SAP, Oracle, Workday).</p>
                </div>
            </header>

            <div className="manage-tab-content">
                <div className="glass-panel" style={{ padding: '32px', maxWidth: '800px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                        <div style={{ 
                            width: '80px', height: '80px', borderRadius: '50%', background: '#e0e7ff', 
                            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' 
                        }}>
                            <HardDrive size={40} color="#4f46e5" />
                        </div>
                        <h2 style={{ color: '#1e293b', fontSize: '1.5rem', marginBottom: '8px' }}>Manual ERP Data Synchronization</h2>
                        <p style={{ color: '#64748b' }}>
                            Pull the latest transactions, travel logs, and procurement spend data. The system will automatically map records to the appropriate emission factors based on NAICS codes and activity types.
                        </p>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
                        <button 
                            className="action-btn" 
                            style={{ 
                                padding: '16px 32px', fontSize: '1.1rem', background: '#4f46e5', color: 'white',
                                display: 'flex', alignItems: 'center', gap: '12px', opacity: isSyncing ? 0.7 : 1,
                                cursor: isSyncing ? 'not-allowed' : 'pointer'
                            }}
                            onClick={handleSync}
                            disabled={isSyncing}
                        >
                            {isSyncing ? (
                                <>
                                    <RefreshCw className="spin" size={20} />
                                    Syncing with ERP...
                                </>
                            ) : (
                                <>
                                    <RefreshCw size={20} />
                                    Trigger Data Sync
                                </>
                            )}
                        </button>
                    </div>

                    {syncResult && (
                        <div style={{ 
                            padding: '24px', 
                            borderRadius: '8px', 
                            background: syncResult.status === 'success' ? '#ecfdf5' : '#fef2f2',
                            border: `1px solid ${syncResult.status === 'success' ? '#a7f3d0' : '#fecaca'}`,
                            display: 'flex', alignItems: 'flex-start', gap: '16px'
                        }}>
                            {syncResult.status === 'success' ? (
                                <CheckCircle size={24} color="#059669" style={{ flexShrink: 0 }} />
                            ) : (
                                <AlertCircle size={24} color="#dc2626" style={{ flexShrink: 0 }} />
                            )}
                            <div>
                                <h3 style={{ 
                                    margin: '0 0 8px 0', 
                                    color: syncResult.status === 'success' ? '#065f46' : '#991b1b',
                                    fontSize: '1.1rem'
                                }}>
                                    {syncResult.status === 'success' ? 'Synchronization Successful' : 'Synchronization Failed'}
                                </h3>
                                <p style={{ margin: 0, color: syncResult.status === 'success' ? '#064e3b' : '#7f1d1d' }}>
                                    {syncResult.message}
                                </p>
                                {syncResult.status === 'success' && (
                                    <p style={{ margin: '8px 0 0 0', color: '#064e3b', fontWeight: 500 }}>
                                        {syncResult.synced_records} records have been imported and are now marked as "Pending" in the Manage Data view.
                                    </p>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ErpSync;
