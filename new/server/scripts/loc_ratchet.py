"""Module-size ratchet for the backend (hardening plan, phase 5).

Existing files may not grow past the line count recorded in loc_baseline.json; files not in
the baseline must stay under NEW_FILE_LIMIT lines. Shrinking a file never fails, and
--write lowers the baseline to the current sizes.

Usage (from new/server):
    python scripts/loc_ratchet.py            # print current sizes of the largest files
    python scripts/loc_ratchet.py --check    # CI gate
    python scripts/loc_ratchet.py --write    # record current sizes (only after a reduction)
"""
import json
import os
import sys

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(SERVER, "scripts", "loc_baseline.json")
WATCHED = ("routes", "calculations", "services")
NEW_FILE_LIMIT = 800


def measure():
    sizes = {}
    for sub in WATCHED:
        root = os.path.join(SERVER, sub)
        for dirpath, _dirs, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        n = sum(1 for _ in fh)
                    sizes[os.path.relpath(path, SERVER).replace(os.sep, "/")] = n
    return dict(sorted(sizes.items()))


def main(argv):
    sizes = measure()
    if "--write" in argv:
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(sizes, fh, indent=2)
            fh.write("\n")
        print(f"baseline written ({len(sizes)} files)")
        return 0
    if "--check" in argv:
        if not os.path.exists(BASELINE):
            print("No baseline. Run: python scripts/loc_ratchet.py --write", file=sys.stderr)
            return 2
        with open(BASELINE, encoding="utf-8") as fh:
            base = json.load(fh)
        problems = []
        for path, n in sizes.items():
            if path in base:
                if n > base[path]:
                    problems.append(f"{path}: {n} lines, baseline {base[path]} (files may only shrink)")
            elif n > NEW_FILE_LIMIT:
                problems.append(f"{path}: new file with {n} lines (limit {NEW_FILE_LIMIT})")
        if problems:
            print("Module size ratchet failed:", *problems, sep="\n  ", file=sys.stderr)
            return 1
        shrunk = [p for p, n in sizes.items() if p in base and n < base[p]]
        note = f" ({len(shrunk)} file(s) smaller than baseline; run --write to lock it in)" if shrunk else ""
        print("Module sizes ok" + note)
        return 0
    for path, n in sorted(sizes.items(), key=lambda kv: -kv[1])[:15]:
        print(f"{n:6d}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
