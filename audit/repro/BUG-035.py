"""flaring-summary unit conversion: 'mmscf' falls into the 'mscf' branch (1000x under) and the prior-year
path treats 'mscf'/'mmscf' as m3. Inserts two synthetic Verified flaring rows into its own db copy (repro_F3).
Exits 1 while the bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, db_path
make_db("repro_F3", overwrite=True)
con = sqlite3.connect(db_path("repro_F3"))
# Year 2031 (current) : 1 MMscf routine flaring ; year 2030 (prior) : 1 MMscf routine flaring. No other flaring in those years.
for yr in (2030, 2031):
    con.execute("insert into emissions (record_id,year,month,process_type,quantity,unit,co2e_total,co2_emissions,ch4_emissions,n2o_emissions,status,facility_id)"
                " values (?,?,1,'routine_flaring',1.0,'mmscf',60.0,59.0,0.03,0.0001,'Verified',169)", (f"auditF3-{yr}", yr))
con.commit(); con.close()
c = api_client("repro_F3", "admin")
f = c.get("/api/dashboard/flaring-summary?year=2031&facilityId=169").get_json()
M3_PER_MMSCF = 1e6 * 0.028316846592          # 1 MMscf = 28,316.8 m3 (exact ft3->m3)
print(f"1 MMscf routine flaring -> expected {M3_PER_MMSCF:.1f} m3 ; API routine volume_m3 = {f['routine_flaring']['volume_m3']}")
print(f"YoY 2031 vs 2030 with identical 1 MMscf -> expected 0.0 % ; API yoy_change_pct = {f['yoy_change_pct']}")
bad = abs(f["routine_flaring"]["volume_m3"] - M3_PER_MMSCF) > 1 or abs(f["yoy_change_pct"]) > 0.01
sys.exit(1 if bad else 0)
