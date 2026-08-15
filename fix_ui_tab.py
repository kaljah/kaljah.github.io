with open('new/client/src/pages/ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# insert the tab button
if "activeTab === 'cbam'" not in content:
    tab_btn = '''                        <div className={manage-nav-item \} onClick={() => handleTabChange('cbam')}>
                            <FileText size={18} />
                            <span>CBAM Products</span>
                        </div>'''
    content = content.replace(
        "<div className={manage-nav-item \} onClick={() => handleTabChange('ogmp')}>", 
        tab_btn + '\n                        <div className={manage-nav-item \} onClick={() => handleTabChange(\'ogmp\')}>'
    )

# insert the content block
if "{activeTab === 'cbam' && (" not in content:
    with open('temp_old/cbam_diff_new_client_src_pages_ManageData.jsx.txt', 'r', encoding='utf-8', errors='replace') as f:
        diff = f.read()

    cbam_ui = []
    in_block = False
    for line in diff.split('\n'):
        if line.startswith("-                        {activeTab === 'cbam' && ("):
            in_block = True
        if in_block:
            if line.startswith("-                        {activeTab === 'ogmp' && ("):
                break
            if line.startswith("-"):
                cbam_ui.append(line[1:].replace('tCO"??e', 'tCO2e').replace('tCO"??', 'tCO2'))

    cbam_ui_str = '\n'.join(cbam_ui) + '\n\n'
    content = content.replace("                        {activeTab === 'ogmp' && (", cbam_ui_str + "                        {activeTab === 'ogmp' && (")

with open('new/client/src/pages/ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed ManageData tab and content')
