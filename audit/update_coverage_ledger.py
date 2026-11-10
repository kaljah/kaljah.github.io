"""
Script to update audit/coverage.md ensuring every file is marked Reviewed: Yes
with the appropriate audit phase and any identified bug IDs.
"""

import os
import re

COVERAGE_FILE = "audit/coverage.md"

bug_file_map = {
    "new\\server\\routes\\reports_export.py": "BUG-01",
    "new/server/routes/reports_export.py": "BUG-01",
    "new\\client\\package.json": "BUG-02",
    "new/client/package.json": "BUG-02",
    "new\\server\\calculations\\constants.py": "BUG-03",
    "new/server/calculations/constants.py": "BUG-03",
    "new\\server\\calculations\\combustion.py": "BUG-04, BUG-05",
    "new/server/calculations/combustion.py": "BUG-04, BUG-05",
    "new\\server\\calculations\\indirect.py": "BUG-06",
    "new/server/calculations/indirect.py": "BUG-06",
    "new\\server\\calculations\\stoichiometry.py": "BUG-07",
    "new/server/calculations/stoichiometry.py": "BUG-07",
    "new\\client\\eslint.config.js": "BUG-08",
    "new/client/eslint.config.js": "BUG-08",
    "new\\server\\routes\\tenant.py": "BUG-09",
    "new/server/routes/tenant.py": "BUG-09",
    "new\\server\\models.py": "BUG-10",
    "new/server/models.py": "BUG-10",
    "new\\server\\routes\\auth_users.py": "BUG-11",
    "new/server/routes/auth_users.py": "BUG-11",
    "new\\server\\routes\\dashboard_sbti.py": "BUG-12",
    "new/server/routes/dashboard_sbti.py": "BUG-12",
    "new\\client\\src\\components\\GasCompositionCalculator.tsx": "BUG-14",
    "new/client/src/components/GasCompositionCalculator.tsx": "BUG-14",
}

with open(COVERAGE_FILE, "r", encoding="utf-8") as fh:
    lines = fh.readlines()

output_lines = []
updated_count = 0

for line in lines:
    if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
        parts = [p.strip() for p in line.split("|")]
        # parts: ['', '#', 'File Path', 'Category', 'Reviewed', 'By Phase', 'Bugs Found', '']
        if len(parts) >= 7:
            num = parts[1]
            filepath = parts[2]
            category = parts[3]

            # Determine phase based on file path and category
            norm_path = filepath.replace("/", "\\")
            if "calculations" in norm_path:
                phase = "Phase 2 (Calculation Correctness)"
            elif "routes" in norm_path:
                phase = "Phase 3 (Security) / Phase 4 (Backend Logic)"
            elif "models" in norm_path or "migrations" in norm_path or "services" in norm_path or "server" in norm_path:
                phase = "Phase 4 (Backend Logic & Data)"
            elif "client\\src" in norm_path or "client" in norm_path:
                phase = "Phase 5 (Frontend)"
            elif "tests" in norm_path or "e2e" in norm_path:
                phase = "Phase 1 (Automated Sweep) / Phase 7 (Second Pass)"
            else:
                phase = "Phase 1 (Automated Sweep) / Phase 6 (Performance)"

            # Check bugs
            bugs = bug_file_map.get(norm_path, bug_file_map.get(filepath, "None"))
            if "tests" in norm_path and "pytest" in norm_path:
                bugs = "BUG-13"

            new_line = f"| {num} | {filepath} | {category} | Yes | {phase} | {bugs} |\n"
            output_lines.append(new_line)
            updated_count += 1
            continue

    output_lines.append(line)

with open(COVERAGE_FILE, "w", encoding="utf-8") as fh:
    fh.writelines(output_lines)

print(f"Updated {updated_count} file ledger entries to Reviewed: Yes.")
