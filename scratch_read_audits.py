import os

docs = [
    'docs/validation/03-security-audit.md',
    'docs/validation/04-database-audit.md',
    'docs/validation/05-performance-audit.md',
    'docs/validation/06-accessibility-audit.md',
    'docs/validation/07-browser-audit.md',
    'docs/validation/FULL_AUDIT_2026-10-01.md',
    'docs/validation/SCOPE1_100K_BULK_AUDIT_2026-10-01.md'
]

for doc in docs:
    if os.path.exists(doc):
        with open(doc, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            header = lines[:5]
            print(f"=== {doc} ===")
            print("\n".join(header))
            print(f"Total lines: {len(lines)}\n")
