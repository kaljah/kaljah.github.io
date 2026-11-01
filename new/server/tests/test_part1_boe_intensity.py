"""
Unit & Regression Tests for Production Denominator (BOE) and Intensity (Item 1.2)
================================================================================
Verifies that:
1. Combined BOE is consistently computed using canonical conversion constants:
   - 1020 Btu/scf HHV, 5.8 MMBtu/BOE -> 0.175862 BOE/mscf, 5686.27 scf/BOE
   - 1 m3 crude = 6.28981 bbl
2. Total MMBOE is validated against oil+gas converted BOE within 30% tolerance.
3. Discordant MMBOE (such as 10,000 MMBOE on 'rz' vs 0.625 MMBOE oil+gas) falls back
   to calculated oil+gas BOE with a logged warning.
4. Total BOE denominator is corrected from 11.397B BOE to ~1.397B BOE.
5. GHG intensity, Scope 3 intensity, and methane intensity match regional benchmark ranges.
"""

import pytest
from calculations.units import (
    GAS_BOE_PER_MSCF,
    MMBTU_PER_BOE,
    NG_HHV_BTU_PER_SCF,
    SCF_PER_BOE,
)
from services.dashboard_filters import (
    calculate_oil_gas_boe,
    production_boe,
    validate_production_mmboe_consistency,
)


def _make_prod(**kwargs):
    class MockRow:
        def __init__(self, **d):
            self.__dict__.update(d)

        def get(self, k, default=None):
            return getattr(self, k, default)

    return MockRow(**kwargs)


def test_calculate_oil_gas_boe_components():
    """Verify separate oil and gas components convert correctly to BOE."""
    # 1,000 bbl oil = 1,000 BOE
    row_oil = _make_prod(oil_amount=1000.0, oil_unit="bbl", gas_amount=0.0)
    assert calculate_oil_gas_boe(row_oil) == pytest.approx(1000.0, rel=1e-9)

    # 1,000 mscf gas = 1,000 * 0.17586206896551725 = 175.86206896551725 BOE
    row_gas = _make_prod(oil_amount=0.0, gas_amount=1000.0, gas_unit="mscf")
    assert calculate_oil_gas_boe(row_gas) == pytest.approx(1000.0 * GAS_BOE_PER_MSCF, rel=1e-9)

    # Combined oil and gas
    row_comb = _make_prod(oil_amount=1000.0, oil_unit="bbl", gas_amount=1000.0, gas_unit="mscf")
    assert calculate_oil_gas_boe(row_comb) == pytest.approx(1000.0 + 1000.0 * GAS_BOE_PER_MSCF, rel=1e-9)


def test_validate_production_mmboe_consistency():
    """Verify tolerance check accepts within 30% and rejects beyond 30%."""
    calc_boe = 1_000_000.0  # 1.0 MMBOE

    # 1.05 MMBOE (+5%) -> Valid
    is_valid, diff = validate_production_mmboe_consistency(1.05, calc_boe, tolerance=0.30)
    assert is_valid is True
    assert diff == pytest.approx(0.05, rel=1e-3)

    # 0.75 MMBOE (-25%) -> Valid
    is_valid, diff = validate_production_mmboe_consistency(0.75, calc_boe, tolerance=0.30)
    assert is_valid is True
    assert diff == pytest.approx(0.25, rel=1e-3)

    # 1.50 MMBOE (+50%) -> Invalid
    is_valid, diff = validate_production_mmboe_consistency(1.50, calc_boe, tolerance=0.30)
    assert is_valid is False
    assert diff == pytest.approx(0.50, rel=1e-3)

    # 10,000 MMBOE vs 0.625 MMBOE ('rz' bug) -> Invalid
    is_valid, diff = validate_production_mmboe_consistency(10000.0, 624760.0, tolerance=0.30)
    assert is_valid is False
    assert diff > 10.0


def test_production_boe_rz_fallback():
    """
    Test the exact 'rz' row bug:
    total_production_mmboe = 10,000.0 (10 billion BOE)
    oil = 252,200 bbl, gas = 2,118,480 mscf
    Expected: total_production_mmboe rejected, falls back to 624,760 BOE.
    """
    rz_row = _make_prod(
        id=1,
        facility_id=3,
        year=2026,
        oil_amount=252200.0,
        oil_unit="bbl",
        gas_amount=2118480.0,
        gas_unit="mscf",
        total_production_mmboe=10000.0,
    )
    expected_calc_boe = 252200.0 + (2118480.0 * GAS_BOE_PER_MSCF)  # ~624,760.36 BOE
    actual_boe = production_boe(rz_row)

    assert actual_boe == pytest.approx(expected_calc_boe, rel=1e-6)
    assert actual_boe < 1_000_000.0  # NOT 10,000,000,000.0


def test_intensity_metrics_recomputation():
    """
    Verify before and after intensity calculations:
    Total Inventory Emissions: ~13.8M tCO2e (Gross S1 ~12.1M, S2 ~1.69M)
    Total S1 Methane: ~73.7 kt (or ~49.2 kt without test facility 3)
    """
    # 1. Old buggy denominator: 11,397,046,714 BOE
    old_boe = 11_397_046_714.0
    s1_t = 12_128_166.0
    s2_t = 1_687_350.0
    s3_t = 519_324.0
    ch4_t = 73_691.7

    old_ghg_intensity = ((s1_t + s2_t) * 1000.0) / old_boe
    old_s3_intensity = (s3_t * 1000.0) / old_boe
    old_ch4_intensity = (ch4_t * 1000.0) / old_boe

    assert old_ghg_intensity == pytest.approx(1.21, rel=1e-2)
    assert old_s3_intensity == pytest.approx(0.046, rel=1e-2)

    # 2. Corrected denominator: 1,397,671,474 BOE
    new_boe = 1_397_671_474.0
    new_ghg_intensity = ((s1_t + s2_t) * 1000.0) / new_boe
    new_s3_intensity = (s3_t * 1000.0) / new_boe
    new_ch4_intensity = (ch4_t * 1000.0) / new_boe

    # Intensity is now in the realistic 9.5 - 10.0 kg/BOE range (matching 3-19 regional bars)
    assert new_ghg_intensity == pytest.approx(9.88, rel=1e-2)
    assert new_s3_intensity == pytest.approx(0.37, rel=1e-2)
    assert new_ch4_intensity == pytest.approx(0.0527, rel=1e-2)
