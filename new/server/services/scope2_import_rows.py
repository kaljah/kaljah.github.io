"""Parts of a Scope 2 file row that follow the manual form's rules (moved out of background_processor._process_row_scope2).

Each helper returns its value(s) and an error text (None when the row is fine), the importer's row contract.
"""
from calculations.indirect import DEFAULT_TRANSMISSION_LOSS
from input_validation import ValidationError


def _bp():
    import background_processor

    return background_processor


def steam_row_trans_loss(row, row_idx):
    """(transmission loss as a fraction, error). The same rule as the form and the JSON API (audit 2026-11 F-S23-04:
    0.10 was 10 % there and 0.1 % here): trans_loss / transmission_loss is a fraction (0.10) or a "%" text; the
    trans_loss_pct column is percent."""
    bp = _bp()
    raw_pct = bp._first(row, "trans_loss_pct")
    raw_tl = raw_pct if raw_pct not in (None, "") else bp._first(row, "trans_loss", "transmission_loss")
    if raw_tl in (None, ""):
        return DEFAULT_TRANSMISSION_LOSS, None
    trans_loss = bp._clean_float(str(raw_tl).replace("%", ""), default=None)
    if trans_loss is None:
        return None, f"Row {row_idx}: transmission loss '{raw_tl}' is not a number (e.g. 0.10 or 10%)"
    if raw_pct not in (None, "") or "%" in str(raw_tl):
        trans_loss /= 100.0
    if not 0 <= trans_loss < 1.0:
        return None, f"Row {row_idx}: transmission loss is a fraction from 0 to below 1, e.g. 0.10 or 10% (got {raw_tl})"
    return trans_loss, None


def chp_row(row, row_idx):
    """(co2e t, heat bought MMBtu, error) of a CHP row. BUG-099 pattern: never book a client-supplied co2e; the
    plant's outputs allocate its emissions and the record books the share bought (audit 2026-11 F-S23-01)."""
    from services.scope2_chp import calc_cogen_allocation, chp_heat_bought

    clean = _bp()._clean_float
    cogen_in = {
        "total_emissions": row.get("total_emissions"),
        "fuel_consumed_mmbtu": row.get("fuel_consumed_mmbtu"),
        "heat_output_mmbtu": row.get("heat_output_mmbtu"),
        "power_output_mwh": row.get("power_output_mwh"),
        "allocation_method": row.get("allocation_method") or "wri_efficiency",
        "heat_efficiency": row.get("heat_efficiency"),
        "power_efficiency": row.get("power_efficiency"),
        "purchased_stream": row.get("purchased_stream") or "heat",
        "quantity_bought": row.get("quantity_bought") or row.get("heat_bought_mmbtu") or row.get("power_bought_mwh"),
    }
    if not clean(cogen_in["heat_output_mmbtu"], default=0.0) or not (
        clean(cogen_in["total_emissions"], default=0.0) or clean(cogen_in["fuel_consumed_mmbtu"], default=0.0)
    ):
        return None, None, f"Row {row_idx}: CHP rows need heat_output_mmbtu and total_emissions or fuel_consumed_mmbtu"
    data = {k: v for k, v in cogen_in.items() if v not in (None, "")}
    try:
        return calc_cogen_allocation(data), chp_heat_bought(data), None
    except ValidationError as exc:
        return None, None, f"Row {row_idx}: {exc}"


def cooling_row_factor(row, row_idx, grid_region, facility_id):
    """(kg CO2e per ton-hour, error): the factor column, else Equation 8-2 from the chiller COP and the row's grid
    (audit 2026-11 F-S23-12). A missing or unreadable factor is refused (bug hunt 2026-10-15 #13)."""
    clean = _bp()._clean_float
    supplied_ef = row.get("factor") if row.get("factor") not in (None, "") else row.get("emission_factor")
    ef = clean(supplied_ef, default=None)
    if supplied_ef in (None, "") and row.get("cooling_cop") not in (None, ""):
        from services.scope2_policy import cooling_factor_from_cop

        try:
            ef = cooling_factor_from_cop(clean(row.get("cooling_cop"), default=None), grid_region, facility_id)[0]
        except ValidationError as exc:
            return None, f"Row {row_idx}: {exc.message}"
    if ef is None or ef < 0:
        return None, (f"Row {row_idx}: cooling needs its emission factor in kg CO2e per ton-hour, or the chiller COP "
                      "(cooling_cop) and grid_region "
                      f"(factor column; got '{supplied_ef if supplied_ef is not None else ''}')")
    return ef, None
