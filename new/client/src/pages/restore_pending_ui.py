import re

with open('ManageData_old.jsx', 'r', encoding='utf-16') as f:
    content = f.read()

# Extract pending tab from old file
# the pending tab starts at {activeTab === 'pending'
# and goes until {activeTab === 'factors'
start_idx = content.find("{activeTab === 'pending'")
end_idx = content.find("{activeTab === 'factors'")
pending_ui = content[start_idx:end_idx].strip()

# Also extract the nav item from the old file
nav_item_start = content.find("<div className={`manage-nav-item ${activeTab === 'pending' ? 'active' : ''}`}")
nav_item_end = content.find("<div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`}")
nav_item = content[nav_item_start:nav_item_end].strip() if nav_item_start != -1 else ""

if nav_item == "":
    nav_item = """                        {(user?.role === 'admin' || user?.role === 'superuser') && (
                            <div className={`manage-nav-item ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => handleTabChange('pending')}>
                                <span style={{display: 'flex', justifyContent: 'space-between', width: '100%'}}>
                                    Pending Review
                                    {pendingEmissions && (pendingEmissions.scope1.length > 0 || pendingEmissions.scope2.length > 0 || pendingEmissions.scope3.length > 0) && (
                                        <span style={{
                                            background: '#ef4444', color: 'white', borderRadius: '12px', padding: '2px 8px', fontSize: '0.75rem', fontWeight: 600
                                        }}>
                                            {pendingEmissions.scope1.length + pendingEmissions.scope2.length + pendingEmissions.scope3.length}
                                        </span>
                                    )}
                                </span>
                            </div>
                        )}"""

# Now write them to ManageData.jsx
with open('ManageData.jsx', 'r', encoding='utf-8') as f:
    new_content = f.read()

# 1. Insert Nav Item right before 'factors' nav item
new_content = new_content.replace(
    """<div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`} onClick={() => handleTabChange('factors')}>""",
    nav_item + "\n                        " + """<div className={`manage-nav-item ${activeTab === 'factors' ? 'active' : ''}`} onClick={() => handleTabChange('factors')}>"""
)

# 2. Insert Pending UI right before Factors UI
new_content = new_content.replace(
    "{/* Factors Tab */}",
    "{/* Pending Tab */}\n" + pending_ui + "\n\n                        {/* Factors Tab */}"
)

with open('ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
    
print("Successfully restored Pending Review UI.")
