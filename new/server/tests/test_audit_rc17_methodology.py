"""RC-17 methodology regressions (BUG-100 .. BUG-103), checked against the API Compendium 2021 text
(scratch/2021-API-GHG-Compendium.pdf) through the dispatcher, i.e. the path the app uses.

Hand values (tables quoted from the Compendium):
- Table 6-14 high bleed (API study): 16.4 scf gas/h, 81.6 mol % CH4 -> 2.25 t CH4/controller-yr.
- Table 6-15 intermittent (Subpart W): 13.5 scf gas/h -> 1.85 t CH4/controller-yr.
- Table 6-22 crude, large tank, no control: 0.193 kg CH4/bbl.  Table 6-24 condensate, large, no
  control: 0.146 kg CH4/bbl.
- Table 6-2 offshore water-based mud: 0.2605 t CH4/drilling-day; onshore 0.0458.
- Table 6-7 offshore gas well completion: 136.2 t CH4/completion-day (no offshore oil row).
- Exhibit 6-25 blowdown: 83.8 ft3 at 100 psig, 80 F, z 0.9864, 90 % CH4 -> 0.011 t CH4
  (Eq 6-32 uses the initial ABSOLUTE pressure: n = 114.7 x 83.8 / (0.9864 x 10.73 x 539.7)).
"""
import pytest

from calculations.dispatcher import dispatcher


def _ch4(pt, inp):
    return dispatcher.dispatch(pt, inp, {})["results"]["ch4"]["value"]


# ---------------- BUG-100 pneumatic controllers ----------------
def test_bug100_table_6_14_high_bleed():
    assert _ch4("pneumatic", {"factor_source": "default", "pneu_controller_type": "high_bleed", "amount": 1,
                              "pneu_hours": 8760}) == pytest.approx(2.25, rel=5e-3)


def test_bug100_table_6_15_subpart_w_intermittent_is_per_hour():
    v = _ch4("pneumatic", {"factor_source": "default", "pneu_controller_type": "intermittent_average",
                           "pneu_factor_standard": "subpart_w", "amount": 1, "pneu_hours": 8760})
    assert v == pytest.approx(1.85, rel=5e-3)


def test_bug100_actuations_need_volume_per_actuation():
    # a zero / missing per-actuation volume is rejected (never a hidden 13.5 scf default)
    with pytest.raises(ValueError, match="per actuation|bleed rate"):
        dispatcher.dispatch("pneumatic", {"factor_source": "specific", "amount": 2, "pneu_bleed_rate": 0,
                                          "pneu_actuations": 100, "pneu_controller_type": ""}, {})


def test_bug100_eq_6_14_monitoring_survey():
    # 10 normal controllers all year at 0.28 scf/h + 1 malfunctioning for 25 % of the year at 24.1 scf/h
    gas_scf = 10 * 0.28 * 8760 + 1 * 24.1 * 8760 * 0.25
    expected = gas_scf * 0.028316846592 * 0.816 * (16.04 / 23.685) / 1000.0
    v = _ch4("pneumatic", {"factor_source": "specific", "amount": 11, "pneu_monitoring": "true",
                           "pneu_normal_count": 10, "pneu_malfunction_count": 1, "pneu_malfunction_fraction": 0.25})
    assert v == pytest.approx(expected, rel=1e-6)


# ---------------- BUG-102 tank flashing ----------------
def test_bug102_no_gor_uses_table_6_22_not_zero():
    assert _ch4("tank_flashing", {"factor_source": "default", "amount": 1000, "unit": "bbl"}) == pytest.approx(0.193)


def test_bug102_condensate_table_6_24():
    assert _ch4("tank_flashing", {"factor_source": "default", "amount": 1000, "unit": "bbl",
                                  "tank_liquid_type": "condensate"}) == pytest.approx(0.146)


def test_bug102_site_gor_still_used():
    # 1,000 bbl x 50 scf/bbl x 60 % CH4, engine density convention
    expected = 1000 * 50 * 0.028316846592 * 0.60 * (16.04 / 23.685) / 1000.0
    assert _ch4("tank_flashing", {"factor_source": "specific", "amount": 1000, "unit": "bbl", "tank_gor": 50,
                                  "tank_ch4_content": 60}) == pytest.approx(expected, rel=1e-6)


