import re

with open('temp_old/cbam_diff_new_client_src_pages_ManageData.jsx.txt', 'r', encoding='utf-8') as f:
    diff = f.read()

added_lines = [line[1:] for line in diff.split('\n') if line.startswith('-') and not line.startswith('---')]
for i, line in enumerate(added_lines):
    if 'activeTab === \'cbam\'' in line:
        print('FOUND CBAM TAB BUTTON:', i)
    if 'activeTab === \'cbam\' && (' in line:
        print('FOUND CBAM TAB CONTENT:', i)

