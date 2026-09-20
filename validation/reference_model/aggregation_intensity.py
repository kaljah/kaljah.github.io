"""
Independent Aggregation, Operational Intensities & Compliance Models.
Source of Truth: IOGP Report 2021e, UNEP OGMP 2.0, EPA 40 CFR Part 99 (IRA §136 WEC).
Zero production dependencies.
"""
from .unit_conversions import DENSITY_CH4_STD

GAS_TO_BOE_FACTOR = 0.178  # 1 Mscf (1,000 scf) ~ 0.178 BOE (approx. 5,618 scf/BOE)


class IndependentIntensityModel:
    @staticmethod
    def calculate_boe(oil_bbl, gas_mscf):
        o = float(oil_bbl or 0.0)
        g = float(gas_mscf or 0.0)
        return o + (g * GAS_TO_BOE_FACTOR)

    @staticmethod
    def calculate_carbon_intensity(total_co2e_tonnes, boe):
        b = float(boe or 0.0)
        if b <= 0.0:
            return 0.0
        return (float(total_co2e_tonnes or 0.0) * 1000.0) / b

    @staticmethod
    def calculate_methane_loss_rate(ch4_tonnes, gas_prod_m3):
        g = float(gas_prod_m3 or 0.0)
        if g <= 0.0:
            return 0.0
        ch4_vol_m3 = (float(ch4_tonnes or 0.0) * 1000.0) / DENSITY_CH4_STD
        return (ch4_vol_m3 / g) * 100.0

    @staticmethod
    def calculate_flaring_rate(flaring_vol_m3, gas_prod_m3):
        g = float(gas_prod_m3 or 0.0)
        if g <= 0.0:
            return 0.0
        return (float(flaring_vol_m3 or 0.0) / g) * 100.0

    @staticmethod
    def calculate_wec(ch4_tonnes, gas_prod_m3=0.0, oil_bbl=0.0, segment="upstream", year=2026):
        seg = str(segment or "upstream").lower()
        yr = int(year or 2026)

        if yr < 2024 or any(k in seg for k in ["downstream", "refining", "petrochem"]):
            return {"excess_ch4_tonnes": 0.0, "wec_rate": 0.0, "wec_fee_usd": 0.0, "status": "Exempt"}

        # Upstream target: 0.20% (0.0020); Midstream target: 0.05% (0.0005)
        threshold = 0.0005 if any(m in seg for m in ["processing", "midstream", "lng"]) else 0.0020
        g_m3 = float(gas_prod_m3 or 0.0)
        o_bbl = float(oil_bbl or 0.0)

        if g_m3 > 0:
            allowed_ch4_t = (g_m3 * threshold * DENSITY_CH4_STD) / 1000.0
        elif o_bbl > 0 and "upstream" in seg:
            # 40 CFR 99.20(a)(2): 10 metric tons CH4 per million barrels of oil
            allowed_ch4_t = (o_bbl / 1_000_000.0) * 10.0
        else:
            allowed_ch4_t = 0.0

        excess_t = max(0.0, float(ch4_tonnes or 0.0) - allowed_ch4_t)
        rate = 900.0 if yr == 2024 else (1200.0 if yr == 2025 else 1500.0)
        fee = round(excess_t * rate, 2)
        status = "Compliant" if excess_t <= 0 else "Taxable Liability"

        return {
            "allowed_ch4_tonnes": allowed_ch4_t,
            "excess_ch4_tonnes": excess_t,
            "wec_rate": rate,
            "wec_fee_usd": fee,
            "status": status,
        }
