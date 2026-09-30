"""RC-15 reports / QA regressions (BUG-077, BUG-084, BUG-113)."""
import pytest

from extensions import db
from models import Emission
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_bug077_emissions_list_filters_by_status(client, ctx):
    f = make_facility(region="West")
    db.session.add_all([Emission(facility_id=f.id, year=2021, month=1, process_type="combustion", co2e_total=1, status="Verified"),
                        Emission(facility_id=f.id, year=2021, month=2, process_type="combustion", co2e_total=2, status="Pending")])
    db.session.commit()
    login(client, make_user("admin", "Global"))
    d = client.get(f"/api/emissions/?facility_id={f.id}&status=Verified&limit=100").get_json()
    rows = d.get("emissions", d) if isinstance(d, dict) else d
    assert rows and all(r["status"] == "Verified" for r in rows)


def test_bug084_stored_outliers_are_reported(client, ctx):
    f = make_facility(region="West")
    for m in range(1, 6):
        db.session.add(Emission(facility_id=f.id, year=2022, month=m, process_type="qa_proc", co2e_total=10, status="Verified"))
    db.session.add(Emission(facility_id=f.id, year=2022, month=6, process_type="qa_proc", co2e_total=5e6, status="Verified"))
    db.session.commit()
    login(client, make_user("admin", "Global"))
    d = client.get("/api/qaqc/dashboard?year=2022").get_json()
    assert d["stored_scan_outlier_count"] >= 1
    assert any(r.get("source") == "stored_scan" and r["co2e"] == 5e6 for r in d["flagged_records"])
    assert "pending_review_count" in d


def test_bug113_pdf_uses_unicode_font(ctx):
    from routes.reports import create_pdf_report

    buf = create_pdf_report([], {"year": "2024"})
    data = buf.getvalue() if hasattr(buf, "getvalue") else buf
    assert b"DejaVuSans" in data or b"GHGSans" in data


def test_bug095_facets_and_export_cover_all_pages(client, ctx):
    """Year facets and the Scope 1 export read the whole filtered set, not the 10-row page."""
    f = make_facility(region="West")
    for i in range(25):
        db.session.add(Emission(facility_id=f.id, year=2010 + (i % 5), month=1 + (i % 12), process_type="combustion",
                                co2e_total=1, status="Verified"))
    db.session.commit()
    login(client, make_user("admin", "Global"))
    years = client.get("/api/filters/available").get_json()["years"]
    assert {2010, 2011, 2012, 2013, 2014} <= {int(y) for y in years}
    d = client.get(f"/api/emissions/?scope=1&limit=all&facility_id={f.id}").get_json()
    assert len(d["emissions"]) == 25
    d = client.get(f"/api/emissions/?scope=1&limit=all&facility_id={f.id}&year=2012").get_json()
    assert len(d["emissions"]) == 5
