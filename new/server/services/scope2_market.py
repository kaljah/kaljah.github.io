"""Market-based electricity factor of a Scope 2 record (GHG Protocol Scope 2 Guidance).

One precedence rule for manual entry, edits and both bulk paths (audit 2026-10-14 BUG-0006, BUG-0024):
a zero-emission contractual instrument (REC, GO, renewable PPA, green tariff) gives 0; otherwise a
supplier-specific factor is used; otherwise the market-based method falls back to the grid-average
(location) factor. A zero-emission instrument together with a non-zero supplier factor contradicts
itself and is refused.

The stored ``market_emission_factor`` is only the contractual factor (the supplier factor, or 0 for
a zero-emission instrument). It is None when the record falls back to the grid factor, so an edit
of the grid region recalculates both methods with the new grid factor.
"""
from input_validation import ValidationError

# a GO is an energy attribute certificate like a REC (Scope 2 Guidance Table 6.3): it was left out, so a German site
# with a GO got the grid average (audit 2026-11 F-S23-07)
ZERO_EMISSION_INSTRUMENTS = ("rec", "go", "guarantee_of_origin", "ppa_zero", "go_zero", "renewable_ppa",
                             "green_tariff_zero")
# instruments whose factor is the contract's own: without it there is nothing to apply (they fell back to the grid)
FACTOR_INSTRUMENTS = ("ppa", "supplier_tariff", "supplier", "supplier_specific", "green_tariff", "utility_tariff")


def is_zero_emission_instrument(instrument):
    return bool(instrument) and str(instrument).strip().lower() in ZERO_EMISSION_INSTRUMENTS


def contractual_factor(instrument, supplier_ef):
    """The market factor fixed by a contract (kg CO2e/kWh), or None when there is none."""
    if is_zero_emission_instrument(instrument):
        if supplier_ef not in (None, "") and float(supplier_ef) > 0:
            raise ValidationError(
                f"A zero-emission instrument ({instrument}) cannot have a supplier emission factor of "
                f"{supplier_ef} kg CO2e/kWh: give one or the other", "market_emission_factor")
        return 0.0
    if supplier_ef not in (None, ""):
        return float(supplier_ef)
    if instrument and str(instrument).strip().lower() in FACTOR_INSTRUMENTS:
        raise ValidationError(f"A {instrument} needs its emission factor (kg CO2e/kWh) for the market-based method",
                              "market_emission_factor")
    return None


def market_factor(location_ef, instrument, supplier_ef, grid_name=None):
    """(factor used for the market-based method, value to store as market_emission_factor).

    Without a contractual factor the grid's residual mix is used when one is published, else the grid average
    (Scope 2 Guidance Table 6.3; audit 2026-11 F-S23-02). The stored value stays the contractual factor only."""
    stored = contractual_factor(instrument, supplier_ef)
    if stored is not None:
        return stored, stored
    from electricity_factors import residual_mix_for

    rm = residual_mix_for(grid_name)
    return (float(rm[0]) if rm else float(location_ef or 0.0)), None


def market_basis(instrument, supplier_ef, grid_name=None):
    """A label of what the market-based factor is (contract, residual mix, or grid average)."""
    if is_zero_emission_instrument(instrument) or supplier_ef not in (None, ""):
        return "contractual instrument"
    from electricity_factors import residual_mix_for

    rm = residual_mix_for(grid_name)
    return f"residual mix ({rm[1]})" if rm else "grid average (no residual mix published)"
