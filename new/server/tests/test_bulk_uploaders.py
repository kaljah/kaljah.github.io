"""Bulk uploader checks (POST /api/emissions/upload/start, background_processor).

Expected values are derived from the source tables (API Compendium 2021 Table 4-5 / 4-6,
EPA supply chain factors v1.3.0), never from the code under test. AR5 GWPs: CH4 28, N2O 265.
"""
import io
import json
import os
import re
import time
import uuid

import openpyxl
import pytest

CH4_GWP, N2O_GWP = 28, 265
NG_KG_PER_MMBTU = 53.06 + 0.001 * CH4_GWP + 0.0001 * N2O_GWP  # Table 4-5 CO2, Table 4-6 CH4 / N2O
NG_HHV_BTU_SCF = 1020


# ---------------------------------------------------------------- fixtures / helpers
@pytest.fixture
def env(app, client):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        u = User(email=f"bulk_{tag}@test.com", fullName="Bulk Admin", orgName="TestCorp", sector="Energy",
                 role="admin", location="Global Corporate Head Office")
        u.set_password("BulkAdmin123!")
        f = Facility(name=f"Bulk Fac {tag}", region="BulkRegion", activity="EP", division="Production",
                     field="BF", segment="Upstream", code=f"BLK-{tag}")
        db.session.add_all([u, f])
        db.session.commit()
        uid, fid, fname = u.id, f.id, f.name
    with client.session_transaction() as sess:
        sess["user_id"] = uid
    return {"uid": uid, "fid": fid, "fac": fname, "tag": tag}


def upload(client, scope, content, filename="rows.csv", mapping=None, **form):
    data = {"scope": str(scope), "global_factor_type": form.pop("gft", "auto"),
            "file": (io.BytesIO(content if isinstance(content, bytes) else content.encode("utf-8")), filename)}
    if mapping is not None:
        data["column_mapping"] = mapping if isinstance(mapping, str) else json.dumps(mapping)
    data.update(form)
    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    if res.status_code != 200:
        return res
    job = res.get_json()["job_id"]
    for _ in range(400):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st["status"] != "processing":
            return st
        time.sleep(0.05)
    raise AssertionError("upload did not finish")


def csv_rows(header, rows):
    return header + "\n" + "\n".join(rows) + "\n"


def reasons(st):
    return [s["reason"] for s in st["skipped_preview"]]


def emissions(app, fid, **flt):
    from models import Emission

    with app.app_context():
        return Emission.query.filter_by(facility_id=fid, **flt).order_by(Emission.id).all()


# ---------------------------------------------------------------- Scope 1
def test_scope1_matches_manual_entry(app, client, env):
    fid, fac = env["fid"], env["fac"]
    st = upload(client, 1, csv_rows("Date,Facility,Process Type,Fuel,Quantity,Unit,Factor Type",
                                    [f"2025-01,{fac},combustion,Natural Gas,50000,scf,default"]))
    assert st["skipped_count"] == 0, reasons(st)
    bulk = emissions(app, fid, year=2025, month=1)[0]
    expected = 50000 * NG_HHV_BTU_SCF / 1e6 * NG_KG_PER_MMBTU / 1000
    assert bulk.co2e_total == pytest.approx(expected, rel=1e-6)

    manual = client.post("/api/emissions/", json={
        "year": 2025, "month": 2, "facility_id": fid, "process_type": "combustion", "fuel": "Natural Gas",
        "amount": 50000, "unit": "scf", "factor_source": "default"})
    assert manual.status_code == 201
    man = emissions(app, fid, year=2025, month=2)[0]
    for col in ("co2e_total", "co2_emissions", "ch4_emissions", "n2o_emissions", "fuel_type", "factor_source",
                "uncertainty", "uncertainty_ch4", "ef_used_co2", "calc_method", "ef_key"):
        assert getattr(bulk, col) == getattr(man, col), col
    assert bulk.factor_source == "default"  # the tier, not the fuel category ("gases")
    assert bulk.status == "Pending"


def test_scope1_rejects_factor_of_another_process(app, client, env):
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit",
                                    [f"2025-01,{env['fac']},tank_flashing,Crude Oil,1000,bbl"]))
    assert st["skipped_count"] == 1
    assert "does not apply to process" in reasons(st)[0]


