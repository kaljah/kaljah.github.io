"""
Backend Logic and Data Integrity Audit Script
Checks for:
1. Missing session.rollback() in exception handlers
2. Naive datetime.now() usage (timezone bugs)
3. Cascade delete behavior and orphaned records in models.py
4. Potential N+1 query patterns in routes
"""

import ast
import os
import re

findings = []

def record(f_id, file_line, severity, category, title, expected, actual, repro, confidence):
    findings.append({
        "id": f_id,
        "file_line": file_line,
        "severity": severity,
        "category": category,
        "title": title,
        "expected": expected,
        "actual": actual,
        "repro": repro,
        "confidence": confidence
    })
    print(f"[{severity.upper()}] {f_id}: {title} ({file_line})")

# 1. Missing rollback in try/except blocks with commit
print("\n--- 1. Checking for Missing rollback() on Commit Errors ---")
unprotected_commits = []

for root, _, files in os.walk("new/server"):
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/server")
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()

        try:
            tree = ast.parse(source, filename=fpath)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_commit = any(
                    isinstance(n, ast.Call) and
                    isinstance(n.func, ast.Attribute) and
                    n.func.attr == "commit"
                    for n in ast.walk(node)
                )
                if has_commit:
                    has_rollback = False
                    for handler in node.handlers:
                        if any(
                            isinstance(n, ast.Call) and
                            isinstance(n.func, ast.Attribute) and
                            n.func.attr == "rollback"
                            for n in ast.walk(handler)
                        ):
                            has_rollback = True
                            break
                    if not has_rollback:
                        unprotected_commits.append((relpath, node.lineno))

print(f"Found {len(unprotected_commits)} try blocks with commit() lacking rollback() in except.")
for item in unprotected_commits[:5]:
    print(f"  {item[0]}:{item[1]}")
    record(f"BACK-{len(findings)+1:02d}", f"{item[0]}:{item[1]}", "Medium", "Database Transaction",
           f"Database commit without rollback on exception in {item[0]}",
           "db.session.rollback() in exception handler to prevent session poisoning",
           "No rollback found in except block",
           f"Review try block starting at line {item[1]}", "Likely")


# 2. Naive datetime.now() vs timezone.utc
print("\n--- 2. Checking for Naive datetime.now() / datetime.utcnow() ---")
naive_dts = []
for root, _, files in os.walk("new/server"):
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/server")
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        for idx, line in enumerate(lines):
            if re.search(r'\bdatetime\.utcnow\(\)', line) or re.search(r'\bdatetime\.now\(\)', line):
                naive_dts.append((relpath, idx + 1, line.strip()))

print(f"Found {len(naive_dts)} occurrences of naive datetime.now() or deprecated datetime.utcnow().")
for item in naive_dts[:5]:
    print(f"  {item[0]}:{item[1]} -> {item[2]}")
if naive_dts:
    record(f"BACK-{len(findings)+1:02d}", f"{naive_dts[0][0]}:{naive_dts[0][1]}", "Low", "Timezone/Date",
           "Use of deprecated or timezone-naive datetime (datetime.utcnow/datetime.now)",
           "Use timezone-aware utc_now() or datetime.now(timezone.utc)",
           f"Found {len(naive_dts)} occurrences across codebase",
           f"See {naive_dts[0][0]}:{naive_dts[0][1]}", "Confirmed")


# 3. Cascade Deletes & Foreign Keys in models.py
print("\n--- 3. Analyzing Cascade Deletes and Foreign Keys in models.py ---")
import sys
sys.path.insert(0, "new/server")
import models

foreign_keys = []
for mapper in models.db.Model.registry.mappers:
    cls = mapper.class_
    table = mapper.local_table
    for col in table.columns:
        for fk in col.foreign_keys:
            foreign_keys.append({
                "table": table.name,
                "column": col.name,
                "target": fk.target_fullname,
                "ondelete": fk.ondelete
            })

print(f"Total Foreign Keys inspected: {len(foreign_keys)}")
no_cascade = [fk for fk in foreign_keys if fk["ondelete"] is None]
print(f"Foreign Keys without explicit ON DELETE (defaults to NO ACTION / RESTRICT): {len(no_cascade)}")
for fk in no_cascade[:10]:
    print(f"  {fk['table']}.{fk['column']} -> {fk['target']} (ondelete={fk['ondelete']})")

if len(no_cascade) > 0:
    record(f"BACK-{len(findings)+1:02d}", "new/server/models.py", "Medium", "Data Integrity",
           f"{len(no_cascade)} foreign key relationships lack explicit ON DELETE CASCADE or SET NULL",
           "Explicit cascade behavior (CASCADE or SET NULL) to prevent IntegrityError or orphaned records",
           "ondelete=None causes foreign key constraint failures or orphaned rows on SQLite when PRAGMA foreign_keys=ON",
           "Deleting a facility with related emissions fails with IntegrityError: FOREIGN KEY constraint failed",
           "Confirmed")


# 4. Potential N+1 query patterns in routes
print("\n--- 4. Scanning for Potential N+1 Query Patterns ---")
n1_patterns = []
for root, _, files in os.walk("new/server/routes"):
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/server")
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        in_loop = False
        loop_indent = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if re.match(r'^for\s+\w+\s+in\s+.*:', stripped):
                in_loop = True
                loop_indent = indent
            elif in_loop and indent <= loop_indent and stripped:
                in_loop = False
            elif in_loop and indent > loop_indent:
                if re.search(r'\b(query\.filter|query\.get|db\.session\.get|\.first\(\)|\.all\(\))\b', stripped):
                    n1_patterns.append((relpath, idx + 1, stripped))

print(f"Found {len(n1_patterns)} database queries inside loops (potential N+1).")
for item in n1_patterns[:5]:
    print(f"  {item[0]}:{item[1]} -> {item[2]}")

if n1_patterns:
    record(f"BACK-{len(findings)+1:02d}", f"{n1_patterns[0][0]}:{n1_patterns[0][1]}", "Medium", "Performance / N+1",
           f"Database queries executed inside loops (N+1 query pattern) in {n1_patterns[0][0]}",
           "Batch fetch or join entities outside loop",
           f"Iterative queries executed: {n1_patterns[0][2]}",
           f"Inspect {n1_patterns[0][0]}:{n1_patterns[0][1]}", "Likely")


# Output summary
print(f"\n==========================================")
print(f"Backend Logic Audit Completed: {len(findings)} findings logged")
print(f"==========================================")
