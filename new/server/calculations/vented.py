"""
API Compendium 2021 - Section 6: Vented and Process Emissions
Implementation of equations for mud degassing, completions, liquids unloading, 
blowdowns (with thermodynamic T & P corrections), tanks, and pneumatics.
"""

from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    calculate_co2e,
    convert,
    to_psia,
    to_kelvin,
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
    Tier,
)
import math




from .vented_production import _split_vent_flare  # noqa: E402  (one flare split)
_split_vented_and_flared = _split_vent_flare


def _propagate_vented_results(
    total_ch4: float,
    total_co2: float,
    flared_n2o: float,
    uncertainties: dict,
    factor_source: str = "specific",
    process_category: str = "vented",
):
    _tier = resolve_tier(factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(process_category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=process_category,
        gas="ch4",
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(process_category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=process_category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            flared_n2o,
            resolve_ef_uncertainty(process_category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=process_category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res



# BlowdownCalculator, TankFlashingCalculator, PneumaticDeviceCalculator: canonical implementations in
# vented_production.py, re-exported at the end of this module (audit RC-17 dedupe)



# ==============================================================================
# Re-exports of all API Compendium 2021 Section 6 Modular Calculators
# ==============================================================================
from .vented_exploration import (
    WellTestingCalculator,
    CoalSeamDrillingCalculator,
)
from .vented_production import (
    # RC-17: single implementations (Tables 6-14/6-15, 6-22/6-24, Eq 6-32 / Table 6-32)
    PneumaticDeviceCalculator,
    TankFlashingCalculator,
    BlowdownCalculator,
    WorkoverWithoutFracturingCalculator,
    CasingGasVentCalculator,
    PneumaticPumpCalculator,
    GasDehydrationCalculator,
    AcidGasRemovalCalculator,
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
)
from .vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringStorageTankCalculator,
    GatheringNonRoutineVentingCalculator,
    ProcessingDehydrationCalculator,
    ProcessingBlanketedTankCalculator,
    ProcessingNonRoutineCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)
from .vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from .vented_ccus_transport import (
    CCUSVentingCalculator,
    CrudeTransportLossesCalculator,
)
from .vented_downstream import (
    RefiningCatalystRegenCalculator,
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    AsphaltBlowingCalculator,
    RefiningCokeCalciningCalculator,
    SulfurRecoveryTailGasCalculator,
    PetrochemicalManufacturingCalculator,
    FireSuppressionCalculator,
)


# Calculators split out of this file; imported last because they use the helpers above.
from .vented_unloading import LiquidsUnloadingCalculator  # noqa: E402,F401
from .vented_associated_gas import AssociatedGasVentingCalculator  # noqa: E402,F401
from .vented_completion import CompletionFlowbackCalculator  # noqa: E402,F401
from .vented_mud import MudDegassingCalculator  # noqa: E402,F401
