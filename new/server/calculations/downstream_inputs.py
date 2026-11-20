"""Required inputs of the refinery calculators (vented_downstream): refused when missing instead of an example value
(audit 2026-11 F-VENT2-03 / -07 / -09)."""


def measured_pcts(co2_pct, co_pct, equation):
    """The measured flue gas CO2 % and CO % (11 / 9 % were Exhibit 6-39's site values)."""
    if co2_pct in (None, "") or co_pct in (None, ""):
        raise ValueError(f"Equation {equation} needs the measured flue gas CO2 % and CO %")
    return float(co2_pct), float(co_pct)


def carbon_difference(fc_spent, fc_regen):
    """Spent minus regenerated catalyst carbon (wt fraction); the spent value is required (0.04 was an example)."""
    if fc_spent in (None, ""):
        raise ValueError("Catalyst regeneration needs the carbon content of the spent catalyst (wt fraction)")
    c_diff = float(fc_spent) - float(fc_regen or 0.0)
    if c_diff < 0:  # a regenerated catalyst with more carbon gave negative CO2 (F-VENT2-09)
        raise ValueError("The regenerated catalyst cannot carry more carbon than the spent catalyst")
    return c_diff


def unit_fraction(value, message):
    if not 0 <= value <= 1:
        raise ValueError(message)
    return value


def feed_molecular_weight(kwargs):
    """A feedstock volume needs its molecular weight to give the feed mass (Eq 6-49). 16.5 was assumed; Exhibit 6-42's
    feed is 18.86 (-12.6 %: F-VENT2-07)."""
    mw_in = kwargs.get("feedstock_mw") if kwargs.get("feedstock_mw") not in (None, "") else kwargs.get("feed_mw")
    if mw_in in (None, ""):
        raise ValueError("A feedstock volume needs the feed composition or its molecular weight (feedstock_mw) "
                         "to give the feed mass (Eq 6-49)")
    if float(mw_in) <= 0:
        raise ValueError("The feedstock molecular weight must be positive")
    return float(mw_in)
