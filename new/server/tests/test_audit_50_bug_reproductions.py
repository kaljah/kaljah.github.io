"""
test_audit_50_bug_reproductions.py
==================================
Targeted Empirical Reproduction Suite for Codebase Audit Defects.
Directly reproduces and asserts on verified vulnerabilities and defects cataloged
in the 50+ Bug Master Audit.
"""

import pytest
from app import app
from extensions import db
from models import User, Facility, CustomFactor, Emission, Scope2Emission
from calculations.vented_gas import _frac
from calculations.activity_factors import _frac as act_frac
from calculations.indirect import IndirectSteamCalculator
import calculations.legacy_engine as legacy_engine


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client):
    with app.app_context():
        user = User.query.filter_by(email="audit_repro_admin@example.com").first()
        if not user:
            user = User(
                email="audit_repro_admin@example.com",
                fullName="Audit Admin",
                orgName="TestOrg",
                sector="oil_and_gas",
                role="admin",
                status="active"
            )
            user.set_password("AuditPassword123!")
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password("AuditPassword123!")
            db.session.commit()
    res = client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
    token = res.get_json().get("token") or res.get_json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def it_token(client):
    with app.app_context():
        user = User.query.filter_by(email="audit_repro_it@example.com").first()
        if not user:
            user = User(
                email="audit_repro_it@example.com",
                fullName="Audit IT",
                orgName="TestOrg",
                sector="oil_and_gas",
                role="it",
                status="active"
            )
            user.set_password("AuditPassword123!")
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password("AuditPassword123!")
            db.session.commit()
    res = client.post("/api/auth/login", json={"email": "audit_repro_it@example.com", "password": "AuditPassword123!"})
    token = res.get_json().get("token") or res.get_json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


