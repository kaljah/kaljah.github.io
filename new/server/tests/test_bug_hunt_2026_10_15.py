"""Regression tests for the 2026-10-15 source-only bug hunt (findings #1-#37)."""
import pytest

from app import app
from calculations import compute_emissions
from calculations import legacy_engine
from calculations.combustion import convert_factor_to_kg_per_unit


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _em(payload, factor=None):
    return compute_emissions(dict(payload), factor or {})[0]


# ── Batch 1: combustion and flaring ─────────────────────────────────────────────────

DIESEL_NO_HHV = {"unit": "kg/MMBtu", "co2": 73.96, "ch4": 0.003, "n2o": 0.0006}
DIESEL = dict(process_type="combustion", fuel="Diesel", amount=1000, unit="gal",
              factor_source="default", date="2025-01-15")


def test_1_density_does_not_replace_the_fuel_hhv_with_1020(ctx):
    plain = _em(DIESEL, DIESEL_NO_HHV)["co2"]
    with_density = _em(dict(DIESEL, density=840), DIESEL_NO_HHV)["co2"]
    assert plain == pytest.approx(10.2065, rel=1e-3)
    assert with_density == pytest.approx(plain, rel=1e-9)  # was 0.076 t (135x low)


def test_1_energy_factor_without_any_hhv_is_refused(ctx):
    with pytest.raises(ValueError, match="HHV"):
        _em(dict(DIESEL, fuel="Not a catalog fuel", density=840), DIESEL_NO_HHV)


FLARE = dict(process_type="flaring", amount=1, unit="MMscf", factor_source="specific",
             ch4_content=90, date="2025-01-15", year=2025, month=1)


def test_2_standard_flare_volume_is_not_corrected_for_temperature_and_pressure_twice(ctx):
    plain = _em(FLARE)["co2"]
    assert plain == pytest.approx(45.70, rel=1e-3)
    assert _em(dict(FLARE, operating_temperature=40, operating_pressure=50))["co2"] == pytest.approx(plain)  # was 188 t
    # an actual volume is still corrected
    actual = _em(dict(FLARE, amount=28316.85, unit="m3", operating_temperature=40, operating_pressure=50))["co2"]
    assert actual > 3 * plain


@pytest.mark.parametrize("hhv,unit", [(1020, "Btu/scf"), (38.0, "MJ/Sm3"), (38.0, "MJ/m3"), (40.1, "MJ/Nm3")])
def test_6_flare_hhv_per_standard_volume_is_rescaled_to_scf(ctx, hhv, unit):
    n2o = _em(dict(FLARE, hhv=hhv, hhv_unit=unit))["n2o"]
    assert n2o == pytest.approx(1.02e-4, rel=0.06)  # MJ/Sm3 was read as Btu/scf: 35x high


def test_6_flare_hhv_per_mass_is_refused(ctx):
    with pytest.raises(ValueError, match="gas volume"):
        _em(dict(FLARE, hhv=50, hhv_unit="MJ/kg"))


def test_9_flare_n2o_factor_in_g_per_mmbtu_is_not_read_as_kg(ctx):
    kg = _em(dict(FLARE, ef_n2o=0.0001, ef_unit="kg/MMBtu"))["n2o"]
    g = _em(dict(FLARE, ef_n2o=0.1, ef_unit="g/MMBtu"))["n2o"]
    assert g == pytest.approx(kg)  # was 1000x high


def test_3_gas_density_is_not_taken_for_a_liquid_in_kg_per_litre():
    # 2.7 kg CO2 per kg of gas, 0.75 kg/m3: 2.025 kg per m3 (was 2025)
    assert convert_factor_to_kg_per_unit(2.7, "kg/kg", "m3", fuel_type="Natural Gas", density=0.75) == pytest.approx(2.025)
    assert convert_factor_to_kg_per_unit(2.7, "kg/kg", "scf", fuel_type="custom", density=0.75) == pytest.approx(2.025 * 0.0283168, rel=1e-4)
    # a liquid in kg/L is still read as such
    assert convert_factor_to_kg_per_unit(3.2, "kg/kg", "gal", fuel_type="Diesel", density=0.84) == pytest.approx(
        convert_factor_to_kg_per_unit(3.2, "kg/kg", "gal", fuel_type="Diesel", density=840))


