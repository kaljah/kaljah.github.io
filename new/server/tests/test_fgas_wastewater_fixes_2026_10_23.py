"""Problems found by the Scope 1 API stress test on wastewater, HFC and SF6 (Compendium 7.5 / 7.6), fixed 2026-10-23:

P1  changing the GWP standard set every HFC / SF6 record to 0 tCO2e (the F-gas CO2e lives only in co2e_total);
P2  an HFC / SF6 record with an activity amount and the default factor source was refused ("No emission factor found");
P3  a wastewater result of zero (aerobic centralized plant, MCF 0) was refused for the same reason;
P4  a decimal comma in a method input was read as a thousands separator ("1,5" mg/L became 15);
P5  an edit with a flat method key was ignored on a record saved with calc_inputs, yet answered "Record updated";
P6  a custom factor on these process types was stored as if it had been used, although these methods never use one.
"""
import pytest

from app import app
from audit_helpers import login, make_facility, make_user, uniq
from calculations.fugitive_other import RefrigerantCalculator, WastewaterCalculator
from extensions import db
from models import CustomFactor, Emission


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _post(client, fac, **body):
    body.setdefault("year", 2025)
    body.setdefault("month", 3)
    body.setdefault("equipment_id", uniq("EQ"))
    return client.post("/api/emissions/", json={"facility_id": fac.id, **body})


def _admin_client():
    c = app.test_client()
    login(c, make_user("admin", "Global"))
    return c


HFC_CHARGE = dict(process_type="hfc", refrigerant_method="charge", refrigerant="HFC-134a", equipment_count=1000,
                  charge_kg=0.5, equipment_type="chillers", operating_days=365)  # 1000 x 0.5 kg x 15 % = 0.075 t


def _created(r):
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:400]
    return db.session.get(Emission, r.get_json()["id"])


# ---- P2 / P3: nothing to look up in a factor table ------------------------------------------------------------------

@pytest.mark.parametrize("source", ["default", "specific"])
def test_hfc_with_an_amount_is_accepted_whatever_the_factor_source(ctx, source):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, factor_source=source, amount=7.5, unit="kg", **HFC_CHARGE))
    assert rec.co2e_total == pytest.approx(0.075 * 1300.0, rel=1e-9)  # HFC-134a, AR5


def test_sf6_with_an_amount_and_default_source_is_accepted(ctx):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, process_type="sf6", factor_source="default", amount=3.0, unit="kg",
                             electrical_method="distance", distance=100, distance_unit="mi", operating_days=365))
    assert rec.co2e_total == pytest.approx(100 * 0.226 / 1000.0 * 23500.0, rel=1e-9)


def test_a_valid_zero_wastewater_result_is_saved(ctx):
    """An aerobic centralized plant has MCF 0 (Table 7-81): zero CH4 is the answer, not a missing factor."""
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, process_type="wastewater", factor_source="default", amount=336659.8466,
                             unit="m3", wastewater_method="ipcc", cod_kg_m3=4.4, treatment_type="aerobic_centralized"))
    assert rec.co2e_total == 0.0 and not rec.ch4_emissions


def test_a_fuel_process_with_a_missing_factor_is_still_refused(ctx):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        r = _post(c, fac, process_type="stationary_combustion", factor_source="default", fuel="No Such Fuel",
                  amount=100, unit="m3")
    assert r.status_code == 422


# ---- P4: decimal comma ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key,value", [("bod5_mg_l", "1,5"), ("flow", "1,000")])
def test_a_comma_in_a_wastewater_input_is_refused(key, value):
    inputs = {"flow": 1000, "flow_unit": "m3", "bod5_mg_l": 1.5, key: value}
    with pytest.raises(ValueError, match="comma"):
        WastewaterCalculator().calculate("aerobic", inputs)


def test_a_comma_in_a_refrigerant_input_is_refused():
    with pytest.raises(ValueError, match="comma"):
        RefrigerantCalculator().calculate("charge", {"equipment_count": 10, "charge_kg": "0,5",
                                                       "operating_rate_pct": 10})


