import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, sql
make_db("agentG")
for q in ["select status,count(*),sum(uncertainty is null),min(uncertainty),max(uncertainty),avg(uncertainty),sum(uncertainty_pct is not null) from emissions group by status",
          "select count(*),sum(uncertainty is null),min(uncertainty),max(uncertainty),sum(uncertainty_pct is not null) from scope2_emissions",
          "select count(*),sum(uncertainty is null),min(uncertainty),max(uncertainty),sum(uncertainty_pct is not null) from scope3_emissions",
          "select count(*),min(uncertainty),max(uncertainty),min(co2_uncertainty),max(co2_uncertainty),max(ch4_uncertainty),max(n2o_uncertainty) from custom_factors",
          "select year,count(*) from emissions where status='Verified' group by year",
          "select uncertainty, uncertainty_ch4, uncertainty_n2o, count(*) from emissions group by 1,2,3 order by 4 desc limit 25"]:
    print(q); print(sql("agentG", q))
