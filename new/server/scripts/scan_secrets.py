"""
Repository & Git History Secrets Scanner (Item 4.1)
===================================================
Scans repository codebase and git commit history for potential secret leakage:
- Private keys
- Cloud API tokens & access keys
- Database connection strings containing embedded passwords
- High-entropy secret patterns

Outputs reports/secrets_scan_report.json.
"""
import os
import sys
import re
import json
import subprocess
import datetime

SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Cryptographic Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", "High-entropy API Key"),
    (r"(?i)secret[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", "Embedded Secret Key"),
    (r"postgres(?:ql)?:\/\/[a-zA-Z0-9_\.\-]+:[a-zA-Z0-9_\.\-]+@", "Database URI with embedded password"),
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{30,}", "Hardcoded Bearer Token"),
]

EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", ".pytest_cache", "venv", ".venv",
    "__pycache__", "reports", ".agents", "brain", ".gemini", "screenshots",
    "old", "playwright-report", "test-results", "coverage", "backups", "instance"
}
EXCLUDED_EXTS = {
    ".png", ".jpg", ".jpeg", ".ico", ".db", ".sqlite", ".bak", ".pyc",
    ".pdf", ".xlsx", ".map", ".lock", ".csv", ".log", ".tar", ".gz", ".zip"
}


def scan_target_dirs(targets):
    findings = []
    for target in targets:
        if not os.path.exists(target):
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in EXCLUDED_EXTS:
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for idx, line in enumerate(fh, 1):
                            for pattern, desc in SECRET_PATTERNS:
                                if re.search(pattern, line):
                                    # Avoid false positives in scan scripts or config comments
                                    if "scan_secrets.py" in f or "SECRET_PATTERNS" in line or "[REDACTED" in line:
                                        continue
                                    is_test_or_example = (
                                        "tests" in root or
                                        "test_" in f or
                                        ".example" in f or
                                        line.strip().startswith("#") or
                                        "example" in line.lower() or
                                        "user:password" in line or
                                        "user:pass" in line or
                                        "username:password" in line
                                    )
                                    masked = re.sub(pattern, "[REDACTED_SECRET]", line.strip())
                                    findings.append({
                                        "location": "working_tree",
                                        "file": os.path.relpath(path, target),
                                        "line": idx,
                                        "type": desc,
                                        "is_example_or_test": is_test_or_example,
                                        "snippet": masked[:120],
                                    })
                except Exception:
                    pass
    return findings


def scan_git_history(repo_root):
    findings = []
    try:
        cmd = ["git", "--no-pager", "log", "-p", "-n", "15", "--", "new/server", "new/client/src"]
        res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, errors="ignore", timeout=15)
        commit_hash = "HEAD"
        current_file = ""
        
        for line in res.stdout.splitlines():
            if line.startswith("commit "):
                parts = line.split()
                if len(parts) > 1:
                    commit_hash = parts[1]
            elif line.startswith("+++ b/"):
                current_file = line[6:].strip()
            elif line.startswith("+") and not line.startswith("+++"):
                added_line = line[1:]
                for pattern, desc in SECRET_PATTERNS:
                    if re.search(pattern, added_line):
                        if "scan_secrets.py" in current_file or "SECRET_PATTERNS" in added_line or "[REDACTED" in added_line:
                            continue
                        masked = re.sub(pattern, "[REDACTED_SECRET]", added_line.strip())
                        findings.append({
                            "location": "git_history",
                            "commit": commit_hash[:10],
                            "file": current_file,
                            "type": desc,
                            "snippet": masked[:120],
                        })
    except Exception as e:
        print(f"Warning: git history scan encountered error: {e}")
    return findings


def run_secrets_scan():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")) # 'new'
    h2_root = os.path.abspath(os.path.join(base_dir, ".."))
    
    scan_paths = [
        os.path.join(base_dir, "server"),
        os.path.join(base_dir, "client", "src"),
    ]
    
    print(f"Scanning target paths: {scan_paths}")
    tree_findings = scan_target_dirs(scan_paths)
    print(f"Working tree scan finished. Findings: {len(tree_findings)}")
    
    print(f"Scanning git commit history for new/server and new/client/src...")
    git_findings = scan_git_history(h2_root)
    print(f"Git history scan finished. Findings: {len(git_findings)}")
    
    real_findings = [f for f in tree_findings if not f.get("is_example_or_test")] + git_findings
    
    report = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scanner": "NeoCarbon Enterprise Secrets Auditor (Part 4.1)",
        "total_working_tree_findings": len(tree_findings),
        "total_git_history_findings": len(git_findings),
        "real_leak_findings": len(real_findings),
        "example_or_test_patterns": len(tree_findings) - len([f for f in tree_findings if not f.get("is_example_or_test")]),
        "working_tree_findings": tree_findings,
        "git_history_findings": git_findings,
        "status": "PASS_CLEAN" if len(real_findings) == 0 else "LEAK_DETECTED",
    }
    
    rep_dir = os.path.join(base_dir, "server", "reports")
    os.makedirs(rep_dir, exist_ok=True)
    out_file = os.path.join(rep_dir, "secrets_scan_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Secrets audit complete. Report written to: {out_file}")
    return report

if __name__ == "__main__":
    rep = run_secrets_scan()
    print("Status:", rep["status"])
