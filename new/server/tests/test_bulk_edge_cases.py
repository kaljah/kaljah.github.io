"""Bulk-upload edge cases checked against the single POST: GWP standard, custom factor, number and
percent formats, partial failure isolation, dry run and anomaly flags."""
import io
import logging

import pytest

from background_processor import _percent_text_to_number
from tests.test_bulk_uploaders import csv_rows, emissions, env, reasons, upload  # noqa: F401

HDR = "Date,Facility,Process Type,Fuel,Quantity,Unit,Factor Type,Equipment ID"


def _post(client, fid, month, amount=1000, unit="MMBtu", fuel="Natural Gas", **kw):
    r = client.post("/api/emissions/", json={"year": 2025, "month": month, "facility_id": fid,
                    "process_type": "combustion", "fuel": fuel, "amount": amount, "unit": unit,
                    "factor_source": "default", **kw})
    assert r.status_code == 201, r.get_data(as_text=True)[:300]


def _pair(app, fid, m1, m2):
    return emissions(app, fid, year=2025, month=m1)[0], emissions(app, fid, year=2025, month=m2)[0]


@pytest.mark.parametrize("std", ["AR4", "AR5", "AR6"])
def test_gwp_standard_applies_to_batch(app, client, env, std):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    assert client.put("/api/auth/settings", json={"gwp_standard": std}).status_code == 200
    try:
        _post(client, fid, 1)
        st = upload(client, 1, csv_rows(HDR, [f"2025-02,{fac},combustion,Natural Gas,1000,MMBtu,default,"]))
        assert st["skipped_count"] == 0, reasons(st)
        a, b = _pair(app, fid, 1, 2)
        assert b.gwp_version == a.gwp_version == std
        assert b.co2e_total == pytest.approx(a.co2e_total, rel=1e-12)
        from calculations.constants import get_active_gwp
        g = get_active_gwp(std)
        assert b.co2e_total == pytest.approx(
            b.co2_emissions + b.ch4_emissions * g["CH4"] + b.n2o_emissions * g["N2O"], rel=1e-9)
    finally:
        client.put("/api/auth/settings", json={"gwp_standard": "AR5"})


@pytest.mark.parametrize("cell,mark", [("1,250.50", "point"), ("1250.5", "point"), ("1.2505e3", "point"),
                                       ("1 250,5", "comma"), ("1250,5", "comma")])
def test_number_formats_equal_plain_number(app, client, env, cell, mark):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    _post(client, fid, 1, amount=1250.5)
    st = upload(client, 1, csv_rows(HDR, [f'2025-02,{fac},combustion,Natural Gas,"{cell}",MMBtu,default,']),
                decimal_mark=mark)
    assert st["skipped_count"] == 0, reasons(st)
    a, b = _pair(app, fid, 1, 2)
    assert b.quantity == pytest.approx(1250.5) and b.co2e_total == pytest.approx(a.co2e_total, rel=1e-12)


@pytest.mark.parametrize("name,text,expected", [
    ("vent_pct", "98%", 98), ("user_unc_co2", "5%", 5), ("ch4_wt_fraction", "50%", 0.5),
    ("ch4_content", "0.5%", 0.005), ("ch4_content", "80%", 80), ("flare_efficiency", "98%", 98),
    ("ch4_content", "1%", 0.01), ("carbon_content", "75%", 0.75), ("ch4_content", " 85.5 % ", 85.5),
    ("ch4_content", "0%", 0.0)])
def test_percent_text(name, text, expected):
    assert _percent_text_to_number(name, text) == pytest.approx(expected)


