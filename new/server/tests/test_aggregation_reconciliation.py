"""
Aggregation, Reconciliation, and Rollup Integrity Test Suite.
============================================================
Validates multi-tier aggregation consistency and reconciliation rules:
1. Rollup hierarchy: Sources -> Facility -> Basin -> Enterprise.
2. Gas-by-Gas vs Total CO2e linearity: Sum(CO2e) == CO2e(Sum(m_i)).
3. Scope Aggregation: Scope 1 + Scope 2 + Scope 3 = Total Inventory.
4. OGMP 2.0 Level 4/5 Top-Down vs Bottom-Up survey reconciliation.
5. Production Intensity (BOE and Carbon Intensity) consistency.
"""
import pytest
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.constants import GWP_AR5
from calculations.units import calculate_co2e
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for
from validation.reference_model.ogmp import IndependentOGMPModel
from validation.reference_model.aggregation_intensity import IndependentIntensityModel


class TestRollupAndGasReconciliation:
    """Verifies that summing across sources and scopes is strictly conservative and commutative."""

    def test_gas_aggregation_commutativity(self):
        """
        Sum(CO2e_i) must equal calculate_co2e(Sum(CO2_i), Sum(CH4_i), Sum(N2O_i)).
        Guarantees that gas-by-gas rollups never diverge from aggregate CO2e rollups.
        """
        sources = [
            {"co2": 150.0, "ch4": 2.5, "n2o": 0.05},
            {"co2": 320.0, "ch4": 0.8, "n2o": 0.01},
            {"co2": 45.0,  "ch4": 12.0, "n2o": 0.00},
            {"co2": 890.0, "ch4": 0.1, "n2o": 0.12},
        ]

        # Method 1: Sum individual source CO2e
        individual_co2e_sum = sum(
            calculate_co2e(s["co2"], s["ch4"], s["n2o"], gwp_dict=GWP_AR5)
            for s in sources
        )

        # Method 2: Sum gases first, then apply GWP
        total_co2 = sum(s["co2"] for s in sources)
        total_ch4 = sum(s["ch4"] for s in sources)
        total_n2o = sum(s["n2o"] for s in sources)
        aggregate_co2e = calculate_co2e(total_co2, total_ch4, total_n2o, gwp_dict=GWP_AR5)

        assert pytest.approx(individual_co2e_sum, rel=1e-8) == aggregate_co2e

    def test_scope_inventory_aggregation(self, client, app):
        """Total GHG = Scope 1 + Scope 2 (location-based) + Scope 3, as the national inventory export totals them (the
        Executive Summary sheet). The test used to add three numbers in the test and compare them to a literal."""
        import io

        import openpyxl

        from extensions import db
        from models import Emission, Scope2Emission, Scope3Emission
        from tests.audit_helpers import login, make_facility, make_user, uniq

        with app.app_context():
            fac = make_facility(region=uniq("AggSite"))
            login(client, make_user("admin", "Global"))
            db.session.add_all([
                Emission(facility_id=fac.id, year=2024, month=3, process_type="combustion", quantity=1.0, unit="m3",
                         co2_emissions=12500.50, ch4_emissions=0.0, n2o_emissions=0.0, co2e_total=12500.50,
                         status="Verified"),
                Scope2Emission(facility_id=fac.id, year=2024, month=3, source_type="electricity",
                               grid_region="Algerian National Grid", electricity_kwh=1.0, co2e=1840.20,
                               co2e_location_based=1840.20, co2e_market_based=100.0, status="Verified"),
                Scope3Emission(facility_id=fac.id, year=2024, month=3, category=1, sub_category="purchased_goods",
                               co2e=45000.00, status="Verified"),
            ])
            db.session.commit()
            res = client.get(f"/api/reports/national-inventory-export?year=2024&facility_id={fac.id}&status=Verified")
            assert res.status_code == 200
            ws = openpyxl.load_workbook(io.BytesIO(res.data))["Executive Summary"]
            rows = {str(r[0]): r[1] for r in ws.iter_rows(values_only=True) if r and r[0] is not None}
            grand = next(v for k, v in rows.items() if k.startswith("Grand Total"))
            scope1 = next(v for k, v in rows.items() if k.startswith("Scope 1"))
            scope2_loc = next(v for k, v in rows.items() if k.startswith("Scope 2") and "marché" not in k)
            scope3 = next(v for k, v in rows.items() if k.startswith("Scope 3"))
            assert scope1 == pytest.approx(12500.50)
            assert scope2_loc == pytest.approx(1840.20)
            assert scope3 == pytest.approx(45000.00)
            assert grand == pytest.approx(12500.50 + 1840.20 + 45000.00)      # 59,340.70; the market-based 100 is not added


class TestOGMPSurveyReconciliation:
    """Verifies OGMP 2.0 Top-Down vs Bottom-Up reconciliation thresholds."""

    def test_ogmp_reconciled_within_threshold(self):
        bu = 100.0
        td = 112.0  # +12% variance <= 20% threshold
        recon = IndependentOGMPModel.reconcile_survey(bu, td, threshold=20.0)

        assert recon["reconciliation_status"] == "Reconciled"
        assert recon["variance_flag"] is False
        assert pytest.approx(recon["variance_pct"], rel=1e-4) == 12.0

    def test_ogmp_unreconciled_exceeds_threshold(self):
        bu = 100.0
        td = 145.0  # +45% variance > 20% threshold
        recon = IndependentOGMPModel.reconcile_survey(bu, td, threshold=20.0)

        assert recon["reconciliation_status"] == "Discrepancy Flagged"
        assert recon["variance_flag"] is True
        assert pytest.approx(recon["variance_pct"], rel=1e-4) == 45.0


class TestIntensityMetrics:
    """Verifies BOE and Carbon/Methane Intensity calculations."""

    def test_boe_calculation(self):
        oil_bbl = 10_000.0
        gas_mscf = 50_000.0
        boe = IndependentIntensityModel.calculate_boe(oil_bbl, gas_mscf)
        # 10,000 + 50,000 * 1.02 / 5.8 = 10,000 + 8,793.1 = 18,793.1 BOE
        assert boe == pytest.approx(10_000 + 50_000 * 1.02 / 5.8)

    def test_carbon_intensity_calculation(self):
        co2e_tonnes = 500.0
        boe = 25_000.0
        ci = IndependentIntensityModel.calculate_carbon_intensity(co2e_tonnes, boe)
        # (500 * 1000) / 25,000 = 20.0 kg CO2e / BOE
        assert ci == 20.0
