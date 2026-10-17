"""calculations/vented_midstream.py beyond tests/test_vented_midstream_compendium.py: every table row, unit,
disposition and refusal, with values from API Compendium 2021 Tables 6-30, 6-31, 6-33, 6-35, 6-36, 6-39, 6-40,
6-41 and 6-43. Fixed while testing: a flare efficiency below 95 % was raised to 95 %; 0 tanks / stations / days
counted as 1 / 1 / 365; unknown rows took the first row; transmission compressors assumed 90 % CH4 (the table
basis is 93.4 %) and, without seal counts, wet seals; Exhibit 6-29 / 6-31 site values were defaults; the
Table 6-43 engine-starts row was missing.
"""
import pytest

from calculations.vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringNonRoutineVentingCalculator,
    GatheringStorageTankCalculator,
    ProcessingBlanketedTankCalculator,
    ProcessingDehydrationCalculator,
    ProcessingNonRoutineCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)

LB_T = 2204.6226218487757


def t_gas(scf, frac, mw=16.04):
    return scf * frac * mw / 379.3 / LB_T


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


# ---------------------------------------------------------------- gathering
@pytest.mark.parametrize("std,ef,basis", [("us_zimmerle", 4.43e-4, 0.816), ("us_ghgrp", 2.07e-5, 0.788),
                                          ("canada_alberta", 1.39e-4, 0.816)])
def test_table_6_30_rows(std, ef, basis):
    res = GatheringCompressorVentingCalculator().calculate(compressor_count=2, pressurized_hours=1000, source_standard=std)
    assert val(res, "ch4") == pytest.approx(2 * ef * 1000)                              # at the table basis
    site = GatheringCompressorVentingCalculator().calculate(compressor_count=2, pressurized_hours=1000,
                                                            source_standard=std, ch4_content=85, co2_content=4)
    assert val(site, "ch4") == pytest.approx(2 * ef * 1000 * 0.85 / basis)
    scf = 2 * 1000 * GatheringCompressorVentingCalculator.TABLE_6_30[std]["scf_gas_hr"]
    assert val(site, "co2") == pytest.approx(t_gas(scf, 0.04, 44.01))


@pytest.mark.parametrize("ctype,scf_hr,basis", [("average_tank", 39.3, 0.855), ("single_unit_vent", 9.21, 0.925),
                                                ("thief_hatch", 9.85, 0.890)])
def test_table_6_31_rows(ctype, scf_hr, basis):
    res = GatheringStorageTankCalculator().calculate(tank_count=2, hours=100, component_type=ctype)
    assert val(res, "ch4") == pytest.approx(t_gas(2 * scf_hr * 100, basis))
    pct = GatheringStorageTankCalculator().calculate(tank_count=2, hours=100, component_type=ctype, ch4_content=80,
                                                     co2_content=3)
    assert val(pct, "co2") == pytest.approx(t_gas(2 * scf_hr * 100, 0.03, 44.01))
    assert val(GatheringStorageTankCalculator().calculate(tank_count=0, component_type=ctype), "ch4") == 0


@pytest.mark.parametrize("act,scf", [("prv_releases", 43.0), ("pipeline_dig_in", 849.0), ("compressor_starts", 10714.0),
                                     ("oil_pump_station", 46.9)])
def test_table_6_33_rows(act, scf):
    res = GatheringNonRoutineVentingCalculator().calculate(activity=act, events_or_count=3, ch4_content=79, co2_content=2)
    assert val(res, "ch4") == pytest.approx(t_gas(3 * scf, 0.79))
    assert val(res, "co2") == pytest.approx(t_gas(3 * scf, 0.02, 44.01))


