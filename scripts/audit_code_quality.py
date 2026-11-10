import os
import re

server_dir = "new/server"
client_dir = "new/client/src"

files_over_800 = []
funcs_over_50 = []
todos_fixmes = []
console_logs = []

# Scan server
for root, _, files in os.walk(server_dir):
    if "tests" in root or "__pycache__" in root:
        continue
    for f in files:
        if f.endswith(".py"):
            filepath = os.path.join(root, f)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()
                if len(lines) > 800:
                    files_over_800.append((filepath, len(lines)))
                for idx, line in enumerate(lines):
                    if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE):
                        todos_fixmes.append((filepath, idx + 1, line.strip()))

# Scan client
for root, _, files in os.walk(client_dir):
    if "__tests__" in root or "test" in f.lower():
        continue
    for f in files:
        if f.endswith((".ts", ".tsx", ".js", ".jsx")):
            filepath = os.path.join(root, f)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()
                if len(lines) > 800:
                    files_over_800.append((filepath, len(lines)))
                for idx, line in enumerate(lines):
                    if "console.log" in line:
                        console_logs.append((filepath, idx + 1, line.strip()))
                    if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE):
                        todos_fixmes.append((filepath, idx + 1, line.strip()))

print(f"=== Files > 800 Lines ({len(files_over_800)}) ===")
for p, l in sorted(files_over_800, key=lambda x: -x[1])[:20]:
    print(f"  {p}: {l} lines")

print(f"\n=== console.log Statements in Client Source ({len(console_logs)}) ===")
for p, l, text in console_logs[:15]:
    print(f"  {p}:{l} -> {text[:80]}")

print(f"\n=== TODO / FIXME Comments ({len(todos_fixmes)}) ===")
for p, l, text in todos_fixmes[:20]:
    print(f"  {p}:{l} -> {text[:80]}")
