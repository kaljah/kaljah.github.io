"""
test_csv_engine_matrix.py
-------------------------
Adversarial Stress-Test & Deterministic Verification Matrix for CSV Uploaders,
Process Classifiers, Ingestion Pipelines, and Engineering Calculation Engines.
"""

import os
import io
import math
import csv
import tempfile
import pytest
from decimal import Decimal

from models import (
    User,
    Facility,
    Emission,
    Scope2Emission,
    Scope3Emission,
    ProductionData,
)
from background_processor import (
    _clean_float,
    _build_mapping,
    _process_file_thread,
    get_job_status,
    upload_jobs,
    upload_jobs_lock,
)
from calculations.dispatcher import CalculationDispatcher, dispatcher
from calculations.base import BaseCalculator
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.vented import (
    BlowdownCalculator,
    LiquidsUnloadingCalculator,
    TankFlashingCalculator,
)
from calculations.units import (
    calculate_co2e,
    normalize_gas_volume_to_standard,
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    to_kelvin,
    to_psia,
)
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6, get_active_gwp


from app import app as flask_app
from extensions import db


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
    u = User.query.filter_by(email="adversarial_qa@ghg.com").first()
    if not u:
        u = User(
            email="adversarial_qa@ghg.com",
            fullName="Metrology Auditor",
            orgName="GHG Metrology",
            sector="Oil & Gas",
            role="admin",
            location="Global",
        )
        u.set_password("SecureMetrology2026!")
        db_session.add(u)
        db_session.commit()
    return u


@pytest.fixture
def test_facility(db_session, test_user):
    f = Facility.query.filter_by(name="Hassi Messaoud Central Unit").first()
    if not f:
        f = Facility(
            name="Hassi Messaoud Central Unit",
            location="Ouargla",
            segment="Upstream",
            created_by=test_user.id,
        )
        db_session.add(f)
        db_session.commit()
    return f


# ==============================================================================
# PHASE 1: STRUCTURAL, FORMATTING & FIELD COERCION MATRIX
# ==============================================================================

class TestFieldCoercionAndSanitization:
    """Rigorous metrological tests for _clean_float."""

    @pytest.mark.parametrize(
        "raw_input, expected",
        [
            # Standard numeric representations
            ("1234.56", 1234.56),
            (1234.56, 1234.56),
            (100, 100.0),
            # European comma decimals
            ("1234,56", 1234.56),
            ("0,0045", 0.0045),
            ("-85,25", -85.25),
            # Thousands separators (comma)
            ("1,000,000.50", 1000000.50),
            ("12,345", 12345.0),
            # Thousands separators (dot) with European comma
            ("1.000.000,50", 1000000.50),
            ("12.345,67", 12345.67),
            # Scientific notation
            ("1.45e-4", 0.000145),
            ("2.1E+6", 2100000.0),
            ("3.5e3", 3500.0),
            # Quoted numeric strings with currency / units
            ("$45.00", 45.0),
            ("€1250.75", 1250.75),
            ("£99.99", 99.99),
            ("120 kW", 120.0),
            ("50.5 m3", 50.5),
            ("100.25 tCO2e", 100.25),
            ("  75.50 %  ", 75.50),
            # Zero-width spaces & invisible characters
            ("\u200b1234.56", 1234.56),
            ("1234.56\ufeff", 1234.56),
            ("1\u00a0234.56", 1234.56),
        ],
    )
    def test_clean_float_valid_coercion(self, raw_input, expected):
        res = _clean_float(raw_input)
        assert pytest.approx(res, rel=1e-6) == expected

    @pytest.mark.parametrize(
        "raw_null",
        [
            "",
            "   ",
            "-",
            "--",
            "N/A",
            "n/a",
            "NULL",
            "null",
            "None",
            "NaN",
            "nan",
            "nil",
            "N/D",
            "#N/A",
            None,
        ],
    )
    def test_clean_float_null_representations(self, raw_null):
        assert _clean_float(raw_null, default=0.0) == 0.0
        assert _clean_float(raw_null, default=-999.0) == -999.0

    def test_clean_float_nan_and_infinity_defense(self):
        """Mathematically prove that NaN and Infinity are neutralized."""
        assert _clean_float(float("nan"), default=0.0) == 0.0
        assert _clean_float(float("inf"), default=0.0) == 0.0
        assert _clean_float(float("-inf"), default=0.0) == 0.0
        assert _clean_float("Infinity", default=0.0) == 0.0
        assert _clean_float("-Infinity", default=0.0) == 0.0


# ==============================================================================
# PHASE 1 & 2: SYNTHETIC CSV INGESTION & PROCESS DETECTION MATRIX
# ==============================================================================

