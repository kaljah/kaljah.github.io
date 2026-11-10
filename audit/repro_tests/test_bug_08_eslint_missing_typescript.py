"""
Verification of Remediation: BUG-08 / AS-03
new/client/eslint.config.js targets TypeScript files (*.ts, *.tsx) alongside JavaScript files.
"""

import os
import re

def test_eslint_config_includes_typescript():
    config_path = "new/client/eslint.config.js"
    assert os.path.exists(config_path), "eslint.config.js not found"

    with open(config_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Find all file pattern lists in config
    file_patterns = re.findall(r"files:\s*\[(.*?)\]", content, re.DOTALL)
    combined_patterns = " ".join(file_patterns)

    print("Configured ESLint file patterns:", combined_patterns)

    has_ts = any(".ts" in pat or "ts}" in pat or "tsx" in pat for pat in file_patterns)
    assert has_ts, "ESLint config must include TypeScript patterns (*.ts, *.tsx)"
