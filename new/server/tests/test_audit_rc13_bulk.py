"""RC-13 bulk-import integrity regressions (BUG-057/058/081/085/089/111)."""
import pytest

from extensions import db
from models import ActivityLog, Emission, Scope2Emission, Scope3Emission
from tests.audit_helpers import login, make_facility, make_user, upload


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


S1_HDR = "date,facility_name,process,fuel,quantity,unit,factor_type\n"


def _s1(fac, rows):
    return S1_HDR + "".join(f"{d},{fac.name},combustion,Natural Gas,{q},{u},default\n" for d, q, u in rows)


# ── BUG-057: in-file duplicates with Overwrite must not double count ─────────────

def test_bug057_in_file_duplicates_with_overwrite_keep_one_record(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1(fac, [("2024-05", 100, "MMBtu"), ("2024-05", 250, "MMBtu")]), "1", overwrite=True)
    assert st["status"] == "completed", st
    rows = Emission.query.filter_by(facility_id=fac.id, year=2024, month=5).all()
    assert len(rows) == 1
    assert rows[0].quantity == 250  # last row wins, applied in place


def test_bug057_scope2_in_file_duplicates_with_overwrite(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,source_type,consumption,unit,grid_region\n"
           f"2024-01,{fac.name},electricity,1000,kWh,Algerian National Grid\n"
           f"2024-01,{fac.name},electricity,3000,kWh,Algerian National Grid\n")
    _, _, st = upload(client, csv, "2", overwrite=True)
    assert st["status"] == "completed", st
    assert Scope2Emission.query.filter_by(facility_id=fac.id, year=2024, month=1).count() == 1


# ── BUG-058: overwrite clears approval and is audited ─────────────────────────────

def test_bug058_overwrite_resets_approval_and_logs_old_values(client, ctx):
    fac = make_facility(region="West")
    admin = make_user("admin", "Global")
    e = Emission(facility_id=fac.id, year=2024, month=6, process_type="combustion", fuel_type="Natural Gas",
                 quantity=10, unit="MMBtu", co2e_total=0.53, status="Verified", approved_by=admin.id, created_by=admin.id)
    db.session.add(e)
    db.session.commit()
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1(fac, [("2024-06", 99, "MMBtu")]), "1", overwrite=True)
    assert st["status"] == "completed", st
    db.session.expire_all()
    row = db.session.get(Emission, e.id)
    assert row.quantity == 99 and row.status == "Pending"
    assert row.approved_by is None and row.approved_at is None
    log = ActivityLog.query.filter_by(action="BULK_OVERWRITE", record_id=str(e.id)).first()
    assert log is not None and '"quantity": 10' in (log.old_values or "")
    assert ActivityLog.query.filter_by(action="IMPORT").count() >= 1


# ── BUG-081: richer natural keys ────────────────────────────────────────────────

def test_bug081_scope3_subcategories_in_same_month_are_distinct(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,category,sub_category,activity_amount,unit,emission_factor,ef_unit\n"
           f"2024-02,{fac.name},1,Steel,10,tonne,1000,kg\n"
           f"2024-02,{fac.name},1,Cement,20,tonne,800,kg\n")
    _, _, st = upload(client, csv, "3", overwrite=False)
    assert st["status"] == "completed", st
    assert st["skipped_count"] == 0, st
    assert Scope3Emission.query.filter_by(facility_id=fac.id, year=2024, month=2).count() == 2


def test_bug081_scope2_separate_meters_are_distinct(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,source_type,consumption,unit,grid_region,meter\n"
           f"2024-03,{fac.name},electricity,1000,kWh,Algerian National Grid,M1\n"
           f"2024-03,{fac.name},electricity,500,kWh,Algerian National Grid,M2\n")
    _, _, st = upload(client, csv, "2", overwrite=False)
    assert st["skipped_count"] == 0, st
    assert Scope2Emission.query.filter_by(facility_id=fac.id, year=2024, month=3).count() == 2


def test_bug081_rejected_rows_do_not_block_reimport(client, ctx):
    fac = make_facility(region="West")
    db.session.add(Emission(facility_id=fac.id, year=2024, month=7, process_type="combustion",
                            fuel_type="Natural Gas", quantity=1, unit="MMBtu", status="Rejected"))
    db.session.commit()
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1(fac, [("2024-07", 5, "MMBtu")]), "1", overwrite=False)
    assert st["skipped_count"] == 0, st


# ── BUG-085 / BUG-111: dates, years, units, categories ──────────────────────────

@pytest.mark.parametrize("date", ["", "not-a-date", "1800-01", "9999-01", "2030-13"])
def test_bug085_111_bad_or_missing_periods_are_row_errors(client, ctx, date):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,source_type,consumption,unit,grid_region\n"
           f"{date},{fac.name},electricity,1000,kWh,Algerian National Grid\n")
    _, _, st = upload(client, csv, "2")
    assert st["skipped_count"] == 1, st
    assert Scope2Emission.query.filter_by(facility_id=fac.id).count() == 0
    _, _, st1 = upload(client, _s1(fac, [(date, 10, "MMBtu")]), "1")
    assert st1["skipped_count"] == 1, st1
    assert Emission.query.filter_by(facility_id=fac.id).count() == 0


def test_bug111_blank_unit_is_row_error(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1(fac, [("2024-01", 10, "")]), "1")
    assert st["skipped_count"] == 1
    assert Emission.query.filter_by(facility_id=fac.id).count() == 0


@pytest.mark.parametrize("cat", ["", "99", "Galaxy"])
def test_bug085_scope3_category_required_and_valid(client, ctx, cat):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,category,activity_amount,unit,emission_factor,ef_unit\n"
           f"2024-01,{fac.name},{cat},10,tonne,100,kg\n")
    _, _, st = upload(client, csv, "3")
    assert st["skipped_count"] == 1, st


def test_bug089_bulk_and_api_store_same_category_form(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,category,activity_amount,unit,emission_factor,ef_unit\n"
           f"2024-01,{fac.name},6,10,km,0.2,kg\n")
    upload(client, csv, "3")
    r = client.post("/api/scope3", json={"facility_id": fac.id, "year": 2024, "month": 2, "category": 6,
                                         "activity_data": 10, "unit": "km", "emission_factor": 0.2})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    cats = {e.category for e in Scope3Emission.query.filter_by(facility_id=fac.id).all()}
    assert cats == {"Category 6"}


def test_bug099_bulk_unknown_grid_without_factor_is_rejected(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,source_type,consumption,unit,grid_region\n"
           f"2024-01,{fac.name},electricity,1000,kWh,Atlantis Grid\n")
    _, _, st = upload(client, csv, "2")
    assert st["skipped_count"] == 1, st
