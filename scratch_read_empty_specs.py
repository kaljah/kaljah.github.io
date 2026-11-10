files = [
    'new/client/e2e/pages-smoke.spec.js',
    'new/client/e2e/responsive.spec.js',
    'new/client/e2e/visual-baseline.spec.js'
]
for f in files:
    print(f"=== {f} ===")
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        print(fp.read()[:500])
