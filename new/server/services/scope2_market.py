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

ZERO_EMISSION_INSTRUMENTS = ("rec", "ppa_zero", "go_zero", "renewable_ppa", "green_tariff_zero")


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
    return None


def market_factor(location_ef, instrument, supplier_ef):
    """(factor used for the market-based method, value to store as market_emission_factor)."""
    stored = contractual_factor(instrument, supplier_ef)
    return (float(location_ef or 0.0) if stored is None else stored), stored
