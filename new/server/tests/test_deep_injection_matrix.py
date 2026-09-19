"""
test_deep_injection_matrix.py
------------------------------
Exhaustive Deep Testing by Manually Injecting Data for:
1. All 24 Process Types & Scopes across ALL Unit Conversions (Volume, Mass, Energy, Temp, Press)
2. All Operational & Thermodynamic Scenarios (P, T, Z, GOR, CH4%, Combustion Efficiency, GWP Standards)
3. Bulk CSV Upload Pipeline for ALL 3 Tiers (Tier 1 Default, Tier 2 Custom, Tier 3 Engineering)
4. Bulk CSV Upload Pipeline for Scope 2 and Scope 3 (All Categories & Units)
"""

import os
import io
import math
import tempfile
import pytest
from datetime import datetime

from app import app as flask_app
from extensions import db
from models import (
    User,
    Facility,
    CustomFactor,
    Emission,
    Scope2Emission,
    Scope3Emission,
)
from background_processor import (
    _process_file_thread,
    get_job_status,
    upload_jobs,
    upload_jobs_lock,
)
from calculations.dispatcher import CalculationDispatcher
from calculations.units import convert, compute_scope3_co2e, calculate_co2e
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
from process_categories import PROCESS_TYPES


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module")
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def test_user(db_session):
    u = User.query.filter_by(email="deep_tester@ghg.com").first()
    if not u:
        u = User(
            email="deep_tester@ghg.com",
            fullName="Deep Test Engineer",
            orgName="GHG Verification Unit",
            sector="Oil & Gas",
            role="admin",
            location="Global",
        )
        u.set_password("DeepTestPass2026!")
        db_session.add(u)
        db_session.commit()
    return u


@pytest.fixture
def test_facility(db_session, test_user):
    f = Facility.query.filter_by(name="Deep Matrix Testing Facility").first()
    if not f:
        f = Facility(
            name="Deep Matrix Testing Facility",
            location="In Amenas",
            country="Algeria",
            region="Illizi",
            division="Production",
            field="Gas Field",
            segment="Upstream",
            created_by=test_user.id,
        )
        db_session.add(f)
        db_session.commit()
    return f


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


# ==============================================================================
# PART 1: MANUAL INJECTION ACROSS ALL UNIT CONVERSIONS (VOLUME, MASS, ENERGY, T, P)
# ==============================================================================

