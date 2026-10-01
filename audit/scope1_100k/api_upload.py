"""Upload CSV files through the HTTP API exactly as a client would (login, CSRF, multipart upload,
status polling, error-CSV download).

python api_upload.py http://127.0.0.1:5001 out_dir file1.csv [file2.csv ...]
"""
import csv
import io
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(__file__))
from harness import ADMIN_EMAIL, ADMIN_PASSWORD  # noqa: E402


def session(base):
    s = requests.Session()
    r = s.post(f"{base}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    r.raise_for_status()
    tok = s.get(f"{base}/api/csrf-token").json()["csrf_token"]
    s.headers["X-CSRFToken"] = tok
    return s


def upload(s, base, path, out_dir):
    t0 = time.time()
    with open(path, "rb") as f:
        r = s.post(f"{base}/api/emissions/upload/start", files={"file": (os.path.basename(path), f, "text/csv")},
                   data={"scope": "1", "global_factor_type": "auto", "overwrite_duplicates": "false"})
    print(os.path.basename(path), "upload/start ->", r.status_code, r.text[:200], flush=True)
    if r.status_code != 200:
        return {"file": path, "http": r.status_code, "body": r.text}
    job = r.json()["job_id"]
    last = None
    while True:
        st = s.get(f"{base}/api/emissions/upload/status/{job}").json()
        if st.get("status") != last or int(time.time()) % 30 == 0:
            print("  status", st.get("status"), st.get("processed"), "/", st.get("total"), "skipped", st.get("skipped_count"),
                  flush=True)
            last = st.get("status")
        if st.get("status") not in ("processing", "queued", "pending"):
            break
        time.sleep(3)
    res = {"file": path, "job_id": job, "status": st, "elapsed_s": round(time.time() - t0, 1)}
    if st.get("has_error_csv"):
        e = s.get(f"{base}/api/emissions/upload/errors/{job}")
        p = os.path.join(out_dir, f"errors_{os.path.basename(path)}")
        open(p, "wb").write(e.content)
        rows = list(csv.reader(io.StringIO(e.content.decode("utf-8-sig"))))
        res["error_csv"] = p
        res["error_rows"] = len(rows) - 1
    st.pop("skipped_preview", None)
    st.pop("anomalies", None)
    return res


if __name__ == "__main__":
    base, out_dir, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(out_dir, exist_ok=True)
    s = session(base)
    results = [upload(s, base, f, out_dir) for f in files]
    json.dump(results, open(os.path.join(out_dir, "api_upload_results.json"), "w"), indent=1, default=str)
    print(json.dumps(results, indent=1, default=str)[:3000])
