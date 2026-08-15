import glob
for file in glob.glob('client/src/components/Scope*ImportWizard.jsx'):
    content = open(file, encoding='utf-8').read()
    content = content.replace('"Start Import"', '"Submit for Review"')
    content = content.replace('{ id: 5, label: "Import"', '{ id: 5, label: "Review"')
    open(file, 'w', encoding='utf-8').write(content)
print('Done updating wizards.')
