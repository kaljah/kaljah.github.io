import glob
import re

spec_files = glob.glob('new/client/e2e/**/*.spec.js', recursive=True) + glob.glob('new/client/e2e/**/*.spec.ts', recursive=True)
print(f"Total Playwright spec files: {len(spec_files)}")
total_specs = 0
for sf in sorted(spec_files):
    with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        tests = re.findall(r'test\s*\(\s*[\'"]([^\'"]+)[\'"]', content)
        total_specs += len(tests)
        print(f"{sf}: {len(tests)} tests")
print(f"\nTotal Playwright test cases: {total_specs}")
