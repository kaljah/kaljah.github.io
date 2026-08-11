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
    # ch4 = 220.97 * 0.85 * 0.6785 kg/m3 / 1000 = ~0.127 tonnes
    assert abs(res["results"]["ch4"]["value"] - 0.127) < 0.01
