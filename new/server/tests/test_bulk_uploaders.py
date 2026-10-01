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


def test_scope1_time_basis_is_the_month_of_the_record(app, client, env):
    fac = env["fac"]
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit,Operating Hours,Equipment ID", [
        f"2025-04,{fac},pneumatic,Production high-bleed controller (API study),12,devices,,PC-A",
        f"2025-04,{fac},pneumatic,Production high-bleed controller (API study),12,devices,720,PC-B",
        f"2025-02,{fac},compressor_venting,\"Centrifugal wet seal, processing\",3,compressors,,CV-1",
    ]))
    assert st["skipped_count"] == 0, reasons(st)
    april = {e.equipment_id: e for e in emissions(app, env["fid"], year=2025, month=4)}
    # no hours given: the controllers operate for April (30 x 24 h), not a year
    assert april["PC-A"].ch4_emissions == pytest.approx(april["PC-B"].ch4_emissions)
    manual = client.post("/api/emissions/", json={
        "year": 2025, "month": 6, "facility_id": env["fid"], "process_type": "pneumatic", "factor_source": "default",
        "activity_key": "prod_pc_high_bleed_api", "amount": 12, "unit": "devices", "activity_hours": 720})
    assert manual.status_code == 201, manual.get_json()
    assert april["PC-A"].ch4_emissions == pytest.approx(emissions(app, env["fid"], year=2025, month=6)[0].ch4_emissions)
    # Table 6-38: 86.43 t CH4 per centrifugal wet-seal compressor-year; February 2025 = 28 / 365 of a year
    feb = emissions(app, env["fid"], year=2025, month=2)[0]
    assert feb.ch4_emissions == pytest.approx(3 * 86.43 * 28 / 365, rel=1e-6)


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


# ---------------------------------------------------------------- Tier 3 methods outside the templates
TIER3_METHODS = [
    dict(process_type="vented_gas", vent_method="gor", gor=500, oil_rate=100, vent_hours=48, ch4_content=80, co2_content=5),
    dict(process_type="vented_gas", vent_method="rate_days", gas_rate=20, gas_rate_unit="Mcf/day", days=10, ch4_content=85),
    dict(process_type="vented_gas", vent_method="actual", actual_volume=1000, actual_unit="ft3", gas_temp_f=100,
         gas_pressure_atm=3, ch4_content=85),
    dict(process_type="desiccant_dehydrator", vent_method="desiccant", vessel_height_ft=10, vessel_diameter_ft=3,
         vessel_pressure_psig=500, refills=4, ch4_content=85),
    dict(process_type="co2_eor", vent_method="co2_mass", physical_volume_m3=50, co2_density=1.8, events=2),
    dict(process_type="combustion", combustion_method="carbon_content", fuel_volume=1000, fuel_volume_unit="gal",
         fuel_density=7.1, density_unit="lb/gal", carbon_wt_pct=85),
    dict(process_type="mobile", combustion_method="vehicle_distance", distance=1000, distance_unit="km",
         vehicle_fuel="diesel", fuel_economy_mpg=8.8),
    dict(process_type="well_testing", vent_method="volume", amount=50, unit="Mscf", ch4_content=85),
]


@pytest.mark.parametrize("case", TIER3_METHODS,
                         ids=lambda c: f"{c['process_type']}-{c.get('vent_method') or c.get('combustion_method')}")
def test_tier3_methods_bulk_equals_manual(app, client, env, case):
    row = dict(case, date="2025-11", facility=env["fac"], factor_type="specific", equipment_id="BULK")
    if "amount" in row:
        row["quantity"] = row.pop("amount")
    st = upload(client, 1, csv_rows(",".join(row), [",".join(str(v) for v in row.values())]))
    assert st["skipped_count"] == 0, reasons(st)
    manual = client.post("/api/emissions/", json=dict(case, year=2025, month=11, facility_id=env["fid"],
                                                      factor_source="specific", equipment_id="MANUAL"))
    assert manual.status_code == 201, manual.get_json()
    recs = {e.equipment_id: e for e in emissions(app, env["fid"], year=2025, month=11)}
    assert recs["BULK"].co2e_total == pytest.approx(recs["MANUAL"].co2e_total, rel=1e-9)
    assert recs["BULK"].co2e_total > 0


