"""Regression tests for the clean-room calculation audit of November 2026, finding F-VENT2-06: Compendium rows that the
catalog did not offer. Expected values are count x the factor printed in API Compendium 2021 Tables 6-34, 6-40, 6-42,
6-43 and 6-46 (tonnes CH4, at each table's own CH4 basis), worked by hand, never read from the engine.
"""
import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions
from services.scope1_calc import resolve_factor


def _act(process, key, amount, unit="count", **kw):
    inputs = {"activity_key": key, "amount": amount, "unit": unit, **kw}
    return {"process_type": process, "factor_source": "default", "amount": amount, "quantity": amount, "unit": unit,
            "calc_inputs": {process: inputs}}


CASES = [
    # Table 6-34: processing average 3.164 t CH4 / plant-yr; 1.425e-4 t / 10^6 scf; 5.034e-3 t / 10^6 Sm3 processed
    ("pneumatic", "proc_pc_avg_plant", 2, "count", {}, 2 * 3.164),
    ("pneumatic", "proc_pc_avg_throughput", 25e6 * 365, "scf", {}, 9125 * 1.425e-4),
    ("pneumatic", "proc_pc_avg_throughput_m3", 20e6 * 365, "m3", {}, 7300 * 5.034e-3),
    # Table 6-42: transmission / storage facility average 21.6 t CH4 / station-yr
    ("pneumatic", "ts_pc_facility", 3, "count", {}, 3 * 21.6),
    # Table 6-40: standby pressurised 1.24e-3 (transmission) / 2.34e-3 (storage); averages 7.42e-3 / 7.99e-3 t / h
    ("compressor_venting", "trans_rp_standby", 5, "count", {"activity_hours": 630}, 5 * 630 * 1.24e-3),
    ("compressor_venting", "stor_rp_standby", 5, "count", {"activity_hours": 630}, 5 * 630 * 2.34e-3),
    ("compressor_venting", "trans_rp_avg", 2, "count", {"activity_hours": 8760}, 2 * 8760 * 7.42e-3),
    ("compressor_venting", "stor_rp_avg", 1, "count", {"activity_hours": 8760}, 8760 * 7.99e-3),
    # Table 6-43: miscellaneous 21.75 t CH4 / station-yr
    ("non_routine_venting", "ts_misc", 2, "count", {}, 2 * 21.75),
    # Table 6-46: dig-ins (Lamb et al., 2015) 0.0466 t CH4 / mile-yr
    ("non_routine_venting", "dist_digins_lamb", 20, "count", {}, 20 * 0.0466),
]


@pytest.mark.parametrize("process,key,amount,unit,kw,ch4", CASES, ids=[c[1] for c in CASES])
def test_f_vent2_06_printed_rows(app, process, key, amount, unit, kw, ch4):
    p = _act(process, key, amount, unit, **kw)
    with app.app_context():
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
    assert em["ch4"] == pytest.approx(ch4, rel=1e-6)


def test_f_vent2_06_storage_average_matches_its_annual_figure():
    """Table 6-40 prints the storage average as 70,000 kg CH4 / compressor-yr and 7.99e-3 t / h (8,760 h)."""
    from calculations.activity_factors import ACTIVITY_FACTORS

    assert ACTIVITY_FACTORS["stor_rp_avg"]["ch4"] * 8760 == pytest.approx(70.0, abs=0.05)
    assert ACTIVITY_FACTORS["trans_rp_avg"]["ch4"] * 8760 == pytest.approx(65.0, abs=0.05)
