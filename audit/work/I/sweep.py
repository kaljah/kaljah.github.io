import sys, json, re
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, get_app, api_client
DB="agentI_sweep"; make_db(DB, overwrite=True)
app = get_app(DB)
clients = {"anon": app.test_client()}
for r in ["user","superuser","admin","it_admin"]: clients[r]=api_client(DB, r)
subs = {"<int:emission_id>":"1","<int:id>":"1","<id>":"1","<int:facility_id>":"3","<int:record_id>":"1","<int:rec_id>":"1","<int:year>":"2024",
 "<int:factor_id>":"1","<string:mitigation_id>":"1","<int:source_id>":"1","<job_id>":"x","<process_category>":"combustion","<segment>":"production"}
mode = sys.argv[1]
out=[]
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    p=str(rule)
    if not p.startswith("/api") or "docs" in p or "stream" in p: continue
    for k,v in subs.items(): p=p.replace(k,v)
    meths=[m for m in rule.methods if m not in ("HEAD","OPTIONS")]
    for m in meths:
        if mode=="get" and m!="GET": continue
        if mode=="anonw" and m=="GET": continue
        roles = ["anon","it_admin","user","superuser"] if mode=="get" else ["anon"]
        row=[m,p]
        for role in roles:
            c=clients[role]
            try:
                r = c.open(p, method=m, json={} if m!="GET" else None)
                body = r.get_data(as_text=True)
                row.append(f"{role}:{r.status_code}:{len(body)}")
            except Exception as e:
                row.append(f"{role}:EXC:{type(e).__name__}")
        out.append(" | ".join(row))
print("\n".join(out))
