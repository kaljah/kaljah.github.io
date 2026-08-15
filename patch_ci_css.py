with open('temp_old/cbam_diff_new_client_src_pages_CarbonIntensity.css.txt', 'r', encoding='utf-8') as f:
    diff = f.read()

cbam_css = []
for line in diff.split('\n'):
    if line.startswith('-'):
        if not line.startswith('---'):
            cbam_css.append(line[1:])

cbam_css_str = '\n'.join(cbam_css) + '\n\n'

with open('new/client/src/pages/CarbonIntensity.css', 'a', encoding='utf-8') as f:
    f.write(cbam_css_str)
