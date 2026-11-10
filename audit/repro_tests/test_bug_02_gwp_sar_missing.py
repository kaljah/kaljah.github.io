"""
Verification Test: BUG-02 / CALC-02 (Fixed)
Verify IPCC SAR (Second Assessment Report) in GWP_STANDARDS in new/server/calculations/constants.py
"""

import sys
import pytest

sys.path.insert(0, "new/server")

from calculations.constants import GWP_STANDARDS, get_active_gwp

def test_sar_gwp_supported():
    # Verify SAR is present in registry
    assert "SAR" in GWP_STANDARDS, "SAR must be present in GWP_STANDARDS"
    sar_100 = get_active_gwp("SAR")
    assert sar_100["CO2"] == 1.0
    assert sar_100["CH4"] == 21.0
    assert sar_100["N2O"] == 310.0

    sar_20 = get_active_gwp("SAR", horizon="20")
    assert sar_20["CO2"] == 1.0
    assert sar_20["CH4"] == 56.0
    assert sar_20["N2O"] == 280.0

