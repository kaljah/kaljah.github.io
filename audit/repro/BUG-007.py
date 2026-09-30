"""BUG-007 repro: manual POST accepts 1e13 MMBtu and auto-Verifies without qa_flag."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentB_r007"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
r=c.post("/api/emissions/", json={"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel":"Natural Gas","amount":1e13,"unit":"MMBtu"})
if r.status_code!=201: print("rejected (fixed)", r.status_code); sys.exit(0)
row=sql(DB,"select status,qa_flag,co2e_total from emissions where id=?",(r.get_json()["id"],))[0]
print("expected: rejected or qa_flag set & not Verified; actual:", row)
sys.exit(1 if row["status"]=="Verified" and not row["qa_flag"] else 0)
