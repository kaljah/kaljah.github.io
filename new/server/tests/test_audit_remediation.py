import pytest
from app import app
from models import db, User, Facility, Emission, Scope2Emission, Scope3Emission, ProductionData, ActivityLog
from calculations.dispatcher import CalculationDispatcher
from calculations.stoichiometry import StoichiometricCalculator
from calculations.base import BaseCalculator


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def test_users():
    with app.app_context():
        admin = User.query.filter_by(email="audit_admin@test.com").first()
        if not admin:
            admin = User(
                email="audit_admin@test.com",
                fullName="Audit Admin",
                orgName="AuditCorp",
                sector="Energy",
                role="admin",
                location="Hassi Messaoud",
            )
            admin.set_password("AuditAdmin123!")
            db.session.add(admin)

        it_admin = User.query.filter_by(email="audit_itadmin@test.com").first()
        if not it_admin:
            it_admin = User(
                email="audit_itadmin@test.com",
                fullName="Audit IT Admin",
                orgName="AuditCorp",
                sector="IT",
                role="it_admin",
                location="Algiers",
            )
            it_admin.set_password("AuditItAdmin123!")
            db.session.add(it_admin)

        regular = User.query.filter_by(email="audit_user@test.com").first()
        if not regular:
            regular = User(
                email="audit_user@test.com",
                fullName="Audit Standard User",
                orgName="AuditCorp",
                sector="Energy",
                role="user",
                location="Hassi Messaoud",
            )
            regular.set_password("AuditUser123!")
            db.session.add(regular)

        fac = Facility.query.filter_by(name="Remediation Test Facility").first()
        if not fac:
            fac = Facility(
                name="Remediation Test Facility",
                location="Hassi Messaoud",
                boundary_type="Operational Control",
                segment="Upstream",
            )
            db.session.add(fac)

        db.session.commit()
        return {
            "admin": admin.id,
            "it_admin": it_admin.id,
            "user": regular.id,
            "facility_id": fac.id,
        }


def test_dispatcher_kg_per_tonne_factor():
    """Verify that a factor with unit 'kg/tonne' is not inflated by 1,000x."""
    dispatcher = CalculationDispatcher()
    calc_data = {
        "process_type": "custom",
        "calc_method": "custom",
        "amount": 10.0,
        "quantity": 10.0,
        "unit": "tonne",
    }
    factor_data = {
        "co2": 2.5,
        "ch4": 0.0,
        "n2o": 0.0,
        "unit": "kg/tonne",
    }
    res = dispatcher.dispatch("custom", calc_data, factor_data, {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
    assert res is not None
    assert abs(res["results"]["co2"]["value"] - 0.025) < 1e-6
    assert abs(res["total_co2e"] - 0.025) < 1e-6


def test_dispatcher_fraction_boundary():
    """Verify _require_fraction handles boundary values and percentages cleanly."""
    dispatcher = CalculationDispatcher()
    val = dispatcher._require_fraction({"eff": 1.0}, "eff", "combustion_efficiency")
    assert val == 1.0

    val_pct = dispatcher._require_fraction({"eff": "100%"}, "eff", "combustion_efficiency")
    assert val_pct == 1.0

    val_95 = dispatcher._require_fraction({"eff": "95%"}, "eff", "combustion_efficiency")
    assert abs(val_95 - 0.95) < 1e-6


def test_stoichiometry_short_ton():
    """Verify short ton conversion to kg (907.185 kg)."""
    calc = StoichiometricCalculator()
    res_short = calc.calculate(1.0, 1.0, {}, mass_unit="ton")
    expected_short_co2 = 907.185 * (44.01 / 12.011) / 1000.0
    assert abs(res_short["results"]["co2"]["value"] - expected_short_co2) < 0.01

    res_metric = calc.calculate(1.0, 1.0, {}, mass_unit="tonne")
    expected_metric_co2 = 1000.0 * (44.01 / 12.011) / 1000.0
    assert abs(res_metric["results"]["co2"]["value"] - expected_metric_co2) < 0.01


def test_base_calculator_uncertainty_k_factor():
    """Verify calculate_uncertainty applies k=2.0 coverage factor for 95% CI."""
    calc = BaseCalculator("TestModule", "Section 1")
    res = calc.calculate_uncertainty(
        value=100.0,
        relative_uncertainty=0.05,
        coverage_factor=2.0,
    )
    assert res["coverage_factor"] == 2.0
    assert res["confidence_level_pct"] == 95
    assert abs(res["abs_uncertainty_95"] - 10.0) < 1e-6
    assert abs(res["lower_bound"] - 90.0) < 1e-6
    assert abs(res["upper_bound"] - 110.0) < 1e-6


def test_profile_location_immutability(client, test_users):
    """Verify that regular users cannot alter their regional location assignment via /profile."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]

    resp = client.put(
        "/api/auth/profile",
        json={
            "fullName": "Updated Audit User",
            "location": "Global Corporate Head Office",
            "department": "HSE Engineering",
        },
    )
    assert resp.status_code == 200

    with app.app_context():
        user = db.session.get(User, test_users["user"])
        assert user.fullName == "Updated Audit User"
        assert user.department == "HSE Engineering"
        assert user.location == "Hassi Messaoud"


def test_audit_sod_for_it_admin(client, test_users):
    """Verify that IT Admin sees only security/account actions and diffs are redacted."""
    with app.app_context():
        log_op = ActivityLog(
            action="CREATE",
            entity="Emission",
            record_id="REC-TEST-999",
            user_name="Audit Standard User",
            details="Created Scope 1 Combustion Emission: 500 tCO2e",
            old_values=None,
            new_values='{"quantity": 1000, "co2e_total": 500}',
        )
        log_sec = ActivityLog(
            action="LOGIN",
            entity="User",
            record_id=str(test_users["user"]),
            user_name="Audit Standard User",
            details="User logged in: audit_user@test.com",
            old_values=None,
            new_values=None,
        )
        db.session.add(log_op)
        db.session.add(log_sec)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["it_admin"]

    resp = client.get("/api/audit/")
    assert resp.status_code == 200
    data = resp.get_json()
    actions = [l["action"] for l in data["logs"]]
    assert "CREATE" not in actions
    assert "LOGIN" in actions

    for l in data["logs"]:
        assert l["old_values"] is None
        assert l["new_values"] is None


def test_scope3_server_side_calculation(client, test_users):
    """Verify that create_scope3_emission computes co2e server-side and rejects spoofed values."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    resp = client.post(
        "/api/scope3",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "category": "Category 11",
            "activity_data": 1000.0,
            "emission_factor": 50.0,
            "unit": "units",
            "co2e": 0.001,
        },
    )
    assert resp.status_code in [200, 201]

    with app.app_context():
        e = Scope3Emission.query.filter_by(
            facility_id=test_users["facility_id"], year=2026
        ).order_by(Scope3Emission.id.desc()).first()
        assert e is not None
        assert abs(e.co2e - 50.0) < 1e-4


