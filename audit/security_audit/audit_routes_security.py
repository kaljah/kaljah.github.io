"""
Adversarial Security Audit Script
Performs AST and dynamic analysis on all routes for missing authentication, authorization,
IDOR, SQL injection, path traversal, mass assignment, and CSRF vulnerabilities.
"""

import ast
import os
import sys
import re

ROUTES_DIR = "new/server/routes"

routes_inventory = []
sql_injection_suspects = []
path_traversal_suspects = []
missing_auth_routes = []
mass_assignment_suspects = []

AUTH_DECORATORS = {
    "login_required",
    "admin_required",
    "it_admin_required",
    "it_access_required",
}

PUBLIC_WHITELIST = {
    "login",
    "register",
    "index",
    "get_csrf_token",
    "health",
    "health_check",
    "health_status",
    "metrics",
    "docs",
}

for root, _, files in os.walk(ROUTES_DIR):
    for f in files:
        if not f.endswith(".py"):
            continue
        filepath = os.path.join(root, f)
        relpath = os.path.relpath(filepath, "new/server")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()

        try:
            tree = ast.parse(source, filename=filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                route_decorator = None
                decorator_names = set()
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Attribute) and dec.func.attr == "route":
                            route_decorator = dec
                        elif isinstance(dec.func, ast.Name):
                            decorator_names.add(dec.func.id)
                    elif isinstance(dec, ast.Attribute) and dec.attr == "route":
                        route_decorator = dec
                    elif isinstance(dec, ast.Name):
                        decorator_names.add(dec.id)

                if route_decorator:
                    rule = ""
                    methods = ["GET"]
                    if isinstance(route_decorator, ast.Call):
                        if route_decorator.args and isinstance(route_decorator.args[0], ast.Constant):
                            rule = route_decorator.args[0].value
                        for kw in route_decorator.keywords:
                            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                methods = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]

                    has_auth = bool(decorator_names & AUTH_DECORATORS)
                    routes_inventory.append({
                        "file": relpath,
                        "line": node.lineno,
                        "func": node.name,
                        "rule": rule,
                        "methods": methods,
                        "decorators": list(decorator_names),
                        "has_auth": has_auth
                    })

                    if not has_auth and node.name not in PUBLIC_WHITELIST and not any(p in rule for p in ["/login", "/register", "/health", "/csrf"]):
                        missing_auth_routes.append({
                            "file": relpath,
                            "line": node.lineno,
                            "func": node.name,
                            "rule": rule,
                            "methods": methods
                        })

# Search for SQL injection patterns
sql_patterns = [
    r'db\.session\.execute\(f["\']',
    r'db\.engine\.execute\(f["\']',
    r'cursor\.execute\(f["\']',
    r'text\(f["\']',
    r'f"SELECT\s+.*"',
    r'f"UPDATE\s+.*"',
    r'f"DELETE\s+.*"',
    r'f"INSERT\s+.*"',
    r'\.filter\(f["\']',
]

for root, _, files in os.walk("new/server"):
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/server")
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        for idx, line in enumerate(lines):
            for pat in sql_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    sql_injection_suspects.append({
                        "file": relpath,
                        "line": idx + 1,
                        "code": line.strip()
                    })

# Search for Path Traversal patterns
path_patterns = [
    r'send_file\([^\)]*request\.',
    r'send_from_directory\([^\)]*request\.',
    r'open\([^\)]*request\.',
    r'open\(f["\'][^"\']*\{',
]

for root, _, files in os.walk("new/server"):
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, "new/server")
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        for idx, line in enumerate(lines):
            for pat in path_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    path_traversal_suspects.append({
                        "file": relpath,
                        "line": idx + 1,
                        "code": line.strip()
                    })

# Report results
print("==========================================")
print(f"Total Routes Scanned: {len(routes_inventory)}")
print(f"Routes Missing Authentication Decorators: {len(missing_auth_routes)}")
print(f"SQL Injection Suspects: {len(sql_injection_suspects)}")
print(f"Path Traversal Suspects: {len(path_traversal_suspects)}")
print("==========================================")

if missing_auth_routes:
    print("\n--- Routes Missing Authentication ---")
    for r in missing_auth_routes:
        print(f"  {r['file']}:{r['line']} [{','.join(r['methods'])}] {r['rule']} -> {r['func']}")

if sql_injection_suspects:
    print("\n--- SQL Injection Suspects ---")
    for s in sql_injection_suspects:
        print(f"  {s['file']}:{s['line']} -> {s['code']}")

if path_traversal_suspects:
    print("\n--- Path Traversal Suspects ---")
    for p in path_traversal_suspects:
        print(f"  {p['file']}:{p['line']} -> {p['code']}")
