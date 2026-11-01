import pytest
from services.dashboard_filters import (
    calculate_oil_gas_boe,
    validate_production_mmboe_consistency,
    production_boe,
    SCF_PER_BOE,
)


class MockProdRow:
    def __init__(self, oil_amount=0.0, oil_unit="bbl", gas_amount=0.0, gas_unit="mscf",
                 gross_gas_mmsm3=0.0, total_production_mmboe=0.0, year=2024, month=1):
        self.id = 101
        self.oil_amount = oil_amount
        self.oil_unit = oil_unit
        self.gas_amount = gas_amount
        self.gas_unit = gas_unit
        self.gross_gas_mmsm3 = gross_gas_mmsm3
        self.total_production_mmboe = total_production_mmboe
        self.year = year
        self.month = month


def test_validate_production_mmboe_consistency():
    # Case 1: Within tolerance (24.85 MMBOE oil + 31.6 MMBOE gas = ~56.45 MMBOE; stored = 67.11 MMBOE -> ~18.8% diff)
    calc_boe = 56.45e6
    stored_mmboe = 67.11
    consistent, diff_pct = validate_production_mmboe_consistency(stored_mmboe, calc_boe, tolerance=0.30)
    assert consistent is True
    assert diff_pct < 0.30

    # Case 2: Discordant outlier (rz bug: stored = 10,000 MMBOE, calc = 0.605 MMBOE)
    calc_boe_outlier = 605280.0
    stored_mmboe_outlier = 10000.0
    consistent_outlier, diff_pct_outlier = validate_production_mmboe_consistency(
        stored_mmboe_outlier, calc_boe_outlier, tolerance=0.30
    )
    assert consistent_outlier is False
    assert diff_pct_outlier > 100.0


def test_production_boe_fallback():
    # Discordant row must fall back to calculated oil + gas BOE
    row_discordant = MockProdRow(
        oil_amount=252200.0,
        oil_unit="bbl",
        gas_amount=2118480.0,
        gas_unit="mscf",
        total_production_mmboe=10000.0,  # 10 Billion BOE outlier
    )
    calculated_boe = calculate_oil_gas_boe(row_discordant)
    result_boe = production_boe(row_discordant)
    assert result_boe == pytest.approx(calculated_boe, rel=1e-4)
    assert result_boe < 10e6  # Definitely not 10 billion

    # Consistent row within tolerance uses stored total_production_mmboe * 1e6
    row_consistent = MockProdRow(
        oil_amount=100000.0,
        oil_unit="bbl",
        gas_amount=600000.0,
        gas_unit="mscf",
        total_production_mmboe=0.205,  # 205,000 BOE vs ~205,500 calculated (~0.2% diff)
    )
    assert production_boe(row_consistent) == pytest.approx(205000.0)