def test_production_upsert_and_delete_audit(client, test_users):
    """Verify ProductionData atomic upsert and audit logging on delete."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    res1 = client.post(
        "/api/data/production",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 5,
            "oil_amount": 10000.0,
            "gas_amount": 5000.0,
            "oil_unit": "bbl",
            "gas_unit": "mscf",
        },
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/api/data/production",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 5,
            "oil_amount": 12000.0,
            "gas_amount": 6000.0,
            "oil_unit": "bbl",
            "gas_unit": "mscf",
        },
    )
    assert res2.status_code == 200

    with app.app_context():
        p = ProductionData.query.filter_by(
            facility_id=test_users["facility_id"], year=2026, month=5
        ).all()
        assert len(p) == 1
        assert p[0].oil_amount == 12000.0
        prod_id = p[0].id

    del_res = client.delete(f"/api/data/production/{prod_id}")
    assert del_res.status_code == 200

    with app.app_context():
        assert db.session.get(ProductionData, prod_id) is None
        log = ActivityLog.query.filter_by(
            entity="ProductionData", action="DELETE", record_id=str(prod_id)
        ).first()
        assert log is not None


def test_scope2_rbac_and_creator_ownership(client, test_users):
    """Verify viewer/auditor blocked from mutate on Scope 2, and creator ownership enforced."""
    with app.app_context():
        viewer = User.query.filter_by(email="audit_viewer@test.com").first()
        if not viewer:
            viewer = User(
                email="audit_viewer@test.com",
                fullName="Audit Viewer",
                orgName="AuditCorp",
                sector="Energy",
                role="viewer",
                location="Hassi Messaoud",
            )
            viewer.set_password("AuditViewer123!")
            db.session.add(viewer)

        other_user = User.query.filter_by(email="audit_user2@test.com").first()
        if not other_user:
            other_user = User(
                email="audit_user2@test.com",
                fullName="Other Standard User",
                orgName="AuditCorp",
                sector="Energy",
                role="user",
                location="Hassi Messaoud",
            )
            other_user.set_password("OtherUser123!")
            db.session.add(other_user)

        db.session.commit()
        viewer_id = viewer.id
        other_user_id = other_user.id

    # 1. Viewer cannot create Scope 2 emission
    with client.session_transaction() as sess:
        sess["user_id"] = viewer_id

    res_v = client.post(
        "/api/scope2",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 6,
            "source_type": "electricity",
            "electricity_kwh": 5000,
            "emission_factor": 0.5,
        },
    )
    assert res_v.status_code == 403

    # 2. Standard user creates Scope 2 emission
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]

    res_u = client.post(
        "/api/scope2",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 6,
            "source_type": "electricity",
            "electricity_kwh": 5000,
            "emission_factor": 0.5,
        },
    )
    assert res_u.status_code == 201
    rec_id = res_u.get_json()["id"]

    # 3. Viewer cannot update Scope 2 emission
    with client.session_transaction() as sess:
        sess["user_id"] = viewer_id
    res_vu = client.put(f"/api/scope2/{rec_id}", json={"electricity_kwh": 6000})
    assert res_vu.status_code == 403

    # 4. Other standard user cannot update another user's Scope 2 emission
    with client.session_transaction() as sess:
        sess["user_id"] = other_user_id
    res_other = client.put(f"/api/scope2/{rec_id}", json={"electricity_kwh": 6000})
    assert res_other.status_code == 403

    # 5. Record creator CAN update own Scope 2 emission
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]
    res_own = client.put(f"/api/scope2/{rec_id}", json={"electricity_kwh": 6000, "emission_factor": 0.5})
    assert res_own.status_code == 200


def test_scope2_case_insensitive_recalc_and_steam_amount(client, test_users):
    """Verify case-insensitive recalculation and steam_ton mapping in Scope 2."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    # 1. Create with source_type="electricity" (lowercase) and verify recalculation on update
    res_el = client.post(
        "/api/scope2",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 7,
            "source_type": "electricity",
            "amount": 10000,
            "unit": "kWh",
            "emission_factor": 0.5,
        },
    )
    assert res_el.status_code == 201
    el_id = res_el.get_json()["id"]

    # Update electricity usage and factor - should recalculate co2e even if source_type is stored lowercase
    res_up = client.put(
        f"/api/scope2/{el_id}",
        json={
            "electricity_kwh": 20000,
            "emission_factor": 0.6,
        },
    )
    assert res_up.status_code == 200
    with app.app_context():
        rec_el = db.session.get(Scope2Emission, el_id)
        # 20,000 kWh * 0.6 kgCO2/kWh / 1000 = 12.0 tCO2e
        assert abs(rec_el.co2e - 12.0) < 1e-4

    # 2. Create indirect steam entry with amount and unit="ton"
    res_steam = client.post(
        "/api/scope2",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 8,
            "source_type": "indirect_steam",
            "amount": 250.0,
            "unit": "ton",
        },
    )
    assert res_steam.status_code == 201
    steam_id = res_steam.get_json()["id"]
    with app.app_context():
        rec_steam = db.session.get(Scope2Emission, steam_id)
        assert rec_steam.steam_ton == 250.0


def test_bulk_anomaly_flag_persistence(client, test_users):
    """Verify that background anomaly detection flags are stored in emission.qa_flag."""
    from calculations.anomaly import AnomalyDetector
    anomaly_detector = AnomalyDetector()
    with app.app_context():
        # Seed 3 baseline emissions to establish statistical distribution
        for m in [1, 2, 3]:
            base_e = Emission(
                facility_id=test_users["facility_id"],
                year=2025,
                month=m,
                process_type="combustion",
                fuel_type="Diesel",
                quantity=100.0,
                co2e_total=100.0,
                status="Verified",
            )
            db.session.add(base_e)
        db.session.commit()

        # High value that triggers outlier flag
        emission = Emission(
            facility_id=test_users["facility_id"],
            year=2026,
            month=9,
            process_type="combustion",
            fuel_type="Diesel",
            quantity=999999999.0,
            co2e_total=5000000.0,
            status="Pending",
        )
        anomaly = anomaly_detector.check_scope1(
            emission.facility_id,
            emission.process_type,
            emission.co2e_total,
            emission.year,
            emission.month,
        )
        assert anomaly.get("flagged") is True
        flag_msg = anomaly.get("message") or "Statistical Anomaly"
        emission.qa_flag = flag_msg[:255]
        db.session.add(emission)
        db.session.commit()

        saved = db.session.get(Emission, emission.id)
        assert saved.qa_flag is not None
        assert len(saved.qa_flag) > 0
        assert "5000000" in saved.qa_flag or "constant" in saved.qa_flag or "Z-score" in saved.qa_flag


def test_fugitive_screening_count_and_fraction():
    """Finding 1: Verify fugitive screening calculation handles component count and ch4_fraction."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "fugitive",
        "factor_source": "specific",
        "fugitive_method": "screening",
        "fugitive_ppm": 15000,  # >= 10000 -> multiplier 2.5
        "amount": 20,           # 20 components
        "hours": 1000,          # 1000 hours
        "ch4_fraction": 0.8,    # 80% CH4
    }
    factor_data = {
        "factor": 0.01,         # 0.01 kg CH4/hr/comp
        "unit": "kg/hr",
    }
    res = dispatcher.dispatch("fugitive", payload, factor_data, {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
    assert res is not None
    # Expected: 20 * 0.01 * 2.5 * 1000 * 0.8 = 400 kg CH4 = 0.4 tonnes CH4
    assert abs(res["results"]["ch4"]["value"] - 0.4) < 1e-5
    assert abs(res["total_co2e"] - (0.4 * 28.0)) < 1e-4


def test_agr_zero_removal_boundary():
    """Finding 2: Verify AGR zero removal boundary condition does not create false 99% removal."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "agr",
        "factor_source": "specific",
        "amount": 100,  # 100 MMscf/yr
        "unit": "mmscf",
        "agr_co2_in": 0.04,   # 4%
        "agr_co2_out": 0.04,  # 4% (equal inlet and outlet, zero true removal)
        "agr_ch4_in": 0.85,
        "agr_ch4_slip": 0.0,
        "agr_control_eff": 0.0,
    }
    res = dispatcher.dispatch("agr", payload, {}, {})
    assert res is not None
    # With equal inlet and outlet, CO2 removed should be 0.0
    assert abs(res["results"]["co2"]["value"] - 0.0) < 1e-6