def test_plain_numbers_and_numeric_text_still_work():
    out = WastewaterCalculator().calculate("aerobic", {"flow": "1000", "flow_unit": "m3", "bod5_mg_l": "1.5"})
    assert out["results"]["co2"]["value"] == pytest.approx(1000 * 1000.0 * 1.5 / 0.7 * 44.0 / 32.0 / 1e9, rel=1e-12)


def test_a_text_gwp_gives_a_clear_message():
    with pytest.raises(ValueError, match="GWP"):
        RefrigerantCalculator().calculate("charge", {"equipment_count": 1, "charge_kg": 1, "operating_rate_pct": 1,
                                                       "gwp": "abc"})


# ---- P5: an edit with a flat key on a record that has calc_inputs -----------------------------------------------------

_SAVED_INPUTS = {"refrigerant": {"refrigerant": "HFC-134a", "equipment_count": 1000, "charge_kg": 0.31,
                                 "operating_rate_pct": 10, "refrigerant_method": "charge", "operating_days": 365}}


def test_a_flat_edit_key_reaches_the_saved_method_inputs(ctx):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, process_type="refrigerant", factor_source="specific", calc_inputs=_SAVED_INPUTS))
        assert rec.co2e_total == pytest.approx(1000 * 0.31 * 0.10 / 1000.0 * 1300.0, rel=1e-9)
        edit = c.put(f"/api/emissions/{rec.id}", json={"charge_kg": 0.93})
        assert edit.status_code == 200, edit.get_data(as_text=True)
        db.session.refresh(rec)
    assert rec.co2e_total == pytest.approx(1000 * 0.93 * 0.10 / 1000.0 * 1300.0, rel=1e-9)


def test_an_explicit_calc_inputs_edit_wins_over_a_flat_key(ctx):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, process_type="refrigerant", factor_source="specific", calc_inputs=_SAVED_INPUTS))
        edit = c.put(f"/api/emissions/{rec.id}",
                     json={"charge_kg": 0.93, "calc_inputs": {"refrigerant": {"charge_kg": 0.5}}})
        assert edit.status_code == 200
        db.session.refresh(rec)
    assert rec.co2e_total == pytest.approx(1000 * 0.5 * 0.10 / 1000.0 * 1300.0, rel=1e-9)


# ---- P6: a custom factor is refused for the methods that never use one ------------------------------------------------

def _approved_factor():
    cf = CustomFactor(name=uniq("CF"), co2_factor=50.1, ch4_factor=0.0, n2o_factor=0.0, unit="kg/m3",
                      status="Approved")
    db.session.add(cf)
    db.session.commit()
    return cf


@pytest.mark.parametrize("body", [
    dict(process_type="hfc", refrigerant_method="charge", refrigerant="HFC-134a", equipment_count=10, charge_kg=1.0,
         operating_rate_pct=10),
    dict(process_type="sf6", electrical_method="distance", distance=10, distance_unit="mi"),
    dict(process_type="wastewater", wastewater_method="aerobic", bod5_mg_l=1.5, flow=1000, flow_unit="m3"),
])
def test_a_custom_factor_on_a_factorless_method_is_refused(ctx, body):
    fac = make_facility(name=uniq("FG"))
    cf = _approved_factor()
    with _admin_client() as c:
        r = _post(c, fac, factor_source="custom", custom_factor_id=cf.id, amount=5, unit="kg", **body)
    assert r.status_code == 422
    assert "custom" in r.get_json()["error"].lower()


# ---- P1: a change of GWP standard keeps HFC / SF6 records -------------------------------------------------------------

