"""
OGMP 2.0 Compliance and Hierarchy Classification Service.
Canonical implementation of source-level (L1-L4) and facility-level (L1-L5)
hierarchy classification per UNEP / OGMP 2.0 Reporting Framework.
"""
from typing import Optional, Union, Dict, Any


def ogmp_level_for(emission) -> int:
    """
    Canonical determination of OGMP 2.0 level (1-4) for a source emission record.
    
    Level 1: Asset-level estimate
    Level 2: National / generic emission factors
    Level 3: Generic emission factors by equipment / source type (e.g. API Compendium tables)
    Level 4: Direct measurement or facility/equipment-specific engineering calculation
    """
    if emission is None:
        return 1

    # Check explicit ogmp_level field if valid
    raw_lvl = getattr(emission, "ogmp_level", None)
    if raw_lvl is not None:
        try:
            val = int(raw_lvl)
            if 1 <= val <= 4:
                return val
        except (ValueError, TypeError):
            pass

    factor_source = (getattr(emission, "factor_source", None) or "").strip().lower()
    calc_method = (getattr(emission, "calc_method", None) or "").strip().lower()

    # Level 4: Specific / direct measurement / engineering
    if (
        factor_source in ("specific", "site_specific", "site-specific", "engineering", "cems", "direct_measurement")
        or calc_method in ("direct_measurement", "tier3", "engineering", "specific", "cems", "site_specific")
    ):
        return 4

    # Level 3: Custom / component-count / equipment-specific factors
    if (
        factor_source in ("custom", "api_table", "basin_specific", "component", "table")
        or calc_method in ("tier2", "component_count", "hi_flow", "custom_factor")
    ):
        return 3

    # Level 2: Generic / default standard factors
    if (
        factor_source in ("default", "generic", "legacy", "epa_table", "standard")
        or calc_method in ("tier1", "generic", "standard", "default")
    ):
        return 2

    # Default fallback for registered equipment inventory
    return 2


def compute_facility_ogmp_level(
    facility,
    year: Optional[int] = None,
    top_down_tch4: Optional[float] = None,
    bottom_up_tch4: Optional[float] = None,
    reconciled_survey: Optional[bool] = None,
    bottom_up_level: Optional[int] = None,
) -> int:
    """
    Canonical determination of facility OGMP 2.0 level (1-5).
    
    - Level 5: Both bottom-up (L4 source-level measured / Tier 3 engineering) and top-down measurement
               exist for the facility/year, reconciled within threshold (<= 20% variance) without discrepancy.
    - Level 4: Top-down site measurements conducted OR source-level direct measurements (L4) exist.
    - Level 3: Equipment-level generic factors (L3) populated.
    - Level 2: Generic asset-level factors.
    - Level 1: Minimal venture-level reporting.
    """
    if facility is None:
        return 1

    threshold = getattr(facility, "reconciliation_threshold", None) or 20.0

    # If top_down and bottom_up were provided or resolved
    td = top_down_tch4 if top_down_tch4 is not None else 0.0
    bu = bottom_up_tch4 if bottom_up_tch4 is not None else 0.0

    # If bottom_up_level not passed, check facility's emission records if in app context
    if bottom_up_level is None and facility is not None:
        try:
            from flask import has_app_context
            if has_app_context():
                from models import Emission
                q = Emission.query.filter_by(facility_id=facility.id)
                if year and year != "all" and str(year).isdigit():
                    q = q.filter_by(year=int(year))
                records = q.all()
                if records:
                    bottom_up_level = max((ogmp_level_for(r) for r in records), default=2)
        except Exception:
            pass

    if td > 0 and bu > 0:
        variance_pct = abs((td - bu) / bu * 100.0)
        # Check if reconciled within threshold
        is_reconciled = reconciled_survey is True or (reconciled_survey is None and variance_pct <= threshold)
        if is_reconciled:
            # Under strict UNEP OGMP 2.0 Gold Standard rules, Level 5 requires that the bottom-up
            # inventory is already Level 4 (source-level measured / Tier 3 engineering).
            # Reconciling with generic Level 2 or Level 3 factors is capped at Level 4.
            if bottom_up_level is not None and bottom_up_level < 4:
                return 4
            return 5
        # If measured but unreconciled, it's Level 4
        return 4
    elif td > 0:
        # Top-down measurement exists but bottom-up missing or pending
        return 4
    elif bu > 0:
        # Return resolved bottom-up level, defaulting to Level 3
        return bottom_up_level if bottom_up_level is not None else 3

    return 2


def ogmp_level_label(level: int) -> str:
    """Formatted label for OGMP level."""
    labels = {
        1: "Level 1 (Asset Reporting)",
        2: "Level 2 (Generic EFs)",
        3: "Level 3 (Generic Factors)",
        4: "Level 4 (Measured / Direct)",
        5: "Level 5 (Reconciled)",
    }
    return labels.get(level, f"Level {level}")
