import os
import glob

dirs_to_check = ['audit', 'docs', 'validation', 'scripts', 'tests', 'archive', 'new', 'reference', '.reports']
patterns = ['*anomal*', '*extract*', '*spot_check*', '*sanity*', '*RESULTS*', '*comparison*', '*check*']

found = []
for d in dirs_to_check:
    for root, dirs, files in os.walk(d):
        if 'node_modules' in root or '.git' in root or '__pycache__' in root:
            continue
        for f in files:
            for p in patterns:
                if glob.fnmatch.fnmatch(f.lower(), p.lower()):
                    found.append(os.path.join(root, f))
                    break

print(f"Found {len(found)} files:")
for f in found:
    print(f)
