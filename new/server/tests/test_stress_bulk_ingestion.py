"""
test_stress_bulk_ingestion.py
=============================
Enterprise Bulk Ingestion Stress & Concurrency Benchmark for GHG Accounting Platform.

Benchmarks:
1. 10,000-Row Scope 1 Dataset Ingestion
2. 50,000-Row Scope 1 Dataset Ingestion (MAX_IMPORT_ROWS Enterprise Limit)

Metrics Tracked:
- Ingestion Duration & Throughput (rows/sec)
- Peak Resident Set Size (RSS) Memory Delta (MB)
- SQLite Commit / Lock Hold Duration (seconds)
- Job Status Queue Polling Latency (mean, p95, max ms)
- Concurrent SQLite Reader Latency under Heavy Ingestion (ms)
- Data Persistence & Integrity Verification (zero missing rows)
"""

import os
import sys
import time
import tempfile
import threading
import psutil
import statistics
import pytest
from sqlalchemy import text, event

# Add server directory to sys.path
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from app import app
from extensions import db
from models import User, Facility, Emission
from background_processor import (
    _process_file_thread,
    get_job_status,
    upload_jobs,
    upload_jobs_lock,
)

# Global commit timing across all worker threads
global_commit_durations = []

from sqlalchemy.orm import Session
@event.listens_for(Session, "before_commit")
def on_before_commit(session):
    session.info["commit_t0"] = time.perf_counter()

@event.listens_for(Session, "after_commit")
def on_after_commit(session):
    t0 = session.info.pop("commit_t0", None)
    if t0:
        global_commit_durations.append(time.perf_counter() - t0)


def generate_synthetic_scope1_csv(file_path: str, row_count: int, facility_name: str):
    """Generates synthetic Scope 1 combustion and flaring records in valid CSV format."""
    fuels = ["Natural Gas", "Diesel (No. 2 Fuel Oil)", "Natural Gas (Flaring)", "Natural Gas"]
    processes = ["combustion", "combustion", "flaring", "combustion"]
    units = ["m3", "liters", "m3", "m3"]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("year,month,facility,process,fuel,equipment_id,quantity,unit,factor_source\n")
        for i in range(1, row_count + 1):
            idx = (i - 1) % 4
            month = ((i - 1) % 12) + 1
            year = 2024
            qty = 50.0 + (i % 500)
            eq_tag = f"EQ-{row_count}-{i:06d}"
            f.write(f"{year},{month},{facility_name},{processes[idx]},{fuels[idx]},{eq_tag},{qty},{units[idx]},default\n")