def test_dispatcher_generic_volume_and_mass_conversions():
    """Finding 3: Verify _generic_calculation converts when factor denominator is scf, bbl, gal."""
    dispatcher = CalculationDispatcher()
    # 10 barrels input with factor in kg/gal
    calc_data = {
        "process_type": "custom",
        "calc_method": "custom",
        "quantity": 10.0,
        "unit": "bbl",
    }
    factor_data = {
        "co2": 5.0,
        "unit": "kg/gal",
    }
    res = dispatcher.dispatch("custom", calc_data, factor_data, {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
    # 10 bbl = 420 gal; 420 * 5.0 kg = 2100 kg = 2.1 tonnes
    assert abs(res["results"]["co2"]["value"] - 2.1) < 0.05


def test_dispatcher_mmbtu_liquid_fuel_hhv():
    """Finding 4: Verify liquid fuel uses ~138,000 Btu/gal HHV under mmbtu factor, not gas 1020 Btu/scf."""
    dispatcher = CalculationDispatcher()
    calc_data = {
        "process_type": "combustion",
        "fuel_type": "Diesel",
        "quantity": 1000.0,  # 1000 gallons
        "unit": "gal",
    }
    factor_data = {
        "co2": 74.0,  # 74 kg CO2 / MMBtu
        "unit": "kg/mmbtu",
    }
    res = dispatcher.dispatch("combustion", calc_data, factor_data, {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
    # 1000 gal * 138,000 Btu/gal = 138 MMBtu
    # 138 MMBtu * 74 kg/MMBtu = 10,212 kg = 10.212 tonnes
    assert abs(res["results"]["co2"]["value"] - 10.212) < 0.1


def test_dispatcher_gram_factor_numerator():
    """Finding 5: Verify factors in g/unit (e.g. g/kWh) are divided by 1,000,000 to yield metric tonnes."""
    dispatcher = CalculationDispatcher()
    calc_data = {
        "process_type": "custom",
        "quantity": 10000.0,  # 10,000 kWh
        "unit": "kwh",
    }
    factor_data = {
        "co2": 500.0,  # 500 g CO2 / kWh
        "unit": "g/kwh",
    }
    res = dispatcher.dispatch("custom", calc_data, factor_data, {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
    # 10,000 kWh * 500 g/kWh = 5,000,000 grams = 5.0 tonnes
    assert abs(res["results"]["co2"]["value"] - 5.0) < 1e-5


def test_combustion_factor_prefix_tco2_and_gram():
    """Finding 6: Verify convert_factor_to_kg_per_unit handles tco2, tch4, tn2o and g/ prefixes."""
    from calculations.combustion import convert_factor_to_kg_per_unit
    # 2.5 tCO2/m3 -> 2500 kg/m3
    assert abs(convert_factor_to_kg_per_unit(2.5, "tco2/m3", "m3") - 2500.0) < 1e-4
    # 1.8 mt/m3 -> 1800 kg/m3
    assert abs(convert_factor_to_kg_per_unit(1.8, "mt/m3", "m3") - 1800.0) < 1e-4
    # 500 g/kwh -> 0.5 kg/kwh
    assert abs(convert_factor_to_kg_per_unit(500.0, "g/kwh", "kwh") - 0.5) < 1e-4


def test_sentinel5p_column_mass_flux():
    """Finding 7: Verify Sentinel-5P flux calculation uses full atmospheric column air mass (~10,332 kg/m2)."""
    from services.sentinel5p import sentinel5p_service, TOTAL_COLUMN_AIR_MASS_KG_M2
    # Check physical constant
    assert 10300 < TOTAL_COLUMN_AIR_MASS_KG_M2 < 10350

    rate = sentinel5p_service.estimate_emission_rate_from_anomaly(
        delta_ch4_ppb=100.0,
        wind_speed_m_s=3.0,
        box_width_km=10.0,
    )
    # Expected: 100e-9 * (16.042 / 28.97) * 10332.27 * 10000 * 3.0 * 3600 = ~61791.64 kg CH4/hr
    assert 60000 < rate < 63000


def test_uncertainty_combine_sum_negative_sinks():
    """Finding 8: Verify combine_uncertainties_sum returns non-negative relative uncertainty on net sinks."""
    from calculations.uncertainty import combine_uncertainties_sum
    # Net negative sink: -100 tCO2e offset and +20 tCO2e residual = -80 tCO2e net
    u_rel = combine_uncertainties_sum(-100.0, 0.10, 20.0, 0.05)
    assert u_rel > 0.0
    # Absolute zero sum guard
    u_zero = combine_uncertainties_sum(50.0, 0.10, -50.0, 0.10)
    assert u_zero == 0.0


def test_anomaly_iqr_quantile_interpolation():
    """Finding 9: Verify IQR quantile calculation does not distort on small N >= 4."""
    from calculations.anomaly import AnomalyDetector
    detector = AnomalyDetector()
    # 4 historical values: [100, 102, 104, 106]
    hist = [100.0, 102.0, 104.0, 106.0]
    res_normal = detector._z_score_check(105.0, hist)
    assert res_normal["flagged"] is False

    # Extreme outlier
    res_outlier = detector._z_score_check(500.0, hist)
    assert res_outlier["flagged"] is True


def test_scope3_tonne_factor_handling(client, test_users):
    """Finding 10: Verify Scope 3 does not divide by 1000 when factor is in tCO2e/unit."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    resp = client.post(
        "/api/scope3",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "category": "Category 1",
            "activity_data": 50.0,
            "emission_factor": 2.0,
            "factor_unit": "tCO2e/unit",
            "unit": "tonnes",
        },
    )
    assert resp.status_code in [200, 201]

    with app.app_context():
        rec = Scope3Emission.query.filter_by(
            facility_id=test_users["facility_id"], year=2026, category="Category 1"
        ).order_by(Scope3Emission.id.desc()).first()
        assert rec is not None
        # 50.0 * 2.0 = 100.0 tCO2e (not 0.1 tCO2e)
        assert abs(rec.co2e - 100.0) < 1e-4


def test_dashboard_sbti_zero_actuals(client, test_users):
    """Finding 11: Verify SBTi net-zero endpoint preserves legitimate 0.0 tCO2e actuals."""
    from models import SbtiTarget
    test_year = 2015
    with app.app_context():
        target = SbtiTarget(
            base_year=test_year,
            base_year_emissions=1000.0,
            target_year=2030,
            reduction_rate_pct=4.2,
            pathway_type="1.5C",
        )
        db.session.add(target)
        db.session.commit()

        # Add a verified emission with 0.0 tCO2e for test_year
        e_zero = Emission.query.filter_by(
            facility_id=test_users["facility_id"], year=test_year
        ).first()
        if not e_zero:
            e_zero = Emission(
                facility_id=test_users["facility_id"],
                year=test_year,
                month=1,
                process_type="combustion",
                fuel_type="Diesel",
                quantity=0.0,
                co2e_total=0.0,
                status="Verified",
            )
            db.session.add(e_zero)
        else:
            e_zero.co2e_total = 0.0
            e_zero.status = "Verified"
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    resp = client.get(f"/api/dashboard/sbti-trajectory?facility_id={test_users['facility_id']}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "trajectory" in data
    traj_test = next((t for t in data["trajectory"] if t["year"] == str(test_year)), None)
    assert traj_test is not None
    # Verified 0.0 record must yield actual == 0.0, NOT None
    assert traj_test["actual"] == 0.0


def test_unit_conversions_mscf_mcf_bidirectional():
    """Verify bidirectional mscf, mcf, and mmscf conversions in units.py."""
    from calculations.units import convert
    import pytest

    # 1 Mscf = 1,000 scf = 28.316846592 m3
    m3_val = convert(10.0, "mscf", "m3")
    assert pytest.approx(m3_val, 1e-4) == 283.1685
    mscf_back = convert(m3_val, "m3", "mscf")
    assert pytest.approx(mscf_back, 1e-5) == 10.0

    # Mcf identical to Mscf
    mcf_m3 = convert(5.0, "mcf", "m3")
    assert pytest.approx(mcf_m3, 1e-4) == 141.5842
    mcf_back = convert(mcf_m3, "m3", "mcf")
    assert pytest.approx(mcf_back, 1e-5) == 5.0

    # MMscf to scf
    scf_val = convert(2.5, "mmscf", "scf")
    assert pytest.approx(scf_val, 1e-3) == 2_500_000.0
    mmscf_back = convert(scf_val, "scf", "mmscf")
    assert pytest.approx(mmscf_back, 1e-6) == 2.5


def test_dehydrator_stoichiometric_co2_combustion():
    """Verify DehydratorCalculator accurately generates stoichiometric CO2 when gas is flared."""
    from calculations.midstream import DehydratorCalculator

    calc = DehydratorCalculator()
    res = calc.calculate(
        pump_rate=100.0,
        pump_unit="gph",
        hours=8760,
        ch4_content=0.90,
        has_flash_tank=False,
        still_control_type="flare",
        control_eff=0.98,
    )
    # 98% CH4 converted to CO2 stoichiometrically (44.01 / 16.04 = ~2.7438)
    assert res["results"]["ch4"]["value"] > 0
    assert res["results"]["co2"]["value"] > 0
    assert res["inputs"]["combusted_co2_tonnes"] > 0
    # CO2 mass should exceed the destroyed CH4 mass by roughly 2.74x
    destroyed_ch4 = (res["results"]["ch4"]["value"] / 0.02) * 0.98
    expected_co2 = destroyed_ch4 * (44.01 / 16.04)
    assert abs(res["results"]["co2"]["value"] - expected_co2) < 0.01


def test_dashboard_intensity_mmscf_scaling(client, test_users):
    """Verify _query_intensity_stats properly normalizes MMscf gas and flaring volumes."""
    from routes.dashboard import _query_intensity_stats
    from models import ProductionData

    with app.app_context():
        fid = test_users["facility_id"]
        # Clear existing production for test year 2029
        ProductionData.query.filter_by(facility_id=fid, year=2029).delete()
        Emission.query.filter_by(facility_id=fid, year=2029).delete()

        # Add 10 MMscf gas production
        prod = ProductionData(
            facility_id=fid,
            year=2029,
            month=1,
            oil_amount=100.0,
            oil_unit="bbl",
            gas_amount=10.0,
            gas_unit="mmscf",
        )
        db.session.add(prod)

        # Add 1 MMscf flaring emission
        flare_e = Emission(
            facility_id=fid,
            year=2029,
            month=1,
            process_type="flaring",
            fuel_type="Natural Gas",
            quantity=1.0,
            unit="mmscf",
            co2e_total=50.0,
            ch4_emissions=0.1,
            status="Verified",
        )
        db.session.add(flare_e)
        db.session.commit()

        stats = _query_intensity_stats(facility_id=str(fid), year="2029", allowed_fids=[fid])
        assert len(stats) > 0
        fac_stat = stats[0]
        # 10 MMscf = 283,168.0 m3
        assert abs(fac_stat["total_gas_m3"] - 283168.0) < 1.0
        # 10 MMscf = 10,000 Mscf -> BOE = 100 + (10,000 * 0.178) = 1,880 BOE
        assert abs(fac_stat["total_boe"] - 1880.0) < 1.0
        # 1 MMscf flaring = 28,316.8 m3
        assert abs(fac_stat["flaring_volume"] - 28316.8) < 1.0
        # Flaring rate % = 28,316.8 / 283,168.0 * 100 = 10.0%
        assert abs(fac_stat["flaring_rate_pct"] - 10.0) < 0.01


def test_dashboard_ogmp_target_status_segment_specific(client, test_users):
    """Verify midstream facility with 0.15% loss rate is Non-Compliant while upstream is Compliant."""
    from routes.dashboard import _query_intensity_stats, _query_intensity_trend_bulk
    from models import ProductionData

    with app.app_context():
        fid = test_users["facility_id"]
        fac = db.session.get(Facility, fid)
        fac.segment = "Midstream Processing"
        db.session.commit()

        # Set gas production and CH4 emission to produce exactly ~0.15% loss rate
        # 100,000 m3 gas -> 0.15% = 150 m3 CH4 -> 150 * 0.6785 / 1000 = 0.101775 tCH4
        ProductionData.query.filter_by(facility_id=fid, year=2028).delete()
        Emission.query.filter_by(facility_id=fid, year=2028).delete()

        prod = ProductionData(
            facility_id=fid,
            year=2028,
            month=1,
            oil_amount=0.0,
            oil_unit="bbl",
            gas_amount=100000.0,
            gas_unit="m3",
        )
        db.session.add(prod)

        em = Emission(
            facility_id=fid,
            year=2028,
            month=1,
            process_type="fugitive",
            quantity=100.0,
            co2e_total=10.0,
            ch4_emissions=0.1018,
            status="Verified",
        )
        db.session.add(em)
        db.session.commit()

        # Midstream evaluation (Target = 0.05%)
        stats_mid = _query_intensity_stats(facility_id=str(fid), year="2028", allowed_fids=[fid])
        assert len(stats_mid) > 0
        assert stats_mid[0]["ogmp_gold_standard_target"] == 0.05
        # Loss rate is ~0.15%, which exceeds 0.05% midstream target -> must be Non-Compliant
        assert stats_mid[0]["ogmp_target_status"] == "Non-Compliant"

        trend_mid = _query_intensity_trend_bulk(facility_id=str(fid), years=[2028], allowed_fids=[fid])
        assert len(trend_mid) > 0
        assert trend_mid[0]["data"][0]["ogmp_gold_standard_target"] == 0.05
        assert trend_mid[0]["data"][0]["ogmp_target_status"] == "Non-Compliant"

        # Change segment to Upstream Production (Target = 0.20%)
        fac.segment = "Upstream Production"
        db.session.commit()

        stats_up = _query_intensity_stats(facility_id=str(fid), year="2028", allowed_fids=[fid])
        assert len(stats_up) > 0
        assert stats_up[0]["ogmp_gold_standard_target"] == 0.20
        # Loss rate is ~0.15%, which is <= 0.20% upstream target -> must be Compliant
        assert stats_up[0]["ogmp_target_status"] == "Compliant"

        trend_up = _query_intensity_trend_bulk(facility_id=str(fid), years=[2028], allowed_fids=[fid])
        assert len(trend_up) > 0
        assert trend_up[0]["data"][0]["ogmp_gold_standard_target"] == 0.20
        assert trend_up[0]["data"][0]["ogmp_target_status"] == "Compliant"


def test_ogmp_survey_zero_top_down_no_false_discrepancy(client, test_users):
    """Verify zero top-down survey observation does not trigger spurious -100% discrepancy flag."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    payload = {
        "facility_id": test_users["facility_id"],
        "year": 2025,
        "survey_date": "2025-06-15",
        "survey_type": "OGI Camera (FLIR GF320)",
        "measured_rate_kg_hr": 0.0,  # Zero detection
        "operating_hours": 8760,
    }
    resp = client.post("/api/data/ogmp-surveys", json=payload)
    assert resp.status_code in [200, 201]
    data = resp.get_json()
    assert "id" in data
    from models import OgmpSurvey
    with app.app_context():
        survey = db.session.get(OgmpSurvey, data["id"])
        assert survey is not None
        # Variance should not evaluate to -100% and variance_flag must be False for zero top-down reading
        assert survey.variance_flag is False
        assert survey.variance_pct != -100.0


# ===========================================================================
# AUDIT REMEDIATION REGRESSION TESTS (DEFECTS 1 - 12)
# ===========================================================================

def test_notifications_stream_heartbeat_init(client, test_users):
    """Defect 1: Verify SSE stream initializes last_heartbeat and does not raise UnboundLocalError."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]
    res = client.get("/api/notifications/stream")
    try:
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type
    finally:
        res.close()


def test_scope2_steam_recalculation_enthalpy(client, test_users):
    """Defect 2: Verify indirect steam update uses thermodynamic enthalpy formula."""
    fid = test_users["facility_id"]
    with app.app_context():
        rec = Scope2Emission(
            facility_id=fid,
            year=2024,
            month=5,
            source_type="Steam / Purchased Heat",
            heat_mmbtu=100.0,
            emission_factor=0.06,
            co2e=6.0,
            status="Draft",
            created_by=test_users["admin"],
        )
        db.session.add(rec)
        db.session.commit()
        rec_id = rec.id

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    # Update steam: steam_ton=200.0, factor=0.06, steam enthalpy=2.75, boiler eff=0.8
    # enthalpy_mult = 2.75 / 0.8 = 3.4375
    # co2e = 200 * 0.06 * 3.4375 = 41.25 tCO2e
    res = client.put(f"/api/scope2/{rec_id}", json={
        "steam_ton": 200.0,
        "emission_factor": 0.06,
        "steam_enthalpy": 2.75,
        "boiler_efficiency": 0.8,
    })
    assert res.status_code == 200
    with app.app_context():
        updated = db.session.get(Scope2Emission, rec_id)
        assert pytest.approx(updated.co2e, 0.01) == 41.25


def test_scope3_eeio_per_thousand_scaling_defect(client, test_users):
    """Defect 3: Verify Scope 3 spend-based EEIO scales per-$1000 factor by 1,000,000."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    payload = {
        "facility_id": test_users["facility_id"],
        "year": 2024,
        "month": 6,
        "category": "Category 1",
        "sub_category": "Purchased Goods",
        "activity_data": 500000.0,  # $500,000
        "unit": "USD",
        "emission_factor": 3200.1,  # 3,200.1 kg CO2e / $1,000
        "factor_unit": "kg CO2e / $1,000",
        "calculation_method": "Spend-based (EEIO)",
    }
    res = client.post("/api/scope3", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    # 500,000 * 3200.1 / 1,000,000 = 1600.05 tCO2e
    assert pytest.approx(data["co2e"], 0.01) == 1600.05


def test_custom_factor_percentage_uncertainty_in_add_emission(client, test_users):
    """Defect 4: Verify custom factor with general uncertainty 5.0 is divided by 100 to 0.05."""
    from models import CustomFactor
    with app.app_context():
        cf = CustomFactor.query.filter_by(name="Test 5% Factor Audit").first()
        if not cf:
            cf = CustomFactor(
                name="Test 5% Factor Audit",
                co2_factor=1.5,
                ch4_factor=0.01,
                n2o_factor=0.001,
                unit="m3",
                uncertainty=5.0,  # 5%
                created_by=test_users["admin"],
            )
            db.session.add(cf)
            db.session.commit()
        cf_id = cf.id

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    payload = {
        "facility_id": test_users["facility_id"],
        "year": 2024,
        "month": 7,
        "process_type": "Combustion",
        "quantity": 100.0,
        "unit": "m3",
        "custom_factor_id": cf_id,
        "status": "Draft",
    }
    res = client.post("/api/emissions", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    with app.app_context():
        em = db.session.get(Emission, data["id"])
        # Propagated uncertainty with 5% EF uncertainty is ~0.0559 (5.59%), not > 5.0 (500%)
        assert em.uncertainty is not None
        assert 0.05 <= em.uncertainty < 0.06
        assert pytest.approx(em.uncertainty, 0.01) == 0.056


def test_update_emission_preserves_calc_payload(client, test_users):
    """Defect 5: Verify update_emission merges existing process_type and inputs."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    payload = {
        "facility_id": test_users["facility_id"],
        "year": 2024,
        "month": 8,
        "process_type": "Venting",
        "quantity": 500.0,
        "unit": "m3",
        "calc_method": "engineering_estimate",
        "status": "Draft",
    }
    res = client.post("/api/emissions", json=payload)
    assert res.status_code == 201
    em_id = res.get_json()["id"]

    update_res = client.put(f"/api/emissions/{em_id}", json={"quantity": 1000.0})
    assert update_res.status_code == 200
    with app.app_context():
        updated_em = db.session.get(Emission, em_id)
        assert updated_em.process_type == "Venting"
        assert updated_em.quantity == 1000.0


def test_bulk_import_scope2_and_3_rbac(client, test_users):
    """Defect 6: Verify bulk import for Scope 2 & 3 blocks it_admin and enforces allowed_fids."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["it_admin"]

    res_s2 = client.post("/api/scope2/bulk-import", json={"records": [{"facility_id": test_users["facility_id"]}]})
    assert res_s2.status_code == 403

    res_s3 = client.post("/api/scope3/bulk-import", json={"records": [{"facility_id": test_users["facility_id"]}]})
    assert res_s3.status_code == 403

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]

    res_unauth = client.post("/api/scope3/bulk-import", json={"records": [
        {"facility_id": 99999, "year": 2024, "amount": 100, "emission_factor": 1.0}
    ]})
    assert res_unauth.status_code in [200, 207]
    data = res_unauth.get_json()
    assert len(data.get("errors", [])) > 0


def test_qaqc_maker_checker_and_it_admin_blocked(client, test_users):
    """Defect 7: Verify IT admin cannot access QA/QC resolve and users cannot verify records they created."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["it_admin"]

    res_it = client.post("/api/qaqc/resolve/1", json={"scope": 1, "resolution": "Verified"})
    assert res_it.status_code == 403

    with app.app_context():
        em = Emission(
            facility_id=test_users["facility_id"],
            year=2024,
            month=1,
            co2e_total=100.0,
            status="Pending",
            created_by=test_users["admin"],
            qa_flag="Outlier",
        )
        db.session.add(em)
        db.session.commit()
        em_id = em.id

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    res_verify_own = client.post(f"/api/qaqc/resolve/{em_id}", json={"scope": 1, "resolution": "Verified"})
    assert res_verify_own.status_code == 403
    assert "Maker-checker violation" in res_verify_own.get_json()["error"]


def test_base_year_recalculation_rbac_and_singleton(client, test_users):
    """Defect 8: Verify base year recalculation route enforces role, sets created_by, and updates singleton."""
    from models import BaseYear, BaseYearRecalculation
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]
    res_user = client.post("/api/dashboard/base-year-recalculation", json={"year": 2020, "reason": "Structural change"})
    assert res_user.status_code == 403

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["it_admin"]
    res_it = client.post("/api/dashboard/base-year-recalculation", json={"year": 2020, "reason": "Structural change"})
    assert res_it.status_code == 403

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]
    res_admin = client.post("/api/dashboard/base-year-recalculation", json={
        "year": 2022,
        "reason": "Boundary revision",
        "previous_emissions": 50000.0,
        "adjusted_emissions": 52000.0,
    })
    assert res_admin.status_code == 201
    with app.app_context():
        singleton = db.session.get(BaseYear, 1)
        assert singleton is not None
        assert singleton.year == 2022
        rec = BaseYearRecalculation.query.filter_by(year=2022).first()
        assert rec is not None
        assert rec.created_by == test_users["admin"]


def test_cbam_export_existing_record_facility_check(client, test_users):
    """Defect 9: Verify save_cbam_export checks facility access for existing records before update."""
    from models import CbamProductExport
    with app.app_context():
        cbam = CbamProductExport(
            facility_id=test_users["facility_id"],
            year=2026,
            month=1,
            product_name="Cement",
            cn_code="2523",
            quantity_tonnes=100.0,
            export_destination="EU",
        )
        db.session.add(cbam)
        db.session.commit()
        cbam_id = cbam.id

        other_user = User.query.filter_by(email="other_restricted_cbam@test.com").first()
        if not other_user:
            other_user = User(
                email="other_restricted_cbam@test.com",
                fullName="Other User",
                orgName="AuditCorp",
                sector="Energy",
                role="user",
                location="Oran",
            )
            other_user.set_password("Pass123!")
            db.session.add(other_user)
            db.session.commit()
        other_uid = other_user.id

    with client.session_transaction() as sess:
        sess["user_id"] = other_uid

    res = client.post("/api/data/cbam-exports", json={
        "id": cbam_id,
        "facility_id": test_users["facility_id"],
        "product_name": "Cement Modified",
        "cn_code": "2523",
        "quantity_tonnes": 200.0,
    })
    assert res.status_code == 403


def test_background_processor_upload_jobs_lock():
    """Defect 10: Verify upload_jobs_lock exists and functions thread-safely."""
    from background_processor import upload_jobs, upload_jobs_lock, _update_job, _append_job_list, get_job_status
    import threading
    assert upload_jobs_lock is not None

    test_jid = "test-lock-job"
    with upload_jobs_lock:
        upload_jobs[test_jid] = {
            "status": "processing",
            "progress": 0,
            "processed": 0,
            "total": 100,
            "errors": [],
            "skipped": [],
            "anomalies": [],
            "created_at": 1000.0,
        }

    threads = []
    def worker():
        for i in range(10):
            _update_job(test_jid, progress=i)
            _append_job_list(test_jid, "skipped", {"row": i})
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    status = get_job_status(test_jid)
    assert status is not None
    assert status["skipped_count"] == 50
    with upload_jobs_lock:
        upload_jobs.pop(test_jid, None)


def test_delete_mitigation_record_admin_required(client, test_users):
    """Defect 11: Verify regular users cannot delete corporate MitigationRecord."""
    from models import MitigationRecord
    with app.app_context():
        rec = MitigationRecord(
            year=2024,
            type="Reforestation",
            quantity_tco2e=500.0,
            notes="Corporate offset",
        )
        db.session.add(rec)
        db.session.commit()
        rec_id = rec.id

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]
    res_user = client.delete(f"/api/mitigation/rec_{rec_id}")
    assert res_user.status_code == 403

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]
    res_admin = client.delete(f"/api/mitigation/rec_{rec_id}")
    assert res_admin.status_code == 200
    with app.app_context():
        assert db.session.get(MitigationRecord, rec_id) is None


def test_auth_update_user_role_whitelist(client, test_users):
    """Defect 12: Verify PUT /api/auth/users/<id> rejects invalid roles."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["it_admin"]

    res = client.put(f"/api/auth/users/{test_users['user']}", json={"role": "super_root_admin"})
    assert res.status_code == 400
    assert "Invalid role" in res.get_json()["error"]


def test_qaqc_fuel_completeness_non_combustion(client, test_users):
    """Verify non-combustion records (pneumatics, fugitives) without fuel do not depress QA/QC fuel_completeness."""
    with app.app_context():
        # Clear out test emissions for year 2099
        Emission.query.filter_by(year=2099).delete()
        db.session.commit()

        import uuid
        test_uid = uuid.uuid4().hex[:8]
        # Insert 3 non-combustion records without fuel
        for i in range(3):
            em = Emission(
                record_id=f"qaqc-test-nc-{test_uid}-{i}",
                year=2099,
                month=i + 1,
                facility_id=1,
                process_type="pneumatics",
                fuel_type=None,
                quantity=100.0,
                unit="count",
                co2_emissions=0.0,
                ch4_emissions=1.0,
                n2o_emissions=0.0,
                co2e_total=28.0,
                status="Verified",
                created_by=test_users["admin"],
            )
            db.session.add(em)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    res = client.get("/api/qaqc/dashboard?year=2099")
    assert res.status_code == 200
    data = res.get_json()
    metrics = data.get("diagnostics", {}).get("dimension_completeness", {})
    # Since all records in this set are non-combustion, fuel_source completeness should be 100.0%
    assert metrics.get("fuel_source") == 100.0


def test_scope2_authoritative_calculation_overrides_injected_co2e(client, test_users):
    """Verify Scope 2 recomputes co2e authoritatively even if client injects an arbitrary co2e."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    payload = {
        "year": 2024,
        "month": 5,
        "facility_id": 1,
        "source_type": "electricity",
        "electricity_kwh": 2000.0,
        "emission_factor": 0.5,  # 2000 kWh * 0.5 kg/kWh / 1000 = 1.0 tCO2e
        "co2e": 9999.0,  # Client-injected bogus value
    }
    res = client.post("/api/scope2", json=payload)
    assert res.status_code == 201
    res_data = res.get_json()
    # The server must have authoritatively calculated 1.0 tCO2e instead of 9999.0
    assert pytest.approx(res_data["co2e"], 0.001) == 1.0
    with app.app_context():
        rec = db.session.get(Scope2Emission, res_data["id"])
        assert pytest.approx(rec.co2e, 0.001) == 1.0


def test_compressor_seal_and_storage_tank_uncertainty_mapping():
    """Verify compressor_seal and storage_tanks map to proper categories and propagate uncertainty."""
    from calculations.dispatcher import CalculationDispatcher
    from calculations.uncertainty import PROCESS_CATEGORY, resolve_ef_uncertainty, Tier

    assert PROCESS_CATEGORY["compressor_seal"] == "fugitive"
    assert PROCESS_CATEGORY["storage_tanks"] == "vented"

    # Fugitive CH4 Tier 1 uncertainty should be 0.60 (60%), NOT 0.15 (combustion)
    u_seal = resolve_ef_uncertainty("compressor_seal", "ch4", Tier.T1)
    assert u_seal == 0.60

    dispatcher = CalculationDispatcher()
    # Test compressor seal dispatch in specific engineering mode
    seal_res = dispatcher.dispatch(
        process_type="compressor_seal",
        inputs={"compressor_count": 2, "seal_type": "reciprocating", "factor_source": "specific"},
        emission_factors={},
        uncertainties={"_factor_source": "specific"},
    )
    assert seal_res is not None
    assert seal_res["total_co2e"] > 0
    assert seal_res["results"]["ch4"]["value"] > 0


def test_stoichiometry_dispatcher_gwp_propagation():
    """Verify stoichiometry calculator accepts gwp_dict and calculates deterministically."""
    from calculations.dispatcher import CalculationDispatcher

    dispatcher = CalculationDispatcher()
    res = dispatcher.dispatch(
        process_type="stoichiometry",
        inputs={"quantity": 1000, "carbon_content": 0.85, "unit": "kg", "factor_source": "specific"},
        emission_factors={},
        uncertainties={"_factor_source": "specific"},
        gwp_dict={"CO2": 1, "CH4": 28, "N2O": 265},
    )
    assert res is not None
    # 1000 kg * 0.85 * (44.01/12.011) / 1000 = ~3.114 tonnes CO2
    assert pytest.approx(res["results"]["co2"]["value"], 0.01) == 3.114
    assert pytest.approx(res["total_co2e"], 0.01) == 3.114


def test_compute_scope3_co2e_units():
    """Verify compute_scope3_co2e distinguishes numerator units from denominator units."""
    from calculations.units import compute_scope3_co2e

    # 1. kg CO2e / liter: 1000 liters * 2.68 kg/L = 2680 kg = 2.68 tonnes (NOT 2680 tonnes!)
    res_l = compute_scope3_co2e(1000, 2.68, "kg CO2e / liter")
    assert pytest.approx(res_l, 0.0001) == 2.68

    # 2. kg CO2e / tonne: 50 tonnes * 1200 kg/t = 60,000 kg = 60.0 tonnes (NOT 60,000 tonnes!)
    res_t = compute_scope3_co2e(50, 1200, "kg CO2e / tonne")
    assert pytest.approx(res_t, 0.0001) == 60.0

    # 3. kg CO2e / metric ton
    res_mt = compute_scope3_co2e(10, 500, "kg CO2e / metric ton")
    assert pytest.approx(res_mt, 0.0001) == 5.0

    # 4. tCO2e / bbl: 100 bbl * 0.43 t/bbl = 43.0 tonnes
    res_bbl = compute_scope3_co2e(100, 0.43, "tCO2e / bbl")
    assert pytest.approx(res_bbl, 0.0001) == 43.0

    # 5. tonne CO2e / unit: 10 * 1.8 = 18.0 tonnes
    res_tonne = compute_scope3_co2e(10, 1.8, "tonne CO2e / unit")
    assert pytest.approx(res_tonne, 0.0001) == 18.0

    # 6. Activity units containing 't' (flight, night, mmbtu) with kg factors
    res_flight = compute_scope3_co2e(4, 250, "kg CO2e / flight")
    assert pytest.approx(res_flight, 0.0001) == 1.0

    res_mmbtu = compute_scope3_co2e(100, 53.06, "kg CO2e / MMBtu")
    assert pytest.approx(res_mmbtu, 0.0001) == 5.306

    # 7. Spend-based EEIO (/ $1000)
    res_eeio = compute_scope3_co2e(100000, 350, "kg CO2e / $1000")
    assert pytest.approx(res_eeio, 0.0001) == 35.0


def test_scope3_bulk_import_and_create_authoritative_calculation(client, test_users):
    """Verify Scope 3 creation and bulk import enforce authoritative calculation and override injected co2e."""
    from models import Scope3Emission

    with client.session_transaction() as sess:
        sess["user_id"] = test_users["user"]

    # 1. Single create endpoint
    res_single = client.post(
        "/api/scope3",
        json={
            "facility_id": test_users["facility_id"],
            "year": 2026,
            "month": 6,
            "category": "1",
            "sub_category": "Diesel Transport",
            "activity_data": 1000,
            "unit": "liter",
            "emission_factor": 2.68,
            "factor_unit": "kg CO2e / liter",
            "co2e": 9999.0,  # Injected mismatched value
        },
    )
    assert res_single.status_code == 201
    s_data = res_single.get_json()
    assert pytest.approx(s_data["co2e"], 0.001) == 2.68

    # 2. Bulk import endpoint
    res_bulk = client.post(
        "/api/scope3/bulk-import",
        json={
            "records": [
                {
                    "facility_id": test_users["facility_id"],
                    "year": 2026,
                    "month": 7,
                    "category": "1",
                    "sub_category": "Purchased Cement",
                    "amount": 50,
                    "unit": "tonne",
                    "emission_factor": 800,
                    "ef_unit": "kg CO2e / tonne",
                    "co2e": 88888.0,  # Injected mismatched value
                }
            ]
        },
    )
    assert res_bulk.status_code == 200
    with client.application.app_context():
        rec = Scope3Emission.query.filter_by(
            facility_id=test_users["facility_id"], year=2026, month=7
        ).first()
        assert rec is not None
        # 50 tonnes * 800 kg/tonne / 1000 = 40.0 tCO2e (NOT 40,000 tCO2e!)
        assert pytest.approx(rec.co2e, 0.001) == 40.0


def test_background_processor_scope3_units(client, test_users):
    """Verify background_processor._process_row_scope3 correctly computes units with 't' in denominator."""
    from background_processor import _process_row_scope3
    from models import Facility

    with client.application.app_context():
        fac = db.session.get(Facility, test_users["facility_id"])
        fac_name_map = {fac.name.lower(): fac}
        fac_id_map = {str(fac.id): fac}

        # Case A: kg CO2e / liter
        row_l = {
            "facility_name": fac.name,
            "year": 2026,
            "month": 8,
            "category": "1",
            "sub_category": "Fuel",
            "amount": "1000",
            "emission_factor": "2.68",
            "ef_unit": "kg CO2e / liter",
        }
        em_obj, errs = _process_row_scope3(
            row_l,
            user_id=test_users["user"],
            fac_name_map=fac_name_map,
            fac_id_map=fac_id_map,
            job_id="test-job",
            row_idx=1,
        )
        assert not errs
        assert em_obj is not None
        assert pytest.approx(em_obj.co2e, 0.001) == 2.68

        # Case B: kg CO2e / tonne
        row_t = {
            "facility_name": fac.name,
            "year": 2026,
            "month": 9,
            "category": "1",
            "sub_category": "Steel",
            "amount": "20",
            "emission_factor": "1800",
            "ef_unit": "kg CO2e / tonne",
        }
        em_obj2, errs2 = _process_row_scope3(
            row_t,
            user_id=test_users["user"],
            fac_name_map=fac_name_map,
            fac_id_map=fac_id_map,
            job_id="test-job",
            row_idx=2,
        )
        assert not errs2
        assert em_obj2 is not None
        # 20 * 1800 / 1000 = 36.0 tonnes
        assert pytest.approx(em_obj2.co2e, 0.001) == 36.0


def test_qaqc_dashboard_regional_facility_scoping(client, test_users):
    """Verify QA/QC dashboard scopes total and active facilities to the user's allowed regions."""
    from models import User

    with client.application.app_context():
        reg_super = User.query.filter_by(email="audit_reg_super@test.com").first()
        if not reg_super:
            reg_super = User(
                email="audit_reg_super@test.com",
                fullName="Audit Regional Superuser",
                orgName="AuditCorp",
                sector="Energy",
                role="superuser",
                location="Hassi Messaoud",
            )
            reg_super.set_password("RegSuper123!")
            db.session.add(reg_super)
            db.session.commit()
        reg_super_id = reg_super.id

    with client.session_transaction() as sess:
        sess["user_id"] = reg_super_id

    res = client.get("/api/qaqc/dashboard")
    assert res.status_code == 200
    diag = res.get_json()["diagnostics"]

    # The regional superuser only has access to Hassi Messaoud facilities
    assert diag["total_facilities"] >= 1
    assert diag["active_facilities"] <= diag["total_facilities"]
    assert diag["unused_facilities"] == diag["total_facilities"] - diag["active_facilities"]


def test_csv_formula_injection_whitespace_and_tab_escaping():
    """Verify formula injection sanitization handles leading whitespace and format bypasses."""
    from routes.audit import sanitize_csv_cell

    assert sanitize_csv_cell("  =SUM(A1:A10)") == "'  =SUM(A1:A10)"
    assert sanitize_csv_cell("\t=CMD()") == "'\t=CMD()"
    assert sanitize_csv_cell("\r-100") == "'\r-100"
    assert sanitize_csv_cell("  +200") == "'  +200"
    assert sanitize_csv_cell("  @MACRO") == "'  @MACRO"
    assert sanitize_csv_cell("  %EVIL") == "'  %EVIL"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell(123.45) == "123.45"
    assert sanitize_csv_cell(None) == ""


def test_facility_boundary_type_and_detail_roundtrip(client, test_users):
    """Verify Facility boundary_type and boundary_detail persistence and retrieval via API."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    # Create facility with explicit boundary_type and boundary_detail
    resp = client.post(
        "/api/facilities",
        json={
            "name": "Boundaries Test Facility",
            "location": "In Salah",
            "activity": "Extraction",
            "division": "Upstream",
            "segment": "Upstream",
            "boundary_type": "Equity Share",
            "boundary_detail": "Sonatrach 51%, Partner 49%",
        },
    )
    assert resp.status_code == 201
    fac_id = resp.get_json()["id"]

    # Verify retrieval via GET /facilities
    get_resp = client.get("/api/facilities")
    assert get_resp.status_code == 200
    all_facs = get_resp.get_json()
    target = next((f for f in all_facs if f["id"] == fac_id), None)
    assert target is not None
    assert target["boundary_type"] == "Equity Share"
    assert target["boundary_detail"] == "Sonatrach 51%, Partner 49%"


def test_custom_factor_description_and_source_roundtrip(client, test_users):
    """Verify CustomFactor description and source lab certification roundtrip via API."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    # Create custom factor with description and source
    resp = client.post(
        "/api/custom-factors",
        json={
            "fuel_name": "Test Flare Gas Lab Blend",
            "process_type": "flaring",
            "unit": "m3",
            "co2_factor": 1.95,
            "ch4_factor": 0.012,
            "n2o_factor": 0.0001,
            "source": "Sonatrach CRD Lab Cert #2026-B84",
            "description": "Gas chromatography sample from separator train B, calibrated to ISO 6974.",
        },
    )
    assert resp.status_code == 201
    factor_id = resp.get_json()["id"]

    # Verify retrieval
    get_resp = client.get("/api/custom-factors")
    assert get_resp.status_code == 200
    factors = get_resp.get_json()
    created = next((f for f in factors if f["id"] == factor_id), None)
    assert created is not None
    assert created["source"] == "Sonatrach CRD Lab Cert #2026-B84"
    assert created["description"] == "Gas chromatography sample from separator train B, calibrated to ISO 6974."


def test_dehydrator_stripping_gas_calculation():
    """Verify Dehydrator stripping gas calculation adds methane volume to still vent before control."""
    from calculations.midstream import DehydratorCalculator
    from calculations.units import convert

    calc = DehydratorCalculator()
    # Baseline without stripping gas
    base_res = calc.calculate(
        pump_rate=100.0,
        pump_unit="gph",
        hours=1000,
        ch4_content=0.90,
        has_flash_tank=False,
        still_control_type="none",
        control_eff=0.0,
        stripping_gas_rate=0.0,
    )

    # With stripping gas (50 scf/hr = 50,000 scf over 1000 hrs)
    strip_res = calc.calculate(
        pump_rate=100.0,
        pump_unit="gph",
        hours=1000,
        ch4_content=0.90,
        has_flash_tank=False,
        still_control_type="none",
        control_eff=0.0,
        stripping_gas_rate=50.0,
        stripping_gas_unit="scf/hr",
    )

    # 50,000 scf * 0.90 CH4 = 45,000 scf CH4
    expected_strip_ch4_tonnes = convert(45000.0, "scf", "m3") * 0.6785 / 1000.0
    diff_ch4 = strip_res["results"]["ch4"]["value"] - base_res["results"]["ch4"]["value"]
    assert abs(diff_ch4 - expected_strip_ch4_tonnes) < 1e-4
    assert strip_res["inputs"]["stripping_gas_scf"] == 50000.0

    # With 98% flare control efficiency, stripping gas is abated and converted to CO2 stoichiometrically
    flared_strip_res = calc.calculate(
        pump_rate=100.0,
        pump_unit="gph",
        hours=1000,
        ch4_content=0.90,
        has_flash_tank=False,
        still_control_type="flare",
        control_eff=0.98,
        stripping_gas_rate=50.0,
        stripping_gas_unit="scf/hr",
    )
    # Remaining uncombusted CH4 must be 2%
    assert abs(flared_strip_res["results"]["ch4"]["value"] - (strip_res["results"]["ch4"]["value"] * 0.02)) < 1e-4
    # Stoichiometric CO2 must be generated from destroyed CH4
    assert flared_strip_res["results"]["co2"]["value"] > 0.0


def test_dehydrator_stripping_gas_dispatcher():
    """Verify dispatcher passes stripping gas parameters correctly."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "dehydrator",
        "factor_source": "specific",
        "dehydrator_calc_method": "glycol_pump",
        "teg_pump_rate": 100.0,
        "teg_pump_unit": "gph",
        "annual_hours": 1000.0,
        "gas_ch4_mole_pct": 90.0,
        "flash_tank": "no",
        "still_vent_control": "none",
        "stripping_gas_rate": 50.0,
        "stripping_gas_unit": "scf/hr",
    }
    gwps = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
    res = dispatcher.dispatch("dehydrator", payload, {}, gwps)
    assert res is not None
    assert res["inputs"]["stripping_gas_scf"] == 50000.0
    assert res["results"]["ch4"]["value"] > 0

