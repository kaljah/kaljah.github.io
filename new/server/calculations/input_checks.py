"""Small refusals shared by the calculators: values that gave negative or impossible emissions (audit 2026-11)."""


def non_negative(value, what):
    v = float(value)
    if v < 0:
        raise ValueError(f"{what} cannot be negative")
    return v


def year_fraction(value):
    """The record's share of a year for per unit-year factors (F-VENT2-10: a month booked a whole year)."""
    yf = float(1.0 if value in (None, "") else value)
    if not 0 < yf <= 1:
        raise ValueError("The period must be a fraction of a year between 0 and 1")
    return yf


def hours_in_year(value, default=8760.0):
    """Operating hours; an entered 0 is 0 (it was a full year: F-VENT2-04)."""
    h = float(default if value in (None, "") else value)
    if not 0 <= h <= 8784:
        raise ValueError("Operating hours must be between 0 and 8,784")
    return h


def above_absolute_zero_r(t_r):
    if t_r <= 0:
        raise ValueError("The vapour temperature cannot be at or below absolute zero")
    return t_r