# ---------------- BUG-103 offshore exploration ----------------
def test_bug103_offshore_mud_degassing_table_6_2():
    base = {"factor_source": "default", "amount": 1, "unit": "days", "mud_type": "water_based", "tier": "tier1"}
    assert _ch4("drilling", dict(base, well_location="offshore")) == pytest.approx(0.2605)
    assert _ch4("drilling", dict(base)) == pytest.approx(0.0458)


def test_bug103_offshore_gas_completion_table_6_7():
    base = {"factor_source": "default", "amount": 1, "unit": "completion-days", "tier": "tier1",
            "well_location": "offshore"}
    assert _ch4("completions", dict(base, well_type="gas")) == pytest.approx(136.2)
    with pytest.raises(ValueError, match="gas wells only"):
        dispatcher.dispatch("completions", dict(base, well_type="oil"), {})


# ---------------- BUG-101 blowdown ----------------
BD = {"factor_source": "specific", "blowdown_volume": 83.8, "blowdown_unit": "scf", "blowdown_pressure": 100,
      "blowdown_events": 1, "ch4_content": 90, "blowdown_temp": 80, "z_factor": 0.9864}


def test_bug101_exhibit_6_25_absolute_pressure():
    lbmol = 114.7 * 83.8 / (0.9864 * 10.73 * 539.7)
    exhibit = lbmol * 0.9 * 16.0 / 2204.62  # 0.0110 t CH4
    assert _ch4("blowdown", dict(BD)) == pytest.approx(exhibit, rel=0.02)


def test_bug101_residual_pressure_counts_only_released_gas():
    full = _ch4("blowdown", dict(BD))
    to_atm = _ch4("blowdown", dict(BD, blowdown_final_pressure=0))
    half = _ch4("blowdown", dict(BD, blowdown_final_pressure=50))
    p_abs = 100 + 14.696  # engine standard atmosphere
    assert to_atm == pytest.approx(full * 100 / p_abs, rel=1e-6)
    assert half == pytest.approx(full * 50 / p_abs, rel=1e-6)


# ---------------- dedupe ----------------
def test_single_implementation_per_source():
    import calculations.vented as v
    import calculations.vented_production as vp

    assert v.PneumaticDeviceCalculator is vp.PneumaticDeviceCalculator
    assert v.TankFlashingCalculator is vp.TankFlashingCalculator
    assert v.BlowdownCalculator is vp.BlowdownCalculator


# ---------------- BUG-104 section 6.11.3 hydrogen plant (was unwired) ----------------
def test_bug104_hydrogen_table_6_51():
    # 50 t H2 = 50 x 2204.62 / 2.016 lbmol x 379.3 scf/lbmol = 20.74e6 scf; x 13.41 t CO2 / 1e6 scf
    gross = 50 * 2204.62 / 2.016 * 379.3 * 13.41e-6
    r = dispatcher.dispatch("hydrogen_production", {"factor_source": "default", "amount": 50, "unit": "tonnes",
                                                    "h2_produced_tonnes": 50}, {})
    assert r["results"]["co2"]["value"] == pytest.approx(gross, rel=1e-6)
    r = dispatcher.dispatch("hydrogen_production", {"factor_source": "default", "h2_produced_tonnes": 50,
                                                    "ccs_capture_rate": 0.85}, {})
    assert r["total_co2e"] == pytest.approx(gross * 0.15, rel=1e-6)


def test_bug104_hydrogen_exhibit_6_44():
    # Exhibit 6-44: 13,000 x 10^6 scf H2 x 13.41 t / 10^6 scf = 174,330 t CO2 (Compendium prints 174,300)
    r = dispatcher.dispatch("hydrogen_production", {"factor_source": "default", "h2_produced_scf": 13_000e6}, {})
    assert r["results"]["co2"]["value"] == pytest.approx(174_330, rel=1e-6)


def test_bug104_hydrogen_without_activity_is_rejected():
    with pytest.raises(ValueError, match="hydrogen produced"):
        dispatcher.dispatch("hydrogen_production", {"factor_source": "default"}, {})
