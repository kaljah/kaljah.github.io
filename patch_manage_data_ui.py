import re

with open('temp_old/cbam_diff_new_client_src_pages_ManageData.jsx.txt', 'r', encoding='utf-8') as f:
    diff = f.read()

# find the block for activeTab === 'cbam'
lines = diff.split('\n')
cbam_ui = []
in_block = False
for line in lines:
    if line.startswith('-                        {activeTab === \'cbam\' && ('):
        in_block = True
    if in_block:
        if line.startswith('-                        {activeTab === \'ogmp\' && ('):
            break
        if line.startswith('-'):
            cbam_ui.append(line[1:])

with open('new/client/src/pages/ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

cbam_ui_str = '\n'.join(cbam_ui) + '\n\n'
content = content.replace('                        {activeTab === \'ogmp\' && (', cbam_ui_str + '                        {activeTab === \'ogmp\' && (')

with open('new/client/src/pages/ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
