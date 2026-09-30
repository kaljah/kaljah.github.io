import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, sql
make_db("agentH")
for q in ["select * from sbti_targets","select * from base_year","select * from base_year_recalculations","select * from goals",
 "select year,status,count(*),sum(co2e_total),sum(coalesce(co2e_total,co2_emissions,0)),sum(case when co2e_total is null then 1 else 0 end) nulls from emissions group by year,status",
 "select year,status,count(*),sum(co2e) from scope2_emissions group by year,status",
 "select year,status,count(*),sum(co2e) from scope3_emissions group by year,status"]:
    print(q); [print(' ',r) for r in sql("agentH",q)]
print([r['name'] for r in sql("agentH","pragma table_info(scope2_emissions)")])
