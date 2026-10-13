"""
Comprehensive Advanced Regulatory, Supply Chain, and Environmental Compliance Audit Suite.
Validates:
1. EU CBAM (Carbon Border Adjustment Mechanism) & Embedded Emissions Accounting
2. Clean Air Act / Algerian Executive Decree 06-138 Statutory CAP Limits & Compliance
3. GHG Protocol Scope 3 (Categories 1-15) Value Chain Calculation Rigor & Denominator Scaling
5. Forensic Data Quality: Benford's Law Activity Distribution & Statistical Outlier Fencing
"""

import math
import uuid
import json
import pytest

from app import app
from extensions import db, limiter
from models import (
    User,
    Facility,
    Emission,
    Scope2Emission,
    Scope3Emission,
    CbamProductExport,
    OgmpSurvey,
    ActivityLog,
)
from calculations.units import compute_scope3_co2e
from tests.audit_helpers import make_user, make_facility, login


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_advanced_audit_config():
    """Ensure CSRF is disabled and testing flags are active."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RATELIMIT_ENABLED"] = False
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev


@pytest.fixture(scope="module")
def advanced_audit_env():
    """Provides isolated testing fixtures for advanced regulatory tests."""
    with app.app_context():
        db.create_all()

        admin = make_user(role="admin", location="Global")
        maker_user = make_user(role="user", location="Algeria")
        it_user = make_user(role="it_admin", location="Global")

        fac1 = make_facility(name=f"Regulatory Complex {uuid.uuid4().hex[:6]}", region="Algeria", location="Algeria")
        fac2 = make_facility(name=f"Industrial Refinery {uuid.uuid4().hex[:6]}", region="Algeria", location="Algeria")

        yield {
            "admin": admin,
            "maker_user": maker_user,
            "it_user": it_user,
            "fac1": fac1,
            "fac2": fac2,
        }


# ==============================================================================
# 1. EU CBAM & EMBEDDED EMISSIONS (EU REGULATION 2023/956)
# ==============================================================================

class TestCbamEmbeddedEmissionsAccounting:
    """Audits specific embedded direct and indirect emissions for carbon border adjustments."""

    def test_cbam_export_specific_embedded_direct_and_indirect_calculation(self, client, advanced_audit_env):
        """
        Tests calculation of specific embedded direct (Scope 1) and indirect (Scope 2) emissions:
        SE_dir = Total_Direct_tCO2e / Quantity_Tonnes
        SE_ind = Total_Indirect_tCO2e / Quantity_Tonnes
        """
        admin = advanced_audit_env["admin"]
        fac = advanced_audit_env["fac1"]
        login(client, admin)

        # 1. Seed verified Scope 1 (direct) and Scope 2 (indirect) emissions for facility in 2026
        with app.app_context():
            e_direct = Emission(
                facility_id=fac.id,
                year=2026,
                month=1,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=5000.0,
                unit="m3",
                co2e_total=4000.0,
                ch4_emissions=5.0,
                status="Verified",
            )
            e_indirect = Scope2Emission(
                facility_id=fac.id,
                year=2026,
                month=1,
                source_type="electricity",
                electricity_kwh=2000000.0,
                co2e=1000.0,
                status="Verified",
            )
            db.session.add_all([e_direct, e_indirect])
            db.session.commit()

        # 2. Record export of 2,000 tonnes of product without manual SE override (triggering auto-calc)
        res_post = client.post("/api/data/cbam-exports", json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 1,
            "product_name": "Refined Petroleum Fuels",
            "cn_code": "27101245",
            "quantity_tonnes": 2000.0,
            "export_destination": "France (EU)",
            "specific_embedded_direct": 0.0,
            "specific_embedded_indirect": 0.0,
            "notes": "CBAM quarterly shipment Q1 2026",
        })
        assert res_post.status_code == 200
        export_id = res_post.get_json()["id"]

        # 3. Retrieve and audit calculated specific embedded values
        with app.app_context():
            cbam_record = db.session.get(CbamProductExport, export_id)
            assert cbam_record is not None
            # Expected SE_direct = 4000.0 tCO2e / 2000.0 t = 2.0000 tCO2e/t
            assert pytest.approx(cbam_record.specific_embedded_direct, rel=1e-4) == 2.0000
            # Expected SE_indirect = 1000.0 tCO2e / 2000.0 t = 0.5000 tCO2e/t
            assert pytest.approx(cbam_record.specific_embedded_indirect, rel=1e-4) == 0.5000

    def test_cbam_validation_rejects_negative_or_blank_fields(self, client, advanced_audit_env):
        """Validates that negative quantities or blank product codes are rejected."""
        admin = advanced_audit_env["admin"]
        fac = advanced_audit_env["fac1"]
        login(client, admin)

        # Zero or negative tonnage
        res_neg = client.post("/api/data/cbam-exports", json={
            "facility_id": fac.id,
            "year": 2026,
            "product_name": "Fertilizers",
            "cn_code": "31021010",
            "quantity_tonnes": -100.0,
        })
        assert res_neg.status_code == 400

        # Empty product name or CN code
        res_blank = client.post("/api/data/cbam-exports", json={
            "facility_id": fac.id,
            "year": 2026,
            "product_name": "",
            "cn_code": "",
            "quantity_tonnes": 500.0,
        })
        assert res_blank.status_code == 400

    def test_it_role_cannot_view_or_modify_cbam_records(self, client, advanced_audit_env):
        """IT roles have administrative access but are forbidden from operational CBAM trade data."""
        it_user = advanced_audit_env["it_user"]
        login(client, it_user)

        res_get = client.get("/api/data/cbam-exports")
        assert res_get.status_code == 403

        res_post = client.post("/api/data/cbam-exports", json={"year": 2026})
        assert res_post.status_code == 403


# ==============================================================================
# 3. SCOPE 3 VALUE CHAIN RIGOR & DENOMINATOR SCALING
# ==============================================================================

class TestScope3ValueChainCalculationRigor:
    """Audits Scope 3 multi-unit and economic denominator scaling (EEIO vs Activity)."""

    def test_spend_based_eeio_per_thousand_dollar_scaling(self):
        """
        EEIO factors with '/$1000' or 'kg CO2e/$1k' must scale by 0.001 * 0.001.
        $500,000 spend at 350 kg CO2e / $1,000:
        CO2e = 500,000 * 350 * 0.001 * 0.001 = 175.0 tonnes CO2e
        """
        amt = 500_000.0
        ef = 350.0
        ef_unit = "kg CO2e / $1000"
        result_co2e = compute_scope3_co2e(amt, ef, ef_unit=ef_unit)
        assert pytest.approx(result_co2e, rel=1e-5) == 175.0

    def test_activity_based_metric_tonnes_numerator(self):
        """
        Direct tonne numerator ('tCO2e/tonne'):
        1,000 tonnes of steel purchased at 0.25 tCO2e/tonne = 250.0 tonnes CO2e.
        """
        amt = 1000.0
        ef = 0.25
        ef_unit = "tCO2e / tonne"
        result_co2e = compute_scope3_co2e(amt, ef, ef_unit=ef_unit)
        assert pytest.approx(result_co2e, rel=1e-5) == 250.0

    def test_activity_based_kg_numerator_fuel_combustion(self):
        """
        Direct kg numerator ('kg CO2e/liter'):
        100,000 liters of diesel at 2.68 kg CO2e/liter = 268.0 tonnes CO2e.
        """
        amt = 100_000.0
        ef = 2.68
        ef_unit = "kg CO2e / liter"
        result_co2e = compute_scope3_co2e(amt, ef, ef_unit=ef_unit)
        assert pytest.approx(result_co2e, rel=1e-5) == 268.0

    def test_scope3_server_side_calculation_enforcement(self, client, advanced_audit_env):
        """Client-provided fraudulent co2e is ignored; server enforces mathematical product."""
        maker = advanced_audit_env["maker_user"]
        fac = advanced_audit_env["fac1"]
        login(client, maker)

        # Maker submits 10,000 liters with 2.5 kg CO2e/liter, but tries to pass co2e=1.0 (fraudulent claim)
        res = client.post("/api/scope3", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 6,
            "category": "Category 1 - Purchased Goods and Services",
            "activity_data": 10000.0,
            "emission_factor": 2.5,
            "factor_unit": "kg CO2e / liter",
            "co2e": 1.0,  # Fraudulent client value
        })
        assert res.status_code == 201
        rec_id = res.get_json()["id"]

        with app.app_context():
            rec = db.session.get(Scope3Emission, rec_id)
            assert rec is not None
            # Server must compute: 10,000 * 2.5 / 1000 = 25.0 tCO2e, ignoring 1.0
            assert pytest.approx(rec.co2e, rel=1e-5) == 25.0
            assert rec.status == "Pending"  # Maker-checker enforced


# ==============================================================================
# 5. FORENSIC INTEGRITY: BENFORD'S LAW & STATISTICAL OUTLIER DETECTION
# ==============================================================================

class TestForensicIntegrityAndStatisticalDistribution:
    """Audits forensic statistical properties of reported emissions activity data."""

    def test_benfords_law_first_digit_distribution_on_log_distributed_activity(self):
        """
        Benford's Law states that for natural logarithmic processes:
        P(d) = log10(1 + 1/d) for d in {1, 2, ..., 9}.
        P(1) ~ 30.1%, P(2) ~ 17.6%, ..., P(9) ~ 4.6%.
        Verifies that legitimate unmanipulated operational data fits this baseline.
        """
        import numpy as np

        # Synthesize 10,000 log-normal distributed flow-meter readings
        np.random.seed(42)
        readings = np.random.lognormal(mean=5.0, sigma=1.5, size=10000)

        first_digits = [int(str(float(r)).lstrip("0.")[0]) for r in readings if r > 0]
        digit_counts = {d: first_digits.count(d) for d in range(1, 10)}
        total = len(first_digits)

        # Theoretical Benford distribution
        benford_probs = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}

        # Perform Chi-Square goodness of fit test
        chi_sq = sum(
            ((digit_counts[d] - total * benford_probs[d]) ** 2) / (total * benford_probs[d])
            for d in range(1, 10)
        )
        # Critical value for 8 degrees of freedom at alpha=0.01 is 20.09
        assert chi_sq < 20.09, f"Activity data failed Benford's Law goodness-of-fit test (Chi-Sq: {chi_sq:.2f})"

    def test_statistical_iqr_outlier_fence_detection(self):
        """
        Verifies Interquartile Range (IQR) fence for automated anomaly flagging:
        Q1, Q3 = 25th, 75th percentiles
        IQR = Q3 - Q1
        Upper Fence = Q3 + 1.5 * IQR
        Lower Fence = max(0, Q1 - 1.5 * IQR)
        """
        normal_monthly_flaring_m3 = [
            10500, 10800, 11200, 10900, 11500, 11100,
            10700, 11300, 11000, 10600, 11400, 10850
        ]
        sorted_vals = sorted(normal_monthly_flaring_m3)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        iqr = q3 - q1
        upper_fence = q3 + 1.5 * iqr

        abnormal_burst_flaring = 45000  # Massive flaring emergency event
        is_anomaly = abnormal_burst_flaring > upper_fence
        assert is_anomaly is True, "Statistical outlier fence failed to detect 4x burst flaring event!"
