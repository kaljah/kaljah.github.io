import sys, inspect, re
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import get_app
app = get_app("agentI")
rows=[]
for rule in app.url_map.iter_rules():
    if rule.endpoint=='static' or 'swagger' in rule.endpoint: continue
    fn = app.view_functions[rule.endpoint]
    base = inspect.unwrap(fn)
    try:
        src, ln = inspect.getsourcelines(base)
        fname = inspect.getsourcefile(base).split("server")[-1]
    except Exception:
        src, ln, fname = [], 0, '?'
    # decorators: read lines above def from the file
    try:
        lines = open(inspect.getsourcefile(base), encoding='utf-8').read().splitlines()
        i = ln-2; decs=[]
        # find def line index
        body=''.join(src)
        j = ln-1
        while j>=0 and not lines[j].lstrip().startswith('def '): j+=1
        k=j-1
        while k>=0 and lines[k].strip().startswith('@'):
            decs.append(lines[k].strip()); k-=1
    except Exception as e:
        decs=['?']; body=''
    auth = [d for d in decs if 'required' in d]
    scope = []
    for kw in ['get_allowed_facility_ids','require_facility_access','_scope','allowed_ids','allowed_facility']:
        if kw in body: scope.append(kw)
    methods = ','.join(sorted(m for m in rule.methods if m not in ('HEAD','OPTIONS')))
    rows.append((str(rule), methods, ' '.join(a.replace('@','') for a in auth) or 'NONE', ','.join(scope) or '-', f"{fname}:{ln}", 'role' if re.search(r"role\s*(==|!=|in|not in)", body) else ''))
rows.sort()
print("| path | methods | auth decorator | facility scope | inline role check | src |")
print("|---|---|---|---|---|---|")
for r in rows: print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[5]} | {r[4]} |")
print(len(rows), file=sys.stderr)