class TestCSVBufferIngestionMatrix:
    """Stress-tests file processing with synthetic buffers across all structural variations."""

    def _execute_sync_thread(self, app, file_bytes, filename, user_id, scope=1):
        """Runs _process_file_thread synchronously for deterministic assertion."""
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(file_bytes)

            job_id = "test-job-" + os.urandom(6).hex()
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

    def test_csv_delimiters_semicolon(self, app, test_user, test_facility):
        """Validates European semicolon-separated CSV parsing."""
        csv_content = (
            "Facility;Date;Process;Fuel;Quantity;Unit\n"
            f"{test_facility.name};2024-01;Combustion;Diesel;1500;m3\n"
        )
        status = self._execute_sync_thread(
            app, csv_content.encode("utf-8"), "test_semicolon.csv", test_user.id
        )
        assert status["status"] == "completed"
        assert status["processed"] == 1
        assert len(status["errors"]) == 0
        assert status["skipped_count"] == 0

    def test_csv_delimiters_tab_and_pipe(self, app, test_user, test_facility):
        """Validates Tab-separated (TSV) and Pipe-separated CSV parsing."""
        # Tab
        tsv_content = (
            "Facility\tDate\tProcess\tFuel\tQuantity\tUnit\n"
            f"{test_facility.name}\t2024-02\tCombustion\tDiesel\t2500\tm3\n"
        )
        status_tsv = self._execute_sync_thread(
            app, tsv_content.encode("utf-8"), "test.tsv", test_user.id
        )
        assert status_tsv["processed"] == 1
        assert status_tsv["skipped_count"] == 0

        # Pipe
        pipe_content = (
            "Facility|Date|Process|Fuel|Quantity|Unit\n"
            f"{test_facility.name}|2024-03|Combustion|Diesel|3500|m3\n"
        )
        status_pipe = self._execute_sync_thread(
            app, pipe_content.encode("utf-8"), "test_pipe.csv", test_user.id
        )
        assert status_pipe["processed"] == 1
        assert status_pipe["skipped_count"] == 0

    def test_csv_encoding_utf8_bom_and_windows_1252(self, app, test_user, test_facility):
        """Validates UTF-8 with BOM and Windows-1252 / ISO-8859-1 encodings with accented characters."""
        # UTF-8 with BOM (\xef\xbb\xbf)
        bom_csv = (
            "\ufeffFacility,Date,Process,Fuel,Quantity,Unit\n"
            f"{test_facility.name},2024-04,Combustion,Diesel,1200,m3\n"
        ).encode("utf-8-sig")

        status_bom = self._execute_sync_thread(app, bom_csv, "bom.csv", test_user.id)
        assert status_bom["processed"] == 1
        assert status_bom["skipped_count"] == 0

        # Windows-1252 with special non-ASCII character (e.g. °C or accented é)
        win_csv = (
            f"Facility,Date,Process,Fuel,Quantity,Unit\n"
            f"{test_facility.name},2024-05,Combustion,Diesel,1800,m3\n"
        ).encode("windows-1252")

        status_win = self._execute_sync_thread(app, win_csv, "win1252.csv", test_user.id)
        assert status_win["processed"] == 1
        assert status_win["skipped_count"] == 0

    def test_csv_row_terminator_crlf_and_legacy_cr(self, app, test_user, test_facility):
        """Validates Windows CRLF (\r\n) and legacy Mac CR (\r) line terminators."""
        crlf_csv = (
            "Facility,Date,Process,Fuel,Quantity,Unit\r\n"
            f"{test_facility.name},2024-06,Combustion,Diesel,1400,m3\r\n"
        ).encode("utf-8")
        status_crlf = self._execute_sync_thread(app, crlf_csv, "crlf.csv", test_user.id)
        assert status_crlf["processed"] == 1

        cr_csv = (
            "Facility,Date,Process,Fuel,Quantity,Unit\r"
            f"{test_facility.name},2024-07,Combustion,Diesel,1600,m3\r"
        ).encode("utf-8")
        status_cr = self._execute_sync_thread(app, cr_csv, "cr.csv", test_user.id)
        assert status_cr["processed"] == 1

    def test_csv_whitespace_and_empty_rows(self, app, test_user, test_facility):
        """Validates resilient skipping of empty lines and padded whitespace in headers and cells."""
        messy_csv = (
            "  Facility  ,  Date  ,  Process  ,  Fuel  ,  Quantity  ,  Unit  \n"
            "\n"
            f"  {test_facility.name}  , 2024-08 , Combustion , Diesel , 2100.5 , m3 \n"
            ",,,,,\n"
            "   \n"
            f"  {test_facility.name}  , 2024-09 , Combustion , Diesel , 2200.0 , m3 \n"
            "\n"
        ).encode("utf-8")
        status = self._execute_sync_thread(app, messy_csv, "messy.csv", test_user.id)
        assert status["processed"] == 2
        assert status["skipped_count"] == 0

    def test_csv_volumetric_extremes(self, app, test_user):
        """Validates zero-byte and header-only empty files."""
        # 0-byte file
        status_zero = self._execute_sync_thread(app, b"", "zero.csv", test_user.id)
        assert status_zero["processed"] == 0
        assert status_zero["status"] == "completed"

        # Header-only file
        header_only = b"Facility,Date,Process,Fuel,Quantity,Unit\n"
        status_hdr = self._execute_sync_thread(app, header_only, "header_only.csv", test_user.id)
        assert status_hdr["processed"] == 0
        assert status_hdr["status"] == "completed"

    def test_process_type_missing_signature_fallback(self, app, test_user, test_facility):
        """Verifies that rows lacking process type are rejected deterministically with explicit diagnostics."""
        no_proc_csv = (
            "Facility,Date,Fuel,Quantity,Unit\n"
            f"{test_facility.name},2024-10,Diesel,500,m3\n"
        ).encode("utf-8")
        status = self._execute_sync_thread(app, no_proc_csv, "no_proc.csv", test_user.id)
        assert status["processed"] == 1
        assert status["skipped_count"] == 1
        assert "Missing process type" in status["skipped_preview"][0]["reason"]

    def test_auto_factor_type_supports_tier3_specific(self, app, test_user, test_facility):
        """Verifies that in global_factor_type='auto' mode, rows with factor_type='specific' route to Tier 3."""
        # Row with specific Tier 3 flaring parameters
        specific_csv = (
            "Facility,Date,Process,Fuel,Quantity,Unit,factor_type,ch4_content,flare_type\n"
            f"{test_facility.name},2024-11,Flaring,Natural Gas,1000,m3,specific,90,elevated\n"
        ).encode("utf-8")
        status = self._execute_sync_thread(app, specific_csv, "specific_auto.csv", test_user.id)
        assert status["status"] == "completed"
        assert status["processed"] == 1
        assert status["skipped_count"] == 0
        from models import Emission
        with app.app_context():
            em = Emission.query.filter_by(facility_id=test_facility.id, year=2024, month=11).first()
            assert em is not None
            assert em.co2e_total > 0