def test_scope1_process_names(app, client, env):
    fac = env["fac"]
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit,Operating Hours", [
        f"2025-03,{fac},Stationary Combustion,Natural Gas,1000,MMBtu,",
        f"2025-03,{fac},Pneumatic Device,Production high-bleed controller (API study),12,devices,744",
        f"2025-03,{fac},tank_working_standing,Crude Oil,1000,bbl,",
    ]))
    assert st["skipped_count"] == 1
    assert "Unknown process type 'tank_working_standing'" in reasons(st)[0]
    got = {e.process_type for e in emissions(app, env["fid"], year=2025, month=3)}
    assert got == {"combustion", "pneumatic"}


def test_scope1_activity_rows_need_the_hours_of_the_month(app, client, env):
    fac = env["fac"]
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit,Operating Hours", [
        f"2025-04,{fac},pneumatic,Production high-bleed controller (API study),12,devices,",
        f"2025-05,{fac},pneumatic,Production high-bleed controller (API study),12,devices,744",
    ]))
    assert st["skipped_count"] == 1 and "operating hours" in reasons(st)[0]
    rec = emissions(app, env["fid"], year=2025, month=5)[0]
    # the manual form with the same device-hours books the same methane
    manual = client.post("/api/emissions/", json={
        "year": 2025, "month": 6, "facility_id": env["fid"], "process_type": "pneumatic", "factor_source": "default",
        "activity_key": "prod_pc_high_bleed_api", "amount": 12, "unit": "devices", "activity_hours": 744})
    assert manual.status_code == 201, manual.get_json()
    assert rec.ch4_emissions == pytest.approx(emissions(app, env["fid"], year=2025, month=6)[0].ch4_emissions)


def test_scope1_blank_and_text_quantities(app, client, env):
    fac = env["fac"]
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit", [
        f"2025-07,{fac},combustion,Natural Gas,abc,MMBtu",
        f"2025-07,{fac},combustion,Diesel (No. 2 Fuel Oil),,gal",
        f"2025-07,{fac},combustion,Natural Gas,10,",
    ]))
    assert st["skipped_count"] == 3
    r = reasons(st)
    assert "Invalid quantity" in r[0] and "Missing quantity" in r[1] and "Missing unit" in r[2]


def test_scope1_drilling_is_in_days(app, client, env):
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit,Factor Type", [
        f"2025-08,{env['fac']},drilling,Drilling - Mud Degassing (Water Based),500,m3,specific",
        f"2025-08,{env['fac']},drilling,Drilling - Mud Degassing (Water Based),30,days,default",
    ]))
    assert st["skipped_count"] == 1 and "drilling days" in reasons(st)[0]
    rec = emissions(app, env["fid"], year=2025, month=8)[0]
    assert rec.ch4_emissions == pytest.approx(30 * 0.0458)  # Table 6-2 onshore water-based, t CH4 / day


def test_scope1_standard_volumes_are_not_pressure_corrected(app):
    from calculations.constants import get_active_gwp
    from calculations.legacy_engine import compute_emissions
    from services.scope1_calc import resolve_factor

    base = {"process_type": "combustion", "factor_source": "specific", "fuel": "Natural Gas", "amount": 50000,
            "c1": 87.5, "c2": 5.2, "c3": 2.1, "c4": 1.0, "c5": 0.5, "co2_mol": 1.8, "n2_mol": 1.9, "hhv": 1010,
            "combustion_efficiency": 99.5}

    def run(**kw):
        p = dict(base, **kw)
        with app.app_context():
            return compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))[0]["co2"]

    at_std = run(unit="scf")
    assert run(unit="scf", operating_pressure=300, press_unit="psig", operating_temperature=45) == pytest.approx(at_std)
    # carbon balance: 50,000 scf / 379.3 scf/lbmol x C atoms per mole x 44.01 lb x efficiency
    c_atoms = 0.875 + 2 * 0.052 + 3 * 0.021 + 4 * 0.010 + 5 * 0.005
    expected_t = 50000 / 379.3 * (c_atoms * 0.995 + 0.018) * 44.01 * 0.45359237 / 1000
    assert at_std == pytest.approx(expected_t, rel=0.01)
    # a volume in m3 read at 300 psig / 45 C is corrected to standard conditions
    ratio = run(unit="m3", operating_pressure=300, press_unit="psig", operating_temperature=45, temp_unit="C") / run(unit="m3")
    assert ratio == pytest.approx((300 + 14.696) / 14.696 * 288.706 / 318.15, rel=0.01)


