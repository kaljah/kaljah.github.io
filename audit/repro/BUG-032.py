"""GET /api/manage/sbti?base_year=Y returns org-wide Verified totals to region-restricted users."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build
from auditlib import api_client
DB = "agentH_BUG032"
build(DB)
u = api_client(DB, "user")   # location West -> allowed facilities are West only
d = u.get("/api/manage/sbti?base_year=2023").get_json()
# West-only 2023 Verified total = S1 350 + S2 100 = 450 ; org-wide = 950 (includes Center facility 3)
print("expected (West-scoped or 403): 450.0")
print("actual  :", d.get("suggested_base_year_emissions"))
sys.exit(1 if d.get("suggested_base_year_emissions") == 950.0 else 0)