def test_10_legacy_hhv_basis_comes_from_its_unit_not_its_size():
    # 38 MJ/m3 gas: 1000 m3 -> 38 GJ; 50 kg/GJ -> 1900 kg per 1000 m3
    kg = legacy_engine._convert_factor_to_kg(50, "kg/GJ", "m3", hhv=38 / 0.001055056, hhv_unit="btu/m3",
                                             fuel_type="gases")
    assert kg * 1000 == pytest.approx(1900, rel=1e-6)


def test_11_legacy_same_unit_factor_is_kg_per_unit_even_for_tonnes():
    kg = legacy_engine._calculate_default_kg(10, "tonnes", {"co2": 2.5, "unit": "tonnes"}, "co2")
    assert kg == pytest.approx(25.0)  # was 25000


def test_11_legacy_unreadable_factor_unit_is_refused():
    with pytest.raises(ValueError):
        legacy_engine._calculate_default_kg(10, "gal", {"co2": 2.5, "unit": "kg/furlong"}, "co2")


# ── Batch 2: units and number parsing ───────────────────────────────────────────────

from calculations.units import (UnitError, composition_fractions, convert_temperature,  # noqa: E402
                                factor_to_kg_per_activity, parse_amount, parse_factor_unit, unit_dimension)


@pytest.mark.parametrize("unit,scf_per_den", [
    ("kg/1000 scf", 1000), ("kg/1,000 scf", 1000), ("kg/10^3 scf", 1000), ("kg/10³ scf", 1000),
    ("tonne CH4/10⁶ scf", 1e6), ("kg/1e6 scf", 1e6), ("kg/thousand scf", 1000), ("kg/scf", 1),
])
def test_4_numeric_denominator_scales(unit, scf_per_den):
    (dim, f, tok), = parse_factor_unit(unit)["denominators"]
    assert tok == "scf" and f == pytest.approx(0.028316846592 * scf_per_den)


def test_4_per_100_gal_is_not_per_gal():
    assert factor_to_kg_per_activity(10, "kg/100 gal", "gal") == pytest.approx(0.1)  # was 10


def test_5_amount_text_with_a_comma_is_refused(ctx):
    with pytest.raises(ValueError, match="comma"):
        parse_amount("1,000")
    assert parse_amount("1000.5") == 1000.5 and parse_amount(None) == 0.0
    with pytest.raises(ValueError):
        _em(dict(DIESEL, amount="1,000"), DIESEL_NO_HHV)  # was booked as 1 gal


def test_7_unknown_target_temperature_unit_is_refused():
    assert convert_temperature(100, "C", "F") == pytest.approx(212)
    with pytest.raises(UnitError):
        convert_temperature(100, "C", "degrees")  # returned Kelvin


@pytest.mark.parametrize("unit", ["ton", "tons", "kg/ton", "kg CO2/tons"])
def test_8_bare_ton_is_refused(unit):
    with pytest.raises(UnitError, match="ambiguous"):
        parse_factor_unit(unit) if "/" in unit else unit_dimension(unit)


def test_8_explicit_short_ton_and_tonne_still_work():
    assert unit_dimension("short_ton")[1] == pytest.approx(907.18474)
    assert unit_dimension("tonne")[1] == 1000.0


def test_12_partial_percent_analysis_with_small_values_is_not_read_as_fractions():
    with pytest.raises(ValueError, match="composition_basis"):
        composition_fractions({"co2": 0.3, "n2": 0.4})  # read as 30 % / 40 %
    with pytest.raises(ValueError, match="composition_basis"):
        composition_fractions({"c1": 0.2, "co2": 0.1})
    fr, _ = composition_fractions({"co2": 0.3, "n2": 0.4}, basis="percent")
    assert fr["co2"] == pytest.approx(0.003)
    # a single fraction and a complete fractional analysis are still read as fractions
    assert composition_fractions({"c1": 0.9})[0]["c1"] == pytest.approx(0.9)
    assert composition_fractions({"c1": 0.9, "c2": 0.1})[0]["c2"] == pytest.approx(0.1)


