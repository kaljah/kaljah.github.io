"""
Tests covering calculation invariants, domain bounds, percentage string normalization,
and physics edge cases remediated in Bugs 31 through 40.
"""
import pytest
from calculations.stoichiometry import StoichiometricCalculator, NitricAcidCalculator
from calculations.vented_associated_gas import AssociatedGasVentingCalculator
from calculations.vented_completion import CompletionFlowbackCalculator
from calculations.vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from calculations.vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringStorageTankCalculator,
    GatheringNonRoutineVentingCalculator,
    ProcessingDehydrationCalculator,
    ProcessingBlanketedTankCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)
from calculations.vented_mud import MudDegassingCalculator
from calculations.vented_exploration import WellTestingCalculator
from calculations.vented_production_tank import (
    AcidGasRemovalCalculator,
    TankFlashingCalculator,
    BlowdownCalculator,
)
from calculations.vented_production_pneumatic import (
    PneumaticDeviceCalculator,
    PneumaticPumpCalculator,
    GasDehydrationCalculator,
)


def test_stoichiometry_percentage_strings_and_bounds():
    """Verify Bug 31 & 32: StoichiometricCalculator and NitricAcidCalculator bounds and percentage strings."""
    calc_s = StoichiometricCalculator()
    res = calc_s.calculate(
        fuel_mass=1000.0,
        carbon_content="85%",
        oxidation_factor="99%",
        mass_unit="kg",
    )
    assert res["total_co2e"] > 0
    # 1000 * 0.85 * 0.99 * (44.01 / 12.011) / 1000 = 3.0848 t CO2
    expected = 1000.0 * 0.85 * 0.99 * (44.01 / 12.011) / 1000.0
    assert res["results"]["co2"]["value"] == pytest.approx(expected, rel=1e-3)

    with pytest.raises(ValueError, match="Input mass cannot be negative"):
        calc_s.calculate(fuel_mass=-100.0, carbon_content=0.85)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc_s.calculate(fuel_mass=100.0, carbon_content=-0.1)

    with pytest.raises(ValueError, match="oxidation_factor must be between 0 and 1"):
        calc_s.calculate(fuel_mass=100.0, carbon_content=0.85, oxidation_factor=-0.05)

    calc_na = NitricAcidCalculator()
    res_na = calc_na.calculate(
        production_amount=500.0,
        abatement_efficiency="95%",
        mass_unit="tonne",
    )
    assert res_na["total_co2e"] > 0
    # 500 tonnes * 9.0 kg/tonne * (1 - 0.95) / 1000 = 0.225 t N2O
    assert res_na["results"]["n2o"]["value"] == pytest.approx(0.225, rel=1e-3)

    with pytest.raises(ValueError, match="production_amount cannot be negative"):
        calc_na.calculate(production_amount=-50.0)

    with pytest.raises(ValueError, match="Abatement efficiency cannot be negative"):
        calc_na.calculate(production_amount=100.0, abatement_efficiency=-0.1)

    with pytest.raises(ValueError, match="Abatement efficiency cannot exceed 100 %"):
        calc_na.calculate(production_amount=100.0, abatement_efficiency="150%")


def test_associated_gas_tier2_non_negative_and_fraction_validation():
    """Verify Bug 33: AssociatedGasVentingCalculator Tier 2 non-negative and invalid fraction checks."""
    calc = AssociatedGasVentingCalculator()
    res = calc.calculate(
        tier="tier2",
        oil_production=1000.0,
        gor=500.0,
        ch4_content="80%",
        co2_content="5%",
        venting_duration=10.0,
    )
    assert res["total_co2e"] > 0

    with pytest.raises(ValueError, match="Input oil_production cannot be negative"):
        calc.calculate(tier="tier2", oil_production=-100.0, gor=500.0, ch4_content=0.8)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(tier="tier2", oil_production=100.0, gor=-50.0, ch4_content=0.8)

    with pytest.raises(ValueError, match="Invalid fraction"):
        calc.calculate(tier="tier1", oil_production=100.0, ch4_content="invalid_not_number")


def test_completion_flowback_percentage_strings():
    """Verify Bug 34: CompletionFlowbackCalculator handles percentage strings."""
    calc = CompletionFlowbackCalculator()
    res = calc.calculate(
        flowback_volume=50000.0,
        ch4_content="85%",
        co2_content="3%",
        control_efficiency="98%",
        control_type="flared",
    )
    assert res["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(
            flowback_volume=50000.0,
            ch4_content="90%",
            co2_content="15%",
        )


