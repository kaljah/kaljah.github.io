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


def _split_vented_and_flared(
    total_gas_m3: float,
    ch4_tonnes: float,
    co2_tonnes: float,
    ctrl_eff: float,
    hhv: float = 1020.0,
    ef_n2o: float = None,
):
    """
    D-01 / API Compendium 2021 stoichiometric flaring partition helper.
    Partitions total gas into vented (1 - ctrl_eff) and flared (ctrl_eff).
    Flared combustion:
      - 98% CH4 converted to CO2 stoichiometrically: CH4 * 0.98 * (44.01 / 16.04)
      - Native CO2 in flared stream passes through unreacted
      - 2% unburnt CH4 emitted
      - N2O emitted = flared_mmbtu * (ef_n2o or 0.0001) where flared_scf = flared_m3 * (1 / scf_to_m3)
        and flared_mmbtu = flared_scf * (hhv or 1020.0) / 1e6.
        Catalog ef_n2o is in kg/MMBtu (default 0.0001 kg/MMBtu); convert to tonnes: / 1000.0.
    """
    ctrl = normalize_efficiency(ctrl_eff, default=0.0)
    vented_frac = 1.0 - ctrl

    vented_ch4 = ch4_tonnes * vented_frac
    vented_co2 = co2_tonnes * vented_frac

    flared_co2 = 0.0
    flared_unburnt_ch4 = 0.0
    flared_n2o = 0.0

    if ctrl > 0:
        flared_ch4_mass = ch4_tonnes * ctrl
        flared_native_co2 = co2_tonnes * ctrl

        # 98% combustion of CH4 to CO2
        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (44.01 / 16.04)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

        # N2O from energy of flared gas
        flared_m3 = total_gas_m3 * ctrl
        flared_scf = convert(flared_m3, "m3", "scf")
        hhv_val = float(hhv or 1020.0)
        flared_mmbtu = (flared_scf * hhv_val) / 1_000_000.0
        n2o_ef_kg = float(ef_n2o if ef_n2o is not None else 0.0001)
        flared_n2o = (flared_mmbtu * n2o_ef_kg) / 1000.0

    total_ch4 = vented_ch4 + flared_unburnt_ch4
    total_co2 = vented_co2 + flared_co2

    return {
        "vented_ch4": vented_ch4,
        "vented_co2": vented_co2,
        "flared_co2": flared_co2,
        "flared_unburnt_ch4": flared_unburnt_ch4,
        "flared_n2o": flared_n2o,
        "total_ch4": total_ch4,
        "total_co2": total_co2,
    }


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