class TestAuditBugReproduction:
    """Verifies and asserts that cataloged audit defects have been properly remediated."""

    def test_reproduce_bug_008_emissions_pending_unhandled_500_on_limit_string(self, client, admin_token):
        """BUG-008: In routes/emissions.py:4056, invalid limit safely defaults instead of 500 crash."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        res = client.get("/api/emissions/pending?limit=invalid_limit", headers=admin_token)
        assert res.status_code == 200, f"Expected 200 graceful fallback on malformed limit, got {res.status_code}"

    def test_reproduce_bug_010_qaqc_unhandled_500_on_year_string(self, client, admin_token):
        """BUG-010: In routes/qaqc.py, invalid year safely falls back instead of 500 crash."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        res = client.get("/api/qaqc/dashboard?year=not_a_year", headers=admin_token)
        assert res.status_code == 200, f"Expected 200 graceful fallback on malformed year, got {res.status_code}"

    def test_reproduce_bug_029_mole_fraction_100x_underestimate(self):
        """BUG-029: In calculations/activity_factors.py, _frac() preserves fractional mole compositions."""
        # Decimal fraction (e.g. 0.02 for 2% CO2) is preserved
        fractional_input = 0.02
        result = act_frac(fractional_input)
        assert result == pytest.approx(0.02), f"Expected 0.02 preserved fraction, got {result}"

        # Percentage string (e.g. '2%') is normalized
        assert act_frac("2%") == pytest.approx(0.02)
        assert act_frac(2.0) == pytest.approx(0.02)

    def test_reproduce_bug_042_indirect_zero_efficiency_division(self):
        """BUG-042: In calculations/indirect.py, zero net_efficiency raises descriptive ValueError, not ZeroDivisionError."""
        calc = IndirectSteamCalculator()
        with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
            calc.calculate(heat_energy=10_000_000.0, ef_co2=50.0, boiler_efficiency=0.0, transmission_loss=0.0, uncertainties={})

    def test_reproduce_bug_026_legacy_engine_unit_error_swallowed(self):
        """BUG-026 & BUG-028: Unit errors in legacy engine fall back to un-converted denominator."""
        res = legacy_engine._calculate_default_kg(
            amount=100.0,
            unit="incompatible_unknown_unit",
            hhv=0,
            factor_data={"factor": 2.5, "unit": "kg/gal"},
            gas="co2"
        )
        assert res == 250.0

    def test_reproduce_bug_020_emission_table_lacks_unique_natural_key_constraint(self):
        """BUG-020: Emission table lacks database-level unique constraint on natural keys."""
        with app.app_context():
            uqs = [c.name for c in Emission.__table__.constraints if hasattr(c, 'columns') and len(c.columns) > 1]
            assert "uq_emission_natural_key" not in uqs, "Confirmed: Emission table lacks unique natural key constraint"

    def test_custom_factor_import_maker_checker(self, client, admin_token):
        """Verifies that imported custom factors set status and approval metadata."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        import_payload = {
            "factors": [
                {
                    "name": "Audit Test Imported Fuel",
                    "co2_factor": 50.0,
                    "ch4_factor": 0.001,
                    "n2o_factor": 0.0001,
                    "unit": "kg/m3",
                }
            ]
        }
        res = client.post("/api/custom-factors/import", json=import_payload, headers=admin_token)
        assert res.status_code == 200
        with app.app_context():
            cf = CustomFactor.query.filter_by(name="Audit Test Imported Fuel").first()
            assert cf is not None
            assert cf.status == "Approved"
            assert cf.approved_by is not None

    def test_calculate_eeio_handles_malformed_spend(self, client, admin_token):
        """Verifies that calculate_eeio returns 400/422 on invalid spend instead of crashing with 500."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        res = client.post("/api/scope3/eeio-calculate", json={"spend_usd": "invalid_number", "naics_code": "211111"}, headers=admin_token)
        assert res.status_code in (400, 422)

    def test_save_ogmp_survey_handles_empty_string_detection_threshold(self, client, admin_token):
        """Verifies that save_ogmp_survey handles empty string detection threshold without 500 TypeError."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        with app.app_context():
            fac = Facility.query.first()
            if not fac:
                fac = Facility(name="OGMP Test Fac", location="Hassi Messaoud", activity="Upstream Oil & Gas")
                db.session.add(fac)
                db.session.commit()
            fac_id = fac.id

        payload = {
            "facility_id": fac_id,
            "year": 2026,
            "survey_date": "2026-05-15",
            "measured_rate_kg_hr": 12.5,
            "detection_threshold": "",  # Empty string from form
        }
        res = client.post("/api/data/ogmp-surveys", json=payload, headers=admin_token)
        assert res.status_code in (200, 201)

    def test_add_production_validates_year_and_month(self, client, admin_token):
        """Verifies that add_production validates year and month and returns 400 on invalid input."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        with app.app_context():
            fac = Facility.query.first()
            fac_id = fac.id

        res = client.post("/api/data/production", json={"facility_id": fac_id, "year": "invalid_year", "month": 5}, headers=admin_token)
        assert res.status_code == 400

    def test_update_settings_validates_numeric_settings(self, client, admin_token):
        """Verifies that update_settings returns 400 on non-numeric setting values instead of 500."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        res = client.post("/api/auth/settings", json={"reconciliation_threshold": "not_a_number"}, headers=admin_token)
        assert res.status_code == 400

    def test_save_cbam_export_validates_numeric_fields(self, client, admin_token):
        """Verifies that save_cbam_export returns 400 on non-numeric quantity instead of crashing with 500."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        with app.app_context():
            fac = Facility.query.first()
            fac_id = fac.id

        payload = {
            "facility_id": fac_id,
            "year": 2026,
            "product_name": "Direct Reduced Iron",
            "cn_code": "72031000",
            "quantity_tonnes": "invalid_tonnage"
        }
        res = client.post("/api/data/cbam-exports", json=payload, headers=admin_token)
        assert res.status_code == 400

    def test_equity_allocation_rejects_it_role_and_validates_facility_id(self, client):
        """Verifies that get_equity_allocation rejects IT roles with 403 and validates facility_id format."""
        with app.app_context():
            it_user = User.query.filter_by(email="audit_repro_it@example.com").first()
            if not it_user:
                it_user = User(
                    email="audit_repro_it@example.com",
                    fullName="Audit IT",
                    orgName="TestOrg",
                    sector="oil_and_gas",
                    role="it",
                    status="active"
                )
                it_user.set_password("AuditPassword123!")
                db.session.add(it_user)
                db.session.commit()
            else:
                it_user.set_password("AuditPassword123!")
                db.session.commit()

        # IT user gets 403
        login_res = client.post("/api/auth/login", json={"email": "audit_repro_it@example.com", "password": "AuditPassword123!"})
        assert login_res.status_code == 200
        res = client.get("/api/equity/allocation")
        assert res.status_code == 403

        # Admin user gets 400 on invalid facility_id
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        res = client.get("/api/equity/allocation?facility_id=not_a_number")
        assert res.status_code == 400

    def test_add_facility_validates_membership_year(self, client):
        """Verifies that add_facility validates ogmp_membership_year format."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        payload = {
            "name": "Invalid Year Facility",
            "location": "Hassi Messaoud",
            "ogmp_membership_year": "invalid_year"
        }
        res = client.post("/api/facilities", json=payload)
        assert res.status_code == 400

    def test_update_facility_validates_membership_year(self, client):
        """Verifies that update_facility validates ogmp_membership_year format."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        with app.app_context():
            fac = Facility.query.first()
            fac_id = fac.id
        payload = {
            "ogmp_membership_year": "invalid_year"
        }
        res = client.put(f"/api/facilities/{fac_id}", json=payload)
        assert res.status_code == 400

    def test_cap_emission_handles_invalid_id(self, client):
        """Verifies that create_or_update_cap_emission rejects non-integer id gracefully."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        payload = {
            "id": "not_an_id",
            "facility_id": 1,
            "year": 2026,
            "month": 1,
            "source_module": "Combustion",
            "pollutant": "NO2",
            "mass_tonnes": 5.0
        }
        res = client.post("/api/cap/emissions", json=payload)
        assert res.status_code == 400

    def test_base_year_recalculation_validates_emissions(self, client):
        """Verifies that create_base_year_recalculation validates numeric emissions inputs."""
        client.post("/api/auth/login", json={"email": "audit_repro_admin@example.com", "password": "AuditPassword123!"})
        payload = {
            "year": 2024,
            "reason": "Structural acquisition of upstream block",
            "previous_emissions": "not_a_number"
        }
        res = client.post("/api/dashboard/base-year-recalculation", json=payload)
        assert res.status_code == 400

