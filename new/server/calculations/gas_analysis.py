"""A gas analysis (mol %) read from a record's inputs, as mole fractions.

Moved out of CalculationDispatcher._composition (BUG-023: one percent / fraction decision for the whole analysis).

An analysis of two or more components must total 100 % (99.5 to 100.5 is rounding, see units.composition_fractions).
The short form is not an analysis: a CH4 content (``ch4_content`` / ``flare_ch4_content``) with an optional CO2 content
(``co2_content``) and nothing else is a pair of contents, the rest of the gas is not described, so its total is not
checked. Any C2..C10, N2, H2S, ``co2_mol`` / ``co2_comp`` or ``c1`` key makes it an analysis.
"""
from .units import composition_fractions


def _given(inputs, key):
    return inputs.get(key) not in (None, "", "-")


def composition(flat_inputs, c1_keys=("c1",)):
    raw, c1_key = {}, None
    for k in c1_keys:
        if _given(flat_inputs, k):
            raw["c1"], c1_key = flat_inputs.get(k), k
            break
    for i in range(2, 11):
        if _given(flat_inputs, f"c{i}"):
            raw[f"c{i}"] = flat_inputs.get(f"c{i}")
    # N2 / H2S under any of their keys: a dropped inert made a 98.4 % analysis renormalise to 100 %
    # and inflated the hydrocarbons by 1.6 % (Exhibit 4.4a)
    co2_key = None
    for key, names in (("co2", ("co2_mol", "co2_content", "co2_comp")),
                       ("n2", ("n2", "n2_mol", "n2_comp", "n2_content", "n2_mole_pct")),
                       ("h2s", ("h2s", "h2s_mol", "h2s_content"))):
        for n in names:
            if _given(flat_inputs, n):
                raw[key] = flat_inputs.get(n)
                co2_key = n if key == "co2" else co2_key
                break
    basis = str(flat_inputs.get("composition_basis") or "").lower() or None
    short_form = (c1_key not in (None, "c1") and set(raw) <= {"c1", "co2"} and co2_key in (None, "co2_content"))
    fr, _info = composition_fractions(
        raw, basis={"mol%": "percent", "percent": "percent", "fraction": "fraction"}.get(basis) if basis else None,
        check_total=not short_form)
    comps = {f"c{i}": fr.get(f"c{i}", 0.0) for i in range(1, 11)}
    comps["co2_comp"] = fr.get("co2", 0.0)
    comps["n2_comp"] = fr.get("n2", 0.0)
    return comps
