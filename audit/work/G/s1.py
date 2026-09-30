import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import sql
print(sql("agentG","select uncertainty_pct, process_type, calc_method, year, count(*), min(id), max(id), sum(co2e_total) from emissions where uncertainty>1 group by 1,2,3,4 limit 20"))
print(sql("agentG","select year, count(*), sum(uncertainty>1), sum(co2e_total), sum(case when uncertainty>1 then co2e_total end) from emissions where status='Verified' group by year"))
print(sql("agentG","select * from emissions where uncertainty>1 limit 1"))
