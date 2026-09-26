"""BUG-106: user create / delete / logout never reach activity_log. Own db repro_bug106."""
import sys, time, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_bug106", "it_admin")
em = f"k{int(time.time())}@audit.local"
uid = c.post("/api/auth/register", json={"fullName": "K Test", "email": em, "password": "Abcdef!2345xyz", "role": "user", "location": "West", "orgName": "A", "sector": "x"}).get_json()["user"]["id"]
c.delete(f"/api/auth/users/{uid}"); c.post("/api/auth/logout")
con = sqlite3.connect(db_path("repro_bug106"))
n_user = con.execute("select count(*) from activity_log where details like ?", (f"%{em}%",)).fetchone()[0]
n_logout = con.execute("select count(*) from activity_log where action='LOGOUT'").fetchone()[0]
print(f"expected >=2 log rows for {em} and >=1 LOGOUT; actual {n_user} and {n_logout}")
sys.exit(0 if n_user >= 2 and n_logout >= 1 else 1)
