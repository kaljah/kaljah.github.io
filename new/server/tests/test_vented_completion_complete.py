"""calculations/vented_completion.py: every tier, unit, disposition and refusal (API Compendium 2021 section
6.2.3, Tables 6-5 / 6-6 / 6-7, Equations 6-4 / 6-5 / 6-7). Fixed while testing: an unknown well type, fracturing
value, control, disposition, volume or rate unit was read as a default (gas well, no fracturing, uncontrolled,
vented, scf, scf/day); Equation 6-7 without a vent duration took one day; an entered catalog CH4 factor of 0 took
the table value; a flare without an entered efficiency converted 98 % of the carbon to CO2 (96.5 % since the
December 2025 corrections; CH4 destruction stays 98 %).
"""
import pytest

from calculations.units import CONVERSIONS, NM3_TO_SM3, convert
from calculations.vented_completion import CompletionFlowbackCalculator

RHO_CH4, RHO_CO2 = CONVERSIONS["density_ch4"], CONVERSIONS["density_co2"]
R = 44.01 / 16.04


def val(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else r


def t(scf, frac, rho):
    return convert(scf, "scf", "m3") * frac * rho / 1000


@pytest.fixture
def c():
    return CompletionFlowbackCalculator()


# ---------------------------------------------------------------- Tier 1
@pytest.mark.parametrize("kw,ch4", [
    (dict(well_type="gas"), 28.8), (dict(well_type="Gas well", control_type="REC"), 13.542),
    (dict(well_type="oil"), 14.419), (dict(well_type="oil", disposition="green_completion"), 0.615),
    (dict(well_type="gas", fracturing="no"), 1.7376), (dict(well_type="oil", fracturing=False), 0.0141),
    (dict(well_type="gas", factor_code="CompGasNoHF_Vented"), 1.7376),
    (dict(well_type="gas", location="offshore"), 136.2),
])
def test_tier1_tables(c, kw, ch4):
    res = c.calculate(tier="tier1", events=2, **kw)
    assert val(res, "ch4") == pytest.approx(2 * ch4)


def test_tier1_composition_flare_and_entered_factor(c):
    lean = c.calculate(tier="1", ch4_content=40.8, co2_content=2)
    ch4 = 28.8 * 0.5
    assert val(lean, "ch4") == pytest.approx(ch4)
    assert val(lean, "co2") == pytest.approx(ch4 * (0.02 / 0.408) * R)
    flared = c.calculate(tier="default", control_type="flared")
    assert val(flared, "ch4") == pytest.approx(28.8 * 0.02)                                       # DE 98 %
    assert val(flared, "co2") == pytest.approx(28.8 * 0.965 * R)                                   # CE 96.5 %
    assert val(flared, "n2o") == pytest.approx(1842577.0 * 1020 / 1e6 * 0.0001 / 1000)
    entered = c.calculate(tier="t1", control_type="flare", control_efficiency=99)
    assert val(entered, "ch4") == pytest.approx(28.8 * 0.01)
    assert val(entered, "co2") == pytest.approx(28.8 * 0.99 * R)
    assert val(c.calculate(tier="factor", ef_ch4=0), "ch4") == 0                                   # entered 0 kept
    assert val(c.calculate(tier="factor", ef_ch4="3.5"), "ch4") == pytest.approx(3.5)


def test_zero_events(c):
    res = c.calculate(tier="tier1", events=0)
    assert val(res, "ch4") == 0 and res["total_co2e"] == 0
    assert c.calculate(factor_code="CompGasHF_Uncontrolled", flowback_volume=5)["inputs"]["tier"] == "Tier 1"  # auto


# ---------------------------------------------------------------- Tier 2
def test_equation_6_7_production_rate(c):
    res = c.calculate(tier="tier2", daily_production_rate=2, prod_rate_unit="MMscf/d", vent_duration_days=3,
                      ch4_content=85)
    assert res["inputs"]["net_flowback_scf"] == pytest.approx(6e6)
    assert val(res, "ch4") == pytest.approx(t(6e6, 0.85, RHO_CH4))
    hours = c.calculate(tier="engineering", daily_production_rate=1000, prod_rate_unit="m3/day",
                        vent_duration_hours=12, ch4_content=85)
    assert hours["inputs"]["net_flowback_scf"] == pytest.approx(convert(500, "m3", "scf"))
    flowback = c.calculate(calculation_method="eq_6_7", daily_production_rate=24, flowback_duration_hours=6,
                           ch4_content=85)
    assert flowback["inputs"]["net_flowback_scf"] == pytest.approx(6000)                          # Mcf/day default


def test_gor_and_rate_methods(c):
    gor = c.calculate(liquid_flowback_bbl=1000, gas_oil_ratio=500, gas_produced_sales_scf=100_000, ch4_content=80)
    assert gor["inputs"]["net_flowback_scf"] == pytest.approx(400_000)
    oversold = c.calculate(calculation_method="gor", liquid_flowback_bbl=1, gas_oil_ratio=10,
                           gas_produced_sales_scf=50, ch4_content=80)
    assert oversold["inputs"]["net_flowback_scf"] == 0
    rate = c.calculate(flowback_rate=10, rate_unit="Mcf/hr", flowback_duration_hours=24, ch4_content=80)
    assert rate["inputs"]["net_flowback_scf"] == pytest.approx(240_000)


# ---------------------------------------------------------------- Tier 3
@pytest.mark.parametrize("unit,scf", [
    ("scf", 1e6), ("Mcf", 1e9), ("MMscf", 1e12), ("m3", convert(1e6, "m3", "scf")),
    ("Nm3", convert(1e6 * NM3_TO_SM3, "m3", "scf")),
])
def test_metered_volume_units(c, unit, scf):
    res = c.calculate(tier="measured", flowback_volume=1e6, volume_unit=unit, ch4_content=80)
    assert res["inputs"]["net_flowback_scf"] == pytest.approx(scf)


def test_equations_6_4_and_6_5(c):
    res = c.calculate(flowback_volume=1_000_000, volume_unit="scf", injected_n2_volume=100, injected_n2_unit="Mcf",
                      initial_flowback_hours=10, flowback_duration_hours=100, ch4_content=80)
    assert res["inputs"]["net_flowback_scf"] == pytest.approx(900_000)                            # Eq 6-4
    assert res["inputs"]["initial_flowback_scf"] == pytest.approx(10 * 900_000 / 100 / 2)          # Eq 6-5
    assert val(res, "ch4") == pytest.approx(t(900_000 + 45_000, 0.80, RHO_CH4))
    co2_injected = c.calculate(flowback_volume=1000, volume_unit="scf", injected_n2_volume=500,
                               injected_gas_type="co2", ch4_content=80)
    assert co2_injected["inputs"]["net_flowback_scf"] == 1000                                     # CO2 not deducted
    zero = c.calculate(tier="tier3", flowback_volume=0, volume_unit="scf")
    assert val(zero, "ch4") == 0                                                                  # no analysis needed


def test_dispositions(c):
    base = dict(tier="tier3", flowback_volume=1_000_000, volume_unit="scf", ch4_content=80, co2_content=5)
    ch4, co2 = t(1e6, 0.80, RHO_CH4), t(1e6, 0.05, RHO_CO2)
    assert val(c.calculate(**base), "ch4") == pytest.approx(ch4)
    assert val(c.calculate(**base, disposition="vented"), "ch4") == pytest.approx(ch4)
    assert val(c.calculate(**base, disposition="recovered"), "ch4") == 0
    flared = c.calculate(**base, disposition="flared", c2plus_content=5)
    assert val(flared, "ch4") == pytest.approx(ch4 * 0.02)
    c2_co2 = t(1e6, 0.05 * 2, RHO_CO2) * 0.965
    assert val(flared, "co2") == pytest.approx(co2 + ch4 * 0.965 * R + c2_co2)
    routed = c.calculate(**base, control_efficiency=95)                                           # 95 % to a flare
    assert routed["inputs"]["frac_flared"] == pytest.approx(0.95)
    assert val(routed, "ch4") == pytest.approx(ch4 * 0.05 + ch4 * 0.95 * 0.02)
    split = c.calculate(**base, frac_vented=0.2, frac_flared=0.5, frac_recovered=0.3, control_efficiency=99)
    assert val(split, "ch4") == pytest.approx(ch4 * 0.2 + ch4 * 0.5 * 0.01)
    assert val(c.calculate(**base, disposition="split", frac_vented="20%", frac_flared="80%"), "ch4") == \
        pytest.approx(ch4 * 0.2 + ch4 * 0.8 * 0.02)


@pytest.mark.parametrize("kw,match", [
    (dict(events=-1), "cannot be negative"),
    (dict(flowback_volume="lots"), "Invalid numeric value"),
    (dict(ch4_content="x"), "Invalid numeric value"),
    (dict(ch4_content=-1), "cannot be negative"),
    (dict(ch4_content=150), "must be between 0 and 1"),
    (dict(ch4_content=90, co2_content=20), "cannot exceed 100%"),
    (dict(well_type="condensate"), "Unknown well type"),
    (dict(well_type="oil and gas"), "Unknown well type"),
    (dict(fracturing="maybe"), "Unknown fracturing value"),
    (dict(tier="tier1", control_type="vru"), "Unknown completion control"),
    (dict(tier="tier1", well_type="oil", location="offshore"), "Table 6-7"),
    (dict(tier="tier2", daily_production_rate=1, prod_rate_unit="bbl", vent_duration_days=1, ch4_content=80),
     "must be a gas rate"),
    (dict(tier="tier2", daily_production_rate=1, ch4_content=80), "vent duration"),
    (dict(tier="tier2", flowback_rate=1, rate_unit="mcf", flowback_duration_hours=1, ch4_content=80), "must be a rate"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="bbl", ch4_content=80), "Unknown flowback volume unit"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", injected_n2_volume=1, injected_n2_unit="kg",
          ch4_content=80), "Unknown injected N2 unit"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", initial_flowback_hours=2, ch4_content=80),
     "cannot be zero"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", disposition="pipeline", ch4_content=80),
     "Unknown disposition"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", frac_vented=0.5, ch4_content=80), "must sum to 100%"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", disposition="flared", ch4_content=80,
          c2plus_content="lots"), "Invalid c2plus_content"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", disposition="flared", ch4_content=80,
          c2plus_content=-1), "cannot be negative"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf", disposition="flared", ch4_content=80,
          c2plus_content=150), "cannot exceed 100%"),
    (dict(tier="tier3", flowback_volume=1, volume_unit="scf"), "CH4 content of the flowback gas"),
])
def test_refusals(c, kw, match):
    with pytest.raises(ValueError, match=match):
        c.calculate(**kw)


def test_dispatcher_passes_an_unentered_efficiency_as_none():
    from calculations.dispatcher import CalculationDispatcher

    res = CalculationDispatcher().dispatch("completions", {
        "comp_tier": "tier3", "flowback_volume": 1_000_000, "volume_unit": "scf", "ch4_content": 80,
        "disposition": "flared", "factor_source": "specific"}, {}, {})
    ch4 = t(1e6, 0.80, RHO_CH4)
    assert res["results"]["ch4"]["value"] == pytest.approx(ch4 * 0.02)
    assert res["results"]["co2"]["value"] == pytest.approx(ch4 * 0.965 * R)
