"""
Process Categories and Segment Classification
API Compendium 2021 - Organized by Upstream/Midstream/Downstream

This module defines the relationship between industry segments and applicable process types.
When a user selects a segment, only relevant process types are shown.
"""

# Industry Segments
SEGMENTS = {
    "upstream": {
        "display_name": "Upstream",
        "description": "Exploration, drilling, production operations",
        "icon": "⛽"
    },
    "midstream": {
        "display_name": "Midstream",
        "description": "Gathering, processing, transmission, storage",
        "icon": "🔄"
    },
    "downstream": {
        "display_name": "Downstream",
        "description": "Refining, petrochemical, distribution, marketing",
        "icon": "🏭"
    }
}

# Process Types with Segment Applicability
# When user selects a segment, show only these process types
PROCESS_TYPES = {
    # ========== COMBUSTION & FLARING (All Segments) ==========
    "stationary_combustion": {
        "display_name": "Stationary Combustion",
        "segments": ["upstream", "midstream", "downstream"],
        "category": "combustion",
        "calculation_method": "fuel_combustion",
        "api_section": "Section 5.1",
        "required_inputs": ["fuel_type", "amount", "unit", "hhv"],
        "description": "Emissions from stationary fuel combustion sources"
    },
    "flaring": {
        "display_name": "Flaring",
        "segments": ["upstream", "midstream", "downstream"],
        "category": "combustion",
        "calculation_method": "flaring_dual_efficiency",
        "api_section": "Section 5.2",
        "required_inputs": ["volume", "gas_composition", "flare_type"],
        "equations": ["API_5_3", "API_5_4"],
        "description": "Gas flaring with dual-efficiency model"
    },
    "mobile_combustion": {
        "display_name": "Mobile Combustion",
        "segments": ["upstream", "midstream", "downstream"],
        "category": "combustion",
        "calculation_method": "fuel_combustion",
        "api_section": "Section 5.1",
        "required_inputs": ["fuel_type", "amount", "unit"],
        "description": "Emissions from mobile sources (vehicles, equipment)"
    },
    
    # ========== UPSTREAM PROCESSES ==========
    "drilling": {
        "display_name": "Drilling - Mud Degassing",
        "segments": ["upstream"],
        "category": "vented",
        "calculation_method": "mud_degassing",
        "api_section": "Section 6.2",
        "required_inputs": ["mud_type", "mud_volume"],
        "description": "CH₄ emissions from drilling mud degassing"
    },
    "completions": {
        "display_name": "Well Completions & Workovers",
        "segments": ["upstream"],
        "category": "vented",
        "calculation_method": "completion_flowback",
        "api_section": "Section 6.3",
        "required_inputs": ["duration", "flow_rate", "control_efficiency"],
        "description": "Flowback emissions during well completion"
    },
    "liquids_unloading": {
        "display_name": "Liquids Unloading",
        "segments": ["upstream"],
        "category": "vented",
        "calculation_method": "unloading_volume",
        "api_section": "Section 6.4",
        "required_inputs": ["frequency", "wellbore_diameter", "depth", "pressure"],
        "description": "Gas venting during liquids unloading operations"
    },
    "wellhead_fugitive": {
        "display_name": "Wellhead Fugitive Emissions",
        "segments": ["upstream"],
        "category": "fugitive",
        "calculation_method": "equipment_factor",
        "api_section": "Section 7.2.2",
        "required_inputs": ["well_count", "production_type"],
        "description": "Equipment leaks from wellheads (oil/gas)"
    },
    "separator_fugitive": {
        "display_name": "Separator Fugitive Emissions",
        "segments": ["upstream"],
        "category": "fugitive",
        "calculation_method": "equipment_factor",
        "api_section": "Section 7.2.2",
        "required_inputs": ["separator_count", "separator_type"],
        "description": "Equipment leaks from separators"
    },
    "storage_tanks": {
        "display_name": "Storage Tanks",
        "segments": ["upstream", "midstream"],
        "category": "vented",
        "calculation_method": "tank_flashing",
        "api_section": "Section 6.8",
        "required_inputs": ["liquid_type", "throughput", "tank_size"],
        "description": "Flash emissions from crude oil and condensate storage"
    },
    "pneumatic_devices": {
        "display_name": "Pneumatic Devices",
        "segments": ["upstream", "midstream"],
        "category": "vented",
        "calculation_method": "equipment_factor",
        "api_section": "Section 6.10",
        "required_inputs": ["device_type", "device_count", "gas_content"],
        "description": "Pneumatic controllers and pumps"
    },
    "blowdown": {
        "display_name": "Blowdown Events",
        "segments": ["upstream", "midstream", "downstream"],
        "category": "vented",
        "calculation_method": "blowdown_volume",
        "api_section": "Section 6.4",
        "required_inputs": ["blowdown_volume", "blowdown_pressure"],
        "description": "Depressurization of vessels or pipelines"
    },
    
    # ========== MIDSTREAM PROCESSES ==========
    "gathering_boosting": {
        "display_name": "Gathering & Boosting",
        "segments": ["midstream"],
        "category": "fugitive",
        "calculation_method": "equipment_or_component",
        "api_section": "Section 7.2.3",
        "required_inputs": ["equipment_counts"],
        "description": "Fugitive emissions from gathering and boosting facilities"
    },
    "gas_processing": {
        "display_name": "Natural Gas Processing",
        "segments": ["midstream"],
        "category": "fugitive",
        "calculation_method": "equipment_or_component",
        "api_section": "Section 7.3",
        "required_inputs": ["equipment_counts", "processing_capacity"],
        "description": "Emissions from gas processing plants"
    },
    "dehydrator": {
        "display_name": "Glycol Dehydrator",
        "segments": ["midstream"],
        "category": "vented",
        "calculation_method": "dehydrator_specific",
        "api_section": "Section 6.11",
        "required_inputs": ["throughput", "ch4_content", "control_device"],
        "description": "CH₄ emissions from glycol dehydrators"
    },
    "acid_gas_removal": {
        "display_name": "Acid Gas Removal (AGR)",
        "segments": ["midstream"],
        "category": "vented",
        "calculation_method": "agr_specific",
        "api_section": "Section 6.12",
        "required_inputs": ["gas_throughput", "co2_content", "removal_efficiency"],
        "description": "CO₂ venting from AGR units"
    },
    "transmission_storage": {
        "display_name": "Transmission & Storage",
        "segments": ["midstream"],
        "category": "fugitive",
        "calculation_method": "equipment_or_pipeline",
        "api_section": "Section 7.4",
        "required_inputs": ["pipeline_length", "equipment_counts"],
        "description": "Fugitive emissions from transmission and storage"
    },
    "compressor_fugitive": {
        "display_name": "Compressor Fugitive Emissions",
        "segments": ["midstream"],
        "category": "fugitive",
        "calculation_method": "equipment_factor",
        "api_section": "Section 7.2.2, 7.2.3",
        "required_inputs": ["compressor_count", "compressor_type"],
        "description": "Equipment leaks from compressors"
    },
    
    # ========== DOWNSTREAM PROCESSES ==========
    "refinery_fugitive": {
        "display_name": "Refinery Gas Systems",
        "segments": ["downstream"],
        "category": "fugitive",
        "calculation_method": "component_or_equipment",
        "api_section": "Section 7.4.1",
        "required_inputs": ["component_counts", "service_type"],
        "description": "Fugitive emissions from refinery gas systems"
    },
    "distribution_fugitive": {
        "display_name": "Natural Gas Distribution",
        "segments": ["downstream"],
        "category": "fugitive",
        "calculation_method": "pipeline_factor",
        "api_section": "Section 7.6",
        "required_inputs": ["pipeline_length", "pipeline_material"],
        "description": "Fugitive emissions from distribution pipelines"
    },
    "lng_operations": {
        "display_name": "LNG Operations",
        "segments": ["downstream"],
        "category": "fugitive",
        "calculation_method": "equipment_factor",
        "api_section": "Section 7.3.6",
        "required_inputs": ["equipment_counts"],
        "description": "Fugitive emissions from LNG facilities"
    },
    "chemical_production": {
        "display_name": "Chemical Production (Process CO₂)",
        "segments": ["downstream"],
        "category": "process",
        "calculation_method": "production_factor",
        "api_section": "Section 6 (Table 6-167)",
        "required_inputs": ["chemical_type", "production_amount"],
        "description": "Process CO₂ from chemical manufacturing",
        "available_chemicals": [
            "acrylonitrile", "carbon_black", "ethylene", 
            "ethylene_dichloride", "ethylene_oxide", "methanol"
        ]
    },
    "nitric_acid_production": {
        "display_name": "Nitric Acid Production (N₂O)",
        "segments": ["downstream"],
        "category": "process",
        "calculation_method": "production_factor_n2o",
        "api_section": "Section 6 (pg 407)",
        "required_inputs": ["production_amount", "abatement_type"],
        "description": "N₂O emissions from nitric acid production"
    },
    "adipic_acid_production": {
        "display_name": "Adipic Acid Production (N₂O)",
        "segments": ["downstream"],
        "category": "process",
        "calculation_method": "production_factor_n2o",
        "api_section": "Section 6 (pg 407)",
        "required_inputs": ["production_amount", "abatement_type"],
        "description": "N₂O emissions from adipic acid production"
    },
    
    # ========== FUGITIVE - COMPONENT LEVEL (All Segments) ==========
    "fugitive_component": {
        "display_name": "Fugitive - Component Level",
        "segments": ["upstream", "midstream", "downstream"],
        "category": "fugitive",
        "calculation_method": "component_screening_or_average",
        "api_section": "Section 7 (Tables 7-1 to 7-8)",
        "required_inputs": ["component_type", "count_or_ppm", "service_type"],
        "description": "Component-level fugitive emissions (valves, connectors, flanges, etc.)"
    }
}

