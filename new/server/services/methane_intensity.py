"""Methane intensity: the NGSI protocol figure and the OGCI / OGMP volume figure, one implementation.

Blind audit BA-053 / BA-054: the dashboard, the Methane Intensity page and the master report each had their own
"methane intensity" (CH4 / all-gas mass at an assumed 0.92 kg/Sm3, CH4 volume / gross gas, CH4 / gas mass at
0.717 kg/m3). Two labelled figures now:

- NGSI (Natural Gas Sustainability Initiative Methane Emissions Intensity Protocol v1.0, Feb 2021 / v3.0):
  CH4 emitted / CH4 contained in the segment throughput, on a mass basis with a methane density of
  0.0192 t per Mcf (40 CFR 98.233(v)); default CH4 content of the throughput 83.3 % (production, gathering),
  87 % (processing), 93.4 % (transmission and storage). Segment values are not additive.
- OGCI / OGMP volume basis (the 0.20 % target): CH4 volume emitted / marketed gas volume.

Marketed gas = gross production - reinjected - flared - vented - burned on site - NGL shrinkage. Each term comes
from the production data when entered there, else from the emission records (flaring records and FlaringDetail
streams, venting records entered as a gas volume, natural-gas combustion records); shrinkage only from the
production data.
"""
from calculations.units import CONVERSIONS

NGSI_CH4_T_PER_MCF = 0.0192
M3_PER_MCF = 28.316846592
CH4_DENSITY_KG_M3 = CONVERSIONS["density_ch4"]

# NGSI default methane content of the throughput by segment (production / gathering, processing, T&S)
NGSI_DEFAULT_CH4_CONTENT = {"upstream": 0.833, "midstream": 0.87, "downstream": 0.934,
                            "production": 0.833, "gathering_boosting": 0.833, "processing": 0.87,
                            "transmission_storage": 0.934, "distribution": 0.934}
# NGSI v3.0 production segment: the gas ratio allocates the CH4 between gas and liquids on energy, with 1.235 MMBtu
# per Mcf of raw gas and 5.8 MMBtu per bbl of crude / condensate (API Compendium Table 3-8 defaults)
NGSI_GAS_MMBTU_PER_MCF = 1.235
NGSI_LIQ_MMBTU_PER_BBL = 5.8


def ngsi_segment(segment, activity=None):
    """The NGSI segment of a facility from its segment and activity text. Gathering, transmission, storage and
    pipelines were all "midstream" at 87 %: NGSI gives 83.3 % to gathering & boosting and 93.4 % to transmission &
    storage (audit 2026-11 F-AGG-05)."""
    text = f"{segment or ''} {activity or ''}".lower()
    if any(k in text for k in ("gathering", "boosting")):
        return "gathering_boosting"
    if any(k in text for k in ("transmission", "storage", "pipeline", "transport")):
        return "transmission_storage"
    if "distribution" in text:
        return "distribution"
    if any(k in text for k in ("processing", "treatment", "lng", "gnl", "midstream")):
        return "processing"
    if any(k in text for k in ("downstream", "refin", "petrochem")):
        return "distribution"
    if any(k in text for k in ("upstream", "production", "exploration", "e&p", "amont")):
        return "production"
    return None


def gas_ratio(segment, gas_m3, liquids_bbl, hhv_btu_scf=None):
    """NGSI gas ratio E_ng / (E_ng + E_liq) for the production segment; 1 for the other segments (all gas) or without
    liquids. It was never applied: an oil-weighted asset showed ~2.8 x its NGSI intensity (F-AGG-05). The gas energy
    uses the facility's own HHV when it is entered, else NGSI's 1.235 MMBtu/Mcf (D7, GB RY2022 GB-004)."""
    if segment != "production" or not liquids_bbl or liquids_bbl <= 0 or not gas_m3 or gas_m3 <= 0:
        return 1.0
    mmbtu_per_mcf = float(hhv_btu_scf) / 1000.0 if hhv_btu_scf not in (None, "") and float(hhv_btu_scf) > 0         else NGSI_GAS_MMBTU_PER_MCF
    e_ng = gas_m3 / M3_PER_MCF * mmbtu_per_mcf
    return e_ng / (e_ng + float(liquids_bbl) * NGSI_LIQ_MMBTU_PER_BBL)

