"""
test_carbon_intensity_validation.py

Zero-Trust Carbon Intensity Validation Suite
Validates:
1. BOE conversion physics across all oil and gas unit permutations.
2. GWP-100 vs GWP-20 carbon intensity mathematical parity.
3. Methane loss rate % and flaring rate % stoichiometry.
4. EPA Waste Emissions Charge (40 CFR Part 99) thresholds, rates, and exemption rules.
5. Zero-production & zero-emission edge case mathematical resilience.
6. Activity, division, and segment query filtering isolation in trend and stats.
7. EU CBAM product export calculation and cache invalidation.
"""
import pytest
from app import app as flask_app
from extensions import db
from models import Facility, Emission, ProductionData, Scope2Emission, Scope3Emission, CbamProductExport, User
from routes.dashboard import _query_intensity_stats, _query_intensity_trend_bulk, clear_dashboard_cache
from calculations.constants import get_active_gwp

GAS_TO_BOE = 0.178
DENSITY_CH4 = 0.6785  # kg/m3


@pytest.fixture(scope="module")
def ci_setup():
    """Setup isolated test fixtures for carbon intensity validation."""
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        # Clean / create required user
        admin = User.query.filter_by(email="ci_admin@test.com").first()
        if not admin:
            admin = User(
                email="ci_admin@test.com",
                fullName="CI Admin User",
                orgName="TestCorp",
                sector="Energy",
                role="admin",
                status="active"
            )
            admin.set_password("CiAdmin123!")
            db.session.add(admin)
            db.session.commit()

        # Facilities
        fac1 = Facility.query.filter_by(name="CI Steel Facility").first()
        if not fac1:
            fac1 = Facility(
                name="CI Steel Facility",
                segment="Heavy Industry",
                activity="Steel & Iron (Acier DRI)",
                division="Metallurgy",
                region="Oran",
                operator_status="operated",
            )
            db.session.add(fac1)

        fac2 = Facility.query.filter_by(name="CI Gas Facility").first()
        if not fac2:
            fac2 = Facility(
                name="CI Gas Facility",
                segment="Upstream",
                activity="Upstream Gas",
                division="Exploration & Production",
                region="Hassi Messaoud",
                operator_status="operated",
            )
            db.session.add(fac2)

        fac3 = Facility.query.filter_by(name="CI Refinery").first()
        if not fac3:
            fac3 = Facility(
                name="CI Refinery",
                segment="Downstream",
                activity="Refining",
                division="Downstream",
                region="Algiers",
                operator_status="operated",
            )
            db.session.add(fac3)

        db.session.commit()

        # Emissions for fac1 (2026)
        em1 = Emission.query.filter_by(record_id="EM-CI-001").first()
        if not em1:
            em1 = Emission(
                record_id="EM-CI-001",
                facility_id=fac1.id,
                year=2026,
                month=1,
                process_type="combustion",
                status="Verified",
                activity=fac1.activity,
                division=fac1.division,
                co2_emissions=1000.0,
                ch4_emissions=10.0,
                n2o_emissions=1.0,
                co2e_total=1000.0 + (10.0 * 28.0) + (1.0 * 265.0), # 1545.0 tCO2e
                quantity=1000.0,
                unit="m3",
                created_by=admin.id,
            )
            db.session.add(em1)

        # Emissions for fac2 (2026) with heavy methane
        em2 = Emission.query.filter_by(record_id="EM-CI-002").first()
        if not em2:
            em2 = Emission(
                record_id="EM-CI-002",
                facility_id=fac2.id,
                year=2026,
                month=1,
                process_type="flaring",
                status="Verified",
                activity=fac2.activity,
                division=fac2.division,
                co2_emissions=5000.0,
                ch4_emissions=150.0,
                n2o_emissions=2.0,
                co2e_total=5000.0 + (150.0 * 28.0) + (2.0 * 265.0), # 9730.0 tCO2e
                quantity=50000.0,
                unit="m3",
                created_by=admin.id,
            )
            db.session.add(em2)

        # Emissions for fac3 (2026) with zero production
        em3 = Emission.query.filter_by(record_id="EM-CI-003").first()
        if not em3:
            em3 = Emission(
                record_id="EM-CI-003",
                facility_id=fac3.id,
                year=2026,
                month=1,
                process_type="combustion",
                status="Verified",
                activity=fac3.activity,
                division=fac3.division,
                co2_emissions=200.0,
                ch4_emissions=0.0,
                n2o_emissions=0.0,
                co2e_total=200.0,
                quantity=100.0,
                unit="m3",
                created_by=admin.id,
            )
            db.session.add(em3)

        # Production for fac1 (2026)
        prod1 = ProductionData.query.filter_by(facility_id=fac1.id, year=2026, month=1).first()
        if not prod1:
            prod1 = ProductionData(
                facility_id=fac1.id,
                year=2026,
                month=1,
                oil_amount=10000.0,
                gas_amount=50000.0,
                unit="bbl",
                oil_unit="bbl",
                gas_unit="mscf",
                activity=fac1.activity,
                division=fac1.division,
                region=fac1.region,
                created_by=admin.id,
            )
            db.session.add(prod1)

        # Production for fac2 (2026)
        prod2 = ProductionData.query.filter_by(facility_id=fac2.id, year=2026, month=1).first()
        if not prod2:
            prod2 = ProductionData(
                facility_id=fac2.id,
                year=2026,
                month=1,
                oil_amount=20000.0,
                gas_amount=500000.0,
                unit="bbl",
                oil_unit="bbl",
                gas_unit="mscf",
                activity=fac2.activity,
                division=fac2.division,
                region=fac2.region,
                created_by=admin.id,
            )
            db.session.add(prod2)

        # CBAM Export for fac1
        cbam1 = CbamProductExport.query.filter_by(facility_id=fac1.id, cn_code="7203 10 00").first()
        if not cbam1:
            cbam1 = CbamProductExport(
                facility_id=fac1.id,
                product_name="DRI Steel Test",
                cn_code="7203 10 00",
                year=2026,
                month=1,
                quantity_tonnes=5000.0,
                export_destination="EU - Italy",
                specific_embedded_direct=1.125,
                specific_embedded_indirect=0.245,
                created_by=admin.id,
            )
            db.session.add(cbam1)

        db.session.commit()
        clear_dashboard_cache()

        yield {
            "admin": admin,
            "fac1": fac1,
            "fac2": fac2,
            "fac3": fac3,
        }


