from calculations.vented import (
    TankFlashingCalculator,
    PneumaticDeviceCalculator,
    BlowdownCalculator,
)


def test_tanks_calculator():
    calc = TankFlashingCalculator()
    data = {
        "throughput": 10000,
        "gas_oil_ratio": 50,
        "control_efficiency": 0.95,
        "ch4_content": 0.80,
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    assert res["results"]["ch4"]["value"] > 0
    # Remediation check: Flared combustion produces CO2
    assert res["results"]["co2"] is not None
    assert res["results"]["co2"]["value"] > 0


def test_pneumatics_calculator():
    calc = PneumaticDeviceCalculator()
    data = {
        "count": 5,
        "hours": 8760,
        "bleed_rate": 10,
        "ch4_content": 0.80,
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    # 6727.68 kg -> 6.72 tonnes
    assert abs(res["results"]["ch4"]["value"] - 6.727) < 0.1


def test_pneumatics_intermittent_actuation():
    """Verify pneumatic intermittent actuation calculation"""
    calc = PneumaticDeviceCalculator()
    data = {
        "count": 2,
        "hours": 8760,
        "bleed_rate": 13.5,  # 13.5 scf/actuation
        "ch4_content": 0.90,
        "actuations": 500,
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    assert res["results"]["ch4"]["value"] > 0
    assert res["inputs"]["mode"] == "intermittent_actuation"


def test_liquids_unloading_units():
    """Verify liquids unloading accepts depth/diam/press units without error"""
    from calculations.vented import LiquidsUnloadingCalculator

    calc = LiquidsUnloadingCalculator()
    res = calc.calculate(
        well_depth=1000,
        diameter=4,
        pressure=150,
        ch4_content=0.85,
        events=5,
        uncertainties={},
        depth_unit="m",
        diameter_unit="in",
        press_unit="psig",
    )
    assert res is not None
    assert res["results"]["ch4"]["value"] > 0


def test_blowdown_calculator():
    calc = BlowdownCalculator()
    data = {
        "blowdown_volume": 1000 * 0.0283168,  # 1000 ft3 converted to m3
        "pressure": 100,
        "events": 1,
        "ch4_content": 0.85,
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    # API Eq 6-4: v_std = v_phys * (p_abs / p_std)
    # 28.32 m3 * (114.696 / 14.696) = ~220.97 m3 at std conditions
    # ch4 = 220.97 * 0.85 * 0.67722 kg/m3 / 1000 = ~0.127 tonnes
    assert abs(res["results"]["ch4"]["value"] - 0.127) < 0.01


def test_offshore_mud_degassing_table_6_2():
    """Verify BUG-103 remediation: Table 6-2 offshore mud factors."""
    from calculations.vented import MudDegassingCalculator
    calc = MudDegassingCalculator()

    # 10 drilling days with water-based mud offshore: 10 * 0.2605 = 2.605 tonnes CH4
    res = calc.calculate(drilling_days=10, mud_type="water_based", location="offshore")
    assert abs(res["results"]["ch4"]["value"] - 2.605) < 0.01
    assert res["inputs"]["location"] == "offshore"


def test_offshore_completion_table_6_7():
    """Verify BUG-103 remediation: Table 6-7 offshore completion factor (136.2 tonnes CH4)."""
    from calculations.vented import CompletionFlowbackCalculator
    calc = CompletionFlowbackCalculator()

    # 1 offshore gas completion: 136.2 tonnes CH4
    res = calc.calculate(events=1, well_type="gas", location="offshore")
    assert abs(res["results"]["ch4"]["value"] - 136.2) < 0.5
    assert res["inputs"]["location"] == "offshore"