MARKETED_TERMS = ("flared", "vented", "fuel", "shrinkage")
PRODUCTION_COLUMNS = {"flared": "flared_gas_mmsm3", "vented": "vented_gas_mmsm3", "fuel": "fuel_gas_consumed_mmsm3",
                      "shrinkage": "ngl_shrinkage_mmsm3"}


def ngsi_ch4_content(segment_cat, analysed=None):
    """CH4 content (fraction) of the throughput: a gas analysis when given, else the NGSI segment default."""
    if analysed not in (None, "") and 0 < float(analysed) <= 1:
        return float(analysed)
    return NGSI_DEFAULT_CH4_CONTENT.get(segment_cat or "upstream", NGSI_DEFAULT_CH4_CONTENT["upstream"])


def facility_gas(fac):
    """(CH4 content as a fraction, HHV in Btu/scf) entered for a facility's gas, each None when not entered (D7)."""
    c = getattr(fac, "gas_ch4_mol_pct", None) if fac is not None else None
    h = getattr(fac, "gas_hhv_btu_scf", None) if fac is not None else None
    c = float(c) / 100.0 if c not in (None, "") and 0 < float(c) <= 100 else None
    h = float(h) if h not in (None, "") and float(h) > 0 else None
    return c, h


def ngsi_intensity_pct(ch4_t, throughput_m3, ch4_content, ratio=1.0):
    """NGSI methane emissions intensity (%) = CH4 x gas ratio / (throughput x CH4 content x 0.0192 t/Mcf), or None."""
    if not throughput_m3 or throughput_m3 <= 0 or not ch4_content:
        return None
    ch4_in_throughput_t = throughput_m3 / M3_PER_MCF * ch4_content * NGSI_CH4_T_PER_MCF
    return float(ch4_t or 0.0) * float(ratio) / ch4_in_throughput_t * 100.0


def volume_intensity_pct(ch4_t, marketed_m3):
    """OGCI / OGMP methane intensity (%): CH4 volume emitted / marketed gas volume, or None."""
    if not marketed_m3 or marketed_m3 <= 0:
        return None
    return float(ch4_t or 0.0) * 1000.0 / CH4_DENSITY_KG_M3 / marketed_m3 * 100.0


def marketed_gas(gross_net_m3, production_terms, record_terms):
    """(marketed m3, basis) from the gas net of reinjection and the four deductions.

    production_terms / record_terms: {term: m3 or None}; a production value (entered) takes priority."""
    used, basis = {}, {}
    for t in MARKETED_TERMS:
        p = (production_terms or {}).get(t)
        if p is not None:
            used[t], basis[t] = float(p), "production data"
        else:
            r = (record_terms or {}).get(t)
            used[t], basis[t] = (float(r), "emission records") if r else (0.0, "not recorded")
    marketed = max(float(gross_net_m3 or 0.0) - sum(used.values()), 0.0)
    return marketed, {"deductions_m3": used, "sources": basis}


def ngsi_parts(matched, seg_cat, fac=None):
    """(CH4 x gas ratio, CH4 contained in the throughput), tonnes, of a facility's matched years: the NGSI numerator
    and denominator, so a page summing facilities gives the same figure as each facility (GB RY2022 GB-061). The
    facility's own gas CH4 content and HHV when entered (D7), else the NGSI defaults."""
    gas_m3 = matched["gas_m3"]
    if not gas_m3 or gas_m3 <= 0:
        return 0.0, 0.0
    seg = ngsi_segment(fac.segment, fac.activity) if fac is not None else seg_cat
    own_c1, own_hhv = facility_gas(fac)
    den = gas_m3 / M3_PER_MCF * ngsi_ch4_content(seg, own_c1) * NGSI_CH4_T_PER_MCF
    num = float(matched["ch4"] or 0.0) * gas_ratio(seg, gas_m3, matched.get("oil_bbl"), own_hhv)
    return num, den


def ngsi_fields(matched, seg_cat, fac=None):
    """The NGSI inputs a facility row reports: the CH4 content used and where it came from, numerator, denominator."""
    own = facility_gas(fac)[0]
    num, den = ngsi_parts(matched, seg_cat, fac)
    return {"ngsi_ch4_content": ngsi_ch4_content(seg_cat, own),
            "ngsi_ch4_content_source": "facility gas" if own is not None else "NGSI segment default",
            "ngsi_numerator_t": num, "ngsi_denominator_t": den}