# Category Definitions
CATEGORIES = {
    "combustion": {
        "display_name": "Combustion",
        "icon": "🔥",
        "color": "#FF6B35"
    },
    "vented": {
        "display_name": "Vented Emissions",
        "icon": "💨",
        "color": "#4ECDC4"
    },
    "fugitive": {
        "display_name": "Fugitive Emissions",
        "icon": "💧",
        "color": "#95E1D3"
    },
    "process": {
        "display_name": "Process Emissions",
        "icon": "⚗️",
        "color": "#FFE66D"
    }
}

# Helper function to get process types for a segment
def get_process_types_for_segment(segment):
    """
    Returns all process types applicable to the given segment.
    
    Args:
        segment (str): One of 'upstream', 'midstream', 'downstream'
    
    Returns:
        dict: Filtered process types dictionary
    """
    if segment not in SEGMENTS:
        return {}
    
    return {
        process_id: process_data
        for process_id, process_data in PROCESS_TYPES.items()
        if segment in process_data["segments"]
    }

# Helper function to get all segments where a process type is applicable
def get_segments_for_process(process_type):
    """
    Returns all segments where the given process type is applicable.
    
    Args:
        process_type (str): Process type ID
    
    Returns:
        list: List of applicable segment IDs
    """
    if process_type not in PROCESS_TYPES:
        return []
    
    return PROCESS_TYPES[process_type]["segments"]

# Helper function to organize process types by category
def get_process_types_by_category(segment=None):
    """
    Returns process types organized by category, optionally filtered by segment.
    
    Args:
        segment (str, optional): Filter by segment
    
    Returns:
        dict: Process types organized by category
    """
    processes = get_process_types_for_segment(segment) if segment else PROCESS_TYPES
    
    organized = {cat_id: [] for cat_id in CATEGORIES}
    
    for process_id, process_data in processes.items():
        category = process_data.get("category", "other")
        if category in organized:
            organized[category].append({
                "id": process_id,
                "display_name": process_data["display_name"],
                "description": process_data.get("description", "")
            })
    
    return {k: v for k, v in organized.items() if v}  # Remove empty categories
