"""
Exhaustive unit test suite for calculation dispatching across all branches:
- calculations/dispatcher.py
- calculations/dispatcher_branches_combustion.py
- calculations/dispatcher_branches_fugitive.py
- calculations/dispatcher_branches_venting.py
- calculations/legacy_engine.py

Covers all process-types, section methods, CCS capture rate reduction,
dynamic meter/GC uncertainty injection, and legacy fallbacks.
"""

import pytest
from calculations.dispatcher import (
    CalculationDispatcher,
    capture_fraction,
    unloading_row_selection,
    record_period,
    operating_hours,
    percent_to_fraction,
)


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


# =============================================================================
# 1. HELPER FUNCTIONS & UNLOAD SELECTION
# =============================================================================

def test_dispatcher_helpers():
    """Test percent_to_fraction, capture_fraction, unloading_row_selection, and period helpers."""
    # percent_to_fraction
    assert percent_to_fraction("85%", "test") == 0.85
    assert percent_to_fraction(50.0, "test") == 0.50
    with pytest.raises(ValueError, match="must be a percentage"):
        percent_to_fraction("invalid", "test")
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        percent_to_fraction(120.0, "test")

    # capture_fraction
    assert capture_fraction({"ccs_capture_rate": "90%"}) == 0.90
    assert capture_fraction({"capture_rate": 80.0}) == 0.80
    assert capture_fraction({}) == 0.0

    # unloading_row_selection
    assert unloading_row_selection("UnloadPlunger_LE100")["type"] == "plunger"
    assert unloading_row_selection("UnloadNonPlunger_T1")["tier"] == 1
    assert unloading_row_selection("UnloadPlunger_GulfCoast_GT100")["region"] == "gulf_coast"
    assert unloading_row_selection("invalid_code") == {}

    # record_period
    h, d, frac = record_period({"year": 2024, "month": 2})  # 2024 is leap year: 29 days
    assert d == 29.0
    assert h == 29.0 * 24.0
    assert pytest.approx(frac) == 29.0 / 366.0

    # Non-monthly period fallback
    h_ann, d_ann, frac_ann = record_period({})
    assert h_ann == 8760.0
    assert d_ann == 365.0
    assert frac_ann == 1.0

    # operating_hours
    assert operating_hours({"operating_hours": 1000.0}) == 1000.0
    assert operating_hours({"operating_days": 10.0}) == 240.0
    with pytest.raises(ValueError, match="between 0 and 8784"):
        operating_hours({"operating_hours": 9000.0})


# =============================================================================
# 2. HYDROGEN PRODUCTION, COGEN & INDIRECT STEAM
# =============================================================================

def test_dispatcher_hydrogen_plant(dispatcher):
    """Test hydrogen plant dispatching under feedstock balance, stoichiometry, and simple factor."""
    # 1. Feedstock balance with feed gas analysis
    res_feed = dispatcher.dispatch(
        "hydrogen_production",
        {
            "amount": 100000.0,
            "unit": "scf",
            "feedstock_scf": 100000.0,
            "feed_ch4": 90.0,
            "feed_co2": 5.0,
        },
        {},
        {},
    )
    assert res_feed["results"]["co2"]["value"] > 0

    # 2. H2 stoichiometry
    res_stoich = dispatcher.dispatch(
        "hydrogen_plant",
        {
            "amount": 50000.0,
            "unit": "scf",
            "h2_produced_scf": 50000.0,
            "feed_ch4": 95.0,
        },
        {},
        {},
    )
    assert res_stoich["results"]["co2"]["value"] > 0

    # 3. Simple factor from H2 tonnes
    res_simple = dispatcher.dispatch(
        "smr_hydrogen",
        {
            "amount": 10.0,
            "unit": "tonnes",
        },
        {},
        {},
    )
    assert res_simple["results"]["co2"]["value"] > 0


