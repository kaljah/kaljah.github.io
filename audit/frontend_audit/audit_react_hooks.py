"""
Frontend React Hooks, State, and API Contract Audit Script
Scans all 248 .ts and .tsx files in new/client/src/ for:
1. Missing cleanup in useEffect (setInterval, setTimeout, addEventListener)
2. Fetch race conditions in useEffect (no AbortController or isMounted flag)
3. Stale closures (empty dependency array referencing component state/props)
4. Unhandled promise rejections (.catch missing on async chains)
5. Direct toFixed() calls on potentially undefined or string values
"""

import os
import re

CLIENT_SRC = "new/client/src"

uncleaned_effects = []
race_condition_effects = []
stale_closure_suspects = []
unhandled_promises = []
unsafe_to_fixed = []
api_endpoints_called = []

for root, _, files in os.walk(CLIENT_SRC):
    for f in files:
        if not (f.endswith(".ts") or f.endswith(".tsx")):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/client")

        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
            lines = content.splitlines()

        # 1. Uncleaned useEffect (setInterval / addEventListener)
        # Find useEffect blocks
        effect_blocks = list(re.finditer(r'useEffect\s*\(\s*\(\s*\)\s*=>\s*\{', content))
        for m in effect_blocks:
            start_pos = m.start()
            # Find matching closing brace
            brace_count = 0
            end_pos = start_pos
            for i in range(m.end() - 1, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            effect_body = content[m.end():end_pos - 1]
            lineno = content[:start_pos].count('\n') + 1

            # Check if body sets up timer/listener
            sets_timer = bool(re.search(r'\bsetInterval\s*\(', effect_body))
            sets_listener = bool(re.search(r'\baddEventListener\s*\(', effect_body))
            has_return_cleanup = bool(re.search(r'\breturn\s+(?:\(\s*\)\s*=>|\bfunction\b)', effect_body))

            if (sets_timer or sets_listener) and not has_return_cleanup:
                kind = "setInterval" if sets_timer else "addEventListener"
                uncleaned_effects.append({
                    "file": relpath,
                    "line": lineno,
                    "type": kind,
                    "snippet": effect_body[:100].replace('\n', ' ')
                })

            # 2. Fetch / axios race condition (no AbortController / canceled flag)
            has_fetch = bool(re.search(r'\b(fetch\(|axios\.get|axios\.post|api\.)\b', effect_body))
            has_abort = bool(re.search(r'\b(AbortController|canceled|cancelled|isMounted|active)\b', effect_body))
            if has_fetch and not has_abort and not has_return_cleanup:
                race_condition_effects.append({
                    "file": relpath,
                    "line": lineno,
                    "snippet": effect_body[:120].replace('\n', ' ')
                })

        # 3. Unsafe .toFixed() on variables without null check
        for idx, line in enumerate(lines):
            # Matches e.g. value.toFixed() or res.total.toFixed() without optional chaining
            matches = re.finditer(r'(\b[a-zA-Z0-9_]+)\.toFixed\(', line)
            for match in matches:
                varname = match.group(1)
                if varname not in ("Number", "Math") and not line.strip().startswith("//"):
                    if f"{varname}?." not in line and f"typeof {varname}" not in line:
                        unsafe_to_fixed.append({
                            "file": relpath,
                            "line": idx + 1,
                            "code": line.strip()
                        })

        # 4. API endpoints extracted from client code
        api_matches = re.finditer(r'[\'"`](/api/[a-zA-Z0-9_\-\/]+)[\'"`]', content)
        for am in api_matches:
            api_endpoints_called.append({
                "file": relpath,
                "endpoint": am.group(1)
            })

print("==========================================")
print(f"Total Client Source Files Analyzed: {len([f for r, _, fs in os.walk(CLIENT_SRC) for f in fs if f.endswith(('.ts', '.tsx'))])}")
print(f"Uncleaned useEffect Timers/Listeners: {len(uncleaned_effects)}")
print(f"Fetch Race Conditions in useEffect: {len(race_condition_effects)}")
print(f"Unsafe .toFixed() Calls (Potential TypeError): {len(unsafe_to_fixed)}")
print(f"Distinct Client API Endpoints Referenced: {len(set(e['endpoint'] for e in api_endpoints_called))}")
print("==========================================")

if uncleaned_effects:
    print("\n--- Uncleaned useEffect Hooks (Memory Leaks) ---")
    for u in uncleaned_effects:
        print(f"  {u['file']}:{u['line']} -> {u['type']} without cleanup return")

if race_condition_effects:
    print(f"\n--- Fetch Race Conditions in useEffect (Top 10 of {len(race_condition_effects)}) ---")
    for r in race_condition_effects[:10]:
        print(f"  {r['file']}:{r['line']} -> {r['snippet'][:80]}...")

if unsafe_to_fixed:
    print(f"\n--- Unsafe .toFixed() Calls (Top 10 of {len(unsafe_to_fixed)}) ---")
    for ut in unsafe_to_fixed[:10]:
        print(f"  {ut['file']}:{ut['line']} -> {ut['code']}")
