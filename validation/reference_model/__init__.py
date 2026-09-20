"""
Independent Reference Calculation Model.
Implemented strictly from published standards (API Compendium 2021, IPCC 2006, ISO 14064-1, EPA Subpart W).
This package does NOT import or reference production calculation modules.
"""
from .unit_conversions import IndependentUnitConverter, normalize_to_standard_volume
from .gwp import IndependentGWPModel
from .combustion_flaring import IndependentCombustionModel, IndependentFlaringModel
from .vented_processes import (
    IndependentVentedPartition,
    IndependentMudDegassing,
    IndependentCompletions,
    IndependentLiquidsUnloading,
    IndependentBlowdown,
    IndependentStorageTanks,
    IndependentPneumatics,
)
from .fugitives import IndependentFugitiveModel
from .midstream import IndependentAGRModel, IndependentDehydratorModel, IndependentStoichiometryModel
from .scope2 import IndependentScope2Model
from .scope3 import IndependentScope3Model
from .uncertainty import IndependentUncertaintyModel
from .aggregation_intensity import IndependentIntensityModel
from .ogmp import IndependentOGMPModel