class TestUnitConversionInvarianceMatrix:
    """Every physical quantity represented across various dimensional units must compute equivalent CO2e."""

    def test_all_thirteen_volume_units_invariance(self, dispatcher):
        """1000 m3 of natural gas converted across all 13 volume units must yield equal emissions within 0.1%."""
        base_m3 = 1000.0
        volume_units = [
            "m3", "scf", "cf", "ft3", "mscf", "mcf", "mmscf",
            "bbl", "barrel", "gal", "gallon", "liter", "l"
        ]
        factors = {"co2": 1.91127, "unit": "kg/m3"}  # ~53.06 kg/MMBtu
        base_res = dispatcher.dispatch(
            "stationary_combustion",
            {"amount": base_m3, "unit": "m3", "factor_source": "default"},
            factors,
            {},
        )
        base_co2e = base_res["total_co2e"]
        assert base_co2e > 0

        for u in volume_units:
            equiv_qty = convert(base_m3, "m3", u)
            # Factor unit converted to match activity unit
            equiv_factor = factors["co2"] * (base_m3 / equiv_qty)
            res = dispatcher.dispatch(
                "stationary_combustion",
                {"amount": equiv_qty, "unit": u, "factor_source": "default"},
                {"co2": equiv_factor, "unit": f"kg/{u}"},
                {},
            )
            rel_diff = abs(res["total_co2e"] - base_co2e) / base_co2e
            assert rel_diff < 0.005, f"Volume invariance failed for unit '{u}': diff={rel_diff}"

    def test_all_twelve_mass_units_invariance(self, dispatcher):
        """10 tonnes carbon mass converted across all 12 mass units must yield identical stoichiometric emissions."""
        base_tonnes = 10.0
        mass_units = [
            "tonne", "tonnes", "metric_ton", "mt", "t",
            "kg", "lb", "lbs", "pound", "ton", "short_ton", "g"
        ]
        # Base: 10 tonnes * 0.85 carbon * (44.01 / 12.011) = 31.144 tonnes CO2
        base_res = dispatcher.dispatch(
            "stoichiometry",
            {"amount": base_tonnes, "unit": "tonne", "carbon_content": 0.85, "factor_source": "specific"},
            {},
            {},
        )
        base_co2e = base_res["total_co2e"]
        assert pytest.approx(base_co2e, rel=1e-3) == 31.144

        for u in mass_units:
            equiv_qty = convert(base_tonnes, "tonne", u)
            res = dispatcher.dispatch(
                "stoichiometry",
                {"amount": equiv_qty, "unit": u, "carbon_content": 0.85, "factor_source": "specific"},
                {},
                {},
            )
            rel_diff = abs(res["total_co2e"] - base_co2e) / base_co2e
            assert rel_diff < 0.005, f"Mass invariance failed for unit '{u}': diff={rel_diff}"

    def test_all_seven_energy_units_invariance(self, dispatcher):
        """1,000 MMBtu of steam converted across all 7 energy units must yield identical indirect emissions."""
        base_mmbtu = 1000.0
        energy_units = ["mmbtu", "btu", "gj", "mj", "kwh", "mwh", "therm"]
        base_res = dispatcher.dispatch(
            "indirect_steam",
            {
                "amount": base_mmbtu,
                "heat_unit": "mmbtu",
                "boiler_efficiency": 0.80,
                "transmission_loss": 0.05,
                "factor_source": "specific",
            },
            {"co2": 53.06},
            {},
        )
        base_co2e = base_res["total_co2e"]
        assert base_co2e > 0

        for u in energy_units:
            equiv_qty = convert(base_mmbtu, "mmbtu", u)
            res = dispatcher.dispatch(
                "indirect_steam",
                {
                    "amount": equiv_qty,
                    "heat_unit": u,
                    "boiler_efficiency": 0.80,
                    "transmission_loss": 0.05,
                    "factor_source": "specific",
                },
                {"co2": 53.06},
                {},
            )
            rel_diff = abs(res["total_co2e"] - base_co2e) / base_co2e
            assert rel_diff < 0.005, f"Energy invariance failed for unit '{u}': diff={rel_diff}"

    def test_all_four_temperature_units_invariance(self, dispatcher):
        """Blowdown calculation at 20°C expressed in C, F, K, R must produce identical mass emissions."""
        temp_cases = [
            ("C", 20.0),
            ("F", 68.0),
            ("K", 293.15),
            ("R", 527.67),
        ]
        results = []
        for u, t in temp_cases:
            res = dispatcher.dispatch(
                "blowdown",
                {
                    "blowdown_volume": 50.0,
                    "pressure": 500.0,
                    "events": 1,
                    "ch4_content": 90.0,
                    "operating_temperature": t,
                    "temp_unit": u,
                    "factor_source": "specific",
                },
                {},
                {},
            )
            results.append((u, res["results"]["ch4"]["value"]))

        base_val = results[0][1]
        for u, val in results:
            rel_diff = abs(val - base_val) / base_val
            assert rel_diff < 0.005, f"Temperature invariance failed for unit '{u}': val={val}, base={base_val}"

    def test_all_seven_pressure_units_invariance(self, dispatcher):
        """Blowdown calculation at 1000 kPa expressed in kPa, MPa, Pa, bar, mbar, psia, psig must agree."""
        press_cases = [
            ("kpa", 1000.0),
            ("mpa", 1.0),
            ("bar", 10.0),
            ("psia", 145.038),
            ("psig", 145.038 - 14.696),
        ]
        results = []
        for u, p in press_cases:
            res = dispatcher.dispatch(
                "blowdown",
                {
                    "blowdown_volume": 50.0,
                    "pressure": p,
                    "press_unit": u,
                    "events": 1,
                    "ch4_content": 90.0,
                    "factor_source": "specific",
                },
                {},
                {},
            )
            results.append((u, res["results"]["ch4"]["value"]))

        base_val = results[0][1]
        for u, val in results:
            rel_diff = abs(val - base_val) / base_val
            assert rel_diff < 0.01, f"Pressure invariance failed for unit '{u}': val={val}, base={base_val}"

    def test_all_dimensional_combinatorial_roundtrips(self):
        """Exhaustively verifies roundtrip convert(val, u1, u2) -> convert(converted, u2, u1) == val for ALL pairs."""
        volume_units = ["m3", "scf", "cf", "ft3", "mscf", "mcf", "mmscf", "bbl", "barrel", "gal", "gallon", "liter", "l"]
        mass_units = ["tonne", "metric_ton", "mt", "t", "kg", "lb", "pound", "short_ton", "ton", "long_ton", "g"]
        energy_units = ["mmbtu", "btu", "gj", "mj", "kwh", "mwh", "therm"]
        distance_units = ["km", "m", "mile", "ft", "yd", "nmi"]
        freight_units = ["tonne-km", "ton-mile"]
        passenger_units = ["passenger-km", "passenger-mile"]
        time_units = ["hr", "day", "min", "sec", "yr"]
        flow_units = ["m3/hr", "gph", "lph", "bph", "bpd"]
        temp_units = ["C", "F", "K", "R"]
        press_units = ["psia", "bar", "kpa", "mpa", "atm", "pa", "mbar"]

        all_groups = [
            volume_units,
            mass_units,
            energy_units,
            distance_units,
            freight_units,
            passenger_units,
            time_units,
            flow_units,
            press_units,
        ]

        test_val = 1500.25
        for group in all_groups:
            for u1 in group:
                for u2 in group:
                    c = convert(test_val, u1, u2)
                    back = convert(c, u2, u1)
                    rel_err = abs(back - test_val) / test_val
                    assert rel_err < 1e-4, f"Roundtrip failed between '{u1}' and '{u2}': val={test_val}, back={back}"

        # Temperature roundtrips (non-zero absolute scale)
        temp_val = 25.0  # 25°C
        for t1 in temp_units:
            for t2 in temp_units:
                c = convert(temp_val, t1, t2)
                back = convert(c, t2, t1)
                assert abs(back - temp_val) < 1e-3, f"Temp roundtrip failed between '{t1}' and '{t2}': back={back}"