def test_scope1_csv_and_excel_templates_import(app, client, env):
    fac = env["fac"]

    def fix(text):
        for n in ("Hassi Messaoud Gas Plant", "Hassi R'Mel Hub", "Field Alpha Processing Plant", "South Field Compressor Stn"):
            text = text.replace(n, fac)
        return text

    for tier in ("1", "3", "auto"):
        txt = fix(client.get(f"/api/emissions/template/csv?tier={tier}&process=all").data.decode("utf-8"))
        st = upload(client, 1, txt.replace("2024-01", f"2023-0{int(tier) if tier != 'auto' else 9}"),
                    overwrite_duplicates="true")
        assert st["status"] == "completed" and st["skipped_count"] == 0, (tier, reasons(st))
        assert st["processed"] == len(txt.strip().split("\n")) - 2  # header and description rows

        wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/emissions/template/excel?tier={tier}&process=all").data))
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str):
                        cell.value = fix(cell.value).replace("2024-01", "2023-11")
        buf = io.BytesIO()
        wb.save(buf)
        st = upload(client, 1, buf.getvalue(), filename="t.xlsx", overwrite_duplicates="true")
        assert st["status"] == "completed" and st["processed"] >= 4 and st["skipped_count"] == 0, (tier, reasons(st))
    flare = [e for e in emissions(app, env["fid"], year=2023, month=11) if e.process_type == "flaring"]
    assert flare and flare[0].factor_source == "specific"  # Tier 3 sheet parameters reached the calculation


def test_template_filters_accept_wizard_process_names(client, env):
    txt = client.get("/api/emissions/template/csv?tier=3&process=pneumatic_device,flaring").data.decode("utf-8")
    header = txt.split("\n")[0]
    assert "[T3-Pneu] pneu_count" in header and "[T3-Flare] flare_type" in header
    assert "[T3-Steam]" not in header and "indirect_steam" not in txt.split("\n", 2)[2]


def test_mapping_is_scope_aware():
    from background_processor import _build_mapping, _canonical_header

    m = _build_mapping(["[Required] date", "[Required] facility_name", "[Required] process_type", "[T3-Tank] tank_gor"], 1)
    assert m["process"] == "[Required] process_type" and "type" not in m
    assert _canonical_header("Bleed Rate (scf/hr)") == "bleed_rate"
    assert _build_mapping(["name", "region"], "facilities") == {"name": "name", "region": "region"}


def test_process_labels_match_the_client():
    from services.scope1_calc import PROCESS_LABELS

    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "utils", "EmissionFactors.js"),
               encoding="utf-8").read()
    block = src[src.index("export const PROCESS_TYPES = {"):]
    block = block[:block.index("};")]
    client_labels = dict(re.findall(r'^\s*([a-z0-9_]+):\s*"([^"]+)"', block, re.M))
    assert client_labels == PROCESS_LABELS


# ---------------------------------------------------------------- Scope 2
def test_scope2_consumption_and_steam(app, client, env):
    from models import Scope2Emission

    fac = env["fac"]
    st = upload(client, 2, csv_rows("Facility,Year,Month,Grid Region,Consumption,Unit,Source Type", [
        f"{fac},2024,1,Algerian National Grid,abc,MWh,",
        f"{fac},2024,2,Algerian National Grid,,MWh,",
        f"{fac},2024,3,,100,MMBtu,steam",
    ]))
    assert st["skipped_count"] == 2 and all("positive number" in r for r in reasons(st))
    with app.app_context():
        steam = Scope2Emission.query.filter_by(facility_id=env["fid"], year=2024, month=3).one()
        # 100 MMBtu of steam from an 80 % natural-gas boiler (Table 4-5 / 4-6)
        assert steam.co2e == pytest.approx(100 / 0.8 * NG_KG_PER_MMBTU / 1000, rel=1e-9)
        assert steam.uncertainty and steam.uncertainty > 0
    manual = client.post("/api/scope2", json={"facility_id": env["fid"], "year": 2024, "month": 4,
                                             "source_type": "indirect_steam", "amount": 100, "unit": "mmbtu"})
    assert manual.get_json()["co2e"] == pytest.approx(steam.co2e)


