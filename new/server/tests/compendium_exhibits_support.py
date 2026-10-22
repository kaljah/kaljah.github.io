"""Shared helpers for the API Compendium 2021 worked-example (Exhibit) tests.

Source: "Compendium of Greenhouse Gas Emissions Methodologies for the Natural Gas and Oil Industry",
API, November 2021 (https://api.org/-/media/Files/Policy/ESG/GHG/API-GHG-Compendium-110921.pdf).
Every expected value in the exhibit test files is the number the exhibit itself prints, quoted as printed
(``"1,263"``, ``"6.46e-4"``). The tolerance is the rounding of that printed number (half a unit of its last
digit) times ``slack``; ``slack`` is above 1 only where the exhibit chains rounded intermediate values, and the
case says why. An exhibit that disagrees with its own tables (an erratum) is marked in the case and the
test then checks the engine against the exhibit's method with the exhibit's own inputs.
"""
import json
import math
import re

import pytest

_NUM = re.compile(r"^\s*([-+]?)([\d,]*\.?\d*)(?:[eE]([-+]?\d+))?\s*$")


def printed(text):
    """(value, half-ulp) of a number as the exhibit prints it: '1,263' -> (1263, 0.5); '6.46e-4' -> (6.46e-4, 5e-7)."""
    m = _NUM.match(str(text))
    if not m:
        raise ValueError(f"not a printed number: {text!r}")
    sign, mant, exp = m.groups()
    mant = mant.replace(",", "")
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    scale = 10 ** int(exp or 0)
    value = float(sign + mant) * scale
    return value, 0.5 * 10 ** (-decimals) * scale


# The exhibits do their arithmetic with rounded molecular weights (CH4 16, CO2 44, C 12) and 379.3 scf/lbmole; the
# engine uses CH4 16.04, CO2 44.01, C 12.011. A CH4 result differs by up to 0.25 %, a CO2 result by up to 0.3 % (CO2
# derived through the CH4 weight), so a value the exhibit prints is matched to this relative tolerance.
REL_MW = 3e-3
# The engine converts scf -> m3 -> mass with fixed gas densities (60 F); the exhibits use 379.3 scf/lbmol and rounded
# molecular weights: the two differ by up to about 0.4 %.
REL_ENGINE = 5e-3


# Mass of one scf of gas: the exhibits use 16 (CH4) and 44 (CO2) lb/lbmole with 379.3 scf/lbmole; the engine uses 16.04 and
# 44.01 kg/kmol with 23.685 m3/kmol. A calculator on the engine's constants therefore reads CH4 0.2235 % above the exhibit's
# arithmetic and CO2 0.0054 % below; ``gas="ch4"`` / ``"co2"`` expects exactly that shift, leaving ``rel`` for everything else.
_ENGINE_LB_PER_SCF = lambda mw: mw / 23.685 * 0.028316846592 / 0.45359237  # noqa: E731
CONSTANTS_SHIFT = {"ch4": _ENGINE_LB_PER_SCF(16.04) / (16.0 / 379.3), "co2": _ENGINE_LB_PER_SCF(44.01) / (44.0 / 379.3)}


def assert_printed(got, text, slack=1.0, what="", rel=0.0, sig=None, gas=None):
    """``got`` equals the exhibit's printed ``text`` to its printed precision (times ``slack``).

    ``rel`` adds a relative allowance for a documented difference of constants (see REL_MW); ``gas`` ("ch4" / "co2")
    applies the engine-constants shift of CONSTANTS_SHIFT to the printed value first; ``sig`` gives the number
    of significant figures the exhibit printed when trailing zeros are not exact ("1,050" is 3). The allowance is the printed
    rounding (times ``slack``) plus the relative allowance: the engine may differ from the exhibit's exact arithmetic by
    ``rel`` and the exhibit's printed figure from its exact arithmetic by half a unit of its last digit."""
    want, half_ulp = printed(text)
    if gas is not None:
        want, half_ulp = want * CONSTANTS_SHIFT[gas], half_ulp * CONSTANTS_SHIFT[gas]
    if sig is not None:  # "1,050" printed to 3 significant figures: its precision is 5, not 0.5
        half_ulp = 0.5 * 10 ** (math.floor(math.log10(abs(want))) - sig + 1)
    allowed = half_ulp * slack + rel * abs(want)
    assert got == pytest.approx(want, abs=allowed, rel=0), (
        f"{what}: engine {got!r} vs exhibit {text} (allowed +/-{allowed:g}, off by {got - want:+g} = "
        f"{(got - want) / want:+.3%})")


def tonnes(res, gas):
    """A gas value (tonnes) from a calculator result or a compute_emissions dict."""
    if "results" in res:
        r = res["results"][gas]
        return float(r["value"] if isinstance(r, dict) else r)
    return float(res.get(gas) or 0)


def run_scope1(app, payload):
    """The path POST /api/emissions takes: resolve_factor then compute_emissions."""
    from calculations.constants import get_active_gwp
    from calculations.legacy_engine import compute_emissions
    from services.scope1_calc import resolve_factor
    with app.app_context():
        p = json.loads(json.dumps(payload))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        return em