def test_custom_factor_in_batch_matches_single(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    r = client.post("/api/custom-factors", json={"name": "Site Fuel X", "co2_factor": 70.0, "ch4_factor": 0.01, "n2o_factor": 0.001,
                                                  "unit": "kg/MMBtu", "source": "Site lab report 2025"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    body = r.get_json()
    cfid = body.get("id") or (body.get("factor") or {}).get("id")
    r = client.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": fid, "process_type": "combustion",
                                             "fuel": "Site Fuel X", "amount": 800, "unit": "MMBtu",
                                             "factor_source": "custom", "custom_factor_id": cfid})
    assert r.status_code == 201, r.get_data(as_text=True)[:300]
    st = upload(client, 1, csv_rows(HDR, [f"2025-02,{fac},combustion,Site Fuel X,800,MMBtu,custom,"]))
    assert st["skipped_count"] == 0, reasons(st)
    a, b = _pair(app, fid, 1, 2)
    assert a.co2e_total > 0
    for col in ("co2e_total", "co2_emissions", "ch4_emissions", "n2o_emissions", "ef_used_co2", "uncertainty"):
        assert getattr(b, col) == pytest.approx(getattr(a, col), rel=1e-12), col
    for col in ("custom_factor_id", "factor_source", "fuel_type"):
        assert getattr(b, col) == getattr(a, col), col


def test_invalid_rows_never_change_valid_rows(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    _post(client, fid, 1, amount=500)
    bad = [f"2025-02,{fac},combustion,Natural Gas,-5,MMBtu,default,N",
           f"2025-02,{fac},combustion,Natural Gas,10,,default,U",
           f"2025-02,{fac},combustion,Natural Gas,abc,MMBtu,default,T",
           f'2025-02,{fac},combustion,"=1+1|cmd",10,MMBtu,default,F',
           f"2025-02,{fac},combustion,Natural Gas,10,furlongs,default,X",
           f"2025-02,NoSuchFacility,combustion,Natural Gas,10,MMBtu,default,Z"]
    good = f"2025-02,{fac},combustion,Natural Gas,500,MMBtu,default,G"
    st = upload(client, 1, csv_rows(HDR, bad[:3] + [good] + bad[3:]))
    assert st["skipped_count"] == len(bad), reasons(st)
    rows = emissions(app, fid, year=2025, month=2)
    assert [e.equipment_id for e in rows] == ["G"]
    ref = emissions(app, fid, year=2025, month=1)[0]
    assert rows[0].co2e_total == pytest.approx(ref.co2e_total, rel=1e-12)


def test_dry_run_saves_nothing_and_matches_import(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    csv_text = csv_rows(HDR, [f"2025-03,{fac},combustion,Natural Gas,700,MMBtu,default,A",
                              f"2025-03,{fac},combustion,Natural Gas,-1,MMBtu,default,B"])
    r = client.post("/api/emissions/upload/check", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(csv_text.encode()), "f.csv"), "scope": "1"})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    assert emissions(app, fid, year=2025, month=3) == []
    st = upload(client, 1, csv_text)
    assert st["skipped_count"] == 1 and len(emissions(app, fid, year=2025, month=3)) == 1


def test_outlier_is_not_altered(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    rows = [f"2025-{m:02d},{fac},combustion,Natural Gas,{1000 + m},MMBtu,default,OUT" for m in range(1, 11)]
    rows.append(f"2025-11,{fac},combustion,Natural Gas,{1000 * 500},MMBtu,default,OUT")
    st = upload(client, 1, csv_rows(HDR, rows))
    assert st["skipped_count"] == 0, reasons(st)
    big = emissions(app, fid, year=2025, month=11)[0]
    _post(client, fid, 12, amount=500000)
    ref = emissions(app, fid, year=2025, month=12)[0]
    assert big.co2e_total == pytest.approx(ref.co2e_total, rel=1e-12)


def test_ccs_capture_matches_between_form_and_file(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    _post(client, fid, 1)
    _post(client, fid, 2, ccs_capture_rate=60)
    st = upload(client, 1, csv_rows(HDR + ",CCS Capture Rate", [f"2025-03,{fac},combustion,Natural Gas,1000,MMBtu,default,,60%"]))
    assert st["skipped_count"] == 0, reasons(st)
    base, single, filed = (emissions(app, fid, year=2025, month=m)[0] for m in (1, 2, 3))
    assert single.co2_emissions == pytest.approx(base.co2_emissions * 0.4, rel=1e-9)
    assert single.ch4_emissions == pytest.approx(base.ch4_emissions, rel=1e-12)
    for col in ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total"):
        assert getattr(filed, col) == pytest.approx(getattr(single, col), rel=1e-12), col
    assert single.co2e_total == pytest.approx(base.co2e_total - base.co2_emissions * 0.6, rel=1e-9)


@pytest.mark.parametrize("unit", ["ton", "Tons"])
def test_bare_ton_is_refused_on_every_path(app, client, env, unit):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    r = client.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": fid, "process_type": "combustion",
                                             "fuel": "Tires", "amount": 10, "unit": unit, "factor_source": "default"})
    assert r.status_code in (400, 422) and "ambiguous" in r.get_data(as_text=True)
    r = client.post("/api/emissions/import", json={"records": [
        {"year": 2025, "month": 1, "facility_id": fac, "process_type": "combustion", "fuel": "Tires", "amount": 10,
         "unit": unit, "factor_source": "default"}]})
    assert "ambiguous" in r.get_data(as_text=True)
    r = client.post("/api/scope2", json={"year": 2025, "month": 1, "facility_id": fid, "source_type": "indirect_steam",
                                         "amount": 5, "unit": unit})
    assert r.status_code in (400, 422) and "ambiguous" in r.get_data(as_text=True)
    st = upload(client, 1, csv_rows(HDR, [f"2025-02,{fac},combustion,Tires,10,{unit},default,"]))
    assert st["skipped_count"] == 1 and "ambiguous" in reasons(st)[0]


def test_short_ton_and_tonne_are_accepted_and_differ(app, client, env):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid = env["fid"]
    for month, unit in ((1, "short_ton"), (2, "tonne")):
        _post(client, fid, month, amount=10, unit=unit, fuel="Tires")
    a, b = _pair(app, fid, 1, 2)
    assert a.co2e_total == pytest.approx(b.co2e_total * 0.90718474, rel=1e-6)
