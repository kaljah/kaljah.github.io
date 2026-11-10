import base64
import os
import sqlite3
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_ENCODED_FORBIDDEN = [
    b"U29uYXRyYWNo",
    b"QmVya2luZQ==",
    b"T2NjaWRlbnRhbA==",
    b"SEJOUw==",
    b"RWwgTWVyaw==",
    b"UmhvdXJkZQ==",
    b"QmVsaGFkag==",
    b"TWFuc291cmk=",
    b"S2hlbGlmaQ==",
    b"c29uYXRyYWNoLmR6",
    b"Q0RTRV9WYXVsdA==",
    b"R3JvdXBlbWVudA==",
]


def _forbidden_words():
    return [base64.b64decode(b).decode("utf-8") for b in _ENCODED_FORBIDDEN]


def test_leak_scan_script_exists_and_detects_sqlite_freelist(tmp_path):
    leak_scan_path = os.path.join(REPO_ROOT, "scripts", "leak_scan.py")
    assert os.path.isfile(leak_scan_path), f"leak_scan.py not found at {leak_scan_path}"

    # Create a SQLite DB, insert a forbidden token + padded payload, then DELETE without VACUUM
    # so the string remains in an unallocated/freelist SQLite page.
    dirty_db = tmp_path / "dirty_freelist.db"
    secret_word = base64.b64decode(b"U29uYXRyYWNo").decode("utf-8")
    conn = sqlite3.connect(str(dirty_db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, note TEXT)")
    for i in range(40):
        conn.execute("INSERT INTO t (note) VALUES (?)", (f"{secret_word}-leak-padding-" + ("X" * 400) + str(i),))
    conn.commit()
    conn.execute("DELETE FROM t")
    conn.commit()
    conn.close()

    res_fail = subprocess.run(
        [sys.executable, leak_scan_path, str(dirty_db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_fail.returncode == 1, f"Expected leak_scan.py to detect freelist leak, got: {res_fail.stdout}"

    # Now VACUUM and confirm leak_scan passes
    conn = sqlite3.connect(str(dirty_db))
    conn.execute("VACUUM")
    conn.commit()
    conn.close()

    res_pass = subprocess.run(
        [sys.executable, leak_scan_path, str(dirty_db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_pass.returncode == 0, f"Expected leak_scan.py clean after VACUUM, got: {res_pass.stdout}"


def test_seed_demo_script_creates_idempotent_clean_dataset(tmp_path):
    seed_demo_path = os.path.join(REPO_ROOT, "scripts", "seed_demo.py")
    assert os.path.isfile(seed_demo_path), f"seed_demo.py not found at {seed_demo_path}"

    # Verify demo DB creation, non-hardcoded passwords, idempotency, and XSS/freelist cleanliness
    demo_db = tmp_path / "demo_a.db"
    res1 = subprocess.run(
        [sys.executable, seed_demo_path, "--db", str(demo_db), "--recreate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res1.returncode == 0, f"seed_demo.py failed: {res1.stdout}\n{res1.stderr}"
    assert "demo.admin@example.org" in res1.stdout
    assert "demo.operator@example.org" in res1.stdout
    assert "demo.auditor@example.org" in res1.stdout

    conn = sqlite3.connect(str(demo_db))
    users = {r[0] for r in conn.execute("SELECT email FROM users").fetchall()}
    facilities = {r[0] for r in conn.execute("SELECT name FROM facilities").fetchall()}
    partners = {r[0] for r in conn.execute("SELECT name FROM jv_partners").fetchall()}
    em_count_1 = conn.execute("SELECT COUNT(*) FROM emissions").fetchone()[0]
    freelist_cnt = conn.execute("PRAGMA freelist_count").fetchone()[0]
    cdse_rows = conn.execute(
        "SELECT key FROM system_settings WHERE lower(key) LIKE '%copernicus%' OR lower(key) LIKE '%cdse%'"
    ).fetchall()
    conn.close()

    assert {"demo.admin@example.org", "demo.operator@example.org", "demo.auditor@example.org"} <= users
    assert {"Facility A-1", "Facility B-2", "Facility C-3"} <= facilities
    assert {"Demo Operator Co.", "Demo JV Partner A", "Demo JV Partner B"} <= partners
    assert em_count_1 >= 20
    assert freelist_cnt == 0
    assert cdse_rows == []

    # Idempotency check: re-run without --recreate; row counts must not duplicate
    res2 = subprocess.run(
        [sys.executable, seed_demo_path, "--db", str(demo_db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res2.returncode == 0
    conn = sqlite3.connect(str(demo_db))
    em_count_2 = conn.execute("SELECT COUNT(*) FROM emissions").fetchone()[0]
    conn.close()
    assert em_count_2 == em_count_1

    # Fresh recreate must generate distinct random passwords (never hardcoded)
    demo_db_b = tmp_path / "demo_b.db"
    res3 = subprocess.run(
        [sys.executable, seed_demo_path, "--db", str(demo_db_b), "--recreate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res3.returncode == 0
    assert res1.stdout != res3.stdout

    # Scan demo_a.db with leak_scan.py -> 0 hits
    leak_scan_path = os.path.join(REPO_ROOT, "scripts", "leak_scan.py")
    scan_res = subprocess.run([sys.executable, leak_scan_path, str(demo_db)], capture_output=True, text=True, check=False)
    assert scan_res.returncode == 0, scan_res.stdout


def test_env_example_has_cdse_placeholder():
    for env_example in (os.path.join(SERVER_ROOT, ".env.example"), os.path.join(REPO_ROOT, ".env.example")):
        assert os.path.isfile(env_example), f".env.example not found at {env_example}"
        with open(env_example, "r", encoding="utf-8") as f:
            content = f.read()
        assert "CDSE_PASSWORD" in content
        vault_token = base64.b64decode(b"Q0RTRV9WYXVsdA==").decode("utf-8")
        assert vault_token not in content


def test_regional_profiles_and_engine_no_real_client_data():
    files_to_check = [
        os.path.join(SERVER_ROOT, "services", "regional_profiles.py"),
        os.path.join(SERVER_ROOT, "services", "master_report_engine.py"),
        os.path.join(SERVER_ROOT, "services", "tenant_config.py"),
        os.path.join(SERVER_ROOT, "seed_showcase_data.py"),
        os.path.join(SERVER_ROOT, "config.py"),
    ]
    forbidden = _forbidden_words()
    for path in files_to_check:
        assert os.path.isfile(path), f"File {path} not found"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
        for word in forbidden:
            assert word.lower() not in content, f"Found forbidden token in {path}"


def test_private_fixtures_folder_and_gitignore():
    private_dir = os.path.join(REPO_ROOT, "tests", "private_fixtures")
    assert os.path.isdir(private_dir), f"private_fixtures directory not found at {private_dir}"
    gitignore_path = os.path.join(REPO_ROOT, ".gitignore")
    assert os.path.isfile(gitignore_path)
    with open(gitignore_path, "r", encoding="utf-8") as f:
        gi_content = f.read()
    assert "tests/private_fixtures" in gi_content
