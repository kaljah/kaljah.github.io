"""
Emission Factors API Routes
Provides endpoints for retrieving emission factors with segment filtering,
process category filtering, and automatic uncertainty loading.
"""

from flask import Blueprint, jsonify, request
from emission_factors import (
    EQUIPMENT_FACTORS,
    ALL_EMISSION_FACTORS,
    get_factor_by_segment,
    get_factor_by_process_category,
    get_factors_by_segment_and_category,
    SEGMENTS,
    PROCESS_TYPES,
    CATEGORIES,
    get_process_types_for_segment,
)

# NEW-03 FIX: import login_required - all EF endpoints require authentication
try:
    from routes.auth import login_required
except ImportError:
    from auth import login_required

factors_bp = Blueprint("factors", __name__)

# =============================================================================
# EMISSION FACTORS ENDPOINTS
# =============================================================================


@factors_bp.route("/api/emission-factors", methods=["GET"])
@login_required  # NEW-03 FIX
def get_all_emission_factors():
    """
    Get all emission factors.

    Returns:
        JSON: Dictionary of all emission factors (120+)
    """
    return jsonify(
        {"count": len(ALL_EMISSION_FACTORS), "factors": ALL_EMISSION_FACTORS}
    )


@factors_bp.route("/api/emission-factors/segments", methods=["GET"])
@login_required  # NEW-03 FIX
def get_segments():
    """
    Get all available segments.

    Returns:
        JSON: List of segments (Upstream, Midstream, Downstream)
    """
    return jsonify(SEGMENTS)


@factors_bp.route("/api/emission-factors/by-segment/<segment>", methods=["GET"])
@login_required  # NEW-03 FIX
def get_factors_for_segment(segment):
    """
    Get emission factors for a specific segment.

    Args:
        segment: Upstream, Midstream, or Downstream

    Returns:
        JSON: Emission factors applicable to that segment
    """
    # Normalize segment input
    segment_normalized = segment.lower().capitalize()

    if segment_normalized not in SEGMENTS:
        return (
            jsonify(
                {"error": f'Invalid segment. Must be one of: {", ".join(SEGMENTS)}'}
            ),
            400,
        )

    factors = get_factor_by_segment(segment_normalized)

    return jsonify(
        {"segment": segment_normalized, "count": len(factors), "factors": factors}
    )


@factors_bp.route("/api/emission-factors/process-types", methods=["GET"])
@login_required  # NEW-03 FIX
def get_all_process_types():
    """
    Get all available process types.

    Returns:
        JSON: Dictionary of process types organized by category
    """
    return jsonify({"process_types": PROCESS_TYPES, "categories": CATEGORIES})


@factors_bp.route("/api/emission-factors/process-types/<segment>", methods=["GET"])
@login_required  # NEW-03 FIX
def get_process_types_for_seg(segment):
    """
    Get process types applicable to a specific segment.

    Args:
        segment: Upstream, Midstream, or Downstream

    Returns:
        JSON: List of process type IDs for that segment
    """
    # Normalize segment input
    segment_normalized = segment.lower()

    if segment_normalized not in ["upstream", "midstream", "downstream"]:
        return (
            jsonify(
                {
                    "error": "Invalid segment. Must be one of: upstream, midstream, downstream"
                }
            ),
            400,
        )

    process_types = get_process_types_for_segment(segment_normalized)

    # Build detailed response with process type info
    # get_process_types_for_segment returns a dict, not a list
    detailed_types = []
    for pt_id, pt_data in process_types.items():
        detailed_types.append(
            {
                "id": pt_id,
                "name": pt_data.get("display_name", pt_id),
                "category": pt_data.get("category", "other"),
            }
        )

    return jsonify(
        {
            "segment": segment_normalized,
            "count": len(detailed_types),
            "process_types": detailed_types,
        }
    )


@factors_bp.route(
    "/api/emission-factors/by-process/<process_category>", methods=["GET"]
)
@login_required  # NEW-03 FIX
def get_factors_for_process_category(process_category):
    """
    Get emission factors for a specific process category.

    Args:
        process_category: Process category ID (e.g., 'stationary_combustion', 'flaring')

    Returns:
        JSON: Emission factors for that process category
    """
    factors = get_factor_by_process_category(process_category)

    if not factors:
        return (
            jsonify(
                {"error": f"No factors found for process category: {process_category}"}
            ),
            404,
        )

    return jsonify(
        {
            "process_category": process_category,
            "count": len(factors),
            "factors": factors,
        }
    )


@factors_bp.route("/api/emission-factors/by-segment-and-process", methods=["GET"])
@login_required  # NEW-03 FIX
def get_factors_by_seg_and_proc():
    """
    Get emission factors for a specific segment AND process category.

    Query Parameters:
        segment: Upstream, Midstream, or Downstream
        process: Process category ID

    Returns:
        JSON: Emission factors matching both criteria
    """
    segment = request.args.get("segment")
    process_category = request.args.get("process")

    if not segment or not process_category:
        return (
            jsonify(
                {"error": "Both segment and process query parameters are required"}
            ),
            400,
        )

    # Normalize segment
    segment_normalized = segment.lower().capitalize()

    if segment_normalized not in SEGMENTS:
        return (
            jsonify(
                {"error": f'Invalid segment. Must be one of: {", ".join(SEGMENTS)}'}
            ),
            400,
        )

    factors = get_factors_by_segment_and_category(segment_normalized, process_category)

    return jsonify(
        {
            "segment": segment_normalized,
            "process_category": process_category,
            "count": len(factors),
            "factors": factors,
        }
    )


