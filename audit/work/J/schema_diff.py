import sys, sqlite3, os
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/new/server")
os.environ["DATABASE_URL"]="sqlite:///C:/Users/samsung/Desktop/H2/audit/work/J/fresh.db"
os.environ["SEED_ADMIN"]="false"
for e in ("","-wal","-shm"):
    p="C:/Users/samsung/Desktop/H2/audit/work/J/fresh.db"+e
    if os.path.exists(p): os.remove(p)
os.chdir(r"C:/Users/samsung/Desktop/H2/new/server")
from app import app
def schema(path):
    con=sqlite3.connect(path); out={}
    for (t,) in con.execute("select name from sqlite_master where type='table'"):
        cols={r[1]:(r[2],r[3],r[4],r[5]) for r in con.execute(f"pragma table_info('{t}')")}
        fks=sorted(tuple(r[2:6]) for r in con.execute(f"pragma foreign_key_list('{t}')"))
        idx={}
        for r in con.execute(f"pragma index_list('{t}')"):
            idx[r[1]]=(r[2], tuple(c[2] for c in con.execute(f"pragma index_info('{r[1]}')")))
        out[t]=(cols,fks,idx)
    return out
a=schema("C:/Users/samsung/Desktop/H2/audit/db/snapshot_original.db")
b=schema("C:/Users/samsung/Desktop/H2/audit/work/J/fresh.db")
print("tables only in snapshot:", set(a)-set(b)); print("tables only in fresh:", set(b)-set(a))
for t in sorted(set(a)&set(b)):
    ca,fa,ia=a[t]; cb,fb,ib=b[t]
    for c in set(ca)|set(cb):
        if ca.get(c)!=cb.get(c): print(f"COL {t}.{c}: snap={ca.get(c)} fresh={cb.get(c)}")
    if fa!=fb: print(f"FK {t}: snap={fa}\n    fresh={fb}")
    for i in set(ia)|set(ib):
        if ia.get(i)!=ib.get(i): print(f"IDX {t}.{i}: snap={ia.get(i)} fresh={ib.get(i)}")