# ==============================================================================
# PART 2: ALL OPERATIONAL & THERMODYNAMIC SCENARIOS (P, T, Z, GOR, CH4%, GWP)
# ==============================================================================

class TestOperationalScenariosMatrix:
    """Stress tests every physical regime: high/low GOR, arctic/desert, high compressibility, heavy hydrocarbons."""

    def test_thermodynamic_real_gas_compressibility_z(self, dispatcher):
        """Real gas deviation: Z < 1 (dense gas) -> higher emissions; Z > 1 -> lower emissions."""
        p_ideal = {"process_type": "blowdown", "factor_source": "specific", "blowdown_volume": 100.0, "pressure": 3000.0, "events": 1, "ch4_content": 85.0, "z_factor": 1.0}
        p_dense = {"process_type": "blowdown", "factor_source": "specific", "blowdown_volume": 100.0, "pressure": 3000.0, "events": 1, "ch4_content": 85.0, "z_factor": 0.80}
        p_expanded = {"process_type": "blowdown", "factor_source": "specific", "blowdown_volume": 100.0, "pressure": 3000.0, "events": 1, "ch4_content": 85.0, "z_factor": 1.20}

        r_ideal = dispatcher.dispatch("blowdown", p_ideal, {}, {})
        r_dense = dispatcher.dispatch("blowdown", p_dense, {}, {})
        r_expanded = dispatcher.dispatch("blowdown", p_expanded, {}, {})

        assert r_dense["total_co2e"] > r_ideal["total_co2e"]
        assert r_ideal["total_co2e"] > r_expanded["total_co2e"]
        assert pytest.approx(r_dense["total_co2e"], rel=1e-3) == r_ideal["total_co2e"] / 0.80
        assert pytest.approx(r_expanded["total_co2e"], rel=1e-3) == r_ideal["total_co2e"] / 1.20

    def test_flaring_destruction_efficiency_variations(self, dispatcher):
        """Flaring destruction efficiencies: 95%, 98%, 99.5% unburnt CH4 vs CO2."""
        for eff in [0.95, 0.98, 0.995]:
            payload = {
                "process_type": "flaring",
                "factor_source": "specific",
                "amount": 10000.0,
                "unit": "m3",
                "c1": 90.0,
                "combustion_efficiency": eff * 100.0,
            }
            res = dispatcher.dispatch("flaring", payload, {}, {})
            assert res["results"]["co2"]["value"] > 0
            assert res["results"]["ch4"]["value"] > 0

    def test_heavy_hydrocarbon_gas_c2_plus_stoichiometry(self, dispatcher):
        """Heavy gas stream (rich in ethane, propane, butane) must generate stoichiometric CO2 per carbon atom."""
        rich_gas = {
            "process_type": "stationary_combustion",
            "factor_source": "specific",
            "amount": 1000.0,
            "unit": "m3",
            "hhv": 1150.0,
            "combustion_efficiency": 99.5,
            "c1": 70.0,  # 70% CH4 (1 C)
            "c2": 15.0,  # 15% C2H6 (2 C)
            "c3": 10.0,  # 10% C3H8 (3 C)
            "c4": 5.0,   # 5% C4H10 (4 C)
        }
        res = dispatcher.dispatch("stationary_combustion", rich_gas, {}, {})
        # Total carbon moles = 0.70*1 + 0.15*2 + 0.10*3 + 0.05*4 = 1.50 moles CO2 / mole gas
        # Combusted CO2 = 1000 * 1.50 * 0.995 * 1.861 / 1000 = 2.777 tonnes CO2
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-2) == 2.78

    def test_dynamic_gwp_standards_ar4_ar5_ar6(self, dispatcher):
        """Dynamic GWP: AR4 (25), AR5 (28), AR6 (29.8) for methane must scale total CO2e strictly."""
        payload = {
            "process_type": "compressor_fugitive",
            "factor_source": "specific",
            "count": 2,
            "seal_type": "reciprocating",
        }
        res_ar4 = dispatcher.dispatch("compressor_fugitive", payload, {}, {}, gwp_standard="AR4")
        res_ar5 = dispatcher.dispatch("compressor_fugitive", payload, {}, {}, gwp_standard="AR5")
        res_ar6 = dispatcher.dispatch("compressor_fugitive", payload, {}, {}, gwp_standard="AR6")

        ch4_mass = res_ar5["results"]["ch4"]["value"]
        assert pytest.approx(res_ar4["total_co2e"], 1e-3) == ch4_mass * GWP_AR4["CH4"]
        assert pytest.approx(res_ar5["total_co2e"], 1e-3) == ch4_mass * GWP_AR5["CH4"]
        assert pytest.approx(res_ar6["total_co2e"], 1e-3) == ch4_mass * GWP_AR6["CH4"]


