"""Tests for Cryptographic Audit Chain Verification (ISO 14064-3 / ISAE 3410)."""
import pytest
from tests.audit_helpers import login, make_user
from models import ActivityLog
from extensions import db


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_verify_audit_chain_streaming(client, ctx):
    """Verifies that the audit chain endpoint streams ActivityLog rows via yield_per."""
    admin = make_user("admin", "Global")
    login(client, admin)

    # Seed at least 10 activity logs
    for i in range(10):
        log = ActivityLog(
            action=f"TEST_ACTION_{i}",
            record_id=str(i),
            user_id=admin.id,
            entity="Emission",
            details=f"Test log entry #{i}",
        )
        db.session.add(log)
    db.session.commit()

    res = client.get("/api/audit/verify-chain")
    assert res.status_code == 200, res.get_data(as_text=True)
    data = res.get_json()

    assert data["status"] == "verified"
    assert data["is_tamper_evident"] is True
    assert data["total_records"] >= 10
    assert len(data["genesis_hash"]) == 64
    assert len(data["chain_head_hash"]) == 64
    assert len(data["checkpoint_hmac"]) == 64
    assert data["hmac_algorithm"] == "HMAC-SHA256"
    assert data["anchor_status"] == "anchored"
    assert len(data["sample_blocks"]) <= 5
    assert len(data["sample_blocks"]) > 0


def test_hmac_checkpoint_verification_endpoint(client, ctx):
    """Verifies that the /api/audit/verify-checkpoint endpoint authenticates valid checkpoints and rejects forged ones."""
    admin = make_user("admin", "Global")
    login(client, admin)

    # 1. Fetch live chain and checkpoint HMAC
    res = client.get("/api/audit/verify-chain")
    assert res.status_code == 200
    chain_info = res.get_json()

    # 2. Verify legitimate checkpoint
    verify_payload = {
        "chain_head_hash": chain_info["chain_head_hash"],
        "total_records": chain_info["total_records"],
        "checkpoint_hmac": chain_info["checkpoint_hmac"],
    }
    verify_res = client.post("/api/audit/verify-checkpoint", json=verify_payload)
    assert verify_res.status_code == 200
    v_data = verify_res.get_json()
    assert v_data["valid"] is True
    assert v_data["status"] == "authenticated"
    assert v_data["algorithm"] == "HMAC-SHA256"

    # 3. Reject tampered/forged HMAC signature
    tampered_payload = dict(verify_payload, checkpoint_hmac="deadbeef" * 8)
    tampered_res = client.post("/api/audit/verify-checkpoint", json=tampered_payload)
    assert tampered_res.status_code == 200
    t_data = tampered_res.get_json()
    assert t_data["valid"] is False
    assert t_data["status"] == "rejected"


def test_pdf_report_contains_iso14064_cryptographic_assurance(client, ctx):
    """Verifies that generated PDF compliance reports include cryptographic SHA-256 watermarks and headers."""
    admin = make_user("admin", "Global")
    login(client, admin)

    res = client.post("/api/reports/generate", json={"filters": {"year": 2024, "scope": "all"}})
    assert res.status_code == 200
    assert "X-Audit-SHA256" in res.headers
    assert res.headers["X-Audit-Standard"] == "ISO 14064-3 / ISAE 3410"
    assert "X-Audit-Timestamp" in res.headers
    assert len(res.headers["X-Audit-SHA256"]) == 64
    assert res.mimetype == "application/pdf"
    pdf_bytes = res.get_data()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_ogmp_excel_contains_audit_assurance_tab(client, ctx):
    """Verifies that OGMP disclosure workbooks embed the ISO 14064-3 Audit Assurance worksheet."""
    import openpyxl
    import io

    admin = make_user("admin", "Global")
    login(client, admin)

    res = client.get("/api/reports/ogmp-export?year=2024")
    assert res.status_code == 200
    assert "X-Audit-SHA256" in res.headers
    assert res.headers["X-Audit-Standard"] == "ISO 14064-3 / ISAE 3410"
    assert len(res.headers["X-Audit-SHA256"]) == 64

    wb = openpyxl.load_workbook(io.BytesIO(res.get_data()))
    assert "Audit Assurance" in wb.sheetnames
    ws = wb["Audit Assurance"]
    assert "ISO 14064-3" in str(ws.cell(row=2, column=1).value)
    assert ws.cell(row=5, column=1).value == "Audit Standard"
    assert ws.cell(row=6, column=1).value == "Cryptographic Fingerprint (SHA-256)"