def test_31_clean_float_never_turns_unreadable_text_into_the_default():
    from background_processor import _clean_float

    assert _clean_float("", default=150.0) == 150.0
    assert _clean_float("n/a", default=150.0) == 150.0
    assert _clean_float("abc", default=150.0) is None  # was 150
    assert _clean_float("12 [ambiguous: decimal or thousands separator?]", default=0.0) is None  # was 0
    assert _clean_float("1,000", default=0.0) is None  # was 1000 (1 in French)
    assert _clean_float("1,234.5") == 1234.5 and _clean_float("1234,5") == 1234.5


# ── Batch 3: venting and tanks ──────────────────────────────────────────────────────

AGV = dict(process_type="associated_gas_venting", amount=10000, unit="bbl", gor=500, ch4_content=80,
           factor_source="specific", tier="tier2", date="2025-01-15", year=2025, month=1)


def test_20_vent_hours_and_the_record_period_share_one_unit(ctx):
    ten_hours = _em(dict(AGV, venting_duration=10))["ch4"]
    # 5e6 scf over 744 h, 10 h vented, 80 % CH4: 1.03 t (the 31-day month was read as 31 h: 21.7 t)
    assert ten_hours == pytest.approx(1.0314, rel=1e-3)
    assert _em(dict(AGV, hours=10))["ch4"] == pytest.approx(ten_hours)
    ten_days = _em(dict(AGV, venting_duration=240))["ch4"]  # was refused as longer than the period
    assert ten_days == pytest.approx(_em(dict(AGV, days=10))["ch4"])
    assert ten_days == pytest.approx(ten_hours * 24, rel=1e-6)


def test_20_an_hours_column_is_not_read_in_days_at_tier_2_default(ctx):
    b = {k: v for k, v in AGV.items() if k != "tier"}
    b["factor_source"] = "default"
    assert _em(dict(b, hours=240))["ch4"] == pytest.approx(_em(dict(b, days=10))["ch4"])


TANK = dict(process_type="tank", amount=10000, unit="bbl", factor_source="specific", gor=50,
            tank_ch4_content=60, date="2025-01-15", year=2025, month=1)


def test_21_tank_co2_content_is_percent_like_co2_content(ctx):
    a = _em(dict(TANK, tank_co2_content=0.5))["co2"]
    assert a == pytest.approx(_em(dict(TANK, co2_content=0.5))["co2"])  # was 100x apart
    assert a == pytest.approx(0.1315, rel=1e-3)


def test_23_condensate_dump_valve_uses_the_condensate_tank_factor():
    from calculations.vented_production_tank import TankFlashingCalculator as T

    r = T().calculate(1000, method="dump_valve", liquid_type="condensate", dump_valve_hours=8760)
    assert r["results"]["ch4"]["value"] == pytest.approx(4.37 * 1000 * 0.146 / 1000, rel=1e-6)


def test_24_working_loss_factor_is_converted_by_its_unit(ctx):
    per_tonne = _em(dict(TANK, gor=None, tank_method="working_loss"), {"ch4": 0.001, "unit": "tonne/bbl"})["ch4"]
    per_kg = _em(dict(TANK, gor=None, tank_method="working_loss"), {"ch4": 1.0, "unit": "kg/bbl"})["ch4"]
    assert per_tonne == pytest.approx(per_kg)
    with pytest.raises(ValueError, match="per bbl"):
        _em(dict(TANK, gor=None, tank_method="working_loss"), {"ch4": 0.1, "unit": "tonne CH4/unit/hr"})


