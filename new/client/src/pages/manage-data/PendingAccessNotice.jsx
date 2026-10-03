import React from 'react';
import { Button } from "../../ui";
import { Clock } from 'lucide-react';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const PendingAccessNotice = ({ handleTabChange }) => (
<div className="manage-tab-content" style={{ padding: '56px 24px', textAlign: 'center', background: '#ffffff', borderRadius: '16px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                                <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#fffbeb', border: '1px solid #fde68a', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto', color: '#d97706' }}>
                                    <Clock size={28} />
                                </div>
                                <h3 className="m-[0_0_8px_0]! text-[length:1.25rem]! text-[color:var(--text-primary)]! font-bold!">
                                    Review Permissions Required
                                </h3>
                                <p className="max-w-[520px]! m-[0_auto_20px_auto]! text-[color:var(--text-secondary)]! text-[length:0.9rem]! leading-[1.6]!">
                                    The pending review queue is restricted to Regional Managers and Administrators under corporate Maker-Checker governance rules. Direct activity logs submitted by operators are audited here before inclusion in official GHG inventories.
                                </p>
                                <Button
                                    type="submit"
                                    onClick={() => handleTabChange('factors')}
                                    className="p-[8px_24px]! text-[length:0.88rem]!"
                                >
                                    Return to Emission Factors
                                </Button>
                            </div>
);

export default PendingAccessNotice;
