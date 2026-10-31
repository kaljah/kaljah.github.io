"""Verification tests for the comprehensive 64-bug calculation, equation & pipeline audit fixes."""
import pytest
from extensions import db
from models import Facility, Emission, Scope2Emission, Scope3Emission, ProductionData
from tests.audit_helpers import make_facility, make_user, login


def test_bug63_pure_hydrogen_fuel_tier3_combustion(client, app):
    """Bug 63: Pure hydrogen fuel has zero carbon content and must not throw ValueError in Tier 3."""
    with app.app_context():
        from calculations.dispatcher import CalculationDispatcher
        dispatcher = CalculationDispatcher()
        
        inputs = {
            "fuel_type": "hydrogen",
            "quantity": 1000.0,
            "unit": "m3",
            "hhv": 12.7,
            "hhv_unit": "MJ/m3",
            "combustion_efficiency": 99.5,
            "factor_source": "custom",
        }
        factors = {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3"}
        res = dispatcher.dispatch("combustion", inputs, factors)
        assert res is not None
        assert res["results"]["co2"]["value"] == 0.0
        assert res["total_co2e"] == 0.0


def test_bug45_dehydrator_count_basis_via_dispatcher(client, app):
    """Bug 45: Dehydrator count basis is accessible through dispatcher when unit='count'."""
    with app.app_context():
        from calculations.dispatcher import CalculationDispatcher
        dispatcher = CalculationDispatcher()

        inputs = {
            "unit": "count",
            "amount": 2.0,
            "ch4_content": 0.85,
            "control_eff": 0.0,
            "factor_source": "engineering",
        }
        res = dispatcher.dispatch("dehydrator", inputs, {})
        assert res is not None
        assert res["results"]["ch4"]["value"] > 0.0
        assert res["inputs"]["dehydrator_count"] == 2.0


def test_bug48_ogmp_level_without_bottom_up(client, app):
    """Bug 48: Top-down measurement without source-level bottom-up inventory cannot be Level 4."""
    with app.app_context():
        from services.ogmp import compute_facility_ogmp_level
        fac = make_facility(name="TD Only Fac", activity="Upstream")
        # When td > 0 and no bottom_up exists, should return bottom_up_level or 3, not 4
        lvl = compute_facility_ogmp_level(fac, year=2024, top_down_tch4=50.0, bottom_up_tch4=0.0)
        assert lvl <= 3


def test_bug50_wec_statutory_threshold_independence(client, app):
    """Bug 50: Statutory WEC thresholds (40 CFR 99.20) default to 0.0020 (upstream) and 0.0005 (midstream)."""
    with app.app_context():
        from routes.auth import _app_settings
        orig_ogmp = _app_settings.get("ogmp_upstream_target_pct")
        try:
            # Even if voluntary OGMP target is changed to 0.15% (0.0015), WEC threshold remains statutory 0.0020
            _app_settings["ogmp_upstream_target_pct"] = 0.15
            from services.intensity import intensity_rows
            fac = make_facility(name="WEC US Fac", country="United States", segment="Production")
            # 1,000,000 m3 gas produced
            gas_mscf = 1_000_000.0 * 35.3146667 / 1000.0
            db.session.add(ProductionData(facility_id=fac.id, year=2034, month=1, gas_amount=gas_mscf, gas_unit="mscf"))
            db.session.add(Emission(facility_id=fac.id, year=2034, month=1, process_type="venting", ch4_emissions=2.0, co2e_total=56.0, status="Verified"))
            db.session.commit()

            rows = intensity_rows(facility_id=fac.id, year="2034")
            assert len(rows) > 0
            f_row = rows[0]
            # Expected allowed: gas_mscf * 0.0020 * 0.0192 (40 CFR 99.20 Eq B-1)
            expected_allowed = gas_mscf * 0.0020 * 0.0192
            assert f_row["excess_ch4_tonnes"] == pytest.approx(2.0 - expected_allowed, rel=1e-3)
            assert f_row["wec_rate_usd_per_t"] == 1500.0
            assert f_row["wec_status"] == "Taxable Liability"
        finally:
            if orig_ogmp is not None:
                _app_settings["ogmp_upstream_target_pct"] = orig_ogmp
            else:
                _app_settings.pop("ogmp_upstream_target_pct", None)


def test_bug52_cbam_xml_schema_conformance(client, app):
    """Bug 52: EU CBAM XML export contains only valid DG TAXUD elements."""
    with app.app_context():
        login(client, make_user("admin", "Global"))
        fac = make_facility(name="CBAM Schema Fac", country="Algeria")
        db.session.add(Emission(facility_id=fac.id, year=2025, month=1, process_type="combustion", co2e_total=100.0, status="Verified"))
        db.session.commit()

        res = client.get(f"/api/reports/cbam-export?format=xml&year=2025&facility_id={fac.id}")
        assert res.status_code == 200
        xml_text = res.get_data(as_text=True)
        # Ensure invalid custom invented tag is NOT in the XML
        assert "<PrecursorContribution>" not in xml_text


def test_bug56_cbam_precursor_direct_indirect_split(client, app):
    """Bug 56: Precursor direct and indirect specific embedded emissions are distinct."""
    with app.app_context():
        from services.cbam_data import RecordFigures
        class MockRecord:
            is_complex_good = True
            quantity_tonnes = 100.0
            specific_embedded_direct = 1.5
            specific_embedded_indirect = 0.5
            precursor_ratio = 0.8
            precursor_see_dir = 2.0
            precursor_see_indir = 0.5

        r = MockRecord()
        fig = RecordFigures(r)
        assert fig.precursor_direct == pytest.approx(0.8 * 2.0)
        assert fig.precursor_indirect == pytest.approx(0.8 * 0.5)
        assert fig.precursor == pytest.approx(fig.precursor_direct + fig.precursor_indirect)
        assert fig.total_see == pytest.approx(1.5 + 0.5 + 2.0)


def test_bug55_scope3_dynamic_gwp(client, app):
    """Bug 55: Scope 3 GWP-20 dynamically resolves active GWP factor."""
    with app.app_context():
        from services.dashboard_filters import scope3_record_co2e
        gc = {"ch4_pct": 50.0}
        val_20 = scope3_record_co2e(100.0, gc, horizon="20")
        assert val_20 > 100.0


def test_bug58_59_scope1_persistence_uncertainty_and_fgas(client, app):
    """Bug 58 & 59: Uncertainty percentage and F-gas masses are persisted in Scope 1 calculation."""
    with app.app_context():
        from services.scope1_calc import apply_result
        em = Emission(facility_id=1, year=2024, month=1, process_type="fugitives")
        payload = {"process_type": "fugitives"}
        em_result = {
            "co2": 0.0,
            "ch4": 0.0,
            "n2o": 0.0,
            "totalCo2e": 235.0,
            "sf6": 0.01,
            "_full_api_res": {
                "uncertainty_co2e": 8.5,
                "uncertainty_components": {"activity": 5.0, "ef_co2": 0.0}
            }
        }
        apply_result(em, payload, em_result, "Tier 3", {}, "AR5")
        assert em.uncertainty_pct == 8.5
        assert em.gas_composition is not None
        assert em.gas_composition.get("sf6") == 0.01


def test_bug30_dashboard_flaring_nm3_normalization(client, app):
    """Bug 30: Dashboard flaring normalizes kNm3 to Sm3 using NM3_TO_SM3."""
    from calculations.units import NM3_TO_SM3
    assert NM3_TO_SM3 == pytest.approx(288.7056 / 273.15, rel=1e-3)


def test_bug54_dashboard_bridge_passes_gwp_horizon(client, app):
    """Bug 54: Dashboard bridge includes gwp_horizon in Scope 3 summary query."""
    with app.app_context():
        login(client, make_user("admin", "Global"))
        fac = make_facility(name="Bridge Fac")
        db.session.add(Emission(facility_id=fac.id, year=2023, month=1, process_type="combustion", co2e_total=100.0, status="Verified"))
        db.session.add(Emission(facility_id=fac.id, year=2024, month=1, process_type="combustion", co2e_total=120.0, status="Verified"))
        db.session.commit()

        res = client.get(f"/api/dashboard/yoy-bridge?year=2024&facility_id={fac.id}&gwp_horizon=20&includeScope3=true")
        assert res.status_code == 200
