"""Size ratchet for the backend (hardening plan, phase 5; reworked 2026-10-16).

Two rules, aimed at code that is hard to read and change rather than at line counts in general:

- Functions: a function may have at most FUNCTION_LIMIT lines. Functions already longer are recorded in
  loc_baseline.json and may only shrink.
- Files: a file may have at most FILE_LIMIT lines. Files already larger are recorded and may only shrink.
  Files under the limit may grow (a new check and the comment explaining it are not a problem).

The first version capped every file at its recorded size, so each round of fixes broke it while the code got
better, and CI stopped before running the tests.

Usage (from new/server):
    python scripts/loc_ratchet.py            # print the largest files and functions
    python scripts/loc_ratchet.py --check    # CI gate
    python scripts/loc_ratchet.py --write    # record current sizes (after a reduction)
"""
import ast
import json
import os
import sys

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(SERVER, "scripts", "loc_baseline.json")
WATCHED_DIRS = ("routes", "calculations", "services")
WATCHED_FILES = ("background_processor.py",)
FILE_LIMIT = 800
FUNCTION_LIMIT = 150


def _python_files(root):
    for sub in WATCHED_DIRS:
        for dirpath, _dirs, files in os.walk(os.path.join(root, sub)):
            if "__pycache__" in dirpath:
                continue
            for name in files:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)
    for name in WATCHED_FILES:
        path = os.path.join(root, name)
        if os.path.exists(path):
            yield path


def _functions(tree):
    """{qualified name: line count} of every function and method (nested ones included)."""
    out = {}

    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                if not isinstance(child, ast.ClassDef):
                    key, i = name, 2
                    while key in out:  # a name defined twice in one scope
                        key, i = f"{name}#{i}", i + 1
                    out[key] = child.end_lineno - child.lineno + 1
                visit(child, name + ".")
            else:
                visit(child, prefix)

    visit(tree, "")
    return out


def measure(root=SERVER):
    """(file sizes, function sizes) keyed by path relative to root ("path::Qual.name" for functions)."""
    files, functions = {}, {}
    for path in _python_files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        files[rel] = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for name, n in _functions(tree).items():
            functions[f"{rel}::{name}"] = n
    return dict(sorted(files.items())), dict(sorted(functions.items()))


def over_limits(files, functions):
    """The sizes the baseline records: only what is over a limit."""
    return ({p: n for p, n in files.items() if n > FILE_LIMIT},
            {f: n for f, n in functions.items() if n > FUNCTION_LIMIT})


def check(files, functions, base):
    """Problems (list of text) against the baseline {"files": {...}, "functions": {...}}."""
    problems = []
    for kind, sizes, limit in (("file", files, FILE_LIMIT), ("function", functions, FUNCTION_LIMIT)):
        recorded = base.get(kind + "s", {})
        for name, n in sizes.items():
            if n <= limit:
                continue
            if name not in recorded:
                problems.append(f"{name}: {kind} has {n} lines (limit {limit})")
            elif n > recorded[name]:
                problems.append(f"{name}: {kind} has {n} lines, recorded {recorded[name]} (may only shrink)")
    return problems


def shrunk(files, functions, base):
    cur = {"files": files, "functions": functions}
    return [name for kind in ("files", "functions") for name, n in base.get(kind, {}).items()
            if cur[kind].get(name, 0) < n]


def main(argv):
    files, functions = measure()
    if "--write" in argv:
        big_files, big_functions = over_limits(files, functions)
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"files": big_files, "functions": big_functions}, fh, indent=2)
            fh.write("\n")
        print(f"baseline written ({len(big_files)} files over {FILE_LIMIT} lines, "
              f"{len(big_functions)} functions over {FUNCTION_LIMIT} lines)")
        return 0
    if "--check" in argv:
        if not os.path.exists(BASELINE):
            print("No baseline. Run: python scripts/loc_ratchet.py --write", file=sys.stderr)
            return 2
        with open(BASELINE, encoding="utf-8") as fh:
            base = json.load(fh)
        problems = check(files, functions, base)
        if problems:
            print("Size ratchet failed:", *problems, sep="\n  ", file=sys.stderr)
            return 1
        smaller = shrunk(files, functions, base)
        note = f" ({len(smaller)} recorded item(s) smaller than recorded; run --write to lock it in)" if smaller else ""
        print("Sizes ok" + note)
        return 0
    print(f"Largest files (limit {FILE_LIMIT}):")
    for path, n in sorted(files.items(), key=lambda kv: -kv[1])[:15]:
        print(f"{n:6d}  {path}")
    print(f"Largest functions (limit {FUNCTION_LIMIT}):")
    for name, n in sorted(functions.items(), key=lambda kv: -kv[1])[:15]:
        print(f"{n:6d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