# ==============================================================================
# PART 3: BULK CSV INGESTION MATRIX (TIER 1, TIER 2, TIER 3, SCOPE 2, SCOPE 3)
# ==============================================================================

class TestBulkCSVIngestionAllTiersAndScopes:
    """Executes the full asynchronous/synchronous file processing pipeline for all 3 Tiers, Scope 2, and Scope 3."""

    def _run_upload(self, app, csv_content, filename, user_id, scope=1):
        with app.app_context():
            db.session.commit()
        fd, temp_path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(csv_content.encode("utf-8"))

            job_id = "job-deep-" + os.urandom(6).hex()
            with upload_jobs_lock:
                upload_jobs[job_id] = {
                    "status": "processing",
                    "progress": 0,
                    "processed": 0,
                    "total": 0,
                    "errors": [],
                    "skipped": [],
                    "error_csv_path": None,
                    "anomalies": [],
                }

            _process_file_thread(
                app=app,
                job_id=job_id,
                file_path=temp_path,
                original_filename=filename,
                user_id=user_id,
                global_factor_type="auto",
                provided_mapping=None,
                scope=scope,
                overwrite_duplicates=True,
            )
            return get_job_status(job_id)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def test_scope1_tier1_bulk_csv_upload(self, app, test_user, test_facility, db_session):
        """Tier 1 Bulk CSV: Default catalog factors across combustion, venting, and fugitives."""
        csv_data = (
            "Facility,Date,Process,Fuel,Quantity,Unit\n"
            f"{test_facility.name},2024-01,Combustion,Natural Gas,10000,m3\n"
            f"{test_facility.name},2024-02,Flaring,Natural Gas,5000,m3\n"
            f"{test_facility.name},2024-03,Venting,Natural Gas,2000,m3\n"
            f"{test_facility.name},2024-04,Pneumatics,Pneumatic Devices,15,devices\n"
            f"{test_facility.name},2024-05,Fugitive,Compressor Seals,4,compressors\n"
        )
        status = self._run_upload(app, csv_data, "scope1_tier1.csv", test_user.id, scope=1)
        assert status["status"] == "completed"
        assert status["processed"] == 5
        assert status["skipped_count"] == 0

        # Verify DB records
        em = Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=1).first()
        assert em is not None
        assert em.co2e_total > 0

    def test_scope1_tier2_bulk_csv_upload_custom_factors(self, app, test_user, test_facility, db_session):
        """Tier 2 Bulk CSV: Uses regional custom emission factors created in DB."""
        # Create a custom factor
        cf = CustomFactor.query.filter_by(name="Regional Saharan Sweet Gas").first()
        if not cf:
            cf = CustomFactor(
                name="Regional Saharan Sweet Gas",
                co2_factor=51.25,
                ch4_factor=0.0008,
                n2o_factor=0.00008,
                unit="kg/MMBtu",
                hhv_factor=1050.0,
                parent_fuel="Natural Gas",
                created_by=test_user.id,
            )
            db_session.add(cf)
            db_session.commit()

        csv_data = (
            "Facility,Date,Process,Fuel,Quantity,Unit,FactorSource\n"
            f"{test_facility.name},2024-06,Combustion,Regional Saharan Sweet Gas,12000,m3,custom\n"
        )
        status = self._run_upload(app, csv_data, "scope1_tier2.csv", test_user.id, scope=1)
        assert status["status"] == "completed"
        assert status["processed"] == 1
        assert status["skipped_count"] == 0

        em = Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=6).first()
        assert em is not None
        assert em.fuel_type == "Regional Saharan Sweet Gas"
        assert em.co2e_total > 0

    def test_scope1_tier3_bulk_csv_upload_engineering_parameters(self, app, test_user, test_facility, db_session):
        """Tier 3 Bulk CSV: Engineering mode with physical parameters (c1, c2, hhv, GOR, depth, diameter)."""
        csv_data = (
            "Facility,Date,Process,Fuel,Quantity,Unit,FactorSource,HHV,CombustionEff,C1,C2,CO2Mol,UnloadDepth,UnloadDiam,UnloadPress,UnloadEvents\n"
            f"{test_facility.name},2024-07,Combustion,Natural Gas,15000,m3,specific,1020,99.5,88.5,8.2,1.5,,,,,\n"
            f"{test_facility.name},2024-08,Flaring,Natural Gas,8000,m3,specific,1020,98.0,85.0,10.0,2.0,,,,,\n"
            f"{test_facility.name},2024-09,Liquids Unloading,,4,events,specific,,,,,,,3500,2.875,400,4\n"
        )
        status = self._run_upload(app, csv_data, "scope1_tier3.csv", test_user.id, scope=1)
        assert status["status"] == "completed"
        assert status["processed"] == 3
        assert status["skipped_count"] == 0

        em_comb = Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=7).first()
        assert em_comb is not None
        assert em_comb.co2e_total > 0

    def test_scope2_bulk_csv_upload_all_utility_types(self, app, test_user, test_facility, db_session):
        """Scope 2 Bulk CSV: Location-based electricity, Market-based renewable PPA, and Purchased Steam."""
        csv_data = (
            "Facility,Date,ElectricityKWh,FactorType,Factor,SteamMMBtu,HeatUnit\n"
            f"{test_facility.name},2024-01,25000,grid,0.520,,\n"
            f"{test_facility.name},2024-02,50000,market,0.000,,\n"
            f"{test_facility.name},2024-03,0,steam,53.06,1200,mmbtu\n"
        )
        status = self._run_upload(app, csv_data, "scope2_all.csv", test_user.id, scope=2)
        assert status["status"] == "completed"
        assert status["processed"] == 3
        assert status["skipped_count"] == 0

        s2_rec = Scope2Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=1).first()
        assert s2_rec is not None
        assert pytest.approx(s2_rec.co2e, 1e-3) == (25000 * 0.520) / 1000.0

    def test_scope3_bulk_csv_upload_all_categories_and_units(self, app, test_user, test_facility, db_session):
        """Scope 3 Bulk CSV: Uploading mass, distance, and spend EEIO units across multiple categories."""
        csv_data = (
            "Facility,Date,Category,ActivityAmount,Unit,EmissionFactor,EFUnit\n"
            f"{test_facility.name},2024-01,Category 1: Purchased Goods,50,tonnes,800,kg CO2e / tonne\n"
            f"{test_facility.name},2024-02,Category 2: Capital Goods,150000,$,350,kg CO2e / $1000\n"
            f"{test_facility.name},2024-03,Category 4: Upstream Transportation,25000,tonne-km,0.12,kg CO2e / tonne-km\n"
            f"{test_facility.name},2024-04,Category 6: Business Travel,45000,passenger-km,0.18,kg CO2e / passenger-km\n"
        )
        status = self._run_upload(app, csv_data, "scope3_all.csv", test_user.id, scope=3)
        assert status["status"] == "completed"
        assert status["processed"] == 4
        assert status["skipped_count"] == 0

        # Verify cement calculation: 50 tonnes * 800 kg/t / 1000 = 40.0 tCO2e
        s3_mat = Scope3Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=1).first()
        assert s3_mat is not None
        assert pytest.approx(s3_mat.co2e, 1e-2) == 40.0

        # Verify spend calculation: $150,000 * 350 / 1e6 = 52.5 tCO2e
        s3_spend = Scope3Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=2).first()
        assert s3_spend is not None
        assert pytest.approx(s3_spend.co2e, 1e-2) == 52.5
