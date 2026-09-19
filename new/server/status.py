"""
Canonical Status Vocabulary for GHG Platform.
Standardizes statuses across Scope 1, 2, and 3 emission inventories.
"""

STATUS_PENDING = "Pending"
STATUS_VERIFIED = "Verified"
STATUS_DRAFT = "Draft"

VALID_STATUSES = {STATUS_PENDING, STATUS_VERIFIED, STATUS_DRAFT}

# Legacy variations mapped to canonical status
STATUS_ALIASES = {
    "pending approval": STATUS_PENDING,
    "pending review": STATUS_PENDING,
    "pending": STATUS_PENDING,
    "verified": STATUS_VERIFIED,
    "approved": STATUS_VERIFIED,
    "draft": STATUS_DRAFT,
}

PENDING_STATUS_SET = {STATUS_PENDING, "Pending Approval", "Pending Review"}


def normalize_status(status_str: str) -> str:
    """Normalize input status string to canonical vocabulary."""
    if not status_str:
        return STATUS_PENDING
    key = str(status_str).strip().lower()
    return STATUS_ALIASES.get(key, status_str)