def test_25_vbe_without_separator_data_is_refused(ctx):
    with pytest.raises(ValueError, match="separator"):
        _em(dict(TANK, gor=None, tank_method="vbe"))


def test_26_dehydrator_tier3_needs_the_gas_ch4_content(ctx):
    b = dict(process_type="dehydrator", amount=100, unit="MMscf", factor_source="specific",
             date="2025-01-15", year=2025, month=1)
    with pytest.raises(ValueError, match="CH4"):
        _em(b)
    assert _em(dict(b, dehy_ch4_content=78.8))["ch4"] == pytest.approx(0.52859, rel=1e-4)


def test_26_agr_slip_needs_the_inlet_ch4(ctx):
    b = dict(process_type="acid_gas_removal", amount=100, unit="MMscf", factor_source="specific",
             agr_co2_in=5, agr_co2_out=1, agr_ch4_slip=0.001, date="2025-01-15", year=2025, month=1)
    with pytest.raises(ValueError, match="inlet CH4"):
        _em(b)


def test_27_an_entered_zero_is_not_the_default(ctx):
    b = dict(process_type="compressor_seal", amount=2, unit="compressors", factor_source="specific",
             seal_type="reciprocating", date="2025-01-15", year=2025, month=1)
    assert _em(dict(b, hours=0))["ch4"] == 0.0  # was the whole month


def test_28_blowdown_temperature_without_a_unit_is_celsius(ctx):
    b = dict(process_type="blowdown", amount=1000, unit="m3", factor_source="specific", ch4_content=90,
             blowdown_pressure=100, blowdown_events=1, date="2025-01-15", year=2025, month=1)
    c = _em(dict(b, blowdown_temp=30))["ch4"]
    assert c == pytest.approx(_em(dict(b, blowdown_temp=86, blowdown_temp_unit="F"))["ch4"], rel=1e-6)
    assert _em(b)["ch4"] == pytest.approx(_em(dict(b, blowdown_temp=60, blowdown_temp_unit="F"))["ch4"], rel=1e-5)


# ── Batch 4: Scope 2 cooling and Scope 3 units ─────────────────────────────────────

from audit_helpers import login, make_facility, make_user, uniq  # noqa: E402


def test_13_cooling_without_a_factor_is_refused(ctx):
    fac = make_facility(name=uniq("CoolFac"), region=uniq("R"))
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/scope2", json={"facility_id": fac.id, "year": 2024, "month": 3, "source_type": "cooling",
                                        "cooling_ton": 1000})
        assert r.status_code == 400, r.get_json()  # was booked at 150 kg CO2e per ton-hour
        r = c.post("/api/scope2", json={"facility_id": fac.id, "year": 2024, "month": 3, "source_type": "cooling",
                                        "cooling_ton": 1000, "emission_factor": 0.5})
        assert r.status_code in (200, 201), r.get_json()


def test_29_cooling_import_checks_the_factor_and_the_unit():
    from background_processor import COOLING_UNITS, _clean_float

    assert "ton_hour" in COOLING_UNITS and "kwh" not in COOLING_UNITS
    assert _clean_float("abc", default=None) is None


def test_30_scope3_activity_unit_is_converted_to_the_factor_denominator():
    from calculations.units import compute_scope3_co2e
    from input_validation import ValidationError

    assert compute_scope3_co2e(1000, 2.5, "kg CO2e/tonne", activity_unit="kg") == pytest.approx(0.0025)  # was 2.5
    assert compute_scope3_co2e(1, 2.5, "kg CO2e/tonne", activity_unit="tonne") == pytest.approx(0.0025)
    assert compute_scope3_co2e(1000, 1, "kg/1000 km", activity_unit="mile") == pytest.approx(0.001609344)
    assert compute_scope3_co2e(100, 1, "kg/$1000", activity_unit="USD") == pytest.approx(0.0001)
    assert compute_scope3_co2e(10, 1, "kg/unit", activity_unit="bbl") == pytest.approx(0.01)
    with pytest.raises(ValidationError):
        compute_scope3_co2e(10, 1, "kg/kg", activity_unit="kWh")


