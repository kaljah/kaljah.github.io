"""
Reporting Period Lock Service (Part 2.3)
========================================
Enforces strict immutability for statutory reporting periods that have undergone
official sign-off.

Rules:
1. No create, edit, or delete operations permitted in locked periods.
2. Unlocking requires an authorized administrative role and a mandatory justification reason (audited).
3. Late-arriving data must be submitted with the 'is_prior_period_adjustment' flag to the current period.
"""
from typing import Optional, Tuple
from extensions import db
from models import PeriodLock


def is_period_locked(year: Optional[int], month: Optional[int] = None) -> bool:
    """Checks whether the given reporting year/month is locked."""
    if year is None:
        return False
    try:
        y = int(year)
    except (ValueError, TypeError):
        return False

    q = PeriodLock.query.filter(PeriodLock.year == y, PeriodLock.status == "locked")
    # If a year-level lock exists (month is None), the entire year is locked
    locks = q.all()
    if not locks:
        return False

    if any(l.month is None for l in locks):
        return True

    if month is not None:
        try:
            m = int(month)
            return any(l.month == m for l in locks)
        except (ValueError, TypeError):
            pass

    return False


def check_period_lock_for_record(
    year: Optional[int],
    month: Optional[int] = None,
    is_prior_period_adjustment: bool = False,
) -> Optional[Tuple[dict, int]]:
    """
    Returns an error payload and 403 status if the period is locked and the submission
    is not marked as a prior-period adjustment.
    """
    if is_prior_period_adjustment:
        return None

    if is_period_locked(year, month):
        return (
            {
                "error": f"Reporting period {year} is locked after official sign-off. Cannot create, edit, or delete records in a locked period without an authorized unlock.",
                "code": "PERIOD_LOCKED",
                "year": year,
                "hint": "To submit late-arriving activity data for a closed period, flag the submission as a prior-period adjustment (is_prior_period_adjustment: true) or request an administrative unlock.",
            },
            403,
        )

    return None
