import os
import re

def count_tests():
    stats = {}
    total_py_cases = 0
    total_ts_cases = 0

    py_pattern = re.compile(r'^\s*def\s+(test_[a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
    ts_pattern = re.compile(r'(?:it|test)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', re.MULTILINE)

    for root, _, files in os.walk('.'):
        if any(p in root for p in ['node_modules', '.venv', '.git', '__pycache__', 'dist', 'build', '.gemini']):
            continue
        
        py_files = [f for f in files if (f.startswith('test_') or f.endswith('_test.py')) and f.endswith('.py')]
        ts_files = [f for f in files if f.endswith('.test.ts') or f.endswith('.test.tsx') or f.endswith('.spec.ts') or f.endswith('.spec.tsx')]

        if not py_files and not ts_files:
            continue

        c_py = 0
        c_ts = 0

        for f in py_files:
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    matches = py_pattern.findall(content)
                    c_py += len(matches)
            except Exception:
                pass

        for f in ts_files:
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    matches = ts_pattern.findall(content)
                    c_ts += len(matches)
            except Exception:
                pass

        stats[root] = {'py_files': len(py_files), 'py_cases': c_py, 'ts_files': len(ts_files), 'ts_cases': c_ts}
        total_py_cases += c_py
        total_ts_cases += c_ts

    print("=== TEST CASE COUNT PER DIRECTORY ===")
    for d, s in sorted(stats.items()):
        print(f"{d} | Files: {s['py_files']} py, {s['ts_files']} ts | Cases: {s['py_cases']} py, {s['ts_cases']} ts")

    print(f"\nTOTAL ACROSS REPOSITORY: {total_py_cases} Python test cases, {total_ts_cases} TypeScript test cases = {total_py_cases + total_ts_cases} TOTAL TESTS")

if __name__ == '__main__':
    count_tests()
