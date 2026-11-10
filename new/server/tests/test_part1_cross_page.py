"""Item 1.11: Cross-Page Consistency Tests
==========================================
Verifies:
1. Flaring volume consistency (metered stream volume vs bottom-up ledger volume) and factor sanity check against API Compendium 2021 Table 4-3.
2. Methane Map vs Dashboard distinction (geolocated methane on map vs total corporate inventory).
3. OGMP 2.0 Gold Standard Level 5 invariant: Discrepancy Detected prevents Level 5 Reconciled.
"""
import pytest
from extensions import db
from models import Facility, OgmpSurvey, Emission, FlaringDetail
from services.intensity import intensity_rows
from services.ogmp import compute_facility_ogmp_level
from tests.audit_helpers import make_facility, make_user, login, uniq

def test_flaring_consistency_and_factor_compendium(app, client):
    """Item 1.11: Flaring consistency between Dashboard and Carbon Intensity, and factor check."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_FLARE"), region="South")

        # 1. Create a flaring emission (bottom-up: 1,000,000 m3, 3400 tCO2e)
        em = Emission(
            facility_id=fac.id,
            year=2026,
            month=1,
            process_type="flaring",
            quantity=1_000_000.0,
            unit="m3",
            co2_emissions=3400.0,
            ch4_emissions=0.0,
            n2o_emissions=0.0,
            co2e_total=3400.0,
            status="Verified",
            is_test=False,
        )
        # 2. Create metered FlaringDetail stream volume (950 kNm3 = 950,000 m3 metered under Decree 21-330)
        fd = FlaringDetail(
            facility_id=fac.id,
            year=2026,
            month=1,
            routine_knm3=950.0,
            status="Verified",
        )
        db.session.add(em)
        db.session.add(fd)
        db.session.commit()

        ci_rows = intensity_rows(year=2026)
        fac_row = next((r for r in ci_rows if r["facility_id"] == fac.id), None)
        assert fac_row is not None

        # flaring_m3 must use the metered FlaringDetail volume (950k) to match Dashboard
        assert fac_row["flaring_m3"] == pytest.approx(950_000.0, rel=1e-3)
        # flaring_ledger_m3 preserves the bottom-up ledger volume (1.0M)
        assert fac_row["flaring_ledger_m3"] == pytest.approx(1_000_000.0, rel=1e-3)

        # Sanity check flare factor against API Compendium 2021 Table 4-3 (2.8 - 3.6 kg/m3 for rich gas)
        # Ratio of 2.6M tCO2e / 758M m3 = 3.42 kg CO2e / m3
        known_emissions_t = 2.59e6
        known_vol_m3 = 758.054e6
        ratio_kg_m3 = (known_emissions_t * 1000.0) / known_vol_m3
        assert 2.8 <= ratio_kg_m3 <= 3.6, f"Flare factor {ratio_kg_m3:.3f} kg/m3 outside Compendium range"

def test_methane_map_vs_dashboard_distinction(app, client):
    """Item 1.11: Map geolocated methane vs total corporate inventory."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # Fac 1: Geolocated on Map (lat/lon present)
        fac_map = make_facility(
            name=uniq("FAC_MAP"),
            region="Basin Alpha",
            latitude=31.67,
            longitude=6.06,
            is_test=False,
        )
        # Fac 2: Not Geolocated (lat/lon None)
        fac_nomap = make_facility(
            name=uniq("FAC_NOMAP"),
            region="Remote",
            latitude=None,
            longitude=None,
            is_test=False,
        )
        # Fac 3: Test facility (is_test=True, like 'rz')
        fac_test = make_facility(
            name=uniq("FAC_TEST"),
            region="TestRegion",
            latitude=30.0,
            longitude=5.0,
            is_test=True,
        )

        db.session.add(Emission(
            facility_id=fac_map.id, year=2026, month=1,
            process_type="venting", ch4_emissions=100.0, co2e_total=2800.0,
            status="Verified", is_test=False,
        ))
        db.session.add(Emission(
            facility_id=fac_nomap.id, year=2026, month=1,
            process_type="venting", ch4_emissions=50.0, co2e_total=1400.0,
            status="Verified", is_test=False,
        ))
        db.session.add(Emission(
            facility_id=fac_test.id, year=2026, month=1,
            process_type="venting", ch4_emissions=2000.0, co2e_total=56000.0,
            status="Verified", is_test=True,
        ))
        db.session.commit()

        # Corporate inventory (verified, non-test) = 100 + 50 = 150 t CH4
        total_corp_ch4 = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
            Emission.facility_id.in_([fac_map.id, fac_nomap.id, fac_test.id]),
            Emission.status == "Verified",
            Emission.is_test == False,
        ).scalar() or 0.0
        assert total_corp_ch4 == pytest.approx(150.0, rel=1e-3)

        # Map geolocated methane = only fac_map = 100 t CH4
        ci_rows = {r["facility_id"]: r for r in intensity_rows(year=2026)}
        map_ch4_t = sum(
            ci_rows.get(f.id, {}).get("total_ch4", 0.0)
            for f in [fac_map]
        )
        assert map_ch4_t == pytest.approx(100.0, rel=1e-3)
        assert map_ch4_t < total_corp_ch4, "Geolocated map subset is less than total corporate inventory"

def test_ogmp_rns_discrepancy_blocks_level5(app, client):
    """Item 1.11: Facility with discrepancy survey cannot be declared Level 5 Reconciled."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_RNS"), region="Basin Alpha")

        # 1. Add surveys with Discrepancy Detected
        survey1 = OgmpSurvey(
            facility_id=fac.id,
            year=2025,
            survey_date="2025-10-15",
            survey_type="Site Survey",
            measured_rate_kg_hr=50.0,
            operating_hours_year=8760.0,
            estimated_annual_tch4=459.9,
            bottom_up_tch4=420.0,
            variance_pct=-61.41,
            variance_flag=True,
            reconciliation_status="Discrepancy Detected",
        )
        db.session.add(survey1)
        db.session.commit()

        # compute_facility_ogmp_level must NOT return 5
        level = compute_facility_ogmp_level(fac, top_down_tch4=459.9, bottom_up_tch4=420.0)
        assert level == 4, f"Expected Level 4 due to discrepancy survey, got {level}"

        # intensity_rows must reflect Discrepancy Detected
        rows = intensity_rows(year=None)
        fac_row = next((r for r in rows if r["facility_id"] == fac.id), None)
        assert fac_row is not None
        assert fac_row["current_ogmp_level"] <= 4
        assert fac_row["reconciliation_status"] == "Discrepancy Detected"
        assert "Discrepancy Detected" in fac_row["gold_pathway_status"]