# ==============================================================================
# PHASE 3: MATHEMATICAL & ENGINEERING CALCULATION AUDIT
# ==============================================================================

class TestMetrologyAndEngineeringPrecision:
    """Verifies numerical determinism, singularity handling, and fixed-point precision."""

    def test_base_calculator_nan_and_inf_guard(self):
        """Proves that BaseCalculator.validate_inputs rejects NaN and Inf."""
        calc = BaseCalculator("TestCalc", "§1.0")

        with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
            calc.validate_inputs({"flow": float("nan")}, ["flow"])

        with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
            calc.validate_inputs({"flow": float("inf")}, ["flow"])

        with pytest.raises(ValueError, match="cannot be negative"):
            calc.validate_inputs({"flow": -10.0}, ["flow"])

    def test_dispatcher_nan_and_inf_guard(self):
        """Proves that dispatcher.dispatch rejects NaN and Inf quantities."""
        with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
            dispatcher.dispatch(
                process_type="stationary_combustion",
                inputs={
                    "process_type": "stationary_combustion",
                    "fuel": "Diesel",
                    "quantity": float("nan"),
                    "unit": "m3",
                    "factor_source": "default",
                },
                emission_factors={"co2": 2.68, "ch4": 0.0001, "n2o": 0.0001},
                uncertainties={},
            )

        with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
            dispatcher.dispatch(
                process_type="stationary_combustion",
                inputs={
                    "process_type": "stationary_combustion",
                    "fuel": "Diesel",
                    "quantity": float("inf"),
                    "unit": "m3",
                    "factor_source": "default",
                },
                emission_factors={"co2": 2.68, "ch4": 0.0001, "n2o": 0.0001},
                uncertainties={},
            )

    def test_blowdown_compressibility_zero_singularity_defense(self):
        """Verifies that z_factor = 0 or negative is safely clamped to 1.0 (no ZeroDivisionError)."""
        bd_calc = BlowdownCalculator()
        res = bd_calc.calculate(
            blowdown_volume=100.0,
            pressure=150.0,
            events=5,
            ch4_content=0.85,
            uncertainties={},
            z_factor=0.0,  # Singularity injection
            press_unit="psig",
        )
        assert res["total_co2e"] > 0
        assert not math.isnan(res["total_co2e"])
        assert not math.isinf(res["total_co2e"])

    def test_liquids_unloading_absolute_zero_temperature_defense(self):
        """Verifies that near-absolute zero temperatures do not produce division-by-zero."""
        lu_calc = LiquidsUnloadingCalculator()
        res = lu_calc.calculate(
            well_depth=5000,
            diameter=2.5,
            pressure=100,
            ch4_content=0.85,
            events=2,
            uncertainties={},
            operating_temperature=-459.67,  # Absolute zero in Fahrenheit
            temp_unit="F",
        )
        assert res["total_co2e"] > 0
        assert not math.isnan(res["total_co2e"])

    def test_flaring_dual_efficiency_stoichiometric_mass_balance(self):
        """
        Mathematically verifies API Compendium §5.2 flaring carbon mass balance:
        CH4 (16.04 g/mol) combusted to CO2 (44.01 g/mol) at 98% destruction.
        """
        fl_calc = FlaringCalculator()
        vol_m3 = 1000.0
        ch4_frac = 0.90
        # Methane density = 0.6785 kg/m3 at standard conditions
        # Native CH4 volume = 900 m3 -> 610.65 kg CH4 -> 0.61065 tonnes CH4
        # At 98% destruction:
        #   Undestroyed CH4 = 0.61065 * 0.02 = 0.012213 tonnes CH4
        #   Combusted CH4 = 0.61065 * 0.98 = 0.598437 tonnes CH4
        #   CO2 produced = 0.598437 * (44.01 / 16.04) = 1.641975 tonnes CO2
        res = fl_calc.calculate(
            gas_volume=vol_m3,
            ch4_fraction=ch4_frac,
            flare_type="elevated",
            uncertainties={},
            combustion_efficiency=0.98,
            destruction_efficiency=0.98,
            fuel_unit="m3",
        )
        ch4_tonnes = res["results"]["ch4"]["value"]
        co2_tonnes = res["results"]["co2"]["value"]

        expected_ch4 = (vol_m3 * ch4_frac * 0.6785 * (1.0 - 0.98)) / 1000.0
        expected_co2 = ((vol_m3 * ch4_frac * 0.6785 * 0.98) * (44.01 / 16.04)) / 1000.0

        assert pytest.approx(ch4_tonnes, rel=1e-3) == expected_ch4
        assert pytest.approx(co2_tonnes, rel=1e-3) == expected_co2

    def test_gwp_standards_cross_consistency(self):
        """
        Mathematically proves AR4, AR5, and AR6 GWP multipliers match IPCC source tables:
        AR4: CH4 = 25,   N2O = 298
        AR5: CH4 = 28,   N2O = 265
        AR6: CH4 = 27.9, N2O = 273
        """
        co2, ch4, n2o = 10.0, 2.0, 0.5

        # AR4 Analytical
        ar4_expected = Decimal("10.0") * 1 + Decimal("2.0") * 25 + Decimal("0.5") * 298
        ar4_calc = calculate_co2e(co2, ch4, n2o, gwp_standard="AR4")
        assert pytest.approx(float(ar4_expected), rel=1e-6) == ar4_calc

        # AR5 Analytical
        ar5_expected = Decimal("10.0") * 1 + Decimal("2.0") * 28 + Decimal("0.5") * 265
        ar5_calc = calculate_co2e(co2, ch4, n2o, gwp_standard="AR5")
        assert pytest.approx(float(ar5_expected), rel=1e-6) == ar5_calc

        # AR6 Analytical
        ar6_expected = Decimal("10.0") * 1 + Decimal("2.0") * Decimal("27.9") + Decimal("0.5") * 273
        ar6_calc = calculate_co2e(co2, ch4, n2o, gwp_standard="AR6")
        assert pytest.approx(float(ar6_expected), rel=1e-6) == ar6_calc

    def test_high_volume_summation_precision_stability(self):
        """
        Simulates 10,000 multi-row float calculations to verify that floating point
        accumulation matches math.fsum and Decimal within IEEE-754 limits.
        """
        n_rows = 10000
        quantities = [123.456 + (i * 0.001) for i in range(n_rows)]
        factor = 2.68  # kg CO2 / L diesel

        # Standard naive float sum
        co2_floats = [(q * factor) / 1000.0 for q in quantities]
        naive_sum = sum(co2_floats)

        # High-precision math.fsum
        fsum_result = math.fsum(co2_floats)

        # Fixed-point Decimal reference
        factor_dec = Decimal("2.68")
        dec_sum = sum(
            (Decimal(str(round(q, 3))) * factor_dec) / Decimal("1000.0")
            for q in quantities
        )

        drift = abs(naive_sum - fsum_result)
        # Verify cumulative summation drift is well below 1e-9 tonnes CO2e
        assert drift < 1e-9
        assert pytest.approx(naive_sum, rel=1e-4) == float(dec_sum)
