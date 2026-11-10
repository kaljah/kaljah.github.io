"""
Regional Operational & Environmental Profiles Registry
====================================================
Provides structured technical, geological, operational, and institutional
profiles for demonstration hydrocarbon basins, gas processing complexes,
and midstream facilities.

Used by the Universal Master Report publication engine to generate asset-specific
and corporate-level environmental statements, compliance analyses, and decarbonization
scorecards.
"""

from typing import Any, Dict, List, Optional

CORPORATE_PROFILE: Dict[str, Any] = {
    "key": "national",
    "name": "Demo Operator Group (Consolidated)",
    "arabic_name": "Demo Operator Co.",
    "basin": "National Demonstration Hydrocarbon Portfolio",
    "operator": "Demo Operator Co.",
    "segment": "integrated",
    "established": 2005,
    "headquarters": "Operations Hub, Demo City",
    "geology": (
        "The demonstration portfolio spans intracratonic Paleozoic and Mesozoic sedimentary basins "
        "comprising clastic sandstone reservoirs and carbonate sequences sealed by regional evaporitic "
        "caprocks at depths of 2,100 to 3,600 meters."
    ),
    "infrastructure": (
        "Integrated value chain encompassing gathering manifolds, central processing facilities (CPFs), "
        "gas compression trains, stabilization units, and coastal export terminals."
    ),
    "flaring_profile": (
        "Flaring reduction roadmap aligned with the World Bank Zero Routine Flaring (ZRF) by 2030 "
        "initiative and statutory flaring intensity caps (<= 1.00% of gross gas produced). "
        "Flare gas recovery (FGR) compressors, vapor recovery units (VRU), and ultrasonic telemetry "
        "monitor and minimize continuous flaring."
    ),
    "decarbonization_projects": [
        {"title": "Central Flare Gas Recovery (FGR) Expansion", "reduction_tco2e": 145000, "status": "Executing"},
        {"title": "Solar PV Hybridization of Remote Processing Facilities", "reduction_tco2e": 82000, "status": "Executing"},
        {"title": "Carbon Capture & Saline Aquifer Storage Pilot (CCUS)", "reduction_tco2e": 120000, "status": "Active"},
        {"title": "OGMP 2.0 Aerial Methane Quantification Pilot", "reduction_tco2e": 45000, "status": "Executing"},
    ],
    "statutory_compliance": "Applicable National GHG & Flaring Regulations, ISO 14064-1, OGMP 2.0 Framework",
}

REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "basin_alpha": {
        "key": "basin_alpha",
        "name": "Basin Alpha Oil & Gas Complex (Facility A-1)",
        "aliases": ["basin alpha", "alpha", "facility a-1", "a-1"],
        "basin": "Basin Alpha (Block 101)",
        "operator": "Demo Operator Co. (60% Operated JV)",
        "segment": "upstream",
        "established": 2008,
        "geology": (
            "Anticlinal structural closure with sandstone reservoirs situated at 3,200 m subsea. "
            "Overlain by an impermeable evaporitic seal and supported by peripheral gas reinjection."
        ),
        "infrastructure": (
            "Central processing facility with two crude stabilization trains, high-pressure gas lift "
            "compression, and produced water treatment units."
        ),
        "flaring_profile": (
            "Equipped with high-efficiency flare tips and a low-pressure flare gas recovery loop "
            "diverting off-gases into fuel gas and reinjection headers."
        ),
        "decarbonization_projects": [
            {"title": "Facility A-1 Low-Pressure Flare Gas Recovery", "reduction_tco2e": 48000, "status": "Executing"},
            {"title": "Optical Gas Imaging (OGI) LDAR Campaign", "reduction_tco2e": 19000, "status": "Active"},
            {"title": "Turbo-Compressor Waste Heat Recovery", "reduction_tco2e": 14000, "status": "Planned"},
        ],
        "statutory_compliance": "Compliant with Statutory Flaring Cap (< 1.00% gross gas)",
    },
    "basin_beta": {
        "key": "basin_beta",
        "name": "Basin Beta Wet Gas Processing Hub (Facility B-2)",
        "aliases": ["basin beta", "beta", "facility b-2", "b-2"],
        "basin": "Basin Beta (Block 202)",
        "operator": "Demo Operator Co. (70% Operated JV)",
        "segment": "upstream",
        "established": 2012,
        "geology": (
            "Fluvio-deltaic wet gas and condensate sandstone formation at 2,300 m depth "
            "managed with multi-stage boosting compression."
        ),
        "infrastructure": (
            "Gas processing complex with twin cryogenic NGL extraction lines, acid gas removal units, "
            "and export booster compression."
        ),
        "flaring_profile": (
            "Closed-loop wet gas processing minimizes routine flaring; non-routine events are tracked "
            "with ultrasonic flare header flow meters."
        ),
        "decarbonization_projects": [
            {"title": "Vapor Recovery Unit on Condensate Spheres", "reduction_tco2e": 31000, "status": "Active"},
            {"title": "Nitrogen Flare Purge Gas Conversion", "reduction_tco2e": 12000, "status": "Completed"},
        ],
        "statutory_compliance": "Benchmark Compliant (< 0.50% Flaring Intensity)",
    },
    "coastal_terminal": {
        "key": "coastal_terminal",
        "name": "Coastal Midstream & Export Terminal (Facility C-3)",
        "aliases": ["coastal terminal", "coastal", "facility c-3", "c-3", "midstream"],
        "basin": "Coastal Export Corridor",
        "operator": "Demo JV Partner A (25% Non-Operated Equity)",
        "segment": "midstream",
        "established": 2015,
        "geology": (
            "Coastal industrial zone serving as the maritime export terminus for stabilized crude "
            "and dry sales gas conveyed via pipeline corridors."
        ),
        "infrastructure": (
            "Tank farm storage, metering skids, export booster pumps, and vapor recovery headers "
            "supplying marine loading berths."
        ),
        "flaring_profile": (
            "Downstream boil-off gas management with closed-loop vapor return headers and thermal oxidizers."
        ),
        "decarbonization_projects": [
            {"title": "Storage Tank Vapor Recovery & Boil-off Compression", "reduction_tco2e": 24000, "status": "Active"},
            {"title": "Grid Electrification of Export Booster Pumps", "reduction_tco2e": 18000, "status": "Executing"},
        ],
        "statutory_compliance": "ISO 14001 / ISO 50001 Certified Terminal Operations",
    },
}


def get_regional_profile(region_identifier: Optional[str]) -> Dict[str, Any]:
    """
    Retrieves the operational and geological profile for a region,
    facility, or corporate entity using case-insensitive matching across keys and aliases.
    Defaults to the corporate consolidated profile if unmatched.
    """
    if not region_identifier or str(region_identifier).strip().lower() in ("all", "national", "global", "corporate"):
        return CORPORATE_PROFILE

    needle = str(region_identifier).strip().lower()

    if needle in REGIONAL_PROFILES:
        return REGIONAL_PROFILES[needle]

    for prof in REGIONAL_PROFILES.values():
        if needle == prof["key"] or needle in prof["name"].lower():
            return prof
        for alias in prof.get("aliases", []):
            if needle == alias or alias in needle or needle in alias:
                return prof

    clean_title = str(region_identifier).replace("_", " ").title()
    dyn_prof = dict(CORPORATE_PROFILE)
    dyn_prof["key"] = needle
    dyn_prof["name"] = f"Demo Operator {clean_title} Asset"
    dyn_prof["basin"] = f"{clean_title} Operational Basin"
    return dyn_prof


def list_available_regions() -> List[Dict[str, str]]:
    """Returns a clean list of regional assets for UI selectors and dropdowns."""
    out = [{"key": "national", "name": "Demo Operator Group (Consolidated)", "segment": "Corporate"}]
    for k, p in REGIONAL_PROFILES.items():
        out.append({"key": k, "name": p["name"], "segment": p["segment"].capitalize()})
    return out
