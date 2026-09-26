import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import sql
print(sql("agentH","select month,count(*),sum(co2e_total) from emissions where year=2026 and status='Verified' group by month"))
print(sql("agentH","select count(*) from emissions where co2e_total=0 and co2_emissions>0"))
print(sql("agentH","select f.region, count(*) from emissions e join facilities f on f.id=e.facility_id where e.year=2025 and e.status='Verified' group by f.region"))
print(sql("agentH","select id,email,role,location from users"))
