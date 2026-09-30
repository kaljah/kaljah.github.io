import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, sql
make_db("agentE")
import sqlite3
con=sqlite3.connect(r"C:/Users/samsung/Desktop/H2/audit/db/agentE.db")
def q(s,p=()):
    cur=con.execute(s,p); cols=[d[0] for d in cur.description]
    print(cols)
    for r in cur.fetchall(): print(r)
for s in sys.argv[1:]: q(s); print()
