"""Figures shown outside the calculation (lists, reports) agree with the stored calculation.

GET /api/emissions/ gave every Scope 2 gas as 0, so the PDF report, which re-weights each record's
CH4 / N2O when printed on another GWP set, left the grid CH4 / N2O on the system set.
"""
import uuid
from types import SimpleNamespace

import pytest


@pytest.fixture
def s2world(app, client):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        f = Facility(name=f"Disp {tag}", region=f"DispR{tag}", activity="EP", division="D", field="F",
                     segment="Upstream", code=f"DSP{tag}")
        u = User(email=f"disp_{tag}@test.com", fullName="Disp Admin", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("DispPass123!")
        db.session.add_all([f, u])
        db.session.commit()
        with client.session_transaction() as s:
            s["user_id"] = u.id
        return {"fid": f.id}


def _list_scope2(client, fid):
    res = client.get("/api/emissions/", query_string={"scope": "2", "facility_id": fid, "limit": 100})
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    rows = body.get("emissions", body) if isinstance(body, dict) else body
    return [r for r in rows if r["scope"] == 2]


def test_scope2_grid_rows_carry_their_gas_split(client, s2world):
    from calculations.constants import get_active_gwp
    from electricity_factors import GRID_FACTORS

    kwh = 100000
    res = client.post("/api/scope2", json={"facility_id": s2world["fid"], "year": 2024, "month": 5,
                                           "source_type": "electricity", "electricity_kwh": kwh,
                                           "grid_region": "Algerian National Grid"})
    assert res.status_code in (200, 201), res.get_json()
    (row,) = _list_scope2(client, s2world["fid"])
    grid = GRID_FACTORS["Algerian National Grid"]
    assert row["ch4_emissions"] == pytest.approx(kwh * grid["ch4"] / 1000)
    assert row["n2o_emissions"] == pytest.approx(kwh * grid["n2o"] / 1000)
    assert row["co2_emissions"] == pytest.approx(kwh * grid["co2"] / 1000)
    g = get_active_gwp()
    assert row["co2_emissions"] + row["ch4_emissions"] * g["CH4"] + row["n2o_emissions"] * g["N2O"] == pytest.approx(
        row["co2e_total"], rel=1e-6)


@pytest.mark.parametrize("row", [
    SimpleNamespace(co2e_total=5.0, fuel="Algerian National Grid", amount=100000),   # CO2e not from the grid factor
    SimpleNamespace(co2e_total=5.0, fuel="No Such Grid", amount=100000),            # unknown region
    SimpleNamespace(co2e_total=5.0, fuel="Algerian National Grid", amount=0),        # steam / heat: no kWh
    SimpleNamespace(co2e_total=None, fuel=None, amount=None),
])
def test_scope2_rows_without_a_grid_split_report_co2e_as_co2(app, row):
    from services.scope2_gases import list_row_gases as _scope2_list_gases

    with app.app_context():
        g = _scope2_list_gases(row)
    assert g == {"co2_emissions": float(row.co2e_total or 0), "ch4_emissions": 0.0, "n2o_emissions": 0.0}