def run_benchmark_for_dataset(row_count: int, benchmark_name: str):
    """Executes asynchronous background ingestion and measures all performance metrics."""
    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss / (1024 * 1024)

    temp_csv = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=f"_{row_count}.csv", encoding="utf-8")
    temp_csv_path = temp_csv.name
    temp_csv.close()

    facility_name = f"Stress Plant {row_count}k"
    user_email = f"benchmark_{row_count}@sonatrach.dz"

    with app.app_context():
        user = User.query.filter_by(email=user_email).first()
        if not user:
            user = User(
                email=user_email,
                fullName=f"Benchmark Worker {row_count}",
                orgName="Sonatrach Exploration",
                sector="Oil & Gas",
                role="admin",
                location="Hassi Messaoud",
            )
            user.set_password("StressPass2026!")
            db.session.add(user)
            db.session.commit()

        fac = Facility.query.filter_by(name=facility_name).first()
        if not fac:
            fac = Facility(
                name=facility_name,
                location="Ouargla",
                activity="Extraction",
                division="Upstream",
                region="South",
                field="Hassi Messaoud South",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()

        user_id = user.id
        fac_id = fac.id

    print(f"\n[{benchmark_name}] Generating {row_count:,} synthetic rows...")
    t_gen_0 = time.perf_counter()
    generate_synthetic_scope1_csv(temp_csv_path, row_count, facility_name)
    gen_time = time.perf_counter() - t_gen_0
    file_size_mb = os.path.getsize(temp_csv_path) / (1024 * 1024)
    print(f"[{benchmark_name}] CSV generated in {gen_time:.2f}s ({file_size_mb:.2f} MB)")

    job_id = f"stress_{row_count}_{int(time.time()*1000)}"
    with upload_jobs_lock:
        upload_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "processed": 0,
            "total": row_count,
            "errors": [],
            "skipped": [],
            "error_csv_path": None,
            "anomalies": [],
            "created_at": time.time(),
        }

    # Tracking metrics
    polling_latencies = []
    concurrent_read_latencies = []
    stop_monitors = threading.Event()
    global_commit_durations.clear()

    # Monitor 1: Polling latency monitor
    def polling_worker():
        while not stop_monitors.is_set():
            t0 = time.perf_counter()
            _ = get_job_status(job_id)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            polling_latencies.append(lat_ms)
            time.sleep(0.05)

    # Monitor 2: Concurrent SQLite reader to verify WAL concurrency
    def concurrent_reader_worker():
        while not stop_monitors.is_set():
            with app.app_context():
                t0 = time.perf_counter()
                try:
                    _ = db.session.execute(text("SELECT count(*) FROM facility")).scalar()
                    lat_ms = (time.perf_counter() - t0) * 1000.0
                    concurrent_read_latencies.append(lat_ms)
                except Exception:
                    pass
            time.sleep(0.1)

    t_poll_thread = threading.Thread(target=polling_worker, daemon=True)
    t_read_thread = threading.Thread(target=concurrent_reader_worker, daemon=True)

    print(f"[{benchmark_name}] Launching ingestion worker thread...")
    t_start = time.perf_counter()
    t_poll_thread.start()
    t_read_thread.start()

    # Run ingestion thread
    ingest_thread = threading.Thread(
        target=_process_file_thread,
        args=(app, job_id, temp_csv_path, os.path.basename(temp_csv_path), user_id, "auto", None, 1, False),
    )
    ingest_thread.start()
    ingest_thread.join()

    total_duration = time.perf_counter() - t_start
    stop_monitors.set()
    t_poll_thread.join(timeout=1.0)
    t_read_thread.join(timeout=1.0)

    rss_after = process.memory_info().rss / (1024 * 1024)
    rss_delta = rss_after - rss_before
    throughput = row_count / total_duration if total_duration > 0 else 0

    # Retrieve job status
    final_job = get_job_status(job_id)

    # Verify rows in DB
    with app.app_context():
        inserted_count = Emission.query.filter_by(facility_id=fac_id).count()

    # Calculate statistics
    avg_poll = statistics.mean(polling_latencies) if polling_latencies else 0
    p95_poll = statistics.quantiles(polling_latencies, n=20)[18] if len(polling_latencies) >= 20 else (max(polling_latencies) if polling_latencies else 0)
    max_poll = max(polling_latencies) if polling_latencies else 0

    avg_read = statistics.mean(concurrent_read_latencies) if concurrent_read_latencies else 0
    max_read = max(concurrent_read_latencies) if concurrent_read_latencies else 0

    total_commit_time = sum(global_commit_durations) if global_commit_durations else 0

    # Cleanup temporary CSV
    try:
        os.remove(temp_csv_path)
    except OSError:
        pass

    results = {
        "benchmark": benchmark_name,
        "row_count": row_count,
        "file_size_mb": file_size_mb,
        "total_duration_s": total_duration,
        "throughput_rows_per_s": throughput,
        "rss_initial_mb": rss_before,
        "rss_peak_mb": rss_after,
        "rss_delta_mb": rss_delta,
        "commit_duration_s": total_commit_time,
        "status": final_job.get("status") if final_job else "unknown",
        "processed": final_job.get("processed", 0) if final_job else 0,
        "inserted_count": inserted_count,
        "skipped_count": final_job.get("skipped_count", 0) if final_job else 0,
        "errors": final_job.get("errors", []) if final_job else [],
        "poll_avg_ms": avg_poll,
        "poll_p95_ms": p95_poll,
        "poll_max_ms": max_poll,
        "read_avg_ms": avg_read,
        "read_max_ms": max_read,
    }

    # Cleanup inserted test emission rows from database to maintain clean state
    with app.app_context():
        try:
            Emission.query.filter_by(facility_id=fac_id).delete()
            from models import ActivityLog
            ActivityLog.query.filter_by(entity_id=str(job_id)).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Warning during cleanup: {e}")

    return results