# ---------------------------------------------------------------- processing
def test_dehydration_per_year_without_pump_and_zero_days():
    d = ProcessingDehydrationCalculator()
    res = d.calculate(gas_throughput_mmscf_yr=1000)
    assert val(res, "ch4") == pytest.approx(1000 * 0.0023315)                           # Table 6-35 at 86.8 %
    pct = d.calculate(gas_throughput_mmscf_yr=1000, has_gas_assisted_pump=True, ch4_content=90, co2_content=5)
    assert val(pct, "ch4") == pytest.approx(1000 * (0.0023315 + 0.0034096) * 0.90 / 0.868)
    assert val(d.calculate(gas_throughput_mmscfd=25, operating_days=0), "ch4") == 0     # 0 days (was 365)
    with pytest.raises(ValueError, match="gas_throughput_mmscfd or gas_throughput_mmscf_yr"):
        d.calculate()


def test_blanketed_tank_in_m3_and_required_inputs():
    b = ProcessingBlanketedTankCalculator()
    bbl = b.calculate(liquid_displacement_bbl=32_000, vapor_temperature_f=75, ch4_content=0.82, co2_content=0.01)
    m3 = b.calculate(liquid_displacement_m3=32_000 * 0.158987, vapor_temperature_f=75, ch4_content=82, co2_content=1)
    assert val(m3, "ch4") == pytest.approx(val(bbl, "ch4"), rel=1e-4)
    cold = b.calculate(liquid_displacement_bbl=1000, vapor_temperature_f=0, ch4_content=0.82)
    acf = 1000 * 42 / 7.48052
    assert val(cold, "ch4") == pytest.approx(t_gas(acf * 519.67 / 459.67, 0.82))         # 0 F is 0 F, not 75 F
    for kwargs, match in ((dict(liquid_displacement_bbl=1, ch4_content=0.8), "vapor_temperature_f"),
                          (dict(liquid_displacement_bbl=1, vapor_temperature_f=70), "ch4_content"),
                          (dict(vapor_temperature_f=70, ch4_content=0.8), "liquid_displacement")):
        with pytest.raises(ValueError, match=match):
            b.calculate(**kwargs)


def test_processing_blowdowns_in_mmscfd():
    p = ProcessingNonRoutineCalculator()
    res = p.calculate(gas_throughput_mmscfd=100, operating_days=365)
    assert val(res, "ch4") == pytest.approx(100e6 * 365 / 35.3147 / 1e6 * 0.1244, rel=1e-4)   # Table 6-39
    with pytest.raises(ValueError, match="gas_throughput_m3_day or gas_throughput_mmscfd"):
        p.calculate()


# ---------------------------------------------------------------- transmission and storage
def test_rod_packing_table_6_40_default_basis():
    res = TransmissionCompressorCalculator().calculate(compressor_count=2, operating_hours=8000, standby_pressurized_hours=500)
    assert val(res, "ch4") == pytest.approx(t_gas(2 * (263 * 8000 + 385 * 500), 0.934))   # 93.4 % (it was 90 %)
    assert val(TransmissionCompressorCalculator().calculate(compressor_count=0, operating_hours=8000), "ch4") == 0
    with pytest.raises(ValueError, match="operating_hours"):
        TransmissionCompressorCalculator().calculate(compressor_count=2)


def test_centrifugal_seals_table_6_41():
    c = TransmissionCompressorCalculator()
    res = c.calculate(compressor_type="centrifugal", wet_seal_count=1, dry_seal_count=1)
    # whole gas 1,028 / 321 scf per compressor-hour at the 93.4 % basis (Table 6-41: 1.84E-02 / 5.75E-03 t CH4/hr)
    assert val(res, "ch4") == pytest.approx((1.84e-2 + 5.75e-3) * 8760, rel=0.02)
    dry_only = c.calculate(compressor_type="centrifugal", dry_seal_count=2, ch4_content=95)
    assert val(dry_only, "ch4") == pytest.approx(2 * 51.1, rel=1e-3)                     # Exhibit 6-32 dry seals
    with pytest.raises(ValueError, match="wet seals and / or with dry seals"):
        c.calculate(compressor_type="centrifugal", compressor_count=3)
    with pytest.raises(ValueError, match="Unknown compressor type"):
        c.calculate(compressor_type="screw", operating_hours=1)


@pytest.mark.parametrize("act,ef", [("storage_station", 43.0), ("compressor_blowdowns", 47.14), ("engine_starts", 29.06),
                                    ("prv_lifts", 3.68), ("esd_activation", 7.97), ("mr_station", 13.75)])
