import os
import glob

dirs = {}
for root, _, files in os.walk('.'):
    if any(p in root for p in ['node_modules', '.venv', '.git', '__pycache__', 'dist', 'build', '.gemini']):
        continue
    py_tests = [f for f in files if (f.startswith('test_') or f.endswith('_test.py')) and f.endswith('.py')]
    ts_tests = [f for f in files if f.endswith('.test.ts') or f.endswith('.test.tsx') or f.endswith('.spec.ts') or f.endswith('.spec.tsx')]
    if py_tests or ts_tests:
        dirs[root] = {'py': len(py_tests), 'ts': len(ts_tests), 'py_files': py_tests, 'ts_files': ts_tests}

print("=== TEST DIRECTORY INVENTORY ===")
total_py = 0
total_ts = 0
for d, info in sorted(dirs.items()):
    print(f"{d}: {info['py']} py files, {info['ts']} ts files")
    total_py += info['py']
    total_ts += info['ts']

print(f"\nTotal test files: {total_py} Python, {total_ts} TypeScript/TSX (Total: {total_py + total_ts})")
