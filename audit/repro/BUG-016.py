import os, shutil, subprocess, sys
H2 = r"C:/Users/samsung/Desktop/H2"
work = os.path.join(H2, "audit", "work", "J"); os.makedirs(work, exist_ok=True)
fail = 0
for label, src in (("existing", os.path.join(H2, "audit", "db", "snapshot_original.db")), ("fresh", None)):
    dst = os.path.join(work, f"alembic_repro_{label}.db").replace("\\", "/")
    for e in ("", "-wal", "-shm"):
        if os.path.exists(dst + e): os.remove(dst + e)
    if src: shutil.copyfile(src, dst)
    env = dict(os.environ, DATABASE_URL="sqlite:///" + dst, SEED_ADMIN="false", FLASK_APP="app.py")
    p = subprocess.run([sys.executable, "-m", "flask", "db", "upgrade"], cwd=os.path.join(H2, "new", "server"), env=env, capture_output=True, text=True)
    err = [l for l in p.stderr.splitlines() if "OperationalError" in l]
    print(f"{label}: expected upgrade rc=0; actual rc={p.returncode} {err[-1] if err else ''}")
    fail |= p.returncode != 0
sys.exit(1 if fail else 0)
