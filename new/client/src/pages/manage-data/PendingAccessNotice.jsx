import React from 'react';
import { Clock } from 'lucide-react';
import { Button, Card, EmptyState } from "../../ui";

const PendingAccessNotice = ({ handleTabChange }) => (
    <Card className="manage-tab-content py-6">
        <EmptyState
            icon={Clock}
            title="Review Permissions Required"
            description="The pending review queue is restricted to Regional Managers and Administrators under corporate Maker-Checker governance rules. Direct activity logs submitted by operators are audited here before inclusion in official GHG inventories."
            action={<Button onClick={() => handleTabChange('factors')}>Return to Emission Factors</Button>}
        />
    </Card>
);

export default PendingAccessNotice;