# ── Batch 5: reports ────────────────────────────────────────────────────────────────

import io as _io  # noqa: E402

import openpyxl  # noqa: E402

from extensions import db  # noqa: E402
from models import Emission, ProductionData, Scope2Emission  # noqa: E402


def _report_setup():
    fac = make_facility(name=uniq("RepFac"), region=uniq("R"))
    rows = [
        Emission(facility_id=fac.id, year=2011, month=1, process_type="routine_flaring", quantity=1, unit="MMscf",
                 co2_emissions=10, ch4_emissions=0.1, n2o_emissions=0, co2e_total=12.5, status="Verified",
                 gwp_version="AR6"),
        Emission(facility_id=fac.id, year=2011, month=2, process_type="tank", quantity=1, unit="bbl",
                 co2_emissions=0, ch4_emissions=1, n2o_emissions=0, co2e_total=28, status="Pending",
                 gwp_version="AR5"),
        Scope2Emission(facility_id=fac.id, year=2011, month=1, source_type="electricity", electricity_kwh=1000,
                       emission_factor=0.5, co2e=0.5, co2e_location_based=None, co2e_market_based=None,
                       status="Verified"),
    ]
    db.session.add_all(rows)
    db.session.commit()
    return fac


def _sheet_values(ws):
    return [[c.value for c in row] for row in ws.iter_rows()]


def test_22_32_33_34_national_report_status_filter_and_record_values(ctx):
    fac = _report_setup()
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        r = c.get(f"/api/reports/national-inventory-export?year=2011&facility_id={fac.id}")
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        wb = openpyxl.load_workbook(_io.BytesIO(r.data))
        inv = _sheet_values(wb["Emissions Inventory"])
        statuses = [row[16] for row in inv[4:] if row[1]]
        assert statuses == ["Verified", "Verified"]  # the Pending tank is left out; S2 row is Verified
        # routine flaring is on the combustion sheet (it was on neither sheet); nothing invented
        comb = _sheet_values(wb["Scope 1 - Combustion & Torchage"])[4:]
        assert [row[2] for row in comb if row[0]] and comb[0][1] in (None, "")
        flat = str([_sheet_values(ws) for ws in wb.worksheets])
        for invented in ("COMP-SEAL-01", "GEN-01", "Campagne OGI", "0.582", "Sonelgaz (Réseau", "± 6.4%"):
            assert invented not in flat, invented
        # Scope 2 location total falls back to co2e on a record without dual reporting
        summary = _sheet_values(wb["Executive Summary"])
        s2 = next(row for row in summary if row[0] and str(row[0]).startswith("Scope 2 — Émissions indirectes"))
        assert s2[1] == pytest.approx(0.5)
        # Verified + Pending on request
        r = c.get(f"/api/reports/national-inventory-export?year=2011&facility_id={fac.id}&status=Verified,Pending")
        wb = openpyxl.load_workbook(_io.BytesIO(r.data))
        vent = _sheet_values(wb["Scope 1 - Évents & Fugitives"])[4:]
        tank = next(row for row in vent if row[0])
        assert tank[6] == 28  # the record's own GWP (AR5), not a fixed AR6 29.8
        for bad in ("year=20x1", "facility_id=abc", "status=Approved"):
            assert c.get(f"/api/reports/national-inventory-export?{bad}").status_code == 400, bad


def test_35_cbam_production_follows_its_units_and_split_covers_every_process(ctx):
    from routes.reports_cbam import _cbam_family, _get_facility_production_tonnes

    fac = make_facility(name=uniq("CbamFac"), region=uniq("R"))
    db.session.add(ProductionData(facility_id=fac.id, year=2012, month=1, oil_amount=0, gas_amount=28316.846592,
                                  oil_unit="bbl", gas_unit="m3"))
    db.session.commit()
    tonnes, from_db = _get_facility_production_tonnes(fac.id, 2012)
    assert from_db and tonnes == pytest.approx(21.0, rel=1e-6)  # 1,000 Mscf; was read as 28,317 Mscf (594.7 t)
    assert _cbam_family("routine_flaring") == "flaring_venting"
    assert _cbam_family("stationary_combustion") == "combustion"
    assert _cbam_family("tank") == "flaring_venting"
    assert _cbam_family("nitric_acid_production") == "process"


