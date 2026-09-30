import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
st = c.get("/api/dashboard/intensity-stats?year=all").get_json()
tot = {k: sum(x[k] for x in st) for k in ("ch4_venting","ch4_fugitive","ch4_flaring","ch4_combustion","total_ch4")}
print("API:", tot)
rows = sql("agentD","select process_type, sum(ch4_emissions) ch4 from emissions where status='Verified' group by process_type")
cat = {"vent":0,"fug":0,"flare":0,"comb":0,"other_methane":0}
for r in rows:
    p=(r["process_type"] or "").lower(); v=r["ch4"] or 0
    if "flar" in p: cat["flare"]+=v
    elif "combust" in p or p in("fuel_gas","mobile"): cat["comb"]+=v
    elif "fugitive" in p or "leak" in p: cat["fug"]+=v
    elif p in ("venting","vent","pneumatic","tank_flashing","tank_working","tank_breathing","unloading","completions","blowdown","dehydrator","agr","drilling","loading"): cat["vent"]+=v
    else: cat["other_methane"]+=v; print("  unclassified", p, v)
print("expected:", cat)
