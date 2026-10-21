"""
API Compendium 2021 - Section 6: Midstream & Process Emissions
Implementation of Acid Gas Removal (AGR / Amine Units) with Table 6-5 Methane Slip,
and glycol dehydrators by API Compendium Table 6-17.
"""

from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e, convert, normalize_efficiency
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty


class AGRCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Acid Gas Removal", "Section 6.5")

    def calculate(
        self,
        throughput,
        co2_in,
        co2_out=0.0,
        uncertainties=None,
        ch4_in=0.85,
        ch4_slip_fraction=0.001,
        acid_gas_control_eff=0.0,
        acid_gas_control_type="vent",
        gwp_dict=None,
    ):
        """
        API Compendium 2021 §6.5 & Table 6-5:
        - CO2 mass balance from amine sweetening process
        - CH4 physical co-absorption and slip from regenerator overhead

        Parameters:
        - throughput: Gas throughput in MMscf/yr
        - co2_in: Native CO2 mole fraction entering unit (e.g. 0.04 for 4%)
        - co2_out: Treated gas CO2 mole fraction (e.g. 0.0005 for 50 ppm)
        - ch4_in: Methane mole fraction in feed gas (e.g. 0.85)
        - ch4_slip_fraction: Methane slip fraction per API Table 6-5 (default 0.001 = 0.1%)
        - acid_gas_control_eff: Destruction/recovery efficiency (e.g. 0.98 for Claus/thermal oxidizer)
        - acid_gas_control_type: Control technology ('vent', 'agi', 'ccus', 'claus', 'thermal_oxidizer', 'flare')
        """
        uncertainties = uncertainties or {}
        self.validate_inputs(
            {"throughput": throughput, "co2_in": co2_in}, ["throughput", "co2_in"]
        )

        # Throughput in scf
        tp = float(throughput)  # >= 0 (validate_inputs)
        throughput_scf = tp * 1_000_000.0

        # 1. CO2 Mass Balance Venting with Contactor Shrinkage Correction (API Compendium 2021 Eq. 6-7)
        s_cin = str(co2_in or 0.0).replace("%", "").strip()
        s_cout = str(co2_out or 0.0).replace("%", "").strip()
        cin = float(s_cin)
        cout = float(s_cout)
        if cin < 0.0 or cout < 0.0:
            raise ValueError("CO2 concentrations cannot be negative")
        in_pct = ("%" in str(co2_in) or "%" in str(co2_out) or cin > 1.0 or cout > 1.0)
        if in_pct:
            cin /= 100.0
            cout /= 100.0
        if cin > 1.0 or cout > 1.0:
            raise ValueError("CO2 concentration cannot exceed 100 %")
        diff_co2 = max(0.0, cin - cout)
        if cout >= 1.0:
            raise ValueError("Outlet CO2 must be below 100 %")
        # Eq 6-18 is V_in*y_in - V_out*y_out; the outlet stream is smaller than the inlet by the CO2
        # removed, V_out = V_in*(1 - y_in)/(1 - y_out), so the balance is V_in*(y_in - y_out)/(1 - y_out).
        # Using V_in for both streams left out that shrinkage (Exhibit 6-17: 78,925 t instead of 80,506 t)
        co2_vented_scf = throughput_scf * diff_co2 / (1.0 - cout)
        co2_vented_m3 = convert(co2_vented_scf, "scf", "m3")
        co2_mass_kg = co2_vented_m3 * CONVERSIONS["density_co2"]

        # 2. CH4: a measured slip (fraction of the inlet CH4) when given; otherwise the API Compendium
        # Table 6-19 AGR vent factor, 0.0185 tonne CH4 per 10^6 scf treated (Exhibit 6-17). The former
        # 0.1 % default had no source.
        if ch4_slip_fraction is not None:
            s_slip = str(ch4_slip_fraction).strip()
            is_pct = "%" in s_slip
            slip_rate = float(s_slip.replace("%", "").strip())
            if is_pct:
                slip_rate /= 100.0
            if not (0.0 <= slip_rate <= 1.0):
                raise ValueError("CH4 slip is a fraction of the inlet CH4 (0-1)")
            c_ch4 = max(0.0, float(str(ch4_in if ch4_in is not None else 0.85).replace("%", "").strip()))
            if c_ch4 > 1.0:
                c_ch4 /= 100.0
            ch4_slipped_m3 = convert(throughput_scf * c_ch4 * slip_rate, "scf", "m3")
            ch4_mass_kg = ch4_slipped_m3 * CONVERSIONS["density_ch4"]
        else:
            slip_rate = None
            ch4_mass_kg = throughput_scf / 1e6 * 0.0185 * 1000.0

        # Apply acid gas control technology
        ctrl_eff = normalize_efficiency(acid_gas_control_eff, default=0.0)
        ctype = str(acid_gas_control_type or "vent").strip().lower()

        if ctype in ["agi", "ccus", "injection", "sequestration"]:
            # Acid Gas Injection (AGI) / Carbon Capture: sequesters both CO2 and slipped CH4
            co2_emitted_kg = co2_mass_kg * (1.0 - ctrl_eff)
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl_eff)
        elif ctype in ["claus", "thermal_oxidizer", "incinerator", "flare", "combustor"]:
            # Thermal destruction / Claus SRU: destroys slipped CH4 to CO2, but native stripped CO2 passes through
            ch4_destroyed_kg = ch4_mass_kg * ctrl_eff
            combusted_co2_kg = ch4_destroyed_kg * (44.01 / 16.04)
            co2_emitted_kg = co2_mass_kg + combusted_co2_kg
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl_eff)
        else:
            # Uncontrolled vent or unspecified: if control efficiency is provided, treat as capture/abatement
            co2_emitted_kg = co2_mass_kg * (1.0 - ctrl_eff)
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl_eff)

        co2_tonnes = co2_emitted_kg / 1000.0
        ch4_tonnes = ch4_emitted_kg / 1000.0

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        co2_res = propagate_uncertainty(
            co2_tonnes,
            resolve_ef_uncertainty("midstream", "co2", _tier, uncertainties.get("co2")),
            tier=_tier,
            process_category="midstream",
            gas="co2",
        )
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            resolve_ef_uncertainty("midstream", "ch4", _tier, uncertainties.get("ch4")),
            tier=_tier,
            process_category="midstream",
            gas="ch4",
        )
        n2o_res = None

        total_co2e = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_mmscf": throughput,
                "co2_in_pct": cin * 100.0,
                "co2_out_pct": cout * 100.0,
                "ch4_slip_pct": slip_rate * 100.0 if slip_rate is not None else None,
                "control_eff_pct": ctrl_eff * 100.0,
            },
            metadata={
                "standard_reference": "API Compendium 2021 §6.5 & Table 6-5",
                "ch4_slip_calculated": True,
            },
        )


class DehydratorCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Glycol Dehydrator", "Section 6.3.8.1")

    def calculate(self, throughput=None, pump_rate=None, ch4_content=None, control_eff=0.0, uncertainties=None,
                  gwp_dict=None, **kwargs):
        """API Compendium 2021 Table 6-17: uncontrolled glycol dehydration, 0.0052859 t CH4 per 10^6 scf
        processed at 78.8 mol % CH4, scaled to the site CH4 content (Exhibit 6-13)."""
        uncertainties = uncertainties or {}

        # 1. Check if Tier 1 (Default Emission Factor based on throughput alone)
        tp = throughput if throughput is not None else kwargs.get("gas_throughput")
        if (pump_rate is None or float(pump_rate or 0) <= 0) and tp is not None:  # Tier 1
            # API Compendium 2021 Table 6-17 (production segment, uncontrolled glycol dehydration, excludes
            # gas-assisted pump emissions): 0.0052859 t CH4 / 10^6 scf processed at 78.8 mol % CH4;
            # scaled by the site CH4 content (Exhibit 6-13). The former 0.266 t/MMscf had no source.
            tp_mmscf = float(tp)
            if tp_mmscf < 0:
                raise ValueError("Throughput cannot be negative")
            eff = normalize_efficiency(control_eff, default=0.0)
            s_c = str(ch4_content if ch4_content is not None else 0.788).replace("%", "").strip()
            c = float(s_c)
            if c < 0:
                raise ValueError("CH4 content cannot be negative")
            if (ch4_content is not None and "%" in str(ch4_content)) or c > 1.0:
                c /= 100.0
            if c > 1.0:
                raise ValueError("CH4 content cannot exceed 100 %")
            default_ef = 0.0052859 * (c / 0.788) * (1.0 - eff)
            ch4_tonnes = tp_mmscf * default_ef

            _tier = resolve_tier("default")
            ch4_res = propagate_uncertainty(
                ch4_tonnes,
                resolve_ef_uncertainty(
                    "midstream", "ch4", _tier, uncertainties.get("ch4")
                ),
                tier=_tier,
                process_category="midstream",
                gas="ch4",
            )
            total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)

            return self.format_result(
                ch4=ch4_res,
                total_co2e=total_co2e,
                inputs={
                    "throughput_mmscf": tp_mmscf,
                    "tier": "Tier 1 (Default Factor)",
                },
                metadata={
                    "method": "API Compendium 2021 Table 6-17 (uncontrolled glycol dehydration)"
                },
            )

        # A glycol circulation rate has no API Compendium method (section 6.3.8.1: Tables 6-17 / 6-18, a
        # GRI-GLYCalc simulation or a measured vent). The parametric solubility model that was here
        # (0.0032 x P^0.96 x ...) has no published source; the dispatcher already refused its inputs.
        raise ValueError("Glycol dehydrator: enter the gas throughput (Table 6-17), or the measured vent volume or "
                         "GLYCalc result; a glycol circulation rate has no API Compendium method")
