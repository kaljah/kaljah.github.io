import os

keywords = ['Heater 2', 'H01 Dehy Regen', '70559', '35528', '119162', 'Flare1 – HP', 'Flare1 - HP']
matches = []

dirs = ['audit', 'validation', 'new/server', 'tests', 'scripts']
for d in dirs:
    for root, _, files in os.walk(d):
        if any(x in root for x in ['node_modules', '.git', '__pycache__', '.pytest_cache']):
            continue
        for f in files:
            if f.endswith(('.py', '.json', '.md', '.csv', '.txt')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                        for kw in keywords:
                            if kw in content:
                                matches.append((p, kw))
                                break
                except Exception:
                    pass

print(f"Total matches: {len(matches)}")
for p, kw in matches:
    print(f"{p}: matched {kw}")
