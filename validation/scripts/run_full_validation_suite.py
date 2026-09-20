"""
Master Validation Test Runner.
=============================
Orchestrates execution of the complete independent validation test suite,
gathers execution statistics, numerical tolerances, and formats validation metrics.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "new" / "server"


def run_pytest(test_path, cwd=REPO_ROOT, extra_args=None):
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_path),
        "-v",
    ]
    if extra_args:
        cmd.extend(extra_args)

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT};{SERVER_DIR}"

    t0 = time.time()
    res = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    duration = time.time() - t0
    return {
        "path": str(test_path),
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "duration": duration,
    }


def parse_pytest_summary(stdout):
    summary_line = ""
    for line in stdout.splitlines():
        if "passed" in line or "failed" in line or "xfailed" in line or "error" in line:
            summary_line = line.strip()
    return summary_line


def main():
    print("=" * 70)
    print("STARTING INDEPENDENT GHG VALIDATION SUITE EXECUTION")
    print("=" * 70)

    test_suites = [
        ("Permanent Regression Archive", REPO_ROOT / "validation" / "regression" / "test_regression_archive.py", REPO_ROOT),
        ("Independent Differential Suite", SERVER_DIR / "tests" / "test_independent_differential.py", SERVER_DIR),
        ("Golden Dataset Validation Suite", SERVER_DIR / "tests" / "test_golden_dataset_validation.py", SERVER_DIR),
        ("Exhaustive Unit Conversions", SERVER_DIR / "tests" / "test_unit_conversions_exhaustive.py", SERVER_DIR),
        ("Property Invariants (Hypothesis)", SERVER_DIR / "tests" / "test_property_invariants.py", SERVER_DIR),
        ("Emission Factor Selection", SERVER_DIR / "tests" / "test_emission_factor_selection.py", SERVER_DIR),
        ("Boundary & Resilience Suite", SERVER_DIR / "tests" / "test_boundary_and_negative.py", SERVER_DIR),
        ("Aggregation & Reconciliation", SERVER_DIR / "tests" / "test_aggregation_reconciliation.py", SERVER_DIR),
        ("Battery: Midstream & Process Equipment", SERVER_DIR / "tests" / "test_battery_midstream_process_equipment.py", SERVER_DIR),
        ("Battery: Stoichiometry & Indirect Energy", SERVER_DIR / "tests" / "test_battery_stoichiometry_indirect_energy.py", SERVER_DIR),
        ("Battery: Statistical Anomaly Detection", SERVER_DIR / "tests" / "test_battery_statistical_anomaly_detection.py", SERVER_DIR),
        ("Battery: Compressor Seals & Fugitives", SERVER_DIR / "tests" / "test_battery_compressor_fugitives_equipment.py", SERVER_DIR),
        ("Battery: GWP Horizons & Regulatory", SERVER_DIR / "tests" / "test_battery_gwp_horizons_regulatory.py", SERVER_DIR),
        ("Battery: Concurrency & Stress Invariants", SERVER_DIR / "tests" / "test_battery_concurrency_stress_invariants.py", SERVER_DIR),
        ("Mutation Testing (10 Mutants)", REPO_ROOT / "validation" / "mutation" / "test_calculation_mutations.py", REPO_ROOT),
    ]

    total_duration = 0.0
    all_passed = True
    results = []

    for name, path, cwd in test_suites:
        print(f"\n[RUNNING] {name} ({path.name})...")
        r = run_pytest(path, cwd=cwd)
        summary = parse_pytest_summary(r["stdout"])
        status = "PASSED" if r["returncode"] == 0 else "FAILED"
        if r["returncode"] != 0:
            all_passed = False
        print(f"[{status}] in {r['duration']:.2f}s | Summary: {summary}")
        results.append((name, path.name, status, r["duration"], summary))
        total_duration += r["duration"]

    print("\n" + "=" * 70)
    print("VALIDATION SUITE SUMMARY REPORT")
    print("=" * 70)
    print(f"{'Suite Name':<35} | {'Status':<8} | {'Time (s)':<8} | {'Results'}")
    print("-" * 70)
    for name, filename, status, dur, summ in results:
        print(f"{name:<35} | {status:<8} | {dur:<8.2f} | {summ}")
    print("-" * 70)
    print(f"Total Validation Wall-Clock Time: {total_duration:.2f}s")
    print(f"Overall Validation Result: {'ALL SUITES PASSED / VERIFIED' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
