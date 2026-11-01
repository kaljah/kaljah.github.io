"""
Worker Process for 100k Performance Benchmark (Item 4.5)
=========================================================
Runs in an isolated process with DATABASE_URL set to the benchmark database.
"""
import os
import sys
import time
import json
import argparse

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True)
    args = parser.parse_args()

    # Import app now that DATABASE_URL is set in environment
    from app import app
    from extensions import limiter
    from routes.dashboard import clear_dashboard_cache

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    limiter.enabled = False

    clear_dashboard_cache()

    client = app.test_client()

    # Authenticate as admin
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_role"] = "admin"
        sess["sv"] = 0

    endpoints = [
        {
            "name": "Dashboard Summary (Scope 1 Aggregate)",
            "url": "/api/dashboard/summary?year=2024",
            "target_ms": 500,
            "iterations": 10,
        },
        {
            "name": "Reports Ledger (Page 1, 50 rows)",
            "url": "/api/emissions?year=2024&page=1&limit=50",
            "target_ms": 1000,
            "iterations": 10,
        },
        {
            "name": "Audit Trail (Page 1, 50 rows)",
            "url": "/api/audit?page=1&limit=50",
            "target_ms": 1000,
            "iterations": 10,
        },
        {
            "name": "QA/QC Dashboard (Flagged Records)",
            "url": "/api/qaqc/dashboard?year=2024",
            "target_ms": 1000,
            "iterations": 10,
        },
    ]

    results = []
    print("\n[BENCHMARK] Executing latency tests across 100,000 records...")

    for ep in endpoints:
        # Warmup request to ensure cold caches / connections are primed
        warmup_res = client.get(ep["url"])
        if warmup_res.status_code != 200:
            print(f"  [WARMUP WARNING] {ep['name']} returned status {warmup_res.status_code}")

        durations = []
        status_codes = []
        for it in range(ep["iterations"]):
            t_start = time.perf_counter()
            res = client.get(ep["url"])
            t_end = time.perf_counter()
            elapsed_ms = (t_end - t_start) * 1000
            durations.append(elapsed_ms)
            status_codes.append(res.status_code)

        durations.sort()
        p95_idx = int(0.95 * len(durations))
        p95_ms = round(durations[min(p95_idx, len(durations) - 1)], 2)
        avg_ms = round(sum(durations) / len(durations), 2)
        min_ms = round(min(durations), 2)
        max_ms = round(max(durations), 2)
        passed = p95_ms <= ep["target_ms"] and all(c == 200 for c in status_codes)

        status_flag = "PASS" if passed else "FAIL"
        print(f"  {status_flag} | {ep['name']:<40} | p95: {p95_ms:>6.1f} ms (Target: <{ep['target_ms']} ms) | Avg: {avg_ms:>6.1f} ms | Status: {status_codes[0]}")

        results.append({
            "endpoint": ep["name"],
            "url": ep["url"],
            "target_ms": ep["target_ms"],
            "p95_ms": p95_ms,
            "avg_ms": avg_ms,
            "min_ms": min_ms,
            "max_ms": max_ms,
            "status_code": status_codes[0],
            "passed": passed,
        })

    overall_pass = all(r["passed"] for r in results)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "database_scale": {
            "total_emissions_records": 100000,
            "total_facilities": 30,
            "years_covered": [2022, 2023, 2024, 2025, 2026],
            "total_production_records": 5000,
            "total_audit_records": 2000,
        },
        "overall_status": "PASS" if overall_pass else "FAIL",
        "endpoints": results,
    }

    rep_dir = os.path.join(SERVER_DIR, "reports")
    os.makedirs(rep_dir, exist_ok=True)
    rep_file = os.path.join(rep_dir, "benchmark_p95_report.json")
    with open(rep_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[BENCHMARK] Benchmark completed. Report written to {rep_file}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
