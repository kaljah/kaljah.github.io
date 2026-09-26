import sys, json, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
import sqlite3
def fresh(DB):
    make_db(DB, overwrite=True)
    con=sqlite3.connect(f"C:/Users/samsung/Desktop/H2/audit/db/{DB}.db"); con.execute("update facilities set name='NULLNAME_'||id where name is null"); con.commit(); con.close()
def upload(c, csv, scope, extra=None):
    d={"file":(io.BytesIO(csv.encode()),"u.csv"),"scope":scope}
    if extra: d.update(extra)
    r=c.post("/api/emissions/upload/start", data=d, content_type="multipart/form-data")
    jid=r.get_json()["job_id"]
    for _ in range(100):
        s=c.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s["status"]!="processing": break
        time.sleep(0.3)
    return s
