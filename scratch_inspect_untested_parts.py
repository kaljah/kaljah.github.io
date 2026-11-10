import glob
import re

files = sorted(glob.glob('new/server/tests/test_untested_calculation_paths*.py'))
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
    test_funcs = re.findall(r'def\s+(test_[a-zA-Z0-9_]+)\s*\(', content)
    docstring = re.search(r'"""(.*?)"""', content, re.DOTALL)
    summary = docstring.group(1).strip() if docstring else "No docstring"
    print(f"=== {f} ({len(test_funcs)} tests) ===")
    print(f"Summary: {summary[:150]}...")
