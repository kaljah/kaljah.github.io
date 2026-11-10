import os

for root, dirs, files in os.walk('.'):
    if 'node_modules' in root or '.git' in root:
        continue
    for f in files:
        if 'result' in f.lower() or 'report' in f.lower() or 'diff' in f.lower():
            p = os.path.join(root, f)
            print(p, os.path.getsize(p))
