"""Sign-in limits and failed sign-in records (pilot check 2026-10-09, F3/F4).

Only failed sign-ins count: a shift starting behind one proxy, NAT or Citrix address is not locked
out. Failures are limited per client address and, separately, per account from any address, so a forged
X-Forwarded-For header cannot spread password guesses over many "clients". The counters live in the
limiter's storage (Redis in production), shared by all workers.
"""
import os
import re

from flask import current_app, request

ACCOUNT_LOCKED = "Too many failed sign-ins for this account. Try again in 15 minutes or ask IT to reset the password."


def get_login_rate_limit():
    """Failed sign-ins allowed per client address."""
    return os.environ.get("LOGIN_RATE_LIMIT", "50 per 15 minutes")


def get_login_account_limit():
    """Failed sign-ins allowed per account, from any address (per-account lockout)."""
    return os.environ.get("LOGIN_ACCOUNT_LIMIT", "10 per 15 minutes")


def login_account_key():
    data = request.get_json(silent=True) or {}
    return "login-account:" + str(data.get("email", "")).strip().lower()


def failed_sign_in(response):
    return response.status_code == 401


def record_failed_sign_in(email, user):
    """FAILED_LOGIN entry in the audit log (the Audit Trail counts it as a security alert)."""
    from extensions import db
    from utils import log_activity_and_notify

    try:
        log_activity_and_notify(action="FAILED_LOGIN", record_id=str(user.id) if user else "", user=None,
                                request=request, entity="User", details=f"Failed sign-in for {email[:120]}")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on failed login: {e}")


def validate_password_complexity(password: str):
    """
    Validates password against NIST SP 800-63B / corporate complexity rules:
    - Minimum 10 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 numeric digit
    - At least 1 special character
    """
    if not password or len(password) < 10:
        return False, "Password must be at least 10 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one numeric digit (0-9)"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/~`]', password):
        return (
            False,
            "Password must contain at least one special character (!@#$%^&*...)",
        )
    return True, ""