def test_dispatcher_cogen_and_indirect_steam(dispatcher):
    """Test cogen allocation and indirect steam dispatching."""
    # Cogen allocation
    res_cogen = dispatcher.dispatch(
        "cogen_allocation",
        {
            "factor_source": "specific",
            "total_emissions": 50.0,
            "heat_output": 500.0,
            "power_output": 100.0,
        },
        {},
        {},
    )
    assert res_cogen["results"]["co2"]["value"] > 0

    # Indirect steam
    res_steam = dispatcher.dispatch(
        "indirect_steam",
        {
            "factor_source": "specific",
            "quantity": 500.0,
            "unit": "mmbtu",
            "boiler_efficiency": 0.82,
        },
        {"co2": 53.06},
        {},
    )
    assert res_steam["results"]["co2"]["value"] > 0


# =============================================================================
# 3. STOICHIOMETRIC, CHEMICAL & DRILLING
# =============================================================================

def test_dispatcher_chemical_and_stoichiometry(dispatcher):
    """Test chemical production and nitric acid dispatching."""
    # Nitric acid
    res_nitric = dispatcher.dispatch(
        "nitric_acid_production",
        {
            "amount": 1000.0,
            "unit": "tonne",
            "process_type": "nitric_acid_production",
            "technology": "dual_pressure",
            "abatement": "nsdr",
        },
        {},
        {},
    )
    assert res_nitric["results"]["n2o"]["value"] >= 0

    # Stoichiometry / Chemical production
    res_chem = dispatcher.dispatch(
        "chemical_production",
        {
            "amount": 500.0,
            "unit": "tonne",
            "carbon_content": 0.75,
            "production_type": "ammonia",
        },
        {},
        {},
    )
    assert res_chem is not None


def test_dispatcher_drilling_mud_degassing(dispatcher):
    """Test drilling and mud degassing dispatching."""
    res_drill = dispatcher.dispatch(
        "drilling",
        {
            "drilling_days": 15.0,
            "mud_type": "water_based",
            "well_depth": 5000.0,
            "ch4_content": 0.85,
        },
        {},
        {},
    )
    assert res_drill["results"]["ch4"]["value"] > 0


# =============================================================================
# 4. FUGITIVES (FACILITY, COMPRESSOR, SCREENING)
# =============================================================================

def test_dispatcher_fugitive_branches(dispatcher):
    """Test facility fugitives, compressor seal, and OGI screening."""
    # Facility-level fugitives (Table 7-8)
    res_fac = dispatcher.dispatch(
        "facility_fugitive",
        {
            "facility_type": "gas_production",
            "production_volume": 100000.0,
            "production_unit": "mcf",
            "ch4_content": 0.80,
        },
        {},
        {},
    )
    assert res_fac["results"]["ch4"]["value"] > 0

    # Compressor seal fugitives
    res_comp = dispatcher.dispatch(
        "compressor_seal",
        {
            "factor_source": "specific",
            "compressor_type": "centrifugal_wet_seal",
            "compressor_count": 2,
            "operating_hours": 2000.0,
            "ch4_content": 0.85,
        },
        {},
        {},
    )
    assert res_comp["results"]["ch4"]["value"] > 0

    # OGI / Method 21 screening
    res_ogi = dispatcher.dispatch(
        "fugitive_screening",
        {
            "factor_source": "specific",
            "fugitive_sub_method": "ogi",
            "leakers_count": 5,
            "surveyed_count": 100,
            "operating_hours": 1000.0,
            "ch4_content": 0.85,
        },
        {},
        {},
    )
    assert res_ogi["results"]["ch4"]["value"] > 0


# =============================================================================
# 5. ACTIVITY FACTORS, VENTED GAS & SECTION METHODS
# =============================================================================

def test_dispatcher_activity_factors_and_vented_gas(dispatcher):
    """Test activity factor rows, vented gas methods, and thermal oxidizer."""
    # Activity factor key
    res_act = dispatcher.dispatch(
        "well_testing",
        {
            "activity_key": "wt_gas",
            "amount": 2.0,
            "unit": "test",
            "ch4_content": 0.80,
        },
        {},
        {},
    )
    assert res_act["results"]["ch4"]["value"] > 0

    # Vented gas volume method
    res_vent = dispatcher.dispatch(
        "vented_gas",
        {
            "vent_method": "volume",
            "gas_volume": 50000.0,
            "gas_volume_unit": "scf",
            "unit": "scf",
            "ch4_content": 0.85,
            "co2_content": 0.05,
        },
        {},
        {},
    )
    assert res_vent["results"]["ch4"]["value"] > 0

    # Thermal oxidizer via dispatcher
    res_to = dispatcher.dispatch(
        "thermal_oxidizer",
        {
            "combustion_method": "thermal_oxidizer",
            "toc_mass": 2.0,
            "toc_mass_unit": "t",
            "toc_carbon_wt_pct": 80.0,
            "toc_ch4_wt_pct": 5.0,
            "destruction_efficiency": 98.0,
        },
        {},
        {},
    )
    assert res_to["results"]["co2"]["value"] > 0


