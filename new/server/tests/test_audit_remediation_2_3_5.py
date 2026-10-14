"""
Verification tests for Remediation Matrix Items 2, 3, and 5:
- Item 2: Resolve default component EFs when numeric counts are passed; raise ValueError on value is None in convert()
- Item 3: Explicit unit parameter for efficiency & carbon weight (unit='pct' vs 'fraction') and support cw == 0.0
- Item 5: Distributed job state tracking (Redis / snapshot) and CSV streaming
"""
import pytest
from unittest.mock import MagicMock, patch

from calculations.fugitive import ComponentFugitiveCalculator
from calculations.units import convert, normalize_efficiency
from calculations.constants import GWP_AR5
from calculations.combustion import CombustionCalculator
from validation.reference_model.fugitives import IndependentFugitiveModel
from validation.reference_model.unit_conversions import IndependentUnitConverter
import background_processor


def _val(x):
    if isinstance(x, dict):
        return float(x.get("value", 0.0))
    if hasattr(x, "value"):
        return float(x.value)
    return float(x)


class TestItem2ComponentFugitivesAndConvert:
    """Item 2: Component EFs resolution on raw numeric counts and convert(None) validation."""

    def test_component_fugitives_raw_numeric_counts_non_zero(self):
        calc = ComponentFugitiveCalculator()
        # Pass raw integer counts (not inner dicts with explicit EF)
        raw_counts = {"valves": 10, "connectors": 50, "flanges": 20}
        res = calc.calculate(component_counts=raw_counts, ch4_content=0.85, uncertainties={}, gwp_dict=GWP_AR5)

        ch4_val = _val(res["results"]["ch4"])
        assert ch4_val > 0.0, f"Expected non-zero CH4 emissions, got {ch4_val}"
        assert res["total_co2e"] > 0.0

        # Assert reference model matches
        ref = IndependentFugitiveModel.calculate_component(component_counts=raw_counts, ch4_content=0.85, gwp_standard="AR5")
        assert ref["ch4"] > 0.0
        assert pytest.approx(ch4_val, rel=1e-4) == ref["ch4"]

    def test_convert_none_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot convert None value"):
            convert(None, "m3", "scf")

        with pytest.raises(ValueError, match="Cannot convert None value"):
            IndependentUnitConverter.convert(None, "tonne", "kg")


class TestItem3UnitScalingAndZeroCarbon:
    """Item 3: Explicit unit parameters ('pct' vs 'fraction') and cw == 0.0 support."""

    def test_normalize_efficiency_modes(self):
        # 1.0% boiler efficiency in percentage mode -> 0.01
        eff_pct = normalize_efficiency(1.0, unit="pct")
        assert eff_pct == pytest.approx(0.01)

        # 1.0 (100%) boiler efficiency in fraction mode -> 1.0
        eff_frac = normalize_efficiency(1.0, unit="fraction")
        assert eff_frac == pytest.approx(1.0)

        # Explicit string with % symbol -> 0.01
        eff_str = normalize_efficiency("1.0%")
        assert eff_str == pytest.approx(0.01)

    def test_combustion_carbon_weight_pct_vs_fraction(self):
        calc = CombustionCalculator()
        fuel_qty = 1000.0  # kg

        # 0.5% carbon weight
        res_pct = calc.calculate(
            fuel_quantity=fuel_qty,
            fuel_unit="kg",
            fuel_type="Diesel",
            carbon_wt=0.5,
            carbon_wt_unit="pct",
            gwp_dict=GWP_AR5,
        )

        # 0.5 (50%) carbon weight
        res_frac = calc.calculate(
            fuel_quantity=fuel_qty,
            fuel_unit="kg",
            fuel_type="Diesel",
            carbon_wt=0.5,
            carbon_wt_unit="fraction",
            gwp_dict=GWP_AR5,
        )

        co2_pct = _val(res_pct["results"]["co2"])
        co2_frac = _val(res_frac["results"]["co2"])

        # 50% carbon should be exactly 100x higher than 0.5% carbon
        assert pytest.approx(co2_frac / co2_pct, rel=1e-3) == 100.0

    def test_combustion_zero_carbon_fuel_hydrogen(self):
        calc = CombustionCalculator()
        # Pure hydrogen combustion (cw == 0.0) must succeed with 0 CO2
        res = calc.calculate(
            fuel_quantity=500.0,
            fuel_unit="kg",
            fuel_type="gases",
            carbon_wt=0.0,
            carbon_wt_unit="pct",
            gwp_dict=GWP_AR5,
        )
        co2_val = _val(res["results"]["co2"])
        assert co2_val == 0.0


class TestItem5JobStateTrackingAndStreaming:
    """Item 5: Redis job state tracking & resilience across workers."""

    def test_redis_job_state_persistence_and_loading(self):
        mock_redis = MagicMock()
        storage = {}

        def mock_setex(name, time, value):
            storage[name] = value

        def mock_get(name):
            return storage.get(name)

        mock_redis.setex.side_effect = mock_setex
        mock_redis.get.side_effect = mock_get

        with patch("background_processor._get_redis", return_value=mock_redis):
            job_id = "test-job-redis-123"
            with background_processor.upload_jobs_lock:
                background_processor.upload_jobs[job_id] = {
                    "status": "processing",
                    "progress": 42,
                    "processed": 420,
                    "total": 1000,
                    "errors": [],
                    "created_at": 123456789,
                }

            # Persist forced
            background_processor._persist_job(job_id, force=True)

            assert f"upload_job:{job_id}" in storage

            # Simulate another worker process where in-memory upload_jobs does NOT have this job
            with background_processor.upload_jobs_lock:
                background_processor.upload_jobs.pop(job_id, None)

            # Load job must retrieve from Redis
            loaded = background_processor._load_job(job_id)
            assert loaded is not None
            assert loaded["progress"] == 42
            assert loaded["processed"] == 420
            assert loaded["status"] == "processing"
