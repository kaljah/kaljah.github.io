"""Spend of an EEIO (spend-based) Scope 3 row in the basis of its factors.

EPA Supply Chain GHG Emission Factors v1.3 are kg CO2e per 2022 USD (purchaser price). GHG Protocol Scope 3
Technical Guidance (spend-based method): convert the spend at the spend year's exchange rate and deflate it to the
factors' year. The importer converted five currencies at fixed, undated and unsourced rates (EUR 1.08, GBP 1.28,
...) and never deflated (audit 2026-11 F-S23-05 / F-UPL-08). A non-USD spend now needs its own rate, and a
deflator (2022 price index / spend-year price index) is applied when given; without one the spend is used as
2022 USD and the record says so.
"""
from input_validation import ValidationError, parse_number

FACTOR_BASIS_YEAR = 2022
_USD = {"USD", "$", "US$", "USD$"}


def spend_in_factor_usd(amount, currency=None, fx_rate_to_usd=None, year=None, deflator_to_2022=None):
    """(spend in 2022 USD, [notes]). Refuses a non-USD spend without its exchange rate."""
    notes = []
    cur = str(currency or "USD").strip().upper()
    if cur in _USD:
        fx = 1.0
    else:
        if fx_rate_to_usd in (None, ""):
            raise ValidationError(
                f"Spend in {cur} needs its exchange rate to USD for the spend year (fx_rate_to_usd): no rate is assumed",
                "fx_rate_to_usd")
        fx = parse_number(fx_rate_to_usd, "fx_rate_to_usd", min_value=0)
        if fx <= 0:
            raise ValidationError("The exchange rate to USD must be greater than 0", "fx_rate_to_usd")
        notes.append(f"{cur} converted at {fx:g} USD/{cur} (entered)")
    usd = float(amount) * fx
    if deflator_to_2022 not in (None, ""):
        d = parse_number(deflator_to_2022, "deflator_to_2022", min_value=0)
        if d <= 0:
            raise ValidationError("The deflator to 2022 USD must be greater than 0", "deflator_to_2022")
        usd *= d
        notes.append(f"deflated to {FACTOR_BASIS_YEAR} USD x {d:g} (entered)")
    elif year not in (None, "") and int(year) != FACTOR_BASIS_YEAR:
        notes.append(f"spend of {int(year)} not deflated to {FACTOR_BASIS_YEAR} USD (the factors' basis): "
                     "give deflator_to_2022")
    return usd, notes