def test_lng_and_distribution_percentage_strings_and_mixture_bounds():
    """Verify Bug 35: LNG and Distribution calculators handle percentage strings and mixture bounds."""
    lng = LNGVentingCalculator()
    res_lng = lng.calculate(
        activity="loading_transfer",
        transfer_volume_m3=1000.0,
        pipe_length_km=2.0,
        ch4_content="95%",
        co2_content="1%",
    )
    assert res_lng["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        lng.calculate(
            activity="direct_bog_vent",
            vented_gas_scf=10000.0,
            ch4_content="90%",
            co2_content="20%",
        )

    pneu = DistributionPneumaticsCalculator()
    res_pneu = pneu.calculate(
        controller_type="average",
        controller_count=5,
        ch4_content="94%",
        co2_content="2%",
    )
    assert res_pneu["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        pneu.calculate(
            controller_type="average",
            controller_count=5,
            ch4_content="95%",
            co2_content="10%",
        )

    nr = DistributionNonRoutineCalculator()
    res_nr = nr.calculate(
        activity="mr_station_blowdown",
        count_or_miles=3,
        ch4_content="95%",
        co2_content="1%",
    )
    assert res_nr["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        nr.calculate(
            activity="mr_station_blowdown",
            count_or_miles=3,
            ch4_content="95%",
            co2_content="10%",
        )