def test_table_6_43_rows(act, ef):
    res = TransmissionNonRoutineCalculator().calculate(activity=act, count_or_miles=2)
    assert val(res, "ch4") == pytest.approx(2 * ef)
    site = TransmissionNonRoutineCalculator().calculate(activity=act, count_or_miles=2, ch4_content=90, co2_content=0.01)
    assert val(site, "ch4") == pytest.approx(2 * ef * 0.90 / 0.934)
    assert val(site, "co2") == pytest.approx(t_gas(2 * TransmissionNonRoutineCalculator.TABLE_6_43[act]["scf_gas"], 0.01,
                                                   44.01))


def test_zero_stations_is_zero():
    assert val(TransmissionNonRoutineCalculator().calculate(count_or_miles=0), "ch4") == 0


# ---------------------------------------------------------------- shared routing and refusals
@pytest.mark.parametrize("make", [
    lambda **k: GatheringCompressorVentingCalculator().calculate(compressor_count=1, pressurized_hours=1000, **k),
    lambda **k: GatheringStorageTankCalculator().calculate(tank_count=1, hours=1000, **k),
    lambda **k: GatheringNonRoutineVentingCalculator().calculate(events_or_count=10, **k),
    lambda **k: ProcessingDehydrationCalculator().calculate(gas_throughput_mmscf_yr=100, **k),
    lambda **k: ProcessingBlanketedTankCalculator().calculate(liquid_displacement_bbl=100, vapor_temperature_f=60,
                                                              ch4_content=0.8, **k),
    lambda **k: ProcessingNonRoutineCalculator().calculate(gas_throughput_m3_day=1e6, **k),
    lambda **k: TransmissionCompressorCalculator().calculate(compressor_count=1, operating_hours=100, **k),
    lambda **k: TransmissionNonRoutineCalculator().calculate(count_or_miles=1, **k),
])
def test_dispositions(make):
    vented = val(make(), "ch4")
    assert vented > 0
    assert val(make(disposition="recovered"), "ch4") == 0
    assert val(make(disposition="flared", control_efficiency=0.90), "ch4") == pytest.approx(vented * 0.10)
    assert val(make(disposition="flared"), "ch4") == pytest.approx(vented * 0.02)
    with pytest.raises(ValueError, match="Unknown disposition"):
        make(disposition="sold")


@pytest.mark.parametrize("call,match", [
    (lambda: GatheringCompressorVentingCalculator().calculate(source_standard="eu"), "Table 6-30 source"),
    (lambda: GatheringStorageTankCalculator().calculate(component_type="vent_stack"), "Table 6-31 component"),
    (lambda: GatheringNonRoutineVentingCalculator().calculate(activity="pigging"), "Table 6-33 activity"),
    (lambda: TransmissionNonRoutineCalculator().calculate(activity="pigging"), "Table 6-43 activity"),
    (lambda: GatheringStorageTankCalculator().calculate(tank_count=-1), "cannot be negative"),
])
def test_refusals(call, match):
    with pytest.raises(ValueError, match=match):
        call()


@pytest.mark.parametrize("make", [
    lambda **k: ProcessingBlanketedTankCalculator().calculate(liquid_displacement_bbl=100, vapor_temperature_f=60,
                                                              ch4_content=0.8, **k),
    lambda **k: TransmissionCompressorCalculator().calculate(compressor_count=1, operating_hours=100, **k),
    lambda **k: TransmissionNonRoutineCalculator().calculate(count_or_miles=1, **k),
])
def test_co2_above_one_is_percent(make):
    assert val(make(co2_content=2), "co2") == pytest.approx(val(make(co2_content=0.02), "co2"))


def test_gas_pump_without_co2():
    res = ProcessingDehydrationCalculator().calculate(gas_throughput_mmscf_yr=100, has_gas_assisted_pump=True)
    assert val(res, "co2") == 0 and val(res, "ch4") == pytest.approx(100 * (0.0023315 + 0.0034096))