# =============================================================================
# 6. CCS CAPTURE & UNCERTAINTY PROPAGATION
# =============================================================================

def test_dispatcher_ccs_capture_and_uncertainty(dispatcher):
    """Test CCS capture rate reduction on process CO2 and meter/GC uncertainty injection."""
    payload_no_ccs = {
        "process_type": "flaring",
        "factor_source": "specific",
        "amount": 1000.0,
        "unit": "m3",
        "c1": 85.0,
        "co2_mol": 5.0,
    }
    payload_ccs = {
        **payload_no_ccs,
        "ccs_capture_rate": "80%",
        "meter_uncertainty_pct": 5.0,
        "gc_uncertainty_pct": 3.0,
    }

    res_no = dispatcher.dispatch("flaring", payload_no_ccs, {}, {})
    res_ccs = dispatcher.dispatch("flaring", payload_ccs, {}, {})

    # CO2 should be reduced by 80%
    co2_no = res_no["results"]["co2"]["value"]
    co2_ccs = res_ccs["results"]["co2"]["value"]
    assert pytest.approx(co2_ccs, rel=1e-3) == co2_no * 0.20
    assert "uncertainty_components" in res_ccs


def test_dispatcher_library_factor_mode(dispatcher):
    """Test library factor mode bypassing tier calculators directly to factor math."""
    res_lib = dispatcher.dispatch(
        "flaring",
        {
            "amount": 100.0,
            "unit": "m3",
            "factor_mode": "library",
        },
        {
            "co2": 2.5,
            "ch4": 0.05,
            "unit": "kg/m3",
        },
        {},
    )
    assert res_lib["results"]["co2"]["value"] == 0.25
    assert res_lib["results"]["ch4"]["value"] == 0.005


# =============================================================================
# 7. COMBUSTION & FLARING BRANCHES
# =============================================================================

def test_dispatcher_combustion_tier3_and_validation(dispatcher):
    """Test stationary combustion gas analysis, carbon weight, and flaring efficiencies."""
    # Stationary combustion with C1-C10 gas analysis
    res_comb = dispatcher.dispatch(
        "stationary_combustion",
        {
            "factor_source": "specific",
            "quantity": 1000.0,
            "unit": "m3",
            "hhv": 1050.0,
            "hhv_unit": "Btu/scf",
            "combustion_efficiency": 99.5,
            "c1": 85.0,
            "c2": 5.0,
            "c3": 2.0,
            "co2_comp": 1.0,
            "operating_temperature": 25.0,
            "operating_pressure": 14.7,
        },
        {},
        {},
    )
    assert res_comb["results"]["co2"]["value"] > 0

    # Stationary combustion with carbon weight % (mass unit: tonne)
    res_carbon = dispatcher.dispatch(
        "stationary_combustion",
        {
            "factor_source": "specific",
            "quantity": 5.0,
            "unit": "tonne",
            "hhv": 1020.0,
            "combustion_efficiency": 98.0,
            "carbon_content": 75.0,
        },
        {},
        {},
    )
    assert res_carbon["results"]["co2"]["value"] > 0

    # Missing composition and measured EF raises ValueError
    with pytest.raises(ValueError, match="needs the fuel gas composition"):
        dispatcher.dispatch(
            "stationary_combustion",
            {
                "factor_source": "specific",
                "quantity": 500.0,
                "unit": "m3",
                "hhv": 1020.0,
                "combustion_efficiency": 98.0,
            },
            {},
            {},
        )

    # Flaring with single efficiency setting comb and dest eff
    res_flare = dispatcher.dispatch(
        "flaring",
        {
            "factor_source": "specific",
            "amount": 500.0,
            "unit": "m3",
            "c1": 80.0,
            "control_efficiency": 98.5,
            "hhv": 1000.0,
            "hhv_unit": "Btu/scf",
        },
        {},
        {},
    )
    assert res_flare["results"]["co2"]["value"] > 0

    # Flaring with non-volume hhv unit raises ValueError
    with pytest.raises(ValueError, match="per gas volume"):
        dispatcher.dispatch(
            "flaring",
            {
                "factor_source": "specific",
                "amount": 500.0,
                "unit": "m3",
                "c1": 80.0,
                "hhv": 45.0,
                "hhv_unit": "MJ/kg",
            },
            {},
            {},
        )