def test_36_generate_refuses_malformed_filters(ctx):
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        for f in ({"year": "20x4"}, {"facility_id": "abc"}, {"month": "13"}):
            r = c.post("/api/reports/generate", json={"filters": f})
            assert r.status_code == 400, (f, r.status_code)


def test_37_process_filter_leaves_out_scope2_and_3(ctx, monkeypatch):
    import routes.reports as rep

    seen = {}

    def fake_pdf(data, filters):
        seen["scopes"] = {d["scope"] for d in data}
        buf = _io.BytesIO(b"%PDF-1.4")
        buf.report_hash = "0" * 64
        return buf

    monkeypatch.setattr(rep, "create_pdf_report", fake_pdf)
    fac = _report_setup()
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/reports/generate", json={"filters": {"year": 2011, "facility_id": fac.id,
                                                              "process_type": "routine_flaring"}})
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        assert seen["scopes"] == {1}


# ── Batch 6: dashboard and filters ──────────────────────────────────────────────────

def test_14_segment_is_stored_in_its_listed_form_and_filtered_whatever_its_case(ctx):
    from services.dashboard_filters import apply_scope
    from services.labels import normalize_segment

    assert normalize_segment(" upstream ") == "Upstream" and normalize_segment("DOWNSTREAM") == "Downstream"
    assert normalize_segment("Petrochemicals") == "Petrochemicals"
    fac = make_facility(name=uniq("SegFac"), region=uniq("R"))
    fac.segment = "upstream "  # stored before the fix
    db.session.add(Emission(facility_id=fac.id, year=2013, month=1, process_type="combustion", co2e_total=1,
                            status="Verified"))
    db.session.commit()
    q = apply_scope(Emission.query, Emission, segment="Upstream").filter(Emission.facility_id == fac.id)
    assert q.count() == 1  # the listed "Upstream" did not match "upstream "
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/facilities", json={"name": uniq("SegNew"), "region": uniq("R"), "segment": "midstream"})
        assert r.status_code in (200, 201), r.get_json()


def test_15_year_lists_cover_the_users_facilities_only(ctx):
    from routes.dashboard import _query_available_years

    mine = make_facility(name=uniq("YrMine"), region=uniq("R"))
    other = make_facility(name=uniq("YrOther"), region=uniq("R"))
    db.session.add_all([
        Emission(facility_id=mine.id, year=2014, month=1, process_type="combustion", co2e_total=1, status="Verified"),
        Emission(facility_id=other.id, year=1987, month=1, process_type="combustion", co2e_total=1, status="Verified"),
    ])
    db.session.commit()
    years = _query_available_years([mine.id])
    assert 2014 in years and 1987 not in years
    user = make_user("user", mine.region)
    with app.test_client() as c:
        login(c, user)
        assert 1987 not in c.get("/api/filters/available").get_json()["years"]


def test_18_gwp20_breakdown_reweights_scope2_like_the_summary(ctx):
    from routes.dashboard import _query_categorical_breakdown, clear_dashboard_cache
    from services.scope2_gases import record_totals

    fac = make_facility(name=uniq("G20Fac"), region=uniq("R"))
    e = Scope2Emission(facility_id=fac.id, year=2015, month=1, source_type="electricity", electricity_kwh=100000,
                       emission_factor=0.5, co2e=50.0, co2e_location_based=50.0, status="Verified")
    db.session.add(e)
    db.session.commit()
    loc20, _ = record_totals(e, "20")
    clear_dashboard_cache()
    rows = _query_categorical_breakdown(year=2015, facility_id=fac.id, gwp_horizon="20")
    assert rows[0]["total_emissions"] == pytest.approx(loc20)
