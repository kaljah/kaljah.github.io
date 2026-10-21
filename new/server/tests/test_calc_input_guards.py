"""Range checks added to the calculators on 2026-10-18 (fugitive, wells, midstream, CCUS, downstream refining):
the ones a direct call can reach (the rest were unreachable behind validate_inputs and were removed)."""
import pytest


def _call(path, cls, method="calculate"):
    import importlib

    return getattr(getattr(importlib.import_module(path), cls)(), method)


@pytest.mark.parametrize("fn,kw,match", [
    (lambda: _call("calculations.fugitive", "ComponentFugitiveCalculator"), dict(component_counts={"valve": 1},
     ch4_content="150%", uncertainties={}), "ch4_content cannot exceed 100%"),
    (lambda: _call("calculations.fugitive", "EquipmentFugitiveCalculator"), dict(equipment_count=1, ef=0.1,
     ch4_content="150%"), "ch4_content cannot exceed 100%"),
    (lambda: _call("calculations.vented_production_wells", "CasingGasVentCalculator"), dict(throughput=100,
     actual_vent_fraction=150), "actual_vent_fraction must be between 0 and 1"),
    (lambda: _call("calculations.vented_ccus_transport", "CCUSVentingCalculator"), dict(
     activity="stripper_vent", inlet_co2_tonnes=10, capture_efficiency=90, ch4_slip_tonnes=-1),
     "Vented emissions cannot be negative"),
    (lambda: _call("calculations.vented_ccus_transport", "CCUSVentingCalculator"), dict(
     activity="wellhead_blowdown", physical_volume_m3=1, co2_density_kg_m3=650, co2_weight_fraction="150%"),
     "co2_weight_fraction cannot exceed 100%"),
    (lambda: _call("calculations.vented_downstream", "RefiningCokerCalculator"), dict(
     coker_type="delayed", vessel_diameter_ft=0, vessel_height_ft=10), "vessel dimensions must be positive"),
    (lambda: _call("calculations.vented_downstream", "RefiningHydrogenPlantCalculator"), dict(
     method="feedstock_balance", feedstock_comp={"CH4": 1.0}, feedstock_volume_scf_yr=-1), "Feedstock volume"),
    (lambda: _call("calculations.vented_downstream", "RefiningHydrogenPlantCalculator"), dict(
     method="feedstock_balance", feedstock_comp={"CH4": 1.0}, feedstock_volume_m3_yr=-1), "Feedstock volume"),
    (lambda: _call("calculations.vented_downstream", "RefiningHydrogenPlantCalculator"), dict(
     method="h2_stoichiometry", co2_to_h2_molar_ratio=-1, h2_production_scf_yr=1), "molar ratio cannot be negative"),
    (lambda: _call("calculations.vented_downstream", "RefiningHydrogenPlantCalculator"), dict(
     method="h2_stoichiometry", co2_to_h2_molar_ratio=0.25, h2_production_m3_yr=-1), "H2 production volume cannot be negative"),
    (lambda: _call("calculations.vented_downstream", "SulfurRecoveryTailGasCalculator"), dict(sour_gas_m3_yr=-1),
     "Sour gas volume cannot be negative"),
    (lambda: _call("calculations.vented_downstream", "PetrochemicalManufacturingCalculator"), dict(
     process_type="mass_balance", feedstocks=[(10, 0.8)], primary_product_tonnes=-1), "Primary product tonnes"),
    (lambda: _call("calculations.vented_downstream", "PetrochemicalManufacturingCalculator"), dict(
     process_type="mass_balance", feedstocks=[(10, 0.8)], primary_product_tonnes=1,
     secondary_products=[(-1, 0.5)]), "Secondary product tonnes"),
])
def test_reachable_range_checks(fn, kw, match):
    with pytest.raises(ValueError, match=match):
        fn()(**kw)


@pytest.mark.parametrize("val,match", [("abc", "Invalid numeric value"), (-1, "cannot be negative"),
                                       ("150%", "cannot exceed 100%")])
def test_downstream_fraction_parser(val, match):
    from calculations.vented_downstream import _parse_fraction

    with pytest.raises(ValueError, match=match):
        _parse_fraction(val, name="share")
    assert _parse_fraction("", default=0.3) == 0.3 and _parse_fraction("45%") == pytest.approx(0.45)


def test_gas_composition_parsers():
    from calculations.vented_midstream import _parse_gas_comp as mid
    from calculations.vented_production_wells import _parse_content, _parse_gas_comp as wells

    with pytest.raises(ValueError, match="ch4_content cannot be negative"):
        mid(-5)
    with pytest.raises(ValueError, match="co2_content cannot be negative"):
        mid(80, -5)
    with pytest.raises(ValueError, match="co2_content cannot be negative"):
        wells(80, -1)
    assert _parse_content("5%") == pytest.approx(0.05) and _parse_content(None, 0.2) == 0.2


def test_sulfur_recovery_zero_and_missing_inputs():
    from calculations.vented_downstream import SulfurRecoveryTailGasCalculator

    s = SulfurRecoveryTailGasCalculator()
    for kw in ({}, {"sour_gas_m3_yr": 0}, {"refinery_throughput_bbl_yr": 0}):
        assert s.calculate(**kw)["total_co2e"] == 0
    m3 = s.calculate(sour_gas_m3_yr=1000)["results"]["co2"]
    assert (m3["value"] if isinstance(m3, dict) else m3) == pytest.approx(1000 * 44.0 / 23.685 * 0.20 / 1000, rel=1e-3)