def test_vented_gas_by_gor_hand_value(app, client, env):
    # 500 scf/bbl x 100 bbl/day x 2 days = 100,000 scf at 80 % CH4 (0.67722 kg per Sm3)
    upload(client, 1, csv_rows("date,facility,process_type,factor_type,vent_method,gor,oil_rate,vent_hours,ch4_content,co2_content",
                               [f"2025-12,{env['fac']},vented_gas,specific,gor,500,100,48,80,5"]))
    rec = emissions(app, env["fid"], year=2025, month=12)[0]
    m3 = 100000 * 0.028316846592
    assert rec.ch4_emissions == pytest.approx(m3 * 0.80 * (16.04 / 23.685) / 1000, rel=2e-3)


# ---------------------------------------------------------------- roles
@pytest.fixture
def regional(app, env):
    from extensions import db
    from models import Facility, User

    tag = env["tag"]
    with app.app_context():
        other = Facility(name=f"Other Fac {tag}", region=f"OtherRegion{tag}", activity="EP", code=f"OTH-{tag}")
        users = {}
        for role in ("superuser", "user", "auditor", "it"):
            u = User(email=f"{role}_{tag}@test.com", fullName=role, orgName="T", sector="Energy", role=role,
                     location="BulkRegion")
            u.set_password("Regional123!")
            db.session.add(u)
            users[role] = u
        db.session.add(other)
        db.session.commit()
        return {k: v.id for k, v in users.items()}, other.name


@pytest.mark.parametrize("role", ["superuser", "user"])
def test_regional_roles_upload_only_their_facilities(app, client, env, regional, role):
    uids, other = regional
    with client.session_transaction() as sess:
        sess["user_id"] = uids[role]
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit", [
        f"2024-03,{env['fac']},combustion,Natural Gas,100,MMBtu", f"2024-03,{other},combustion,Natural Gas,100,MMBtu"]))
    assert st["processed"] == 2 and st["skipped_count"] == 1
    assert "does not have permission" in reasons(st)[0]
    rec = emissions(app, env["fid"], year=2024, month=3)[0]
    assert rec.status == "Pending" and rec.created_by == uids[role]


@pytest.mark.parametrize("role", ["auditor", "it"])
def test_read_only_roles_cannot_upload(client, env, regional, role):
    uids, _ = regional
    with client.session_transaction() as sess:
        sess["user_id"] = uids[role]
    assert upload(client, 1, "Date,Facility\n2024-01,x\n").status_code == 403


def test_user_cannot_import_supplier_co2e(app, client, env, regional):
    uids, _ = regional
    with client.session_transaction() as sess:
        sess["user_id"] = uids["user"]
    st = upload(client, 3, csv_rows("Facility,Year,Month,Category,Sub Category,Amount,Unit,CO2e",
                                    [f"{env['fac']},2024,6,1,Supplier X,1,lot,500"]))
    assert "Only admins and superusers" in reasons(st)[0]


# ---------------------------------------------------------------- Scope 3 factors of the form
def test_scope3_takes_the_form_factor_when_none_is_given(app, client, env):
    from models import Scope3Emission

    st = upload(client, 3, csv_rows("Facility,Year,Month,Category,Sub Category,Amount,Unit", [
        f"{env['fac']},2024,8,4,Truck Transport,10000,t-km", f"{env['fac']},2024,9,4,Truck Transport,10,t",
        f"{env['fac']},2024,8,15,Equity Investments,1000,USD"]))
    r = reasons(st)
    assert len(r) == 2 and "per ton-km" in r[0] and "no published default" in r[1]
    with app.app_context():
        rec = Scope3Emission.query.filter_by(facility_id=env["fid"], year=2024, month=8).one()
        # EPA Hub 2025 Table 8 truck: 0.186 kg CO2 + 0.0016 g CH4 + 0.0054 g N2O per short ton-mile (AR5)
        per_tkm = (0.186 + 0.0016 * 28 / 1000 + 0.0054 * 265 / 1000) / (0.90718474 * 1.609344)
        assert rec.co2e == pytest.approx(10000 * per_tkm / 1000, rel=1e-3)


def test_scope3_factor_table_matches_the_client():
    from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS

    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "utils", "scope3Factors.js"),
               encoding="utf-8").read()
    rows = re.findall(r'\{ value: "([^"]+)", unit: "([^"]+)", factor: ([0-9.]+|null) \}', src)
    ours = [(v, u, f) for cat in SCOPE3_ACTIVITY_FACTORS.values() for v, u, f in cat]
    assert [(v, u, None if f == "null" else float(f)) for v, u, f in rows] == ours