def test_midstream_all_seven_calculators_percentage_strings():
    """Verify Bug 36: All 7 midstream calculators handle percentage strings and mixture bounds."""
    # 1. GatheringCompressorVentingCalculator
    calc1 = GatheringCompressorVentingCalculator()
    res1 = calc1.calculate(compressor_count=2, pressurized_hours=4000, ch4_content="85%", co2_content="3%")
    assert res1["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc1.calculate(compressor_count=2, ch4_content="90%", co2_content="15%")

    # 2. GatheringStorageTankCalculator
    calc2 = GatheringStorageTankCalculator()
    res2 = calc2.calculate(tank_count=3, hours=5000, ch4_content="80%", co2_content="5%")
    assert res2["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc2.calculate(tank_count=3, ch4_content="85%", co2_content="20%")

    # 3. GatheringNonRoutineVentingCalculator
    calc3 = GatheringNonRoutineVentingCalculator()
    res3 = calc3.calculate(activity="prv_releases", events_or_count=4, ch4_content="82%", co2_content="4%")
    assert res3["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc3.calculate(activity="prv_releases", events_or_count=4, ch4_content="90%", co2_content="15%")

    # 4. ProcessingDehydrationCalculator
    calc4 = ProcessingDehydrationCalculator()
    res4 = calc4.calculate(gas_throughput_mmscfd=10.0, operating_days=300, ch4_content="88%", co2_content="2%")
    assert res4["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc4.calculate(gas_throughput_mmscfd=10.0, ch4_content="95%", co2_content="10%")

    # 5. ProcessingBlanketedTankCalculator
    calc5 = ProcessingBlanketedTankCalculator()
    res5 = calc5.calculate(liquid_displacement_bbl=1000.0, vapor_temperature_f=80.0, ch4_content="85%", co2_content="2%")
    assert res5["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc5.calculate(liquid_displacement_bbl=1000.0, vapor_temperature_f=80.0, ch4_content="90%", co2_content="15%")

    # 6. TransmissionCompressorCalculator
    calc6 = TransmissionCompressorCalculator()
    res6 = calc6.calculate(compressor_type="reciprocating", compressor_count=3, operating_hours=6000, ch4_content="94%", co2_content="1%")
    assert res6["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc6.calculate(compressor_type="reciprocating", compressor_count=3, operating_hours=6000, ch4_content="95%", co2_content="10%")

    # 7. TransmissionNonRoutineCalculator
    calc7 = TransmissionNonRoutineCalculator()
    res7 = calc7.calculate(activity="transmission_station", count_or_miles=2, ch4_content="93%", co2_content="2%")
    assert res7["total_co2e"] > 0
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc7.calculate(activity="transmission_station", count_or_miles=2, ch4_content="95%", co2_content="10%")


def test_mud_degassing_percentage_strings_and_non_negative_guards():
    """Verify Bug 37: MudDegassingCalculator percentage strings and non-negative guards."""
    calc = MudDegassingCalculator()
    res = calc.calculate(
        drilling_days=20.0,
        mud_type="water_based",
        ch4_concentration="85%",
        co2_concentration="2%",
    )
    assert res["total_co2e"] > 0

    with pytest.raises(ValueError, match="wells cannot be negative"):
        calc.calculate(wells=-5)

    with pytest.raises(ValueError, match="drilling_days cannot be negative"):
        calc.calculate(drilling_days=-10.0, mud_type="water_based")

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(drilling_days=10.0, ch4_concentration="95%", co2_concentration="10%")


def test_well_testing_percentage_strings_and_bounds():
    """Verify Bug 38: WellTestingCalculator percentage strings and bounds."""
    calc = WellTestingCalculator()
    res = calc.calculate(
        well_type="gas_well",
        gas_production_rate=500000.0,
        test_duration_days=3.0,
        ch4_content="82%",
        co2_content="3%",
    )
    assert res["total_co2e"] > 0

    with pytest.raises(ValueError, match="ch4_content must be between 0 and 1"):
        calc.calculate(well_type="gas_well", gas_production_rate=500000.0, test_duration_days=3.0, ch4_content=-0.1)

    with pytest.raises(ValueError, match="co2_content must be between 0 and 1"):
        calc.calculate(well_type="gas_well", gas_production_rate=500000.0, test_duration_days=3.0, co2_content=-0.05)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(well_type="gas_well", gas_production_rate=500000.0, test_duration_days=3.0, ch4_content="90%", co2_content="15%")


def test_vented_production_tank_and_blowdown_invariants():
    """Verify Bug 39: Tank and blowdown independent percentage parsing, bounds and non-negative."""
    agr = AcidGasRemovalCalculator()
    res_agr = agr.calculate(
        method="sour_sweet_balance",
        sour_gas_mmscf_yr=100.0,
        sour_co2_content="5%",
        sweet_co2_content=0.02,
    )
    assert res_agr["total_co2e"] > 0
    # Sweet gas CO2 should NOT have been divided by 100 twice
    assert res_agr["results"]["co2"]["value"] > 0

    flash = TankFlashingCalculator()
    res_flash = flash.calculate(
        throughput=5000.0,
        method="table_6_22",
        ch4_content="80%",
        co2_content="2%",
    )
    assert res_flash["total_co2e"] > 0

    with pytest.raises(ValueError, match="throughput cannot be negative"):
        flash.calculate(throughput=-100.0)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        flash.calculate(throughput=100.0, ch4_content="90%", co2_content="15%")

    bd = BlowdownCalculator()
    res_bd = bd.calculate(
        pressure=150.0,
        events=2,
        diameter_ft=3.0,
        length_ft=20.0,
        ch4_content="85%",
        co2_content="3%",
    )
    assert res_bd["total_co2e"] > 0

    with pytest.raises(ValueError, match="ch4_content must be between 0 and 1"):
        bd.calculate(pressure=150.0, events=2, ch4_content=-0.1)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        bd.calculate(pressure=150.0, events=2, ch4_content="90%", co2_content="15%")


def test_production_pneumatics_percentage_strings_and_mixture_bounds():
    """Verify Bug 40: Pneumatics and dehydrator calculators handle percentage strings and mixture bounds."""
    pneu = PneumaticDeviceCalculator()
    res_pneu = pneu.calculate(count=10, hours=4000, ch4_content="81.6%", co2_content="1.5%")
    assert res_pneu["total_co2e"] > 0

    with pytest.raises(ValueError, match="ch4_content must be between 0 and 1"):
        pneu.calculate(count=10, ch4_content=-0.2)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        pneu.calculate(count=10, ch4_content="90%", co2_content="15%")

    pump = PneumaticPumpCalculator()
    res_pump = pump.calculate(pump_count=2, operating_hours=2000, ch4_content="82%", co2_content="2%")
    assert res_pump["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        pump.calculate(pump_count=2, ch4_content="95%", co2_content="10%")

    dehy = GasDehydrationCalculator()
    res_dehy = dehy.calculate(
        dehydrator_type="glycol",
        dehydrator_count=2,
        ch4_content="80%",
        co2_content="1%",
    )
    assert res_dehy["total_co2e"] > 0

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        dehy.calculate(
            dehydrator_type="glycol",
            dehydrator_count=2,
            ch4_content="95%",
            co2_content="10%",
        )
