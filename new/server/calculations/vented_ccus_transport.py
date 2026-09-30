"""
API Compendium 2021 - Sections 6.9 & 6.10: CCUS, EOR & Crude Oil Transport
Vented and Process Emissions Calculation Modules

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021:
- §6.9 Enhanced Oil Recovery, Carbon Capture, and Geological Storage:
    * §6.9.1 Enhanced Oil Recovery (references §6.3.10)
    * §6.9.2 Carbon Capture (Stripper off-gas venting, slip, solvent regeneration)
    * §6.9.3 Geological Storage (Wellhead depressurization, injection system vents)
- §6.10 Crude Oil Transport:
    * §6.10.1 Loading Loss Emissions – Truck, Rail, and Marine (Table 6-47, Exhibit 6-35)
    * §6.10.2 Marine Ballasting Emissions (Table 6-48, Exhibit 6-36)
    * §6.10.3 Marine Transit Loss Emissions (Table 6-49, Exhibit 6-37)
"""

import math
from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    STD_PRESSURE_PSIA,
    convert,
    calculate_co2e,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)

MOLAR_VOL_US = 379.3   # scf / lb-mole
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_N2O = 44.013
LB_PER_TONNE = 2204.6226218487757


def _split_vent_flare(total_gas_m3, ch4_tonnes, co2_tonnes, ctrl_eff=0.0, hhv=1020.0, ef_n2o=None):
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

        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (MW_CO2 / MW_CH4)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

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


