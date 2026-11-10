import os
import ast

routes_dir = "new/server/routes"
results = []

for f in sorted(os.listdir(routes_dir)):
    if not f.endswith(".py") or f.startswith("__"):
        continue
    filepath = os.path.join(routes_dir, f)
    with open(filepath, "r", encoding="utf-8") as fp:
        try:
            tree = ast.parse(fp.read(), filename=f)
        except Exception as e:
            results.append((f, "PARSE_ERROR", str(e)))
            continue

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if this function is a route
            is_route = False
            decorators = []
            for dec in node.decorator_list:
                name = ""
                if isinstance(dec, ast.Name):
                    name = dec.id
                elif isinstance(dec, ast.Attribute):
                    name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        name = dec.func.id
                    elif isinstance(dec.func, ast.Attribute):
                        name = dec.func.attr
                decorators.append(name)
                if "route" in name or name in ("get", "post", "put", "delete", "patch"):
                    is_route = True

            if is_route:
                has_auth = any(d in ("login_required", "admin_required", "superuser_required", "auditor_required", "role_required", "token_required") for d in decorators)
                results.append((f, node.name, node.lineno, decorators, has_auth))

unprotected = [r for r in results if not r[4]]
print(f"Total routes analyzed: {len(results)}")
print(f"Routes with explicit auth decorators: {len(results) - len(unprotected)}")
print(f"Routes without auth decorators: {len(unprotected)}\n")

for r in unprotected:
    print(f"UNPROTECTED: {r[0]}:{r[2]} -> def {r[1]}() [decorators: {', '.join(r[3])}]")
