import pytest
from types import SimpleNamespace
from services.dashboard_filters import (
    production_gas_m3,
    production_boe,
    calculate_oil_gas_boe,
    SCF_PER_BOE,
)


def test_production_gas_m3_with_gas_without_injected():
    """When gas_without_injected_mmsm3 is explicitly recorded, it should take precedence."""
    row = SimpleNamespace(
        gross_gas_mmsm3=100.0,
        injected_gas_mmsm3=30.0,
        gas_without_injected_mmsm3=70.0,
    )
    gas_m3 = production_gas_m3(row)
    assert gas_m3 == 70.0 * 1e6


def test_production_gas_m3_with_injected_gas_deduction():
    """When gross and injected gas are provided, reinjected gas must be subtracted from gross."""
    row = SimpleNamespace(
        gross_gas_mmsm3=100.0,
        injected_gas_mmsm3=25.0,
        gas_without_injected_mmsm3=None,
    )
    gas_m3 = production_gas_m3(row)
    assert gas_m3 == 75.0 * 1e6


def test_production_gas_m3_gross_only_no_reinjection():
    """When no reinjection is recorded, gross gas is used."""
    row = SimpleNamespace(
        gross_gas_mmsm3=50.0,
        injected_gas_mmsm3=0.0,
        gas_without_injected_mmsm3=None,
    )
    gas_m3 = production_gas_m3(row)
    assert gas_m3 == 50.0 * 1e6


def test_production_gas_m3_dict_support():
    """Functions must support dict payloads (e.g., from bulk upload validators)."""
    payload = {
        "gross_gas_mmsm3": 80.0,
        "injected_gas_mmsm3": 20.0,
    }
    gas_m3 = production_gas_m3(payload)
    assert gas_m3 == 60.0 * 1e6


def test_production_boe_prefers_total_production_no_injected():
    """total_production_no_injected_mmboe must be preferred over gross total_production_mmboe."""
    # Net gas 60 Mm3 = ~372,630 BOE + 100,000 bbl oil = ~472,630 calculated BOE
    # A stored net of 0.48 MMBOE (480,000 BOE) is within the 30% tolerance window
    row = SimpleNamespace(
        oil_amount=100000.0,
        oil_unit="bbl",
        gross_gas_mmsm3=100.0,
        injected_gas_mmsm3=40.0,
        gas_without_injected_mmsm3=60.0,
        total_production_mmboe=0.72,               # Gross: 720,000 BOE
        total_production_no_injected_mmboe=0.48,  # Net: 480,000 BOE
    )
    boe = production_boe(row)
    assert boe == 480000.0


def test_production_boe_calculated_uses_net_gas():
    """Calculated BOE should use net gas (gross - injected) rather than gross gas."""
    # 0 oil, 100 Mm3 gross gas, 40 Mm3 reinjected gas -> 60 Mm3 net gas
    row = SimpleNamespace(
        oil_amount=0.0,
        oil_unit="bbl",
        gross_gas_mmsm3=100.0,
        injected_gas_mmsm3=40.0,
        gas_without_injected_mmsm3=None,
        total_production_mmboe=None,
        total_production_no_injected_mmboe=None,
    )
    boe = production_boe(row)
    expected_gas_m3 = 60.0 * 1e6
    expected_boe = expected_gas_m3 * 35.314666721 / SCF_PER_BOE
    assert boe == pytest.approx(expected_boe, rel=1e-4)


def test_flaring_intensity_impact_of_reinjected_gas():
    """Demonstrate that removing reinjected gas correctly reports true marketed flaring intensity."""
    flared_volume_m3 = 1_000_000.0  # 1 million m3 flared
    gross_gas_mmsm3 = 100.0         # 100 million m3 gross gas
    injected_gas_mmsm3 = 20.0       # 20 million m3 reinjected -> 80 million m3 net

    row_gross_only = SimpleNamespace(
        gross_gas_mmsm3=gross_gas_mmsm3,
        injected_gas_mmsm3=0.0,
    )
    row_with_reinjection = SimpleNamespace(
        gross_gas_mmsm3=gross_gas_mmsm3,
        injected_gas_mmsm3=injected_gas_mmsm3,
    )

    gas_m3_gross = production_gas_m3(row_gross_only)
    gas_m3_net = production_gas_m3(row_with_reinjection)

    intensity_gross = (flared_volume_m3 / gas_m3_gross) * 100.0
    intensity_net = (flared_volume_m3 / gas_m3_net) * 100.0

    # Under gross, 1 Mm3 / 100 Mm3 = 1.00% (falsely compliant or boundary)
    assert intensity_gross == pytest.approx(1.00)
    # Under net, 1 Mm3 / 80 Mm3 = 1.25% (accurately flagged as exceeding threshold)
    assert intensity_net == pytest.approx(1.25)
    assert intensity_net > intensity_gross