def _propagate_results(total_ch4, total_co2, flared_n2o, uncertainties, factor_source="default", category="vented"):
    _tier = resolve_tier(factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=category,
        gas="ch4",
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            flared_n2o,
            resolve_ef_uncertainty(category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


# ==============================================================================
# §6.9 Carbon Capture, Utilization and Storage (CCUS)
# ==============================================================================
class CCUSVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.9 - CCUS & Geological Storage Vented Emissions
    Covers:
      - Carbon capture facility stripper off-gas venting:
          Accounts for uncaptured CO2 and CH4 slip through the capture absorber/stripper vent stack.
      - Supercritical CO2 injection wellhead blowdowns (Equation 6-27):
          Depressurization of storage wellhead manifolds and surface piping.
      - Geological storage monitoring / measurement vent releases.
    """

    def __init__(self):
        super().__init__("CCUS Vented Emissions", "Section 6.9")

    def calculate(
        self,
        activity="stripper_vent",  # "stripper_vent", "wellhead_blowdown", "monitoring_vent"
        # Stripper off-gas inputs
        inlet_co2_tonnes=None,
        capture_efficiency=0.90,       # capture rate, e.g. 90% (10% vented)
        ch4_slip_tonnes=0.0,
        # Wellhead blowdown inputs (Equation 6-27)
        events=1.0,
        physical_volume_m3=None,
        co2_density_kg_m3=650.0,
        co2_weight_fraction=0.985,
        # Direct measured vent volume
        vented_co2_tonnes=None,
        vented_ch4_tonnes=0.0,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "stripper_vent").lower().strip()

        gross_co2_tonnes = 0.0
        gross_ch4_tonnes = 0.0

        if act == "stripper_vent":
            if vented_co2_tonnes is not None:
                gross_co2_tonnes = float(vented_co2_tonnes)
                gross_ch4_tonnes = float(vented_ch4_tonnes or 0.0)
            elif inlet_co2_tonnes is not None:
                inlet = float(inlet_co2_tonnes)
                eff = normalize_efficiency(capture_efficiency, default=0.90)
                # Uncaptured CO2 vented through stripper/absorber stack
                gross_co2_tonnes = inlet * (1.0 - eff)
                gross_ch4_tonnes = float(ch4_slip_tonnes or 0.0)
            else:
                raise ValueError("inlet_co2_tonnes or vented_co2_tonnes must be provided for stripper_vent")

        elif act == "wellhead_blowdown":
            self.validate_inputs({"physical_volume_m3": physical_volume_m3}, ["physical_volume_m3"])
            n = max(0.0, float(1.0 if events is None else events))
            v_m3 = float(physical_volume_m3)
            rho = float(co2_density_kg_m3 if co2_density_kg_m3 is not None else 650.0)
            wt_frac = float(co2_weight_fraction if co2_weight_fraction is not None else 0.985)
            if wt_frac > 1.0:
                wt_frac /= 100.0

            gross_co2_tonnes = n * v_m3 * rho * wt_frac * 0.001
            gross_ch4_tonnes = 0.0

        else:
            gross_co2_tonnes = float(vented_co2_tonnes or 0.0)
            gross_ch4_tonnes = float(vented_ch4_tonnes or 0.0)

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=gross_ch4_tonnes,
            total_co2=gross_co2_tonnes,
            flared_n2o=0.0,
            uncertainties=uncertainties,
            factor_source="API_Section_6.9",
            category="ccus_venting",
        )

        total_co2e = calculate_co2e(ch4=gross_ch4_tonnes, co2=gross_co2_tonnes, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "gross_co2_tonnes": gross_co2_tonnes, "gross_ch4_tonnes": gross_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.9"},
        )


# ==============================================================================
# §6.10 Crude Oil Transport Losses
# ==============================================================================
class CrudeTransportLossesCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.10 - Crude Oil Transport
    Supports:
      - 6.10.1 Loading Losses (Table 6-47 & Exhibit 6-35):
          * Rail/Truck submerged dedicated: 0.91 tonne TOC / 10^6 gal loaded (2 lb/10^3 gal)
          * Rail/Truck submerged vapor balance: 1.51 tonne TOC / 10^6 gal loaded (3 lb/10^3 gal)
          * Rail/Truck splash dedicated: 2.20 tonne TOC / 10^6 gal loaded (5 lb/10^3 gal)
          * Rail/Truck splash vapor balance: 1.51 tonne TOC / 10^6 gal loaded (3 lb/10^3 gal)
          * Marine ships / ocean barges: 0.28 tonne TOC / 10^6 gal loaded (0.61 lb/10^3 gal)
          * Marine barges: 0.45 tonne TOC / 10^6 gal loaded (1.0 lb/10^3 gal)
      - 6.10.2 Marine Ballasting Operations (Table 6-48 & Exhibit 6-36):
          * Fully loaded: 0.420 tonne TOC / 10^6 gal ballast (0.9 lb/10^3 gal)
          * Lightered: 0.647 tonne TOC / 10^6 gal ballast (1.4 lb/10^3 gal)
          * Typical overall: 0.488 tonne TOC / 10^6 gal ballast (1.1 lb/10^3 gal)
      - 6.10.3 Marine Transit Losses (Table 6-49 & Exhibit 6-37):
          * Crude oil marine transit: 0.57 tonne TOC / (week * 10^6 gal transported)
    Verified against Exhibits 6-35, 6-36, and 6-37.
    """

    TABLE_6_47_LOADING = {
        "submerged_dedicated": {"tonne_toc_per_mmgal": 0.91, "lb_toc_per_mgal": 2.0},
        "submerged_vapor_balance": {"tonne_toc_per_mmgal": 1.51, "lb_toc_per_mgal": 3.0},
        "splash_dedicated": {"tonne_toc_per_mmgal": 2.20, "lb_toc_per_mgal": 5.0},
        "splash_vapor_balance": {"tonne_toc_per_mmgal": 1.51, "lb_toc_per_mgal": 3.0},
        "marine_ships": {"tonne_toc_per_mmgal": 0.28, "lb_toc_per_mgal": 0.61},
        "marine_barges": {"tonne_toc_per_mmgal": 0.45, "lb_toc_per_mgal": 1.0},
    }

    TABLE_6_48_BALLASTING = {
        "fully_loaded": {"tonne_toc_per_mmgal": 0.420, "lb_toc_per_mgal": 0.9},
        "lightered": {"tonne_toc_per_mmgal": 0.647, "lb_toc_per_mgal": 1.4},
        "typical": {"tonne_toc_per_mmgal": 0.488, "lb_toc_per_mgal": 1.1},
    }

    TABLE_6_49_TRANSIT = {
        "crude_marine": {"tonne_toc_per_week_mmgal": 0.57},
    }

    def __init__(self):
        super().__init__("Crude Oil Transport Losses", "Section 6.10")

    def calculate(
        self,
        activity="loading",  # "loading", "ballasting", "transit"
        # Loading inputs (Exhibit 6-35)
        loading_service="splash_dedicated",  # from TABLE_6_47_LOADING keys
        volume_loaded_bbl=None,
        volume_loaded_gal=None,
        ch4_weight_pct=12.0,  # wt% of TOC that is CH4 (default 12% in Exhibit 6-35, or 15% AP-42)
        # Ballasting inputs (Exhibit 6-36)
        ballast_condition="typical",  # "fully_loaded", "lightered", "typical"
        ballast_water_bbl=None,
        ballast_water_gal=None,
        # Transit inputs (Exhibit 6-37)
        volume_transported_bbl=None,
        trip_duration_days=10.0,
        trips_per_year=1.0,
        # Control & routing
        control_efficiency=0.0,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "loading").lower().strip()

        gross_ch4_tonnes = 0.0
        total_toc_tonnes = 0.0

        wt_ch4 = float(ch4_weight_pct if ch4_weight_pct is not None else 15.0)
        if wt_ch4 > 1.0:
            wt_ch4 /= 100.0

        # ----------------------------------------------------------------------
        # Case 1: Loading Losses (Exhibit 6-35)
        # ----------------------------------------------------------------------
        if act == "loading":
            if volume_loaded_gal is not None:
                gal = float(volume_loaded_gal)
            elif volume_loaded_bbl is not None:
                gal = float(volume_loaded_bbl) * 42.0
            else:
                raise ValueError("volume_loaded_bbl or volume_loaded_gal must be provided")

            ltype = str(loading_service or "splash_dedicated").lower().strip()
            factor_info = self.TABLE_6_47_LOADING.get(ltype, self.TABLE_6_47_LOADING["splash_dedicated"])

            # E_TOC = (gal / 1e6) * EF_tonne_toc
            total_toc_tonnes = (gal / 1_000_000.0) * factor_info["tonne_toc_per_mmgal"]
            gross_ch4_tonnes = total_toc_tonnes * wt_ch4

        # ----------------------------------------------------------------------
        # Case 2: Ballasting Losses (Exhibit 6-36)
        # ----------------------------------------------------------------------
        elif act == "ballasting":
            if ballast_water_gal is not None:
                gal = float(ballast_water_gal)
            elif ballast_water_bbl is not None:
                gal = float(ballast_water_bbl) * 42.0
            else:
                raise ValueError("ballast_water_bbl or ballast_water_gal must be provided")

            bcond = str(ballast_condition or "typical").lower().strip()
            factor_info = self.TABLE_6_48_BALLASTING.get(bcond, self.TABLE_6_48_BALLASTING["typical"])

            # Exhibit 6-36 uses Table 6-48: 0.488 tonne TOC / 10^6 gal
            total_toc_tonnes = (gal / 1_000_000.0) * factor_info["tonne_toc_per_mmgal"]
            gross_ch4_tonnes = total_toc_tonnes * wt_ch4

        # ----------------------------------------------------------------------
        # Case 3: Marine Transit Losses (Exhibit 6-37)
        # ----------------------------------------------------------------------
        elif act == "transit":
            self.validate_inputs({"volume_transported_bbl": volume_transported_bbl}, ["volume_transported_bbl"])
            gal = float(volume_transported_bbl) * 42.0
            d_days = float(trip_duration_days or 7.0)
            n_trips = max(1.0, float(trips_per_year or 1.0))
            weeks_per_trip = d_days / 7.0

            # Exhibit 6-37: 0.57 tonnes TOC / (week * 10^6 gal) * (gal / 1e6) * (days / 7) * trips * wt_ch4
            ef_transit = self.TABLE_6_49_TRANSIT["crude_marine"]["tonne_toc_per_week_mmgal"]
            total_toc_tonnes = ef_transit * (gal / 1_000_000.0) * weeks_per_trip * n_trips
            gross_ch4_tonnes = total_toc_tonnes * wt_ch4

        ctrl = normalize_efficiency(control_efficiency, default=0.0)
        net_ch4_tonnes = gross_ch4_tonnes * (1.0 - ctrl)

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=net_ch4_tonnes,
            total_co2=0.0,
            flared_n2o=0.0,
            uncertainties=uncertainties,
            factor_source="API_Section_6.10",
            category="crude_transport",
        )

        total_co2e = calculate_co2e(ch4=net_ch4_tonnes, co2=0.0, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "total_toc_tonnes": total_toc_tonnes, "net_ch4_tonnes": net_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.10", "tables": "Table 6-47, Table 6-48, Table 6-49"},
        )
