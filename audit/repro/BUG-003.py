"""BUG-003 repro: PUT quantity does not recalc emissions. Uses db agentB_r003."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentB_r003"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
p={"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,
   "fuel":"Natural Gas","fuel_type":"Natural Gas","amount":1000,"quantity":1000,"unit":"MMBtu"}
i=c.post("/api/emissions/", json=p).get_json()["id"]
c.put(f"/api/emissions/{i}", json={"quantity":2000})
row=sql(DB,"select quantity,co2e_total from emissions where id=?",(i,))[0]
expected=2000*53.06/1000 + 2000*0.001/1000*28 + 2000*0.0001/1000*265
print(f"quantity={row['quantity']} expected co2e={expected:.4f} actual={row['co2e_total']:.4f}")
sys.exit(1 if abs(row['co2e_total']-expected)>0.01 else 0)