def test_changing_the_gwp_standard_reweights_hfc_and_sf6_records(ctx):
    fac = make_facility(name=uniq("FG"))
    c = app.test_client()
    login(c, make_user("admin", "Global"))
    try:
        hfc = _created(_post(c, fac, factor_source="specific", **HFC_CHARGE))                       # 0.075 t HFC-134a
        sf6 = _created(_post(c, fac, process_type="sf6", factor_source="specific", electrical_method="distance",
                             distance=100, distance_unit="mi", operating_days=365))                 # 0.0226 t SF6
        blend = _created(_post(c, fac, factor_source="specific", **{**HFC_CHARGE, "refrigerant": "R-410A"}))
        ww = _created(_post(c, fac, process_type="wastewater", factor_source="specific", wastewater_method="ipcc",
                            amount=1000, unit="m3", cod_kg_m3=2.0, treatment_type="anaerobic_reactor"))
        blend_before, ww_ch4 = blend.co2e_total, ww.ch4_emissions
        assert hfc.co2e_total == pytest.approx(0.075 * 1300.0, rel=1e-9)

        r = c.put("/api/auth/settings", json={"gwp_standard": "AR4"})
        assert r.status_code == 200, r.get_data(as_text=True)
        for rec in (hfc, sf6, blend, ww):
            db.session.refresh(rec)
        assert hfc.co2e_total == pytest.approx(0.075 * 1430.0, rel=1e-9) and hfc.gwp_version == "AR4"
        assert sf6.co2e_total == pytest.approx(100 * 0.226 / 1000.0 * 22800.0, rel=1e-9) and sf6.gwp_version == "AR4"
        assert ww.co2e_total == pytest.approx(ww_ch4 * 25.0, rel=1e-9)  # AR4 CH4
        # Table 7-84 prints blend GWPs for AR5 only: the record is kept as it was, never zeroed
        assert blend.co2e_total == pytest.approx(blend_before, rel=1e-12) and blend.gwp_version == "AR5"

        r = c.put("/api/auth/settings", json={"gwp_standard": "AR5"})
        assert r.status_code == 200
        for rec in (hfc, sf6):
            db.session.refresh(rec)
        assert hfc.co2e_total == pytest.approx(0.075 * 1300.0, rel=1e-9) and hfc.gwp_version == "AR5"
        assert sf6.co2e_total == pytest.approx(100 * 0.226 / 1000.0 * 23500.0, rel=1e-9)
    finally:
        c.put("/api/auth/settings", json={"gwp_standard": "AR5"})


def test_a_flat_layout_record_is_recalculated_by_a_flat_edit(ctx):
    """Records saved with the method inputs at the top level of the payload (no calc_inputs) edit the same way."""
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, factor_source="specific", **{**HFC_CHARGE, "operating_rate_pct": 10}))
        edit = c.put(f"/api/emissions/{rec.id}", json={"equipment_count": 2000})
        assert edit.status_code == 200, edit.get_data(as_text=True)
        db.session.refresh(rec)
    assert rec.co2e_total == pytest.approx(2000 * 0.5 * 0.10 / 1000.0 * 1300.0, rel=1e-9)


def test_an_edit_of_a_label_does_not_recalculate(ctx):
    fac = make_facility(name=uniq("FG"))
    with _admin_client() as c:
        rec = _created(_post(c, fac, factor_source="specific", **HFC_CHARGE))
        before = rec.co2e_total
        edit = c.put(f"/api/emissions/{rec.id}", json={"group_name": "Chiller hall"})
        assert edit.status_code == 200
        db.session.refresh(rec)
    assert rec.co2e_total == before and rec.group_name == "Chiller hall"


def test_a_blend_with_an_entered_gwp_follows_a_change_of_standard(ctx):
    """The site's own GWP is a value of the record, so the blend can be re-run under AR4 (Table 7-84 alone cannot)."""
    fac = make_facility(name=uniq("FG"))
    c = app.test_client()
    login(c, make_user("admin", "Global"))
    try:
        blend = _created(_post(c, fac, factor_source="specific",
                               **{**HFC_CHARGE, "refrigerant": "R-410A", "gwp": 2088}))
        assert blend.co2e_total == pytest.approx(0.075 * 2088.0, rel=1e-9)
        assert c.put("/api/auth/settings", json={"gwp_standard": "AR4"}).status_code == 200
        db.session.refresh(blend)
        assert blend.co2e_total == pytest.approx(0.075 * 2088.0, rel=1e-9) and blend.gwp_version == "AR4"
    finally:
        c.put("/api/auth/settings", json={"gwp_standard": "AR5"})
