import React from 'react';
import { Button } from "../../ui";
import { Clock } from 'lucide-react';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const PendingAccessNotice = ({ handleTabChange }) => (
<div className={`manage-tab-content [padding:56px_24px]! [text-align:center]! [background:#ffffff]! [border-radius:16px]! [border:1px_solid_var(--border-color)]! [box-shadow:0_2px_8px_rgba(0,0,0,0.04)]!`}>
                                <div className="w-[56px]! h-[56px]! [border-radius:50%]! bg-[color:#fffbeb]! [border:1px_solid_#fde68a]! flex! items-center! justify-center! m-[0_auto_16px_auto]! text-[color:#d97706]!">
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
