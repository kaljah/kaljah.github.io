"""
Route Permissions & Authorization Auditor (Part 3.1)
===================================================
Scans all Flask routes across blueprints, inspects view decorators, role gates,
and produces docs/route_permissions.md.
"""
import sys
import os
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app

def audit_routes():
    rows = []
    
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, list(r.methods)[0])):
        methods = [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
        if not methods:
            continue
        methods_str = ", ".join(sorted(methods))
        endpoint = rule.endpoint
        url = rule.rule
        
        view_func = app.view_functions.get(endpoint)
        if not view_func:
            continue
            
        doc = (view_func.__doc__ or "").strip().split("\n")[0]
        
        # Analyze source code for role checks and decorators
        try:
            source = inspect.getsource(view_func)
        except Exception:
            source = ""
            
        is_public = False
        required_role = "Authenticated User"
        idor_protection = "N/A"
        
        # Check authentication / role
        if "login_required" not in source and "get_current_user" not in source and "current_user" not in source:
            if url.startswith("/static") or url.startswith("/api/auth/login") or url == "/" or url == "/health":
                is_public = True
                required_role = "Public"
            elif "login" in url or "logout" in url or "check-auth" in url or "ping" in url:
                is_public = True
                required_role = "Public"
        
        if "admin_required" in source or 'role == "admin"' in source or "role in ['admin'" in source or 'role != "admin"' in source:
            required_role = "Admin"
        elif "it_admin" in source or "it_manager" in source:
            if "admin_required" in source:
                required_role = "Admin / IT Manager"
            else:
                required_role = "IT Manager / Admin"
        elif "super_user_required" in source or "superuser" in source:
            required_role = "Admin / Superuser"
        elif "auditor" in source:
            required_role = "Auditor (Read-Only) / Admin"
            
        # Check IDOR protection
        has_id_param = any(p in url for p in ("<id>", "<int:", "<record_id>", "<facility_id>", "<facilityId>", "<str:"))
        if has_id_param:
            if "get_allowed_facility_ids" in source or "facility_access_error" in source or "_org_factor_denied" in source or "tenant_id" in source or "user.id" in source:
                idor_protection = "Protected (Scoped by Facility/Org/Tenant)"
            elif required_role in ("Admin", "IT Manager / Admin"):
                idor_protection = "Protected (Admin Only)"
            else:
                idor_protection = "Review Required / Scoped"
                
        rows.append({
            "url": url,
            "methods": methods_str,
            "endpoint": endpoint,
            "required_role": required_role,
            "idor_protection": idor_protection,
            "description": doc or endpoint,
        })
        
    # Write markdown
    md_lines = [
        "# NeoCarbon API Route Permissions & Authorization Matrix",
        "",
        "| HTTP Method | Route URL | Endpoint | Required Role | IDOR / Tenant Scoping | Description |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in rows:
        md_lines.append(f"| `{r['methods']}` | `{r['url']}` | `{r['endpoint']}` | **{r['required_role']}** | {r['idor_protection']} | {r['description'][:60]} |")
        
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../docs/route_permissions.md"))
    os.makedirs(os.path.dirname(doc_path), exist_ok=True)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
        
    print(f"Generated {doc_path} with {len(rows)} audited routes.")

if __name__ == "__main__":
    audit_routes()
