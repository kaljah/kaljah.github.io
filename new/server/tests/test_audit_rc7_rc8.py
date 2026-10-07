"""RC-7 (GWP constants) and RC-8 (gas composition basis) regressions."""
import pytest

from calculations.constants import get_active_gwp
from calculations.units import composition_fractions


# BUG-013: IPCC AR5 WG1 Table 8.7 and AR6 WG1 Table 7.15
@pytest.mark.parametrize("std,h,ch4,n2o", [
    ("AR5", "20", 84.0, 264.0), ("AR5", "100", 28.0, 265.0),
    ("AR6", "20", 81.2, 273.0), ("AR6", "100", 27.9, 273.0),
    ("AR4", "20", 72.0, 289.0), ("AR4", "100", 25.0, 298.0),
])
def test_bug013_gwp_tables(std, h, ch4, n2o):
    g = get_active_gwp(standard=std, horizon=h)
    assert g["CH4"] == ch4 and g["N2O"] == n2o


def test_bug013_client_constants_match_server():
    import os
    import re

    path = os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "constants.ts")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "constants.js")
    js = open(path, encoding="utf-8").read()
    for block, std in (("GWP_AR5", "AR5"), ("GWP_AR6", "AR6")):
        body = js[js.index(block):js.index("}", js.index(block))]
        for key, horizon, gas in (("CH4_20", "20", "CH4"), ("N2O_20", "20", "N2O")):
            m = re.search(rf"{key}\s*:\s*([0-9.]+)", body)
            assert m and float(m.group(1)) == get_active_gwp(standard=std, horizon=horizon)[gas], (block, key)


# BUG-023 / BUG-024
def test_bug023_percent_basis_decided_once():
    fr, info = composition_fractions({"c1": 85, "c2": 8, "c3": 4, "c4": 1.0, "c5": 0.5, "co2": 1.0, "n2": 0.5})
    assert info["basis"] == "percent"
    assert fr["c4"] == pytest.approx(0.01) and fr["c5"] == pytest.approx(0.005) and fr["co2"] == pytest.approx(0.01)


def test_bug023_fraction_basis():
    fr, info = composition_fractions({"c1": 0.9, "c2": 0.05, "co2": 0.02, "n2": 0.03})
    assert info["basis"] == "fraction" and fr["c1"] == pytest.approx(0.9)


def test_bug024_inerts_counted_incomplete_not_renormalised():
    fr, info = composition_fractions({"c1": 70, "co2": 5})  # 75 %: rest unspecified
    assert fr["c1"] == pytest.approx(0.70) and not info["renormalised"]
    fr, _ = composition_fractions({"c1": 90, "n2": 10})
    assert fr["c1"] == pytest.approx(0.90)


def test_composition_over_100_rejected():
    with pytest.raises(ValueError):
        composition_fractions({"c1": 95, "c2": 10})


def test_bug023_flaring_c4_one_mol_percent():
    """Hand calc per the audit repro: 1.0 mol% C4 must be 1 %, not 100 %."""
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    comps = d._composition({"c1": 85, "c2": 8, "c3": 4, "c4": 1.0, "c5": 0.5, "co2_mol": 1.0, "n2": 0.5})
    assert comps["c4"] == pytest.approx(0.01) and comps["c5"] == pytest.approx(0.005)
    assert sum(v for k, v in comps.items()) == pytest.approx(1.0)
