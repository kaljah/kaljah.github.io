"""
Independent Reference Model Package
Clean-slate implementation - ZERO production dependencies.
"""

from .ref_constants import (
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    DENSITY_CH4,
    DENSITY_CO2,
    DENSITY_N2O,
    resolve_gwp,
)
from .ref_combustion import (
    ref_normalize_gas_volume,
    ref_calculate_combustion,
)
from .ref_flaring import ref_calculate_flaring
from .ref_venting import (
    ref_calculate_pneumatic_devices,
    ref_calculate_blowdown,
    ref_calculate_tank_flashing,
)
from .ref_midstream import ref_calculate_agr, ref_calculate_dehydrator
from .ref_fugitives import (
    ref_calculate_component_fugitives,
    ref_calculate_equipment_fugitives,
)
from .ref_scope2 import (
    ref_calculate_scope2_electricity,
    ref_calculate_scope2_steam,
    ref_calculate_scope2_cooling,
)
from .ref_scope3 import ref_calculate_scope3, SCOPE3_CATEGORIES
from .ref_stoichiometry import ref_calculate_hydrocarbon_stoichiometry
from .ref_uncertainty import (
    ref_propagate_product_uncertainty,
    ref_propagate_sum_uncertainty,
)
from .ref_intensity import (
    ref_calculate_carbon_intensity,
    ref_calculate_methane_loss_rate,
    ref_evaluate_ogmp_level,
)

__all__ = [
    "STD_TEMP_K",
    "STD_PRESSURE_PSIA",
    "DENSITY_CH4",
    "DENSITY_CO2",
    "DENSITY_N2O",
    "resolve_gwp",
    "ref_normalize_gas_volume",
    "ref_calculate_combustion",
    "ref_calculate_flaring",
    "ref_calculate_pneumatic_devices",
    "ref_calculate_blowdown",
    "ref_calculate_tank_flashing",
    "ref_calculate_agr",
    "ref_calculate_dehydrator",
    "ref_calculate_component_fugitives",
    "ref_calculate_equipment_fugitives",
    "ref_calculate_scope2_electricity",
    "ref_calculate_scope2_steam",
    "ref_calculate_scope2_cooling",
    "ref_calculate_scope3",
    "SCOPE3_CATEGORIES",
    "ref_calculate_hydrocarbon_stoichiometry",
    "ref_propagate_product_uncertainty",
    "ref_propagate_sum_uncertainty",
    "ref_calculate_carbon_intensity",
    "ref_calculate_methane_loss_rate",
    "ref_evaluate_ogmp_level",
]