# ---------------------------------------------------------------- Scope 3
def test_scope3_numbers_and_eeio(app, client, env):
    from models import Scope3Emission

    fac = env["fac"]
    st = upload(client, 3, csv_rows("Facility,Year,Month,Category,Sub Category,Amount,Unit,Emission Factor,EF Unit", [
        f"{fac},2024,1,4,Truck,abc,t-km,0.12841,kg",
        f"{fac},2024,1,4,Truck,1000,t-km,xyz,kg",
    ]))
    assert reasons(st) == ["Activity amount 'abc' is not a number", "Emission factor 'xyz' is not a number"]
    st = upload(client, "3_eeio", csv_rows("Facility,Year,Month,NAICS Code,Spend USD", [f"{fac},2024,2,331110.0,100000"]))
    assert st["skipped_count"] == 0, reasons(st)
    with app.app_context():
        rec = Scope3Emission.query.filter_by(facility_id=env["fid"], year=2024, month=2).one()
        assert rec.co2e == pytest.approx(100000 * 0.787 / 1000)  # EPA v1.3.0, NAICS 331110 with margins


# ---------------------------------------------------------------- Manage Data imports
def test_production_validation(app, client, env):
    fac = env["fac"]
    st = upload(client, "production", csv_rows("facility_id,year,month,oil_amount,oil_unit,gas_amount,gas_unit", [
        f"{fac},2024,13,1,bbl,1,mscf", f"{fac},2024,2,-5,bbl,1,mscf", f"{fac},2024,3,abc,bbl,1,mscf",
        f"{fac},2024,4,1,barrels,1,xyz", f"{fac},2023,5,100,bbl,50,mscf"]))
    assert st["skipped_count"] == 4
    r = reasons(st)
    assert "month" in r[0] and "non-negative" in r[1] and "non-negative" in r[2] and "Unknown" in r[3]


def test_mitigation_validation(client, env):
    fac = env["fac"]
    st = upload(client, "mitigation", csv_rows("facility_id,name,project_type,year,quantity_tco2e,start_date", [
        f"{fac},P1,REC,,100,2024-01-01", f"{fac},P2,REC,2024,abc,2024-01-01", f"{fac},P3,REC,2024,50,2024-13-01",
        f"{fac},P4,REC,2024,50,2024-02-01"]))
    assert st["skipped_count"] == 3
    r = reasons(st)
    assert "'year' is required" in r[0] and "Quantity" in r[1] and "start date" in r[2]


def test_facilities_validation(app, client, env):
    tag = env["tag"]
    st = upload(client, "facilities", csv_rows("name,location,latitude,longitude", [
        f"NF {tag},Oran,95,1", f"NF {tag},Oran,35.7,-0.6", f"NF {tag},Oran,35.7,-0.6"]))
    assert st["skipped_count"] == 2
    assert "latitude" in reasons(st)[0] and "more than once" in reasons(st)[1]


def test_sources_validation(client, env):
    fac = env["fac"]
    st = upload(client, "sources", csv_rows("facility_id,name,equipment_id,installation_date", [
        f"{fac},S1,E1,2020-01-01", f"{fac},S1,E1,2020-01-01", f"{fac},S2,E2,notadate"]))
    assert st["skipped_count"] == 2
    assert "more than once" in reasons(st)[0] and "installation date" in reasons(st)[1]


# ---------------------------------------------------------------- endpoint
def test_upload_start_rejects_bad_requests(client, env):
    assert upload(client, 1, b"x", filename="old.xls").status_code == 400
    assert upload(client, "bogus", "a,b\n1,2\n").status_code == 400
    assert upload(client, 1, "a,b\n1,2\n", mapping="{not json").status_code == 400


def test_no_reviewer_notification_when_nothing_imported(app, client, env):
    from models import Notification

    with app.app_context():
        before = Notification.query.filter_by(title="Scope 1 Bulk Upload Pending Review").count()
    upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit", [f"2025-01,{env['fac']},combustion,Nope,1,MMBtu"]))
    with app.app_context():
        assert Notification.query.filter_by(title="Scope 1 Bulk Upload Pending Review").count() == before
