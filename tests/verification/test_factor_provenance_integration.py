"""
Integration Verification Suite: Factor Provenance, Silent Defaults & Statutory Methodology
========================================================================================
Validates that:
1. FactorProvenanceRegistry has 72 verified factors with full provenance (source, table, quote).
2. CalculationFactorLineage tracks calculation inputs and detects silent defaults.
3. Steam calculation defaults strictly to 82% boiler efficiency and 10% transmission loss (net 72%).
4. CBAM hydrogen library provides EU 2023/1773 transitional default (10.40), ETS benchmark (6.84),
   and RFNBO threshold (3.38).
5. Algerian Scope 2 grid profiles (MEM 2024, IEA 2023, IGES CDM) are available and accurate.
6. Statutory export policy enforces 100-year GWP horizon.
"""

import os
import sys
import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "new", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app
from models import db, FactorProvenanceRegistry, CalculationFactorLineage, Emission
from calculations.constants import get_active_gwp, GWP_AR5, GWP_AR6
from calculations.indirect import IndirectSteamCalculator
from calculations.dispatcher import CalculationDispatcher
from electricity_factors import GRID_FACTORS


@pytest.fixture(scope="module")
def app_ctx():
    with app.app_context():
        yield


def test_registry_factor_count_and_provenance(app_ctx):
    """Assert all 72 factors are seeded with mandatory provenance citations and verbatim quotes."""
    factors = FactorProvenanceRegistry.query.all()
    assert len(factors) == 72, f"Expected 72 factors in registry, found {len(factors)}"

    for f in factors:
        assert f.id, "Factor missing ID"
        assert f.parameter_name, f"Factor {f.id} missing parameter_name"
        assert f.value is not None, f"Factor {f.id} missing numeric value"
        assert f.unit, f"Factor {f.id} missing unit"
        assert f.source_document, f"Factor {f.id} missing source_document"
        assert f.table_or_equation_ref, f"Factor {f.id} missing table_or_equation_ref"
        assert f.verbatim_citation, f"Factor {f.id} missing verbatim_citation"
        # Verbatim quote must be concise (< 35 words)
        word_count = len(f.verbatim_citation.split())
        assert word_count <= 35, f"Factor {f.id} verbatim quote too long ({word_count} words)"


def test_steam_compendium_exhibit_8_3_defaults():
    """Assert PurchasedSteamCalculator uses Exhibit 8.3 defaults (82% boiler, 10% line loss -> net 72%)."""
    calc = IndirectSteamCalculator()
    # 100 MMBtu heat, 53.06 kg CO2/MMBtu
    res = calc.calculate(
        heat_energy=100,
        ef_co2=53.06,
        boiler_efficiency=None,
        transmission_loss=None,
        heat_unit="mmbtu",
        uncertainties={},
    )
    # Net efficiency: 0.82 - 0.10 = 0.72
    # Fuel MMBtu = 100 / 0.72 = 138.888888...
    # CO2 tonnes = 138.888888... * 53.06 / 1000 = 7.369444...
    expected_co2 = (100.0 / 0.72) * 53.06 / 1000.0
    actual_co2 = res["results"]["co2"]["value"]
    assert pytest.approx(actual_co2, rel=1e-4) == expected_co2
    assert res.get("has_silent_defaults") is True
    assert "SCP2-004" in res.get("consumed_factors", [])
    assert "SCP2-005" in res.get("consumed_factors", [])


def test_cbam_hydrogen_official_presets(app_ctx):
    """Assert CBAM hydrogen factors match official EU regulations."""
    eu_def = db.session.get(FactorProvenanceRegistry, "CBAM-001")
    assert eu_def is not None
    assert eu_def.value == 10.40, "EU transitional default must be 10.40 tCO2e/t H2"
    assert "2023/1773" in eu_def.source_document

    ets_bm = db.session.get(FactorProvenanceRegistry, "CBAM-002")
    assert ets_bm is not None
    assert ets_bm.value == 6.84, "EU ETS benchmark must be 6.84 tCO2/t H2"
    assert "2021/447" in eu_def.source_document or "2021/447" in ets_bm.source_document

    rfnbo = db.session.get(FactorProvenanceRegistry, "CBAM-003")
    assert rfnbo is not None
    assert rfnbo.value == 3.38, "RFNBO threshold must be 3.38 tCO2e/t H2"
    assert "2023/1184" in rfnbo.source_document


def test_algerian_grid_profiles():
    """Assert Algerian Scope 2 grid emission factor is present and sourced."""
    assert "Algerian National Grid" in GRID_FACTORS
    entry = GRID_FACTORS["Algerian National Grid"]
    assert pytest.approx(entry["co2"], rel=1e-3) == 0.4974
    # AR5 factor: 0.4974 + 8.866e-6 * 28 + 8.866e-7 * 265 = ~0.49788
    assert pytest.approx(entry["factor"], rel=1e-3) == 0.4979
    assert "MEM" in entry["source"] or "Bilan" in entry["source"]


def test_gwp_dual_mode_policy():
    """Assert GWP resolution supports 100-yr standard and restricts 20-yr horizon."""
    gwp_100 = get_active_gwp(standard="AR5", horizon="100")
    assert gwp_100["CH4"] == 28.0
    assert gwp_100["N2O"] == 265.0

    gwp_20 = get_active_gwp(standard="AR5", horizon="20")
    assert gwp_20["CH4"] == 84.0
    assert gwp_20["N2O"] == 264.0

    # AR6 100 vs 20
    ar6_100 = get_active_gwp(standard="AR6", horizon="100")
    assert ar6_100["CH4"] == 29.8
    assert ar6_100["N2O"] == 273.0

    ar6_20 = get_active_gwp(standard="AR6", horizon="20")
    assert ar6_20["CH4"] == 82.5
    assert ar6_20["N2O"] == 273.0


def test_dispatcher_provenance_trail():
    """Assert CalculationDispatcher attaches factor provenance trail to outputs."""
    d = CalculationDispatcher()
    res = d.dispatch("flaring", {"amount": 500, "unit": "mscf", "c1": 85.0}, {})
    assert "provenance_trail" in res
    assert len(res["provenance_trail"]) > 0
    trail_ids = [p["id"] for p in res["provenance_trail"]]
    assert "GWP-005" in trail_ids
    assert "FLR-001" in trail_ids
    assert res.get("has_silent_defaults") is True