# ---------------------------------------------------------------- period of a record
def test_record_period():
    from calculations.dispatcher import operating_hours, record_period

    assert record_period({"year": 2024, "month": 2}) == (29 * 24.0, 29.0, 29 / 366)
    assert record_period({}) == (8760.0, 365.0, 1.0)
    assert operating_hours({"year": 2025, "month": 4}) == 720.0
    assert operating_hours({"year": 2025, "month": 4, "operating_hours": 100}) == 100.0


# ---------------------------------------------------------------- jobs across workers / restarts
def test_job_snapshot_survives_the_worker(app, client, env):
    import background_processor as bp

    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit",
                                    [f"2024-09,{env['fac']},combustion,Nope,1,MMBtu"]))
    job = [j for j, v in bp.upload_jobs.items() if v.get("owner_id") == env["uid"]][-1]
    with bp.upload_jobs_lock:
        saved = bp.upload_jobs.pop(job)  # as another worker, or the server after a restart, sees it
    try:
        again = client.get(f"/api/emissions/upload/status/{job}").get_json()
        assert again["status"] == "completed" and again["skipped_count"] == st["skipped_count"] == 1
        assert client.get(f"/api/emissions/upload/errors/{job}").status_code == 200
    finally:
        with bp.upload_jobs_lock:
            bp.upload_jobs[job] = saved


def test_interrupted_job_is_reported(app, client, env):
    import background_processor as bp

    jid = "interrupted-" + env["tag"]
    os.makedirs(bp.UPLOAD_JOB_DIR, exist_ok=True)
    with open(bp._job_file(jid), "w", encoding="utf-8") as fh:
        json.dump({"status": "processing", "owner_id": env["uid"], "heartbeat": time.time() - 3600,
                   "errors": [], "skipped_preview": []}, fh)
    st = client.get(f"/api/emissions/upload/status/{jid}").get_json()
    assert st["status"] == "error" and "interrupted" in st["errors"][0]


def test_fatal_error_saves_nothing(app, client, env, monkeypatch):
    import background_processor as bp

    calls = {"n": 0}
    real = bp._process_row

    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("disk full")
        return real(*a, **k)

    monkeypatch.setattr(bp, "_process_row", boom)
    st = upload(client, 1, csv_rows("Date,Facility,Process,Fuel,Quantity,Unit,Equipment ID", [
        f"2022-01,{env['fac']},combustion,Natural Gas,100,MMBtu,A", f"2022-01,{env['fac']},combustion,Natural Gas,100,MMBtu,B",
        f"2022-01,{env['fac']},combustion,Natural Gas,100,MMBtu,C"]))
    assert st["status"] == "error" and "No rows were saved" in st["errors"][0]
    assert emissions(app, env["fid"], year=2022, month=1) == []


def test_skipped_rows_report_the_file_line(client, env):
    st = upload(client, 1, "Date,Facility,Process,Fuel,Quantity,Unit\n"
                           f"2024-10,{env['fac']},combustion,Natural Gas,1,MMBtu\n\n"
                           f"2024-10,{env['fac']},combustion,Nope,1,MMBtu\n")
    assert [s["row"] for s in st["skipped_preview"]] == [4]


# ---------------------------------------------------------------- recalculation tool
def test_recalculation_tool(app, env, capsys):
    import sys

    from extensions import db
    from models import ActivityLog, Emission, User

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
    import recalculate_emissions as tool

    with app.app_context():
        payload = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000, "unit": "MMBtu",
                   "factor_source": "default", "ch4_content": 85.0, "co2_content": 2.0}
        rec = Emission(facility_id=env["fid"], year=2021, month=5, process_type="combustion", fuel_type="Natural Gas",
                       quantity=1000, unit="MMBtu", factor_source="gases", co2e_total=1.0, status="Verified",
                       source_payload=json.dumps(payload), gwp_version="AR5")
        db.session.add(rec)
        db.session.commit()
        rid = rec.id
        email = db.session.get(User, env["uid"]).email
    tool.main(["--ids", str(rid)])
    assert "report only" in capsys.readouterr().out
    with app.app_context():
        assert db.session.get(Emission, rid).co2e_total == 1.0  # nothing written without --apply
    tool.main(["--ids", str(rid), "--apply", "--user", email])
    with app.app_context():
        db.session.expire_all()
        rec = db.session.get(Emission, rid)
        assert rec.co2e_total == pytest.approx(1000 * NG_KG_PER_MMBTU / 1000)
        assert rec.factor_source == "default" and rec.status == "Pending"
        assert "ch4_content" not in json.loads(rec.source_payload)
        assert ActivityLog.query.filter_by(action="RECALCULATE", record_id=str(rid)).count() == 1