def test_bulk_ingestion_10k_stress():
    """Benchmark 10,000-row bulk ingestion."""
    results = run_benchmark_for_dataset(10_000, "10K Stress Test")
    print(f"\n--- 10K RESULTS ---")
    print(f"Status: {results['status']}")
    print(f"Duration: {results['total_duration_s']:.2f}s | Throughput: {results['throughput_rows_per_s']:.1f} rows/s")
    print(f"Memory: Initial {results['rss_initial_mb']:.1f} MB -> Peak {results['rss_peak_mb']:.1f} MB (Delta: +{results['rss_delta_mb']:.1f} MB)")
    print(f"SQLite Commit Lock Time: {results['commit_duration_s']:.3f}s")
    print(f"Queue Polling Latency: Avg {results['poll_avg_ms']:.2f}ms | P95 {results['poll_p95_ms']:.2f}ms | Max {results['poll_max_ms']:.2f}ms")
    print(f"Concurrent Read Latency: Avg {results['read_avg_ms']:.2f}ms | Max {results['read_max_ms']:.2f}ms")
    print(f"Rows Verified: {results['inserted_count']:,} / {results['row_count']:,}")

    assert results["status"] == "completed"
    assert results["inserted_count"] == 10_000
    assert results["errors"] == []


def test_bulk_ingestion_50k_stress():
    """Benchmark 50,000-row bulk ingestion (Enterprise ceiling)."""
    results = run_benchmark_for_dataset(50_000, "50K Stress Test")
    print(f"\n--- 50K RESULTS ---")
    print(f"Status: {results['status']}")
    print(f"Duration: {results['total_duration_s']:.2f}s | Throughput: {results['throughput_rows_per_s']:.1f} rows/s")
    print(f"Memory: Initial {results['rss_initial_mb']:.1f} MB -> Peak {results['rss_peak_mb']:.1f} MB (Delta: +{results['rss_delta_mb']:.1f} MB)")
    print(f"SQLite Commit Lock Time: {results['commit_duration_s']:.3f}s")
    print(f"Queue Polling Latency: Avg {results['poll_avg_ms']:.2f}ms | P95 {results['poll_p95_ms']:.2f}ms | Max {results['poll_max_ms']:.2f}ms")
    print(f"Concurrent Read Latency: Avg {results['read_avg_ms']:.2f}ms | Max {results['read_max_ms']:.2f}ms")
    print(f"Rows Verified: {results['inserted_count']:,} / {results['row_count']:,}")

    assert results["status"] == "completed"
    assert results["inserted_count"] == 50_000
    assert results["errors"] == []


if __name__ == "__main__":
    print("=" * 70)
    print("SONATRACH ENTERPRISE BULK INGESTION STRESS BENCHMARK (10K & 50K)")
    print("=" * 70)
    r10 = run_benchmark_for_dataset(10_000, "10K Benchmark")
    r50 = run_benchmark_for_dataset(50_000, "50K Benchmark")

    print("\n" + "=" * 70)
    print("FINAL BENCHMARK COMPARATIVE RESULTS")
    print("=" * 70)
    fmt = "{:<25} | {:<18} | {:<18}"
    print(fmt.format("Metric", "10,000 Rows", "50,000 Rows"))
    print("-" * 70)
    print(fmt.format("Dataset CSV Size", f"{r10['file_size_mb']:.2f} MB", f"{r50['file_size_mb']:.2f} MB"))
    print(fmt.format("Total Elapsed Time", f"{r10['total_duration_s']:.2f}s", f"{r50['total_duration_s']:.2f}s"))
    print(fmt.format("Throughput", f"{r10['throughput_rows_per_s']:.1f} rows/s", f"{r50['throughput_rows_per_s']:.1f} rows/s"))
    print(fmt.format("Peak Memory Delta", f"+{r10['rss_delta_mb']:.1f} MB", f"+{r50['rss_delta_mb']:.1f} MB"))
    print(fmt.format("SQLite Commit Lock Time", f"{r10['commit_duration_s']:.3f}s", f"{r50['commit_duration_s']:.3f}s"))
    print(fmt.format("Polling Latency (Avg)", f"{r10['poll_avg_ms']:.2f} ms", f"{r50['poll_avg_ms']:.2f} ms"))
    print(fmt.format("Polling Latency (P95)", f"{r10['poll_p95_ms']:.2f} ms", f"{r50['poll_p95_ms']:.2f} ms"))
    print(fmt.format("Concurrent Read (Avg)", f"{r10['read_avg_ms']:.2f} ms", f"{r50['read_avg_ms']:.2f} ms"))
    print(fmt.format("Rows Verified in DB", f"{r10['inserted_count']:,}", f"{r50['inserted_count']:,}"))
    print("=" * 70)