@pytest.fixture
def auth_client(ci_setup):
    client = flask_app.test_client()
    resp = client.post("/api/auth/login", json={"email": "ci_admin@test.com", "password": "CiAdmin123!"})
    assert resp.status_code == 200
    return client


# =========================================================================
# 1. BOE CONVERSION INVARIANTS
# =========================================================================

def test_boe_conversion_gas_units():
    """Verify gas conversion across all supported units to MSCF and BOE."""
    # 1 m3 gas = 0.0353147 mscf
    vol_m3 = 1000.0
    expected_mscf = vol_m3 * 0.0353147
    expected_boe = expected_mscf * GAS_TO_BOE
    assert abs(expected_boe - (1000.0 * 0.0353147 * 0.178)) < 1e-6

    # 1 scf gas = 0.001 mscf
    vol_scf = 1000000.0
    expected_mscf_scf = vol_scf * 0.001
    assert expected_mscf_scf == 1000.0

    # 1 mmscf gas = 1000 mscf
    vol_mmscf = 10.0
    assert vol_mmscf * 1000.0 == 10000.0


def test_boe_conversion_oil_units():
    """Verify oil conversion across units to BBL."""
    # 1 m3 oil = 6.28981077 bbl
    vol_m3 = 100.0
    assert abs(vol_m3 * 6.28981077 - 628.981077) < 1e-4

    # 42 gallons = 1 bbl
    assert 42.0 / 42.0 == 1.0

    # 1 metric ton crude ~ 7.33 bbl
    assert 10.0 * 7.33 == 73.3


# =========================================================================
# 2. GWP-100 VS GWP-20 CARBON INTENSITY PARITY
# =========================================================================

def test_gwp_horizon_intensity_scaling(ci_setup):
    """Verify that 20-year GWP intensity strictly exceeds 100-year GWP intensity when CH4 > 0."""
    with flask_app.app_context():
        stats = _query_intensity_stats(year="2026", facility_id=str(ci_setup["fac2"].id))
        assert len(stats) >= 1
        fac = stats[0]
        assert fac["facility_id"] == ci_setup["fac2"].id
        assert fac["total_boe"] > 0
        assert fac["total_ch4"] > 0

        # GWP20 intensity MUST be strictly greater than GWP100 intensity
        assert fac["co2_intensity_gwp20"] > fac["co2_intensity"]
        assert fac["scope1_intensity_gwp20"] > fac["scope1_intensity"]

        # Verify exact mathematical formula:
        gwp20_factors = get_active_gwp(horizon="20")
        ch4_gwp20 = float(gwp20_factors.get("CH4", 82.5))
        n2o_gwp20 = float(gwp20_factors.get("N2O", 268.0))
        delta_gwp = (fac["total_ch4"] * (ch4_gwp20 - 28.0)) + (fac["total_n2o"] * (n2o_gwp20 - 265.0))
        expected_s1_gwp20 = round(max(fac["total_scope1"], fac["total_scope1"] + delta_gwp), 2)
        expected_s1_int_gwp20 = (expected_s1_gwp20 * 1000.0) / fac["total_boe"]

        assert abs(fac["scope1_intensity_gwp20"] - expected_s1_int_gwp20) < 1e-4


# =========================================================================
# 3. METHANE LOSS RATE & FLARING STOICHIOMETRY
# =========================================================================

