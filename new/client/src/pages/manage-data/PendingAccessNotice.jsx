import React from 'react';
import { Clock } from 'lucide-react';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const PendingAccessNotice = ({ handleTabChange }) => (
<div className="manage-tab-content" style={{ padding: '56px 24px', textAlign: 'center', background: '#ffffff', borderRadius: '16px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                                <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#fffbeb', border: '1px solid #fde68a', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto', color: '#d97706' }}>
                                    <Clock size={28} />
                                </div>
                                <h3 style={{ margin: '0 0 8px 0', fontSize: '1.25rem', color: 'var(--text-primary)', fontWeight: 700 }}>
                                    Review Permissions Required
                                </h3>
                                <p style={{ maxWidth: '520px', margin: '0 auto 20px auto', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                    The pending review queue is restricted to Regional Managers and Administrators under corporate Maker-Checker governance rules. Direct activity logs submitted by operators are audited here before inclusion in official GHG inventories.
                                </p>
                                <button
                                    className="btn-primary"
                                    onClick={() => handleTabChange('factors')}
                                    style={{ padding: '8px 24px', fontSize: '0.88rem' }}
                                >
                                    Return to Emission Factors
                                </button>
                            </div>
);

export default PendingAccessNotice;