@factors_bp.route("/api/emission-factors/search", methods=["GET"])
@login_required  # NEW-03 FIX
def search_emission_factors():
    """
    Search emission factors by name, code, or description.

    Query Parameters:
        q: Search query string
        segment: Optional segment filter
        process: Optional process category filter

    Returns:
        JSON: Matching emission factors
    """
    query = request.args.get("q", "").lower()
    segment_filter = request.args.get("segment")
    process_filter = request.args.get("process")

    if not query:
        return jsonify({"error": 'Query parameter "q" is required'}), 400

    # Start with all factors or filtered subset
    if segment_filter and process_filter:
        segment_normalized = segment_filter.lower().capitalize()
        factors = get_factors_by_segment_and_category(
            segment_normalized, process_filter
        )
    elif segment_filter:
        segment_normalized = segment_filter.lower().capitalize()
        factors = get_factor_by_segment(segment_normalized)
    elif process_filter:
        factors = get_factor_by_process_category(process_filter)
    else:
        factors = ALL_EMISSION_FACTORS

    # Search through factors
    results = {}
    for factor_name, factor_data in factors.items():
        # Search in factor name
        if query in factor_name.lower():
            results[factor_name] = factor_data
            continue

        # Search in code
        if "code" in factor_data and query in factor_data["code"].lower():
            results[factor_name] = factor_data
            continue

        # Search in description
        if "description" in factor_data and query in factor_data["description"].lower():
            results[factor_name] = factor_data
            continue

        # Search in source
        if "source" in factor_data and query in factor_data["source"].lower():
            results[factor_name] = factor_data
            continue

    return jsonify({"query": query, "count": len(results), "factors": results})


@factors_bp.route("/api/emission-factors/uncertainties", methods=["GET"])
@login_required  # NEW-03 FIX
def get_factors_with_uncertainties():
    """
    Get all emission factors that have uncertainty values defined.

    Query Parameters:
        min_uncertainty: Optional minimum uncertainty threshold (0-1)
        max_uncertainty: Optional maximum uncertainty threshold (0-1)

    Returns:
        JSON: Emission factors with uncertainty information
    """
    min_unc = request.args.get("min_uncertainty", type=float)
    max_unc = request.args.get("max_uncertainty", type=float)

    results = {}
    for factor_name, factor_data in ALL_EMISSION_FACTORS.items():
        if "uncertainty" in factor_data:
            # Get max uncertainty across all gases
            max_factor_unc = max(
                factor_data["uncertainty"].get("co2", 0),
                factor_data["uncertainty"].get("ch4", 0),
                factor_data["uncertainty"].get("n2o", 0),
            )

            # Apply filters if provided
            if min_unc is not None and max_factor_unc < min_unc:
                continue
            if max_unc is not None and max_factor_unc > max_unc:
                continue

            results[factor_name] = {**factor_data, "max_uncertainty": max_factor_unc}

    return jsonify({"count": len(results), "factors": results})


# =============================================================================
# STATISTICS & METADATA ENDPOINTS
# =============================================================================


@factors_bp.route("/api/emission-factors/stats", methods=["GET"])
@login_required  # NEW-03 FIX
def get_emission_factors_stats():
    """
    Get statistics about the emission factors database.

    Returns:
        JSON: Database statistics (counts by segment, category, etc.)
    """
    stats = {
        "total_factors": len(ALL_EMISSION_FACTORS),
        "by_segment": {},
        "by_process_category": {},
        "with_uncertainties": 0,
        "combustion_factors": len(
            [
                f
                for f in ALL_EMISSION_FACTORS.values()
                if "combustion" in f.get("usage", [])
            ]
        ),
        "flaring_factors": len(
            [
                f
                for f in ALL_EMISSION_FACTORS.values()
                if "flaring" in f.get("usage", [])
            ]
        ),
        "equipment_factors": len(EQUIPMENT_FACTORS),
    }

    # Count by segment
    for segment in SEGMENTS:
        stats["by_segment"][segment] = len(get_factor_by_segment(segment))

    # Count factors with uncertainties
    stats["with_uncertainties"] = len(
        [f for f in ALL_EMISSION_FACTORS.values() if "uncertainty" in f]
    )

    return jsonify(stats)


@factors_bp.route("/api/emission-factors/version", methods=["GET"])
@login_required  # NEW-03 FIX
def get_database_version():
    """
    Get the version and source information for the emission factors database.

    Returns:
        JSON: Database version, source, and compliance information
    """
    return jsonify(
        {
            "version": "1.0.0",
            "source": "API Compendium 2021",
            "sections": [
                "Section 5 (Combustion & Flaring)",
                "Section 6 (Vented & Process)",
                "Section 7 (Fugitive & Equipment)",
            ],
            "total_factors": len(ALL_EMISSION_FACTORS),
            "features": [
                "Automatic uncertainty loading",
                "Segment-based categorization",
                "Process type organization",
                "Helper functions for filtering",
            ],
            "last_updated": "2026-02-10",
        }
    )
