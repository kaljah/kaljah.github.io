content = open('routes/dashboard.py', encoding='utf-8').read()
old = '.status != "Draft"'
new = '.status == "Verified"'
updated = content.replace(old, new)
count = updated.count(new)
open('routes/dashboard.py', 'w', encoding='utf-8').write(updated)
print(f'Done. {count} occurrences of Verified filter now present.')