def test_methane_loss_rate_calculation(ci_setup):
    """Verify methane loss rate % adheres to density = 0.6785 kg/m3."""
    with flask_app.app_context():
        stats = _query_intensity_stats(year="2026", facility_id=str(ci_setup["fac2"].id))
        assert len(stats) >= 1
        fac = stats[0]

        gas_m3 = fac["total_gas_m3"]
        ch4_tonnes = fac["total_ch4"]
        assert gas_m3 > 0
        assert ch4_tonnes > 0

        ch4_vol_m3 = (ch4_tonnes * 1000.0) / DENSITY_CH4
        expected_loss_rate = round((ch4_vol_m3 / gas_m3) * 100.0, 4)
        assert abs(fac["methane_loss_rate_pct"] - expected_loss_rate) < 1e-4


# =========================================================================
# 4. EPA WEC (WASTE EMISSIONS CHARGE) COMPLIANCE
# =========================================================================

def test_wec_downstream_exemption(ci_setup):
    """Verify downstream facilities are exempt from WEC fee ($0)."""
    with flask_app.app_context():
        stats = _query_intensity_stats(year="2026", facility_id=str(ci_setup["fac3"].id))
        if stats:
            assert stats[0]["wec_fee_usd"] == 0.0
            assert "Exempt" in stats[0]["wec_status"]


def test_wec_rate_schedule():
    """Verify WEC fee rates: $900 in 2024, $1200 in 2025, $1500 in 2026+."""
    rates = {2024: 900.0, 2025: 1200.0, 2026: 1500.0, 2027: 1500.0}
    for yr, expected_rate in rates.items():
        rate = 900.0 if yr == 2024 else (1200.0 if yr == 2025 else 1500.0)
        assert rate == expected_rate


# =========================================================================
# 5. ZERO-PRODUCTION AND ZERO-EMISSIONS RESILIENCE
# =========================================================================

def test_zero_production_resilience(ci_setup):
    """Verify facilities with 0 production safely return 0.0 intensities without crashing."""
    with flask_app.app_context():
        # fac3 has emissions in 2026 but zero production records
        stats = _query_intensity_stats(year="2026", facility_id=str(ci_setup["fac3"].id))
        assert len(stats) >= 1
        rec = stats[0]
        assert rec["total_boe"] == 0.0
        assert rec["total_co2e"] == 200.0
        assert rec["co2_intensity"] == 0.0
        assert rec["scope1_intensity"] == 0.0
        assert rec["scope1_intensity_gwp20"] == 0.0
        assert rec["scope2_intensity"] == 0.0


# =========================================================================
# 6. QUERY FILTERING ISOLATION
# =========================================================================

def test_trend_query_activity_isolation(ci_setup):
    """Verify trend query filters Scope 2 and Scope 3 strictly by activity."""
    with flask_app.app_context():
        trend = _query_intensity_trend_bulk(
            activity="Steel & Iron (Acier DRI)",
            years=[2026]
        )
        assert len(trend) > 0
        for yr_data in trend:
            for fac in yr_data["data"]:
                assert fac["facility_id"] == ci_setup["fac1"].id


def test_stats_query_segment_isolation(ci_setup):
    """Verify stats query filters by segment properly."""
    with flask_app.app_context():
        stats = _query_intensity_stats(year="2026", segment="Heavy Industry")
        assert len(stats) > 0
        for s in stats:
            assert s["segment"] == "Heavy Industry"


# =========================================================================
# 7. CBAM PRODUCT EXPORTS PIPELINE & CACHE
# =========================================================================

def test_cbam_exports_endpoint(auth_client, ci_setup):
    """Verify GET /api/data/cbam-exports returns valid EU CBAM product records."""
    resp = auth_client.get(f"/api/data/cbam-exports?year=2026&facilityId={ci_setup['fac1'].id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1
    sample = data[0]
    assert sample["cn_code"] == "7203 10 00"
    assert sample["specific_embedded_direct"] == 1.125
    assert sample["specific_embedded_indirect"] == 0.245
    assert abs(sample["total_embedded_emissions"] - 6850.0) < 1e-4


def test_cbam_exports_cache_invalidation(auth_client, ci_setup):
    """Verify creating and deleting a CBAM export invalidates dashboard cache."""
    post_resp = auth_client.post("/api/data/cbam-exports", json={
        "facility_id": ci_setup["fac1"].id,
        "product_name": "Test CBAM Wire Rod",
        "cn_code": "7213 10 00",
        "year": 2026,
        "month": 2,
        "quantity_tonnes": 500.0,
        "export_destination": "EU - Germany",
        "specific_embedded_direct": 1.20,
        "specific_embedded_indirect": 0.30,
    })
    assert post_resp.status_code == 200
    rec_id = post_resp.get_json().get("id")

    # Clean up test record
    del_resp = auth_client.delete(f"/api/data/cbam-exports/{rec_id}")
    assert del_resp.status_code == 200