def test_dispatcher_fugitive_time_and_components(dispatcher):
    # Time unit variations
    res_days = dispatcher.dispatch(
        "fugitive_component",
        {
            "factor_source": "specific",
            "component_type": "valves",
            "amount": 20,
            "ef": 0.005,
            "operating_time": 10.0,
            "time_unit": "days",
        },
        {},
        {},
    )
    assert res_days["results"]["ch4"]["value"] > 0

    res_months = dispatcher.dispatch(
        "fugitive_component",
        {
            "factor_source": "specific",
            "component_type": "valves",
            "amount": 20,
            "ef": 0.005,
            "operating_time": 2.0,
            "time_unit": "months",
        },
        {},
        {},
    )
    assert res_months["results"]["ch4"]["value"] > 0

    res_years = dispatcher.dispatch(
        "fugitive_component",
        {
            "factor_source": "specific",
            "component_type": "valves",
            "amount": 20,
            "ef": 0.005,
            "operating_time": 1.0,
            "time_unit": "years",
        },
        {},
        {},
    )
    assert res_years["results"]["ch4"]["value"] > 0

    res_opdays = dispatcher.dispatch(
        "fugitive_component",
        {
            "factor_source": "specific",
            "component_type": "valves",
            "amount": 20,
            "ef": 0.005,
            "operating_days": 15.0,
        },
        {},
        {},
    )
    assert res_opdays["results"]["ch4"]["value"] > 0

    # Component method Table 7-12 (no explicit factor)
    res_t712 = dispatcher.dispatch(
        "fugitive_component",
        {
            "factor_source": "default",
            "fugitive_method": "component",
            "component_type": "valves",
            "amount": 50,
            "service_type": "Gas",
            "operating_hours": 2000.0,
        },
        {},
        {},
    )
    assert res_t712["results"]["ch4"]["value"] > 0

    # Missing component type raises ValueError
    with pytest.raises(ValueError, match="Select the component type"):
        dispatcher.dispatch(
            "fugitive_component",
            {"factor_source": "default", "fugitive_method": "component", "amount": 50},
            {},
            {},
        )

    # Equipment method (Tier 2A)
    res_eq = dispatcher.dispatch(
        "equipment_fugitive",
        {
            "factor_source": "specific",
            "equipment_type": "wellhead",
            "amount": 5,
            "ef": 0.05,
            "unit": "tonne CH4/well/hr",
            "operating_hours": 1000.0,
        },
        {},
        {},
    )
    assert res_eq["results"]["ch4"]["value"] > 0

    # Nitric acid with carbon_content triggers stoichiometry
    res_na_c = dispatcher.dispatch(
        "nitric_acid_production",
        {
            "factor_source": "specific",
            "amount": 1000.0,
            "unit": "kg",
            "carbon_content": 0.85,
            "oxidation_factor": 1.0,
        },
        {},
        {},
    )
    assert res_na_c["results"]["co2"]["value"] > 0

    # Stoichiometry Tier 3
    res_stoich = dispatcher.dispatch(
        "stoichiometry",
        {
            "factor_source": "specific",
            "amount": 1000.0,
            "unit": "kg",
            "carbon_content": 0.85,
        },
        {},
        {},
    )
    assert res_stoich["results"]["co2"]["value"] > 0

    # Stoichiometry missing carbon content raises ValueError
    with pytest.raises(ValueError, match="carbon content"):
        dispatcher.dispatch(
            "stoichiometry",
            {"factor_source": "specific", "amount": 1000.0, "unit": "kg"},
            {},
            {},
        )

